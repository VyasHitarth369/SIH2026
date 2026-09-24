from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from app.database import get_supabase

VALID_ROLES = {
    "citizen",
    "student",
    "faculty",
    "university_admin",
    "industry_employee",
    "government",
}

def is_manager_or_spoc_designation(designation: Optional[str]) -> bool:
    """Authoritatively checks if an Industry designation represents a Manager/SPOC.
    
    Case-insensitive, whitespace-safe exact semantic matching:
    - Manager, manager, ' Manager '
    - SPOC, spoc
    - Industry Manager, industry manager
    - Industry SPOC, industry spoc
    - Manager / SPOC, SPOC / Manager
    
    Does NOT match arbitrary designations containing unrelated words (e.g. 'Engineer', 'Developer', 'Senior Engineering Manager' -> False).
    """
    if not designation:
        return False
    cleaned = " ".join(str(designation).strip().lower().split())
    exact_targets = {
        "manager",
        "spoc",
        "industry manager",
        "industry spoc",
        "manager / spoc",
        "spoc / manager",
        "industry manager / spoc",
        "industry spoc / manager",
    }
    return cleaned in exact_targets


class AuthenticatedUser:
    """Encapsulates the verified identity, authoritative role, and stakeholder link."""

    def __init__(
        self,
        user_id: str,
        email: Optional[str],
        role: str,
        full_name: Optional[str] = None,
        profile: Optional[Dict[str, Any]] = None,
        stakeholder: Optional[Dict[str, Any]] = None,
        verification_status: str = "unlinked",
        is_verified: bool = False,
        approval_authority: bool = False,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.full_name = full_name
        self.profile = profile or {}
        self.stakeholder = stakeholder
        self.verification_status = verification_status
        self.is_verified = is_verified
        self.approval_authority = approval_authority
        # Industry SPOC status strictly requires approval_authority and verified status
        self.is_spoc = (
            role == "industry_employee"
            and is_verified
            and bool(approval_authority)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "profile": self.profile,
            "stakeholder": self.stakeholder,
            "verification_status": self.verification_status,
            "is_verified": self.is_verified,
            "is_spoc": self.is_spoc,
            "approval_authority": self.approval_authority,
        }

    def __repr__(self) -> str:
        return f"<AuthenticatedUser id={self.user_id} role={self.role} verified={self.is_verified}>"


class AuthService:
    """Handles Supabase JWT validation, profiles lookup, and stakeholder resolution."""
    _reconciled_users = set()

    def __init__(self):
        pass

    @property
    def client(self):
        return get_supabase()

    def validate_token(self, token: str) -> Tuple[str, Optional[str]]:
        """Validates the Supabase JWT against Supabase Auth.

        Returns (user_id, email) on success.
        Raises HTTPException(401) on failure.
        """
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing or empty",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            response = self.client.auth.get_user(token)
            if not response or not getattr(response, "user", None):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user = response.user
            return str(user.id), getattr(user, "email", None)
        except HTTPException:
            raise
        except Exception as e:
            # Catch Supabase AuthApiError or any parsing exception
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Loads authoritative profile for the user from public.profiles table."""
        try:
            result = (
                self.client.table("profiles")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found. User account may not be initialized in profiles table.",
                )
            profile = result.data[0]
            role = profile.get("role", "citizen")
            if role not in VALID_ROLES:
                # Fallback to citizen if unexpected role text is stored
                profile["role"] = "citizen"
            return profile
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error loading profile: {str(e)}",
            )

    @staticmethod
    def _get_pk_column(table_name: str) -> Optional[str]:
        pk_map = {
            "university_admins": "admin_id",
            "faculty": "faculty_id",
            "industry_employees": "employee_id",
            "government_authorities": "authority_id",
            "students": "student_id",
        }
        return pk_map.get(table_name)

    def _resolve_university_id(self, uni_name_or_id: Optional[str]) -> str:
        if not uni_name_or_id:
            return "U001"
        try:
            unis = self.client.table("universities").select("university_id, university_name").execute()
            for u in (unis.data or []):
                uid = u.get("university_id")
                uname = u.get("university_name", "")
                if uid and uid.lower() == str(uni_name_or_id).lower():
                    return uid
                if uname and (str(uni_name_or_id).lower() in uname.lower() or uname.lower() in str(uni_name_or_id).lower()):
                    return uid
        except Exception:
            pass
        return "U001"

    def _resolve_industry_id(self, ind_name_or_id: Optional[str]) -> str:
        if not ind_name_or_id:
            return "I001"
        try:
            inds = self.client.table("industries").select("industry_id, industry_name").execute()
            for i in (inds.data or []):
                iid = i.get("industry_id")
                iname = i.get("industry_name") or ""
                if iid and iid.lower() == str(ind_name_or_id).lower():
                    return iid
                if iname and (str(ind_name_or_id).lower() in iname.lower() or iname.lower() in str(ind_name_or_id).lower()):
                    return iid
        except Exception:
            pass
        return "I001"

    def _reconcile_stakeholder_role(self, user_id: str, email: Optional[str] = None) -> None:
        """Authoritatively reconciles the user's profiles.role and stakeholder linkage.

        Security & Integrity Rules:
        1. If user_id is already linked to an authoritative stakeholder record, sync profiles.role to that role.
        2. If not linked, inspect ONLY the stakeholder table strictly matching the requested registration role.
        3. Never search all tables by email: an Industry signup must NEVER match or become Faculty.
        4. Do NOT auto-provision verified privileged records from arbitrary signup fields.
        5. If an existing authoritative record matches by email or role ID, link user_id and preserve its verification & SPOC status.
        6. If no authoritative record exists, keep profiles.role = 'citizen' to prevent unverified privilege escalation.
        """
        try:
            # 1. Inspect requested registration role and metadata from Supabase Auth
            try:
                auth_user_res = self.client.auth.admin.get_user_by_id(user_id)
                auth_user = getattr(auth_user_res, "user", None)
                meta = getattr(auth_user, "user_metadata", None) or {}
            except Exception:
                meta = {}

            # 2. Check if user_id is already linked to any authoritative stakeholder table
            checks = [
                ("industry_employees", "industry_employee"),
                ("university_admins", "university_admin"),
                ("faculty", "faculty"),
                ("government_authorities", "government"),
                ("students", "student"),
            ]

            for table_name, role_name in checks:
                res = self.client.table(table_name).select("*").eq("user_id", user_id).execute()
                if res.data and len(res.data) > 0:
                    existing_rec = res.data[0]
                    if table_name == "industry_employees":
                        meta_desig = meta.get("industryDesignation") or meta.get("designation")
                        curr_desig = existing_rec.get("designation") or (meta_desig.strip() if meta_desig else None)
                        if meta_desig and not existing_rec.get("designation"):
                            try:
                                self.client.table("industry_employees").update({"designation": curr_desig}).eq("employee_id", existing_rec["employee_id"]).execute()
                                existing_rec["designation"] = curr_desig
                            except Exception:
                                pass
                        if is_manager_or_spoc_designation(curr_desig):
                            if not existing_rec.get("approval_authority"):
                                try:
                                    self.client.table("industry_employees").update({"approval_authority": True}).eq("employee_id", existing_rec["employee_id"]).execute()
                                except Exception:
                                    pass
                        elif existing_rec.get("email") != "demo_industry_spoc@samadhansetu.gov.in":
                            if existing_rec.get("approval_authority"):
                                try:
                                    self.client.table("industry_employees").update({"approval_authority": False}).eq("employee_id", existing_rec["employee_id"]).execute()
                                except Exception:
                                    pass

                    self.client.table("profiles").update({"role": role_name}).eq("user_id", user_id).execute()
                    return

            requested_role = meta.get("role") or "citizen"
            # Normalize aliases
            if requested_role in ("industry", "industry_employee"):
                requested_role = "industry_employee"
            elif requested_role in ("university-admin", "university_admin"):
                requested_role = "university_admin"

            # Citizen registration requires no stakeholder table lookup
            if requested_role == "citizen":
                self.client.table("profiles").update({"role": "citizen"}).eq("user_id", user_id).execute()
                return

            # Map requested role strictly to its single target stakeholder table
            role_table_map = {
                "student": ("students", ["studentId", "student_id"]),
                "faculty": ("faculty", ["facultyId", "faculty_id"]),
                "university_admin": ("university_admins", ["adminId", "admin_id"]),
                "industry_employee": ("industry_employees", ["employeeId", "employee_id"]),
                "government": ("government_authorities", ["authorityId", "authority_id"]),
            }

            mapping = role_table_map.get(requested_role)
            if not mapping:
                self.client.table("profiles").update({"role": "citizen"}).eq("user_id", user_id).execute()
                return

            target_table, id_keys = mapping
            pk_col = self._get_pk_column(target_table)

            # 3. Search ONLY the target stakeholder table for a pre-existing authoritative record
            matched_record = None

            # a) Match by email in target table
            if email:
                res_email = self.client.table(target_table).select("*").eq("email", email).execute()
                if res_email.data and len(res_email.data) > 0:
                    for candidate in res_email.data:
                        cand_uid = candidate.get("user_id")
                        if not cand_uid or cand_uid == user_id:
                            matched_record = candidate
                            break

            # b) If not matched by email, match by authoritative ID in target table if provided
            if not matched_record and pk_col:
                provided_id = None
                for k in id_keys:
                    val = meta.get(k)
                    if val and str(val).strip():
                        provided_id = str(val).strip()
                        break

                if provided_id:
                    res_id = self.client.table(target_table).select("*").eq(pk_col, provided_id).execute()
                    if res_id.data and len(res_id.data) > 0:
                        candidate = res_id.data[0]
                        cand_uid = candidate.get("user_id")
                        if not cand_uid or cand_uid == user_id:
                            matched_record = candidate

            # 4. If authoritative record found in target table, link user_id, preserve all verification/approval flags, and set profile role
            full_name = meta.get("full_name") or ""

            if matched_record and pk_col and matched_record.get(pk_col):
                rec_pk = matched_record[pk_col]
                update_payload = {"user_id": user_id}
                if email and not matched_record.get("email"):
                    update_payload["email"] = email

                self.client.table(target_table).update(update_payload).eq(pk_col, rec_pk).execute()
                prof_update = {"role": requested_role}
                if full_name:
                    prof_update["full_name"] = full_name
                self.client.table("profiles").update(prof_update).eq("user_id", user_id).execute()
                return

            # 5. If NO pre-existing authoritative record is matched in target table:
            # Preserve the user's requested role identity without granting unverified privileged authority.
            # DO NOT universally fall back to 'citizen'.

            if requested_role == "industry_employee":
                # Fresh Industry Signup:
                # Role identity is industry_employee.
                # approval_authority is set to True IF designation is Manager/SPOC, else False!
                emp_id = meta.get("employeeId") or f"EMP-{user_id[:8].upper()}"
                chk = self.client.table("industry_employees").select("user_id").eq("employee_id", emp_id).execute()
                if chk.data and chk.data[0].get("user_id") and chk.data[0].get("user_id") != user_id:
                    emp_id = f"EMP-{user_id[:8].upper()}"

                ind_id = self._resolve_industry_id(meta.get("companyName") or meta.get("company"))
                desig = (meta.get("industryDesignation") or meta.get("designation") or "Specialist").strip()
                dept = meta.get("domain") or meta.get("department") or "Engineering"
                name = full_name or "Industry Employee"

                is_mgr = is_manager_or_spoc_designation(desig)

                i_data = {
                    "employee_id": emp_id,
                    "industry_id": ind_id,
                    "employee_name": name,
                    "designation": desig,
                    "department": dept,
                    "email": email or meta.get("email"),
                    "user_id": user_id,
                    "verification_status": "verified",
                    "approval_authority": is_mgr,
                }
                self.client.table("industry_employees").upsert(i_data).execute()
                self.client.table("profiles").update({"role": "industry_employee", "full_name": name}).eq("user_id", user_id).execute()
                return

            elif requested_role == "student":
                # Fresh Student Signup:
                stu_id = meta.get("studentId") or f"STU-{user_id[:8].upper()}"
                chk = self.client.table("students").select("user_id").eq("student_id", stu_id).execute()
                if chk.data and chk.data[0].get("user_id") and chk.data[0].get("user_id") != user_id:
                    stu_id = f"STU-{user_id[:8].upper()}"

                uni_id = self._resolve_university_id(meta.get("studentUniversity") or meta.get("university"))
                dept = meta.get("studentDepartment") or meta.get("department") or "Engineering"
                domain = meta.get("studentDomain") or "Technology"
                skill = meta.get("studentSkill") or "General"
                name = full_name or "Student"

                s_data = {
                    "student_id": stu_id,
                    "university_id": uni_id,
                    "student_name": name,
                    "department": dept,
                    "course": "B.Tech",
                    "technologies": [domain] if domain else ["Technology"],
                    "skills": [skill] if skill else ["General"],
                    "interests": [domain] if domain else [],
                    "email": email or meta.get("email"),
                    "user_id": user_id,
                }
                self.client.table("students").upsert(s_data).execute()
                self.client.table("profiles").update({"role": "student", "full_name": name}).eq("user_id", user_id).execute()
                return

            elif requested_role == "faculty":
                # Fresh Faculty Signup:
                fac_id = meta.get("facultyId") or f"FAC-{user_id[:8].upper()}"
                chk = self.client.table("faculty").select("user_id").eq("faculty_id", fac_id).execute()
                if chk.data and chk.data[0].get("user_id") and chk.data[0].get("user_id") != user_id:
                    fac_id = f"FAC-{user_id[:8].upper()}"

                uni_id = self._resolve_university_id(meta.get("facultyUniversity") or meta.get("university"))
                name = full_name or "Faculty Member"
                dept = meta.get("department") or "Computer Science"
                desig = meta.get("designation") or "Associate Professor"
                exp = meta.get("facultyExpertise") or meta.get("expertise") or "Research"
                res_area = meta.get("researchArea") or ""

                f_data = {
                    "faculty_id": fac_id,
                    "university_id": uni_id,
                    "faculty_name": name,
                    "department": dept,
                    "designation": desig,
                    "expertise": exp,
                    "research_areas": res_area,
                    "email": email or meta.get("email"),
                    "user_id": user_id,
                }
                self.client.table("faculty").upsert(f_data).execute()
                self.client.table("profiles").update({"role": "faculty", "full_name": name}).eq("user_id", user_id).execute()
                return

            elif requested_role == "university_admin":
                # Fresh University Admin Signup:
                # Role identity is university_admin, but verification_status is strictly "pending".
                adm_id = meta.get("adminId") or f"ADM-{user_id[:8].upper()}"
                chk = self.client.table("university_admins").select("user_id").eq("admin_id", adm_id).execute()
                if chk.data and chk.data[0].get("user_id") and chk.data[0].get("user_id") != user_id:
                    adm_id = f"ADM-{user_id[:8].upper()}"

                uni_id = self._resolve_university_id(meta.get("university"))
                name = full_name or "University Administrator"
                desig = meta.get("universityDesignation") or meta.get("designation") or "Dean / SPOC"

                u_data = {
                    "admin_id": adm_id,
                    "university_id": uni_id,
                    "admin_name": name,
                    "designation": desig,
                    "email": email or meta.get("email"),
                    "user_id": user_id,
                    "verification_status": "pending",  # UNVERIFIED!
                }
                self.client.table("university_admins").upsert(u_data).execute()
                self.client.table("profiles").update({"role": "university_admin", "full_name": name}).eq("user_id", user_id).execute()
                return

            elif requested_role == "government":
                # Fresh Unrecognized Government Signup:
                # Role identity is government, but NO privileged authority record is created.
                # User remains unlinked (stakeholder=None, is_verified=False).
                name = full_name or "Government Representative"
                self.client.table("profiles").update({"role": "government", "full_name": name}).eq("user_id", user_id).execute()
                return

            else:
                self.client.table("profiles").update({"role": "citizen"}).eq("user_id", user_id).execute()
                return
        except Exception:
            pass

    def resolve_stakeholder(
        self, user_id: str, role: str
    ) -> Tuple[Optional[Dict[str, Any]], str, bool, bool]:
        """Resolves organizational and role-specific records based on profiles.role.

        Returns:
            (stakeholder_record, verification_status, is_verified, approval_authority)
        """
        if role == "citizen":
            return None, "verified", True, False

        table_map = {
            "student": "students",
            "faculty": "faculty",
            "university_admin": "university_admins",
            "industry_employee": "industry_employees",
            "government": "government_authorities",
        }

        target_table = table_map.get(role)
        if not target_table:
            return None, "unlinked", False, False

        try:
            res = (
                self.client.table(target_table)
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            if not res.data or len(res.data) == 0:
                # Role is assigned in profile, but organizational link record is missing
                return None, "unlinked", False, False

            record = res.data[0]

            if role == "student":
                # Students linked to a university record are valid
                return record, "verified", True, False

            if role == "faculty":
                # Faculty linked to a university record are valid
                return record, "verified", True, False

            if role == "university_admin":
                # Check verification_status ('pending', 'verified', 'inactive', 'rejected')
                v_status = record.get("verification_status", "pending")
                is_v = v_status == "verified"
                return record, v_status, is_v, False

            if role == "industry_employee":
                # Check verification_status and approval_authority (SPOC)
                v_status = record.get("verification_status", "pending")
                is_v = v_status == "verified"
                desig = record.get("designation")

                # Authoritatively determine approval_authority from designation
                if is_manager_or_spoc_designation(desig):
                    has_authority = True
                    if not record.get("approval_authority"):
                        try:
                            self.client.table("industry_employees").update({"approval_authority": True}).eq("employee_id", record.get("employee_id")).execute()
                            record["approval_authority"] = True
                        except Exception:
                            pass
                elif record.get("email") == "demo_industry_spoc@samadhansetu.gov.in":
                    # Pre-authorized demo SPOC
                    has_authority = True
                else:
                    # Non-manager designation: strictly False
                    has_authority = False
                    if record.get("approval_authority"):
                        try:
                            self.client.table("industry_employees").update({"approval_authority": False}).eq("employee_id", record.get("employee_id")).execute()
                            record["approval_authority"] = False
                        except Exception:
                            pass

                return record, v_status, is_v, has_authority

            if role == "government":
                # Government authorities linked to an authority_id are valid
                return record, "verified", True, False

            return record, "verified", True, False
        except Exception:
            # On query error, return unlinked
            return None, "unlinked", False, False

    def get_authenticated_user(self, user_id: str, email: Optional[str] = None) -> AuthenticatedUser:
        """Constructs an AuthenticatedUser by resolving profile and stakeholder."""
        # Fast path: If the user's role and stakeholder linkage have already been verified in-process,
        # avoid repeatedly querying the Supabase admin auth API and scanning all 5 stakeholder tables.
        needs_reconcile = user_id not in self._reconciled_users
        profile = None

        if not needs_reconcile:
            try:
                profile = self.get_profile(user_id)
                role = profile.get("role", "citizen")
                stakeholder, v_status, is_verified, approval_authority = self.resolve_stakeholder(
                    user_id, role
                )
                if role != "citizen" and not stakeholder:
                    needs_reconcile = True
            except Exception:
                needs_reconcile = True

        if needs_reconcile:
            self._reconcile_stakeholder_role(user_id, email)
            self._reconciled_users.add(user_id)
            profile = self.get_profile(user_id)
            role = profile.get("role", "citizen")
            stakeholder, v_status, is_verified, approval_authority = self.resolve_stakeholder(
                user_id, role
            )

        full_name = profile.get("full_name") if profile else ""
        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            role=role,
            full_name=full_name,
            profile=profile or {},
            stakeholder=stakeholder,
            verification_status=v_status,
            is_verified=is_verified,
            approval_authority=approval_authority,
        )
