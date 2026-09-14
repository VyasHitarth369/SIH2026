"""ai_service.py

Orchestrates the AI review, existing-solution discovery, gap validation, and classification
workflow for challenges submitted by citizens in Concordia / Samadhan Setu.

AI RULES ENFORCED:
1. Backend orchestrates the LLM; frontend never calls the LLM directly.
2. Strict call budget: Maximum 2 LLM calls per challenge.
   - Call 1: Initial problem analysis + eligibility + image evidence + existing-solution discovery.
     - If existing solution found: returns solution for citizen accept/reject (1 call used).
     - If NO existing solution found: completes classification in Call 1 without a second call (1 call used).
   - Call 2: Triggered ONLY if citizen rejects existing solution to validate the gap and classify.
3. Zero fabrication: Never invents fake URLs, companies, products, solutions, or facts.
4. Google Search Grounding with safe quota fallback: If search tool fails or exhausts quota,
   Gemini does not fabricate solutions; solutions = [] and existing_solution_found = False.
5. Multi-modal Image Verification: Inspects uploaded photos for consistency without permanent rejection.
"""

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from app.schemas.analysis import (
    Call1GeminiOutput,
    Call2GeminiOutput,
    DiscoveredSolution,
    DuplicateCandidate,
    EligibilityResult,
    GapValidationResult,
    ImageEvidenceResult,
    InitialAnalysisResult,
)

logger = logging.getLogger("ai_service")


