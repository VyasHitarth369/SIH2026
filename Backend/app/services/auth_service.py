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
        """Ensures that users linked to stakeholder records or registered with a specific
        stakeholder role have their profiles.role and stakeholder tables synchronized.
        Preserves profiles.role as authoritative while preventing desync between
        Supabase Auth registration metadata and public.profiles.
        """
        try:
            # 1. Check if user already exists in any stakeholder table (by user_id or email)
            checks = [
                ("university_admins", "university_admin"),
                ("faculty", "faculty"),
                ("industry_employees", "industry_employee"),
                ("government_authorities", "government"),
                ("students", "student"),
            ]

            for table_name, role_name in checks:
                # Check by user_id
                res = self.client.table(table_name).select("*").eq("user_id", user_id).execute()
                if res.data and len(res.data) > 0:
                    self.client.table("profiles").update({"role": role_name}).eq("user_id", user_id).execute()
                    return

                # If not found by user_id, check by email if available
                if email:
                    res_email = self.client.table(table_name).select("*").eq("email", email).execute()
                    if res_email.data and len(res_email.data) > 0:
                        rec = res_email.data[0]
                        if not rec.get("user_id") or rec.get("user_id") != user_id:
                            pk_col = self._get_pk_column(table_name)
                            if pk_col and rec.get(pk_col):
                                self.client.table(table_name).update({"user_id": user_id}).eq(pk_col, rec[pk_col]).execute()
                        self.client.table("profiles").update({"role": role_name}).eq("user_id", user_id).execute()
                        return

            # 2. Privileged roles MUST NOT be auto-provisioned from user_metadata.role.
            # Authoritative stakeholder assignment strictly requires an existing verified
            # record in stakeholder tables (linked above via user_id or email).
            # Registration metadata captures user signup preferences only.
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
                has_authority = bool(record.get("approval_authority", False))
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
        # Reconcile stakeholder record and profile role if necessary
        self._reconcile_stakeholder_role(user_id, email)

        profile = self.get_profile(user_id)
        role = profile.get("role", "citizen")
        full_name = profile.get("full_name")

        stakeholder, v_status, is_verified, approval_authority = self.resolve_stakeholder(
            user_id, role
        )

        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            role=role,
            full_name=full_name,
            profile=profile,
            stakeholder=stakeholder,
            verification_status=v_status,
            is_verified=is_verified,
            approval_authority=approval_authority,
        )