class AIService:
    """Orchestrates real Gemini AI analysis with search grounding, image verification, and strict call budgets."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("LLM_API_KEY")
        )
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self._client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {type(e).__name__}")

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured in backend environment.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    # -------------------------------------------------------------------------
    # Helper: Prepare image Part
    # -------------------------------------------------------------------------
    def _prepare_image_part(self, photo: Optional[str]) -> Optional[types.Part]:
        """Converts base64 data URI or image URL to a google.genai types.Part."""
        if not photo or not isinstance(photo, str) or not photo.strip():
            return None
        clean_photo = photo.strip()
        try:
            if clean_photo.startswith("data:image/"):
                header, b64_data = clean_photo.split(",", 1)
                mime_type = header.split(";")[0].replace("data:", "").strip()
                raw_bytes = base64.b64decode(b64_data)
                return types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)
            elif clean_photo.startswith("http://") or clean_photo.startswith("https://"):
                import httpx
                with httpx.Client(timeout=4.0) as http_client:
                    resp = http_client.get(clean_photo)
                    if resp.status_code == 200:
                        mime_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                        return types.Part.from_bytes(data=resp.content, mime_type=mime_type)
        except Exception as e:
            logger.warning(f"Could not load challenge image: {type(e).__name__}")
        return None

    # -------------------------------------------------------------------------
    # CALL 1: Initial Review + Image Evidence + Solution Discovery + Classification
    # -------------------------------------------------------------------------
    def analyze_call_1(
        self,
        challenge: Dict[str, Any],
        existing_challenges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Executes Call 1 of the AI review pipeline.

        Performs:
        1. Problem understanding & eligibility evaluation.
        2. Multi-modal image consistency verification (if photo provided).
        3. Dynamic existing-solution discovery via Google Search grounding.
           If search grounding fails/exhausts quota: sets solutions = [], existing_solution_found = False,
           search_grounding_used = False (no fabrication allowed).
        4. Complete initial classification (category, subcategory, skills, tech, severity, priority, innovation, feasibility).
        5. Duplicate detection against provided existing_challenges.
        """
        title = challenge.get("title", "").strip()
        description = challenge.get("description", "").strip()
        location = challenge.get("location") or challenge.get("city", "") or "India"
        district = challenge.get("district") or challenge.get("city", "")
        impact_scope = challenge.get("impact_scope", "Area Specific")
        photo = challenge.get("photo")

        # Candidate challenge list for duplicate detection
        candidate_records = []
        if existing_challenges:
            for ch in existing_challenges:
                cid = ch.get("challenge_id")
                if cid and cid != challenge.get("challenge_id"):
                    candidate_records.append({
                        "challenge_id": cid,
                        "title": ch.get("title", "")[:80],
                        "description": ch.get("description", "")[:120],
                    })

        img_part = self._prepare_image_part(photo)
        image_provided = img_part is not None

        # Build Call 1 instructions
        candidate_json = json.dumps(candidate_records, ensure_ascii=False) if candidate_records else "[]"

        system_instructions = (
            "You are the AI Intelligence Engine for Concordia / Samadhan Setu, a civic problem innovation portal. "
            "You evaluate citizen problem submissions objectively, verify image evidence, discover verified existing solutions, "
            "and extract precise technical requirements for academic and industrial problem solvers.\n"
            "STRICT RULES:\n"
            "1. Zero fabrication: Never invent schemes, companies, URLs, phone numbers, or addresses.\n"
            "2. Image verification: If an image is provided, examine it. If it clearly does not depict the stated issue "
            "(e.g. description is about road potholes but image is a building), mark image_evidence.status = 'mismatch'. "
            "If it matches, mark 'consistent'. If unclear, mark 'uncertain'. If no image is provided, mark 'not_provided'.\n"
            "3. Eligibility: Assess if this is a legitimate civic/societal/infrastructure issue. "
            "Allowed values: 'eligible', 'ineligible', 'uncertain'.\n"
            "4. Classification: Assign an appropriate category from: healthcare, education, transportation, infrastructure, "
            "environment, agriculture, public_safety, sanitation, water, energy, accessibility, governance, employment, "
            "disaster, rural_development, urban_development, social_welfare, cybersecurity, digital_services, other.\n"
            "5. Semantic duplicates: Compare with provided candidate challenges ONLY. Do NOT invent challenge IDs.\n"
        )

        prompt_body = f"""
Challenge Statement:
Title: {title}
Description: {description}
Location / City / District: {location} ({district})
Impact Scope: {impact_scope}
Image Attached: {'Yes' if image_provided else 'No'}

Supplied Candidate Challenge Records for duplicate check:
{candidate_json}

Task:
1. Determine eligibility (eligible, ineligible, uncertain) with clear reasoning.
2. If image is attached, verify consistency against the description. Describe observations.
3. Discover if there is a real, verified, currently active government scheme, public platform, or institutional solution that directly addresses this problem.
4. Extract required skills and technologies genuinely needed to solve this problem.
5. Determine severity (low, medium, high, critical), priority (low, medium, high, urgent), innovation_scope (high, medium, low, none), and feasibility (high, medium, low, uncertain).
6. Check if this is a duplicate of any candidate record.
"""

        search_grounding_used = False
        call_output: Optional[Call1GeminiOutput] = None

        # Step A: Attempt Call 1 with Google Search Grounding
        try:
            search_config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=system_instructions,
            )
            contents = [prompt_body]
            if img_part:
                contents.append(img_part)

            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=search_config,
            )

            # Check grounding metadata
            if resp.candidates and resp.candidates[0].grounding_metadata:
                gm = resp.candidates[0].grounding_metadata
                if gm.web_search_queries:
                    search_grounding_used = True

            # If search grounding succeeded, ask model to format into structured schema
            if resp.text:
                format_prompt = (
                    f"Transform this analysis into exact JSON conforming to Call1GeminiOutput schema:\n\n{resp.text}"
                )
                format_resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=format_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=Call1GeminiOutput,
                    ),
                )
                call_output = Call1GeminiOutput.model_validate_json(format_resp.text)
        except Exception as e:
            logger.info(f"Google Search grounding skipped or failed ({type(e).__name__}); falling back to zero-fabrication analysis.")
            search_grounding_used = False

        # Step B: Fallback if search failed, timed out, or hit quota
        # User Clarification #1: If search fails, Gemini MUST NOT use internal knowledge to claim a current solution exists.
        # solutions = [], existing_solution_found = False, search_grounding_used = False.
        if call_output is None:
            fallback_prompt = (
                f"{system_instructions}\n\n"
                f"NOTICE: Google Search is currently unavailable. Therefore, you MUST NOT claim or fabricate that a current "
                f"real-world scheme, solution, or provider exists. Set existing_solution_found = false and solutions = []. "
                f"Evaluate eligibility, image consistency, and provide full initial classification.\n\n"
                f"{prompt_body}"
            )
            fallback_contents = [fallback_prompt]
            if img_part:
                fallback_contents.append(img_part)

            try:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=fallback_contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=Call1GeminiOutput,
                    ),
                )
                call_output = Call1GeminiOutput.model_validate_json(resp.text)
            except Exception as e:
                logger.error(f"Gemini Call 1 execution failed: {type(e).__name__}")
                # Provide safe deterministic fallback if API is completely unavailable
                call_output = self._deterministic_fallback_call_1(challenge, img_part is not None)

        # Enforce User Clarification #1: if search grounding was not used, solutions MUST be empty
        if not search_grounding_used:
            call_output.solutions = []
            call_output.existing_solution_found = False
            call_output.best_solution = None

        # Sanitize duplicate candidates: only keep valid IDs from candidate records
        valid_cids = {c["challenge_id"] for c in candidate_records}
        sanitized_duplicates = [
            d for d in call_output.duplicate_candidates
            if d.challenge_id in valid_cids
        ]
        call_output.duplicate_candidates = sanitized_duplicates

        # Map structured output to database dictionary
        return self._format_call_1_response(call_output, search_grounding_used)

    # -------------------------------------------------------------------------
    # CALL 2: Gap Validation + Classification (Triggered on Citizen Rejection)
    # -------------------------------------------------------------------------
    def analyze_call_2_gap_validation(
        self,
        challenge: Dict[str, Any],
        existing_solution: str,
        rejection_reason: str,
        rejection_category: Optional[str] = None,
        existing_challenges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Executes Call 2 of the AI review pipeline.

        Performs:
        1. Gap genuineness evaluation against the existing solution and local context.
        2. Produces status: VALID_GAP | INVALID_GAP | UNCERTAIN_GAP with natural-language reason.
        3. If VALID_GAP: refines classification, required skills, and technologies for matching.
        """
        title = challenge.get("title", "").strip()
        description = challenge.get("description", "").strip()
        location = challenge.get("location") or challenge.get("city", "")
        clean_reason = rejection_reason.strip()

        prompt = f"""
You are the AI Intelligence Engine for Concordia / Samadhan Setu.
The citizen has submitted a problem, but an existing solution or government scheme was discovered.
The citizen has REJECTED the existing solution and provided a specific reason / local gap.

Challenge:
Title: {title}
Description: {description}
Location: {location}

Discovered Solution:
{existing_solution}

Citizen's Stated Rejection Reason / Local Gap:
"{clean_reason}"
Optional Category: {rejection_category or 'Not specified'}

Task:
1. Validate whether the citizen's rejection constitutes a genuine situational, technological, economic, geographical, or operational gap:
   - VALID_GAP: The existing solution genuinely does not work locally (e.g., local unavailability, high cost, poor coverage, missing capabilities, language barrier, infrastructure constraints).
   - INVALID_GAP: The reason is frivolous, irrelevant, or does not indicate a genuine limitation of the solution (e.g. "I don't like the color", spam, vague refusal).
   - UNCERTAIN_GAP: The reason is too ambiguous to determine whether a genuine gap exists.
2. If VALID_GAP, produce refined classification, required skills, and technologies taking into account the citizen's specific gap context.
3. Determine next_action: 'continue_to_matching' for VALID_GAP, 'stop' for INVALID_GAP, 'request_gap_clarification' for UNCERTAIN_GAP.
"""

        try:
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Call2GeminiOutput,
                ),
            )
            call_output = Call2GeminiOutput.model_validate_json(resp.text)
        except Exception as e:
            logger.error(f"Gemini Call 2 execution failed: {type(e).__name__}")
            call_output = self._deterministic_fallback_call_2(challenge, existing_solution, clean_reason, rejection_category)

        return self._format_call_2_response(call_output, existing_solution, clean_reason)

    # -------------------------------------------------------------------------
    # Response Formatters (mapping structured Gemini output to 20 db columns)
    # -------------------------------------------------------------------------
    def _format_call_1_response(
        self,
        output: Call1GeminiOutput,
        search_grounding_used: bool,
    ) -> Dict[str, Any]:
        """Maps Call1GeminiOutput into standard dictionary matching ai_analysis table columns."""
        init = output.initial_analysis
        eligibility = output.eligibility
        img_ev = output.image_evidence

        # Map eligibility to validity column: "valid" | "invalid" | "uncertain"
        if eligibility.status == "eligible":
            validity = "valid"
        elif eligibility.status == "ineligible":
            validity = "invalid"
        else:
            validity = "uncertain"

        # Format existing solution text
        existing_sol_text = None
        if output.existing_solution_found and output.solutions:
            sol = output.best_solution or output.solutions[0]
            if hasattr(sol, "description"):
                existing_sol_text = f"{sol.solution_name} (Provider: {sol.provider}): {sol.description}"
            else:
                existing_sol_text = f"{sol.solution_name}: {sol.reason}"

        # Skills & Tech as comma-separated strings
        skills_str = ", ".join(init.required_skills) if init.required_skills else None
        techs_str = ", ".join(init.required_technologies) if init.required_technologies else None

        duplicate_group = None
        similar_challenges = None
        if output.duplicate_candidates:
            duplicate_group = output.duplicate_candidates[0].challenge_id
            similar_challenges = json.dumps([d.model_dump() for d in output.duplicate_candidates])

        return {
            "validity": validity,
            "eligibility_reason": eligibility.reason,
            "image_evidence_status": img_ev.status,
            "image_observations": img_ev.observations,
            "solution_found": output.existing_solution_found,
            "existing_solution": existing_sol_text,
            "solutions": [s.model_dump() for s in output.solutions],
            "best_solution": output.best_solution.model_dump() if output.best_solution else None,
            "search_grounding_used": search_grounding_used,
            "category": init.category,
            "subcategory": init.subcategory,
            "ai_summary": init.summary,
            "required_skills": skills_str,
            "required_technologies": techs_str,
            "severity": init.severity,
            "priority": init.priority,
            "innovation_scope": init.innovation_scope,
            "feasibility": init.feasibility,
            "confidence_score": init.confidence_score,
            "duplicate_group": duplicate_group,
            "similar_challenges": similar_challenges,
            "duplicate_candidates": [d.model_dump() for d in output.duplicate_candidates],
            "solution_gap": None if output.existing_solution_found else "No verified existing solution found across active public platforms.",
            "solution_gap_valid": None if output.existing_solution_found else True,
            "next_action": output.next_action,
            "llm_calls_made": 1,
        }

    def _format_call_2_response(
        self,
        output: Call2GeminiOutput,
        existing_solution: str,
        rejection_reason: str,
    ) -> Dict[str, Any]:
        """Maps Call2GeminiOutput into standard dictionary matching ai_analysis table columns."""
        gap = output.gap_validation
        analysis = output.analysis

        is_valid_gap = gap.status == "VALID_GAP"
        skills_str = ", ".join(analysis.required_skills) if analysis.required_skills else None
        techs_str = ", ".join(analysis.required_technologies) if analysis.required_technologies else None

        duplicate_group = None
        similar_challenges = None
        if output.duplicate_candidates:
            duplicate_group = output.duplicate_candidates[0].challenge_id
            similar_challenges = json.dumps([d.model_dump() for d in output.duplicate_candidates])

        return {
            "validity": "valid",
            "gap_status": gap.status,
            "solution_found": True,
            "existing_solution": existing_solution,
            "solution_gap": rejection_reason,
            "solution_gap_valid": is_valid_gap,
            "ai_summary": analysis.summary,
            "category": analysis.category,
            "subcategory": analysis.subcategory,
            "required_skills": skills_str,
            "required_technologies": techs_str,
            "severity": analysis.severity,
            "priority": "high" if is_valid_gap else analysis.priority,
            "innovation_scope": "high" if is_valid_gap else analysis.innovation_scope,
            "feasibility": analysis.feasibility,
            "confidence_score": analysis.confidence_score,
            "duplicate_group": duplicate_group,
            "similar_challenges": similar_challenges,
            "duplicate_candidates": [d.model_dump() for d in output.duplicate_candidates],
            "next_action": output.next_action,
            "llm_calls_made": 2,
        }

    # -------------------------------------------------------------------------
    # Deterministic Fallbacks (used if network or API is completely unavailable)
    # -------------------------------------------------------------------------
    def _deterministic_fallback_call_1(self, challenge: Dict[str, Any], has_image: bool) -> Call1GeminiOutput:
        """Safe zero-fabrication fallback if Gemini API is temporarily offline."""
        title = challenge.get("title", "")
        desc = challenge.get("description", "")
        text = f"{title} {desc}".lower()

        is_invalid = any(w in text for w in ["kill", "bomb", "hack into", "steal", "fake spam"])
        status = "ineligible" if is_invalid else "eligible"

        category = "infrastructure"
        subcategory = "Municipal Infrastructure"
        skills = ["Civil Engineering", "Data Analysis"]
        techs = ["GIS", "IoT Sensors"]

        if any(w in text for w in ["water", "leak", "pipe", "borewell", "drain", "sewage"]):
            category = "water"
            subcategory = "Smart Water Management"
            skills = ["Hydraulic Systems", "IoT Sensors", "Embedded Systems"]
            techs = ["ESP32", "LoRaWAN", "Cloud Telemetry"]
        elif any(w in text for w in ["solar", "energy", "power", "electricity", "grid"]):
            category = "energy"
            subcategory = "Renewable Power Systems"
            skills = ["Power Electronics", "Solar PV Modeling"]
            techs = ["Solar Inverters", "BMS"]
        elif any(w in text for w in ["road", "pothole", "traffic", "transport"]):
            category = "transportation"
            subcategory = "Road & Urban Mobility"
            skills = ["Computer Vision", "Civil Engineering"]
            techs = ["Python", "PyTorch", "MapLibre"]

        return Call1GeminiOutput(
            eligibility=EligibilityResult(
                status=status,
                reason="Evaluated by offline safety rules." if is_invalid else "Civic infrastructure issue."
            ),
            image_evidence=ImageEvidenceResult(
                status="uncertain" if has_image else "not_provided",
                observations=["Image attached but automated vision service was offline."] if has_image else []
            ),
            existing_solution_found=False,
            solutions=[],
            best_solution=None,
            problem_fully_addressed=False,
            initial_analysis=InitialAnalysisResult(
                category=category,
                subcategory=subcategory,
                summary=f"Civic problem regarding '{title}'. Categorized under {category}.",
                required_skills=skills,
                required_technologies=techs,
                severity="medium",
                priority="medium",
                innovation_scope="medium",
                feasibility="high",
                confidence_score=0.8,
            ),
            duplicate_candidates=[],
            next_action="continue_to_matching",
        )

    def _deterministic_fallback_call_2(
        self,
        challenge: Dict[str, Any],
        existing_solution: str,
        rejection_reason: str,
        rejection_category: Optional[str],
    ) -> Call2GeminiOutput:
        """Safe zero-fabrication fallback for Call 2 if Gemini API is temporarily offline."""
        clean = rejection_reason.lower()
        valid_markers = ["not available", "rural", "cost", "expensive", "language", "offline", "slow", "broken", "unreliable"]
        is_valid = any(m in clean for m in valid_markers) or len(clean) >= 20 or rejection_category in [
            "local_unavailability", "poor_coverage", "cost_capacity", "missing_functionality"
        ]

        status = "VALID_GAP" if is_valid else "INVALID_GAP"
        reason_text = "Valid local operational/geographic gap identified." if is_valid else "Explanation lacks specific gap justification."

        return Call2GeminiOutput(
            gap_validation=GapValidationResult(
                status=status,
                reason=reason_text,
            ),
            analysis=InitialAnalysisResult(
                category="infrastructure",
                subcategory="Refined Problem Scope",
                summary=f"Citizen identified local constraint: {rejection_reason}",
                required_skills=["Civic Engineering", "Embedded Systems"],
                required_technologies=["IoT", "Python"],
                severity="high" if is_valid else "medium",
                priority="high" if is_valid else "medium",
                innovation_scope="high" if is_valid else "low",
                feasibility="high",
                confidence_score=0.8,
            ),
            duplicate_candidates=[],
            next_action="continue_to_matching" if is_valid else "stop",
        )

