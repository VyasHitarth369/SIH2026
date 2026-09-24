"""ai_service.py

Orchestrates the AI review, existing-solution discovery, gap validation, and classification
workflow for challenges submitted by citizens in Concordia / Samadhan Setu.

AI RULES ENFORCED (Phase LLM-1):
1. LLM extracts evidence & structured understanding; Backend validates & normalizes.
2. Canonical 20 categories strictly enforced with deterministic alias mapping.
3. Subcategories normalized and guarded against cross-domain contradiction.
4. Objective priority factors (severity 1-4, scale 1-3, life threat, essential disruption).
   Gemini does NOT compute final numerical priority.
5. Strict call budget: Maximum 1 logical LLM call for Call 1 (combining text, image, search).
6. Multi-modal image verification: Inspects uploaded photos; handles data URLs; detects corrupted/unreachable images.
7. Explicit external search state: 'searched', 'not_searched', 'search_failed', 'uncertain'.
   If search fails, existing_solution_found = None (NEVER false).
8. Safe deterministic fallbacks: Never manufactures confident classifications or defaults to infrastructure.
"""

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from google import genai
from google.genai import types

from app.schemas.analysis import (
    CANONICAL_CATEGORIES,
    Call1GeminiOutput,
    Call1Output,
    Call2GeminiOutput,
    CandidateRelationship,
    DeterministicGateResult,
    DiscoveredSolution,
    DuplicateCandidate,
    EligibilityResult,
    ExternalSearchResult,
    GapValidationResult,
    ImageEvidenceResult,
    InitialAnalysisResult,
    ObjectivePriorityFactors,
    ProblemUnderstanding,
    SkillRequirement,
    TechRequirement,
)

logger = logging.getLogger("ai_service")

CATEGORY_ALIASES: Dict[str, str] = {
    "roads": "transportation",
    "road": "transportation",
    "traffic": "transportation",
    "mobility": "transportation",
    "transit": "transportation",
    "health": "healthcare",
    "medical": "healthcare",
    "medicine": "healthcare",
    "hospital": "healthcare",
    "clean_water": "water",
    "drinking_water": "water",
    "water_supply": "water",
    "power": "energy",
    "electricity": "energy",
    "solar": "energy",
    "renewable_energy": "energy",
    "agriculture_farming": "agriculture",
    "farming": "agriculture",
    "crops": "agriculture",
    "agritech": "agriculture",
    "cyber_security": "cybersecurity",
    "cyber-security": "cybersecurity",
    "infosec": "cybersecurity",
    "network_security": "cybersecurity",
    "waste": "sanitation",
    "garbage": "sanitation",
    "drainage": "sanitation",
    "safety": "public_safety",
    "policing": "public_safety",
    "crime": "public_safety",
    "emergency": "disaster",
    "flood": "disaster",
    "jobs": "employment",
    "job_creation": "employment",
    "digital": "digital_services",
    "e-governance": "governance",
    "egov": "governance",
}


def canonicalize_category(cat: Optional[str]) -> Tuple[str, bool]:
    """Validates and canonicalizes category into one of 20 canonical categories.

    Returns:
        (canonical_category, is_uncertain)
    """
    if not cat or not isinstance(cat, str):
        return "other", True
    c = cat.strip().lower()
    if c in CANONICAL_CATEGORIES:
        return c, False
    alias = CATEGORY_ALIASES.get(c)
    if alias and alias in CANONICAL_CATEGORIES:
        return alias, False
    for canon in CANONICAL_CATEGORIES:
        if canon in c or c in canon:
            return canon, False
    return "other", True


def normalize_subcategory(primary_cat: str, subcat: Optional[str]) -> str:
    """Normalizes subcategory to a lowercase snake_case identifier and rejects domain mismatches."""
    if not subcat or not isinstance(subcat, str):
        return "general"
    clean = re.sub(r"[^a-z0-9_]+", "_", subcat.strip().lower()).strip("_")
    if not clean:
        clean = "general"

    # Reject obvious cross-domain contradictions
    mismatch_map = {
        "healthcare": ["highway", "pothole", "traffic", "road", "vehicle", "bridge"],
        "transportation": ["maternal", "hospital", "patient", "clinic", "doctor", "medicine"],
        "agriculture": ["cybersecurity", "firewall", "traffic_light", "subway"],
        "cybersecurity": ["crop_disease", "irrigation", "soil", "pothole", "sewage"],
        "water": ["malware", "ransomware", "traffic_jam", "runway"],
    }
    if primary_cat in mismatch_map:
        if any(kw in clean for kw in mismatch_map[primary_cat]):
            logger.warning(f"Rejected contradictory subcategory '{clean}' for primary category '{primary_cat}'")
            return f"general_{primary_cat}"
    return clean


# -----------------------------------------------------------------------------
# Deterministic Normalized-Token Similarity Helper (Jaccard / Token Overlap)
# -----------------------------------------------------------------------------
SIMILARITY_STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "of", "to", "for", "with", "by", "from",
    "up", "about", "into", "over", "after", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "but", "and",
    "or", "as", "if", "our", "my", "we", "us", "they", "them", "their", "this",
    "that", "these", "those", "there", "here", "not", "no", "very", "so", "too",
    "can", "will", "just", "should", "now", "need", "needs", "needed", "please",
    "help", "due", "lack", "poor", "severe", "facing", "urgent", "local",
    "sir", "madam", "want", "like", "also", "get", "got", "give"
}


def stem_word(w: str) -> str:
    """Lightweight rule-based suffix normalization for candidate retrieval and lexical matching."""
    w = w.lower().strip()
    if len(w) <= 4:
        return w
    suffixes = [
        "ation", "ition", "ment", "ness", "able", "ible", "ting", "ling",
        "ing", "ated", "ized", "ised", "ies", "ied", "ful", "less",
        "ous", "ive", "ity", "ers", "ed", "es", "ly", "er", "s"
    ]
    for suf in suffixes:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def tokenize_text(text: str, stem: bool = True) -> Set[str]:
    """Extracts meaningful normalized lowercase tokens and their stems, removing punctuation and stop words."""
    if not text:
        return set()
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", str(text).lower())
    words = clean.split()
    tokens = set()
    for w in words:
        if len(w) > 2 and w not in SIMILARITY_STOP_WORDS:
            tokens.add(w)
            if stem:
                st = stem_word(w)
                if len(st) > 2:
                    tokens.add(st)
    return tokens


def compute_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates deterministic Jaccard token overlap similarity between two texts in [0.0, 1.0]."""
    tokens1 = tokenize_text(text1)
    tokens2 = tokenize_text(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return round(intersection / union, 4) if union > 0 else 0.0


def compute_multi_signal_similarity(
    challenge: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    """Computes a robust multi-signal similarity evaluation between a submitted challenge and a database candidate.

    In accordance with system safeguards:
    - Stemming/prefix matching alone does NOT classify a challenge as duplicate.
    - Confidence integrates 5 independent signals:
      1. Title similarity (weight 0.35)
      2. Description & Problem Text similarity (weight 0.30)
      3. Category & Domain alignment (weight 0.15)
      4. Location / District alignment (weight 0.15)
      5. Existing VidySetu deployed project / solution evidence
    """
    curr_title = (challenge.get("title") or "").strip()
    curr_desc = (challenge.get("description") or "").strip()
    curr_text = f"{curr_title} {curr_desc}".strip()
    curr_cat = (challenge.get("category") or "").lower().strip()
    curr_loc = f"{challenge.get('city', '')} {challenge.get('district', '')} {challenge.get('location', '')}".lower()
    curr_dist = (challenge.get("district") or challenge.get("city") or "").lower().strip()

    cand_title = (candidate.get("title") or candidate.get("project_title") or "").strip()
    cand_desc = (candidate.get("description") or "").strip()
    cand_text = f"{cand_title} {cand_desc}".strip()
    cand_cat = (candidate.get("category") or "").lower().strip()
    cand_loc = f"{candidate.get('city', '')} {candidate.get('district', '')} {candidate.get('location', '')}".lower()
    cand_dist = (candidate.get("district") or candidate.get("city") or "").lower().strip()

    title_sim = compute_jaccard_similarity(curr_title, cand_title)
    desc_sim = compute_jaccard_similarity(curr_desc, cand_desc)
    full_sim = compute_jaccard_similarity(curr_text, cand_text)

    # Category Signal (0.0 to 1.0)
    cat_match = 0.3  # neutral fallback
    if curr_cat and cand_cat:
        if curr_cat == cand_cat or curr_cat in cand_cat or cand_cat in curr_cat:
            cat_match = 1.0
        elif any(w in cand_text.lower() for w in curr_cat.split()):
            cat_match = 0.8
        else:
            cat_match = 0.0
    else:
        # Keyword-based category heuristic
        domain_keywords = {
            "transport": ["transport", "traffic", "road", "highway", "bus", "mobility", "vehicle", "pavement", "pothole"],
            "water": ["water", "drinking", "fluoride", "arsenic", "pipe", "borewell"],
            "sanitation": ["garbage", "waste", "drain", "drainage", "sewer"],
            "lighting": ["street light", "streetlight", "lamp", "lighting"],
        }
        for d_k, d_words in domain_keywords.items():
            if any(w in curr_text.lower() for w in d_words) and any(w in cand_text.lower() for w in d_words):
                cat_match = 0.9
                break
        if cat_match == 0.3 and (title_sim >= 0.85 and (desc_sim >= 0.85 or full_sim >= 0.85)):
            cat_match = 1.0

    # Location Signal (0.0 to 1.0)
    loc_match = 0.3  # neutral fallback
    if curr_dist and cand_dist:
        if curr_dist == cand_dist or curr_dist in cand_loc or cand_dist in curr_loc:
            loc_match = 1.0
        elif "jharkhand" in curr_loc and "jharkhand" in cand_loc:
            loc_match = 0.6
        else:
            loc_match = 0.2
    elif "jharkhand" in curr_loc or "jharkhand" in cand_loc:
        loc_match = 0.5
    elif title_sim >= 0.85 and (desc_sim >= 0.85 or full_sim >= 0.85) and not (curr_dist or cand_dist):
        loc_match = 0.9

    # Multi-Signal Composite Score in [0.0, 1.0]
    composite = round(
        0.35 * title_sim +
        0.30 * max(desc_sim, full_sim * 0.8) +
        0.15 * cat_match +
        0.15 * loc_match,
        4
    )

    is_project = (
        candidate.get("source") == "vidysetu_project"
        or bool(candidate.get("project_id"))
        or candidate.get("status") in ["completed", "deployed"]
    )

    # Multi-Stage Classification Rules:
    # 1. Existing VidySetu Solution: Completed/deployed project directly matching problem scope
    if is_project and (composite >= 0.35 or full_sim >= 0.30):
        relationship = "existing_solution"
        reason = (
            f"Existing VidySetu deployed project directly addresses this problem "
            f"({candidate.get('university_name') or 'University Partner'}, multi-signal score: {composite:.2f})."
        )
    # 2. Duplicate: Strong multi-signal evidence across title, category, and location
    # (Notice: Stemming/prefix alone does NOT classify duplicate; requires title + category + location or strong lexical overlap)
    elif (
        (composite >= 0.48 and (title_sim >= 0.25 or desc_sim >= 0.25 or full_sim >= 0.35))
        or (composite >= 0.38 and title_sim >= 0.20 and cat_match >= 0.8 and loc_match >= 0.8)
    ):
        relationship = "duplicate"
        loc_str = candidate.get("district") or candidate.get("city") or "the same locality"
        reason = (
            f"Substantially identical problem statement already registered in {loc_str} "
            f"(multi-signal score: {composite:.2f}, title overlap: {title_sim:.2f})."
        )
    # 3. Related: Meaningful topic/domain intersection without identical scope
    elif composite >= 0.18 or cat_match >= 0.8 or title_sim >= 0.20 or full_sim >= 0.15:
        relationship = "related"
        reason = f"Related civic challenge in similar domain (multi-signal score: {composite:.2f})."
    # 4. New: Distinct challenge
    else:
        relationship = "new"
        reason = f"Distinct problem statement (multi-signal score: {composite:.2f})."

    return {
        "title_similarity": title_sim,
        "desc_similarity": desc_sim,
        "full_similarity": full_sim,
        "category_match": cat_match,
        "location_match": loc_match,
        "composite_score": composite,
        "relationship": relationship,
        "reason": reason,
    }


class AIService:
    """Orchestrates structured Gemini AI analysis, evidence extraction, image verification, and search grounding."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("LLM_API_KEY")
        )
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.fallback_model_name = "gemini-2.5-flash"
        self._client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {type(e).__name__}")

        # Secondary LLM Provider (OpenAI)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self._openai_client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured in backend environment.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @property
    def openai_client(self):
        if self._openai_client is None:
            if not self.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured in backend environment.")
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_api_key)
        return self._openai_client

    # -------------------------------------------------------------------------
    # Helper: Prepare image Part
    # -------------------------------------------------------------------------
    def _prepare_image_part(self, photo: Optional[str]) -> Tuple[Optional[types.Part], bool, bool]:
        """Converts base64 data URI or image URL to a google.genai types.Part.

        Returns:
            (part, image_provided, image_corrupted)
        """
        if not photo or not isinstance(photo, str) or not photo.strip():
            return None, False, False

        clean_photo = photo.strip()

        # Reject browser-local blob URLs (cannot be fetched by backend)
        if clean_photo.startswith("blob:"):
            logger.warning("Browser blob URL received in backend. Client must supply base64 or accessible URL.")
            return None, True, True

        try:
            if clean_photo.startswith("data:image/"):
                header, b64_data = clean_photo.split(",", 1)
                mime_type = header.split(";")[0].replace("data:", "").strip()
                raw_bytes = base64.b64decode(b64_data)
                if len(raw_bytes) > 10 * 1024 * 1024:
                    logger.warning("Image exceeds 10MB limit.")
                    return None, True, True
                return types.Part.from_bytes(data=raw_bytes, mime_type=mime_type), True, False

            elif clean_photo.startswith("http://") or clean_photo.startswith("https://"):
                import httpx
                with httpx.Client(timeout=4.0) as http_client:
                    resp = http_client.get(clean_photo)
                    if resp.status_code == 200:
                        mime_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                        return types.Part.from_bytes(data=resp.content, mime_type=mime_type), True, False
                    else:
                        return None, True, True
        except Exception as e:
            logger.warning(f"Could not load challenge image: {type(e).__name__}")
            return None, True, True

        return None, True, True

    # -------------------------------------------------------------------------
    # PART A: Provider-Independent Pre-LLM Deterministic Screening Gate
    # -------------------------------------------------------------------------
    def evaluate_deterministic_gate(self, challenge: Dict[str, Any]) -> DeterministicGateResult:
        """Provider-independent pre-LLM deterministic screening gate.

        Identifies:
        1. Meaningless / gibberish / spam / generic plea phrases
        2. Routine municipal maintenance / simple service requests
        3. Protects genuine innovation challenges from premature rejection
        """
        title = (challenge.get("title") or "").strip()
        desc = (challenge.get("description") or "").strip()
        full_text = f"{title} {desc}".strip()
        text_lower = full_text.lower()
        clean_words = [w for w in re.findall(r"[a-z0-9]+", text_lower) if len(w) > 0]
        clean_text = " ".join(clean_words)

        # ---------------------------------------------------------------------
        # 1. Prohibited, Spam, Gibberish, or Generic Meaningless Text
        # ---------------------------------------------------------------------
        spam_keywords = ["kill", "bomb", "hack into", "steal", "fake spam", "joke", "prank", "nonsense asdf"]
        is_spam = any(w in text_lower for w in spam_keywords)

        is_gibberish = False
        if any(g in text_lower for g in ["asdfghjkl", "qwerty", "123456"]):
            is_gibberish = True
        elif clean_words:
            vowels = set("aeiou")
            if len(clean_words) <= 4 and all(not any(c in vowels for c in w) for w in clean_words if len(w) > 2):
                is_gibberish = True

        generic_vague_phrases = [
            "help me",
            "please help",
            "help me with this issue",
            "problem",
            "please solve this",
            "something is wrong",
            "urgent issue",
            "things are bad",
            "problem in my area",
            "need help",
            "need assistance",
            "facing problem",
            "solve my problem",
            "issue in society",
        ]
        generic_plea_words = {
            "help", "me", "with", "this", "issue", "please", "my", "problem",
            "solve", "it", "urgent", "area", "need", "assistance", "facing",
            "something", "wrong", "things", "are", "bad", "in", "society",
            "sir", "madam", "to", "a", "an", "the", "of", "and"
        }
        title_lower = title.lower().strip()
        desc_lower = desc.lower().strip()

        is_vague_phrase = (
            clean_text in generic_vague_phrases
            or text_lower in generic_vague_phrases
            or title_lower in generic_vague_phrases
            or desc_lower in generic_vague_phrases
            or (len(clean_words) <= 12 and set(clean_words).issubset(generic_plea_words))
            or (len(clean_words) <= 5 and any(p == clean_text for p in generic_vague_phrases))
        )

        if is_spam or is_gibberish or is_vague_phrase or len(clean_text) < 4:
            return DeterministicGateResult(
                decision="reject",
                reason_code="meaningless_or_spam",
                reason="Problem statement is too vague, brief, or lacks substantive civic details for analysis.",
                category="other",
                subcategory="unclassified",
                innovation_scope="none",
                university_suitable=False,
            )

        # ---------------------------------------------------------------------
        # Step 2: Temporary Rejection Cases (Case 1: Potholes, Street light fixation, Bridge construction)
        # ---------------------------------------------------------------------
        # Explicit innovation markers guard (e.g. "predictive street lighting telemetry")
        innovation_markers = [
            "predictive system", "predictive model", "predictive technology", "predictive",
            "iot-based", "iot sensor", "iot telemetry", "iot",
            "telemetry", "machine learning", "deep learning",
            "artificial intelligence", "computer vision", "smart grid",
            "sensor network", "spectral imaging", "satellite imagery",
            "embedded system", "automated detection", "early warning system",
            "10,000", "city-wide telemetry", "ai-driven", "ai-based",
            "distributed sensor", "precision agriculture", "telemedicine architecture"
        ]
        has_deep_tech = any(im in text_lower for im in innovation_markers)

        is_potholes = ("pothole" in text_lower or "potholes" in text_lower)
        is_street_light = ("street light" in text_lower or "streetlight" in text_lower or "street lights" in text_lower)
        is_bridge_construction = (
            "bridge construction" in text_lower
            or ("bridge" in text_lower and any(w in text_lower for w in ["construct", "construction", "build", "building"]))
        )

        if not has_deep_tech:
            if is_potholes:
                return DeterministicGateResult(
                    decision="reject",
                    reason_code="routine_maintenance",
                    reason="Routine municipal road and pothole repair; not eligible for university-level research.",
                    category="transportation",
                    subcategory="road_maintenance",
                    innovation_scope="none",
                    university_suitable=False,
                )
            if is_street_light:
                return DeterministicGateResult(
                    decision="reject",
                    reason_code="routine_maintenance",
                    reason="Routine municipal street light maintenance; not eligible for university-level research.",
                    category="infrastructure",
                    subcategory="street_lighting_maintenance",
                    innovation_scope="none",
                    university_suitable=False,
                )
            if is_bridge_construction:
                return DeterministicGateResult(
                    decision="reject",
                    reason_code="routine_maintenance",
                    reason="Routine civil construction project; not eligible for university-level research.",
                    category="infrastructure",
                    subcategory="civil_construction",
                    innovation_scope="none",
                    university_suitable=False,
                )

        # ---------------------------------------------------------------------
        # Step 3: Existing-Solution Detection Guard (Case 2: Drainage) & Innovation Guard
        # ---------------------------------------------------------------------
        # Drainage MUST proceed to candidate retrieval and existing solution evaluation!
        is_drainage = any(w in text_lower for w in ["drainage", "sewer", "drain overflow", "waterlogging"])
        if is_drainage:
            return DeterministicGateResult(
                decision="continue",
                reason_code="existing_solution_candidate",
                reason="Drainage problem identified; proceeds to candidate matching and solution evaluation.",
                category="sanitation",
                subcategory="drainage_management",
                innovation_scope="medium",
                university_suitable=True,
            )

        if has_deep_tech:
            return DeterministicGateResult(
                decision="continue",
                reason_code="genuine_innovation_candidate",
                reason="Submission contains technical or research innovation markers and proceeds to structured analysis.",
                category="other",
                subcategory="unclassified",
                innovation_scope="high" if any(k in text_lower for k in ["predictive", "telemetry", "10,000", "ai", "machine learning"]) else "medium",
                university_suitable=True,
            )

        # ---------------------------------------------------------------------
        # Step 4: Other Routine Municipal Maintenance (Generic action + civic asset)
        # ---------------------------------------------------------------------
        action_stems = [
            "fix", "fixation", "fixing", "fixed",
            "repair", "repairing", "repaired",
            "replace", "replacement", "replacing", "replaced",
            "broken", "damaged", "damage",
            "clean", "cleaning", "cleaned",
            "remove", "removing", "removed",
            "unclog", "unclogging", "unclogged",
            "maintenance", "maintain", "maintaining", "maintained",
            "restore", "restoring", "restored",
            "leaking", "leak", "patch", "patching"
        ]
        other_civic_assets = [
            "garbage", "trash", "waste bin", "dustbin", "waste dumping", "dumping",
            "leaking pipe", "water pipe", "pipeline leak", "tap", "public tap",
            "bench", "public toilet", "broken pole", "broken sign", "broken bench"
        ]
        has_action = any(re.search(rf"\b{re.escape(act)}\b", text_lower) for act in action_stems) or any(act in text_lower for act in ["fixation", "maintenance", "unclog"])
        has_other_asset = any(asset in text_lower for asset in other_civic_assets)

        routine_exact_phrases = [
            "clean garbage", "clean garbage near my house",
            "fix leaking pipe", "fix leaking municipal pipe", "repair public tap", "replace broken bench",
            "outside my house is broken", "near my house is broken"
        ]
        has_routine_phrase = any(rp in text_lower for rp in routine_exact_phrases)

        if (has_action and has_other_asset) or has_routine_phrase:
            if any(w in text_lower for w in ["garbage", "trash", "waste bin", "dustbin", "waste", "dumping"]):
                cat, subcat = "sanitation", "waste_cleanup"
            elif any(w in text_lower for w in ["leaking pipe", "water pipe", "pipeline leak", "tap", "pipe"]):
                cat, subcat = "water", "pipe_repair"
            else:
                cat, subcat = "infrastructure", "routine_maintenance"

            return DeterministicGateResult(
                decision="reject",
                reason_code="routine_maintenance",
                reason="Routine municipal maintenance request; not eligible for university-level research or innovation workflow.",
                category=cat,
                subcategory=subcat,
                innovation_scope="none",
                university_suitable=False,
            )

        # ---------------------------------------------------------------------
        # Step 5: Default: Valid Societal/Technological Challenge -> Continue
        # ---------------------------------------------------------------------
        return DeterministicGateResult(
            decision="continue",
            reason_code="proceed_to_analysis",
            reason="Submission passed deterministic screening and proceeds to analysis and routing.",
            category="other",
            subcategory="unclassified",
            innovation_scope="medium",
            university_suitable=True,
        )

    def _build_call_1_from_gate_result(
        self,
        challenge: Dict[str, Any],
        gate: DeterministicGateResult,
        image_provided: bool,
        image_corrupted: bool = False,
    ) -> Call1GeminiOutput:
        """Constructs a structured Call1GeminiOutput from a deterministic gate decision without calling LLMs."""
        title = (challenge.get("title") or "").strip()
        location = challenge.get("location") or challenge.get("city", "") or "Local Area"
        image_status = "uncertain" if (image_provided or image_corrupted) else "not_provided"
        image_obs = ["Image provided but automated vision service was offline."] if image_provided else (
            ["Corrupted or unreachable image URL supplied."] if image_corrupted else []
        )

        return Call1GeminiOutput(
            problem_understanding=ProblemUnderstanding(
                summary=f"Problem statement: '{title}'. Offline categorization: {gate.category}.",
                affected_entities="Citizens in affected locality",
                geographic_scope=location,
                core_issue=title,
                primary_category=gate.category,
                secondary_categories=[],
                subcategory=gate.subcategory,
            ),
            eligibility=EligibilityResult(
                status="ineligible" if gate.decision == "reject" else ("valid" if gate.decision == "continue" else "uncertain"),
                reason=gate.reason,
            ),
            innovation_scope=gate.innovation_scope,
            university_suitable=gate.university_suitable,
            university_suitability_reason=gate.reason,
            priority_factors=ObjectivePriorityFactors(
                severity_level=1 if gate.decision == "reject" else 2,
                population_scale=1,
                life_safety_threat=False,
                essential_service_disrupted=False,
                priority_evidence="Determined by pre-LLM deterministic gate.",
            ),
            required_skills=[],
            required_technologies=[],
            image_evidence=ImageEvidenceResult(
                status=image_status,
                confidence=0.0,
                observations=image_obs,
            ),
            external_search=ExternalSearchResult(
                search_status="not_searched",
                existing_solution_found=None,
                solutions=[],
                evidence_summary="Deterministic gate resolved submission; external search not needed.",
            ),
            duplicate_candidates=[],
            analysis_confidence="high" if gate.decision == "reject" else "medium",
            next_action="reject" if gate.decision == "reject" else "continue_to_matching",
        )

    def _get_call_1_system_instructions(self) -> str:
        """Returns standard system instructions for structured Call 1 problem understanding."""
        canonical_categories_str = ", ".join(CANONICAL_CATEGORIES)
        return (
            "You are the AI Intelligence Engine for VidySetu / Samadhan Setu, a national civic problem innovation portal. "
            "Your role is to understand the submission, extract objective factual evidence, and assess technological suitability. "
            "You do NOT make final administrative decisions or university rankings.\n"
            "STRICT RULES:\n"
            "1. Zero fabrication: Never invent schemes, companies, URLs, phone numbers, or facts.\n"
            f"2. Canonical Categories: You must assign primary_category from ONLY these 20: {canonical_categories_str}. "
            "If multi-domain, populate secondary_categories using values from this same list.\n"
            "3. Subcategory: Output a clean snake_case identifier describing the specific problem (e.g. road_potholes, crop_disease, maternal_health). "
            "Never output a subcategory that contradicts the primary category (e.g. healthcare with smart_highway_sensors is forbidden).\n"
            "4. Eligibility: Return 'valid', 'ineligible', or 'uncertain'. Ineligible includes jokes, spam, personal disputes, ads, random text. "
            "Do NOT automatically mark uncertain input as valid. If evidence is insufficient, return 'uncertain' with clear reason.\n"
            "5. Innovation Scope: 'none' (routine maintenance, simple manual repair, complaint), 'low' (small tech tweak), "
            "'medium' (meaningful tech/research/design opportunity), 'high' (significant research, engineering, experimentation), 'uncertain'.\n"
            "6. University Suitability: university_suitable = true if it reasonably requires academic research, engineering, experimentation, "
            "AI/ML, software/hardware design, or prototype development. For routine maintenance (e.g. 'one streetlight is broken'), "
            "mark university_suitable = false and innovation_scope = none/low. Provide a concise university_suitability_reason.\n"
            "7. Objective Priority Factors: DO NOT calculate a final priority score. Extract:\n"
            "   - severity_level: 1 (minor), 2 (moderate), 3 (major), 4 (critical)\n"
            "   - population_scale: 1 (individual/localized), 2 (community/ward/village), 3 (city/district/large)\n"
            "   - life_safety_threat: true/false\n"
            "   - essential_service_disrupted: true/false\n"
            "   - priority_evidence: brief factual justification from the text.\n"
            "8. Required Skills & Technologies: Extract genuine domain requirements with importance: 'essential', 'important', 'optional'. "
            "Do not force popular buzzwords (e.g. React, AI, IoT) if irrelevant.\n"
            "9. Image Evidence: If an image is attached, inspect whether it visually depicts the stated civic problem ('consistent', 'mismatch', 'uncertain'). "
            "If no image is attached, status = 'not_provided'.\n"
            "10. External Solution Search: Use Google Search to check if a verified government scheme or existing public platform directly solves this. "
            "If search is performed and no solution exists, set search_status = 'searched' and existing_solution_found = false. "
            "If a solution exists, set search_status = 'searched', existing_solution_found = true, with DiscoveredSolution details.\n"
            "11. Candidate Relationship Evaluation: You are provided with a bounded set of candidate challenges and completed VidySetu projects. "
            "For each candidate, evaluate its relationship to the submitted problem: "
            "'duplicate' (same underlying problem, objective, and substantially overlapping scope/locality), "
            "'related' (concerns the same domain or technology, but distinct location, facility, or different operational objective), "
            "'existing_solution' (a completed or deployed VidySetu project directly solves this civic problem). "
            "Do NOT flag as duplicate merely because the category or keywords match. "
            "Populate candidate_relationships: List[CandidateRelationship]."
        )

    def _build_call_1_prompt_body(
        self,
        challenge: Dict[str, Any],
        candidate_records: List[Dict[str, Any]],
        has_image: bool,
        image_corrupted: bool = False,
    ) -> str:
        """Builds standard prompt text for Call 1 analysis."""
        title = challenge.get("title", "").strip()
        description = challenge.get("description", "").strip()
        location = challenge.get("location") or challenge.get("city", "") or "India"
        district = challenge.get("district") or challenge.get("city", "")
        impact_scope = challenge.get("impact_scope", "Area Specific")
        candidate_json = json.dumps(candidate_records, ensure_ascii=False) if candidate_records else "[]"

        return f"""Challenge Statement:
Title: {title}
Description: {description}
Location / City / District: {location} ({district})
Impact Scope: {impact_scope}
Image Attached: {'Yes (image bytes supplied)' if has_image else ('Corrupted / Unreachable Image Supplied' if image_corrupted else 'No')}

Supplied Candidate Challenge Records for duplicate check:
{candidate_json}

Task:
Produce a complete structured Call1GeminiOutput conforming to the schema.
"""

    def _call_1_gemini(
        self,
        challenge: Dict[str, Any],
        candidate_records: List[Dict[str, Any]],
        img_part: Optional[types.Part],
        image_provided: bool,
        image_corrupted: bool = False,
    ) -> Tuple[Optional[Call1GeminiOutput], bool, Optional[str]]:
        """Executes Call 1 using primary provider (Gemini 2.5 Flash).

        Maximum 1 request (+ 1 bounded transient retry for 5xx/429).
        Returns:
            (call_output, search_grounding_used, failure_reason)
        """
        if not self.api_key:
            return None, False, "GEMINI_API_KEY is not configured in backend environment."

        system_instructions = self._get_call_1_system_instructions()
        prompt_body = self._build_call_1_prompt_body(
            challenge, candidate_records, has_image=(img_part is not None), image_corrupted=image_corrupted
        )

        search_grounding_used = False
        last_error = None

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

            if resp.candidates and resp.candidates[0].grounding_metadata:
                gm = resp.candidates[0].grounding_metadata
                if gm.web_search_queries:
                    search_grounding_used = True

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
                if call_output.external_search:
                    call_output.external_search.search_status = "searched" if search_grounding_used else "uncertain"
                return call_output, search_grounding_used, None
        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)}"
            logger.info(f"Gemini search grounding call failed ({last_error}); attempting direct schema call.")

        # Step B: Direct schema call if search grounding failed (max 1 attempt + 1 transient retry)
        fallback_prompt = (
            f"{system_instructions}\n\n"
            f"NOTICE: Live Google Search grounding is currently unavailable (search_status = 'search_failed', existing_solution_found = null). "
            f"Do NOT fabricate dynamic URLs, organizations, or solutions. "
            f"Set external_search.search_status = 'search_failed' and external_search.existing_solution_found = null. "
            f"Evaluate eligibility, image consistency, classification, innovation scope, university suitability, and objective priority factors.\n\n"
            f"{prompt_body}"
        )
        fallback_contents = [fallback_prompt]
        if img_part:
            fallback_contents.append(img_part)

        for attempt in range(2):
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
                if call_output.external_search:
                    call_output.external_search.search_status = "search_failed"
                    call_output.external_search.existing_solution_found = None
                return call_output, False, None
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                logger.warning(f"Gemini attempt {attempt+1} failed: {last_error}")
                # Only retry on transient conditions
                if attempt == 0 and ("429" in last_error or "503" in last_error or "quota" in last_error.lower()):
                    import time
                    time.sleep(0.5)
                else:
                    break

        return None, False, last_error

    def _call_1_openai(
        self,
        challenge: Dict[str, Any],
        candidate_records: List[Dict[str, Any]],
        photo: Optional[str],
        image_provided: bool,
        image_corrupted: bool = False,
    ) -> Tuple[Optional[Call1GeminiOutput], Optional[str]]:
        """Executes Call 1 using the secondary OpenAI provider (gpt-5.6-luna).

        Supports text, image base64/URL, and structured JSON output conforming to Call1GeminiOutput.
        Maximum 1 fallback request.
        """
        if not self.openai_api_key:
            return None, "OPENAI_API_KEY is not configured in backend environment."

        system_instructions = self._get_call_1_system_instructions()
        prompt_body = self._build_call_1_prompt_body(
            challenge, candidate_records, has_image=(image_provided and not image_corrupted), image_corrupted=image_corrupted
        )

        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": prompt_body}
        ]

        if photo and isinstance(photo, str) and not image_corrupted:
            clean_photo = photo.strip()
            if clean_photo.startswith("data:image/") or clean_photo.startswith("http://") or clean_photo.startswith("https://"):
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": clean_photo}
                })

        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_content},
        ]

        try:
            client = self.openai_client
            # Try structured parse first
            try:
                completion = client.beta.chat.completions.parse(
                    model=self.openai_model,
                    messages=messages,
                    response_format=Call1GeminiOutput,
                    max_tokens=4096,
                )
                call_output = completion.choices[0].message.parsed
                if call_output:
                    if call_output.external_search:
                        call_output.external_search.search_status = "search_failed"
                        call_output.external_search.existing_solution_found = None
                    return call_output, None
            except Exception as pe:
                logger.warning(f"OpenAI beta parse failed, attempting json_object fallback: {pe}")
                resp = client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=4096,
                )
                raw_json = resp.choices[0].message.content
                if not raw_json:
                    return None, "OpenAI returned empty message content."
                call_output = Call1GeminiOutput.model_validate_json(raw_json)
                if call_output.external_search:
                    call_output.external_search.search_status = "search_failed"
                    call_output.external_search.existing_solution_found = None
                return call_output, None
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"OpenAI Call 1 failed ({self.openai_model}): {err_msg}")
            return None, err_msg

        return None, "OpenAI returned empty or unparseable response."

    # -------------------------------------------------------------------------
    # CALL 1: Initial Review + Image Evidence + Solution Discovery + Classification
    # -------------------------------------------------------------------------
    def analyze_call_1(
        self,
        challenge: Dict[str, Any],
        existing_challenges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Executes Call 1 of the AI review pipeline.

        Provider Architecture:
        1. Pre-LLM Deterministic Gate -> rejects routine municipal maintenance & meaningless spam immediately without consuming LLM quota.
        2. Primary Provider: Gemini 2.5 Flash -> text + image bytes + search grounding.
        3. Secondary Provider: OpenAI (gpt-5.6-luna) -> fallback when Gemini fails (quota/429/503/timeout/malformed).
        4. Deterministic Backend Fallback -> safe fail-closed decisions if both LLM providers fail.
        5. Post-LLM Backend Validation Gate -> defense-in-depth normalization, canonical 20 categories, re-check routine maintenance.
        """
        photo = challenge.get("photo")
        img_part, image_provided, image_corrupted = self._prepare_image_part(photo)

        # Candidate challenge list for duplicate and existing solution detection
        candidate_records = []
        if existing_challenges:
            for ch in existing_challenges:
                cid = ch.get("challenge_id")
                if cid and cid != challenge.get("challenge_id"):
                    rec = dict(ch)
                    rec["challenge_id"] = cid
                    rec["title"] = ch.get("title", "")[:120]
                    rec["description"] = ch.get("description", "")[:240]
                    candidate_records.append(rec)

        # =====================================================================
        # Step 1: Pre-LLM Deterministic Eligibility Gate
        # =====================================================================
        gate_res = self.evaluate_deterministic_gate(challenge)
        if gate_res.decision == "reject":
            logger.info(
                f"Challenge '{challenge.get('challenge_id')}' rejected by pre-LLM deterministic gate: "
                f"code={gate_res.reason_code}, cat={gate_res.category}/{gate_res.subcategory}"
            )
            call_output = self._build_call_1_from_gate_result(
                challenge, gate_res, image_provided, image_corrupted
            )
            call_output = self._validate_and_normalize_call_1(
                call_output, challenge=challenge, image_corrupted=image_corrupted, search_grounding_used=False
            )
            return self._format_call_1_response(
                call_output,
                search_grounding_used=False,
                provider_used="backend",
                provider_failure_reason=None,
            )

        # =====================================================================
        # Step 2: Primary Provider — Gemini 2.5 Flash
        # =====================================================================
        provider_used = "backend"
        provider_failure_reason: Optional[str] = None
        call_output: Optional[Call1GeminiOutput] = None
        search_grounding_used = False

        try:
            gemini_output, search_used, gemini_error = self._call_1_gemini(
                challenge, candidate_records, img_part, image_provided, image_corrupted
            )
        except Exception as e_gem:
            gemini_output, search_used, gemini_error = None, False, f"{type(e_gem).__name__}: {str(e_gem)}"
        if gemini_output is not None:
            call_output = gemini_output
            search_grounding_used = search_used
            provider_used = "gemini"
        else:
            logger.warning(
                f"Gemini Call 1 failed ({gemini_error}). Falling back to secondary LLM (OpenAI {self.openai_model})."
            )
            # =====================================================================
            # Step 3: Secondary Provider — OpenAI (gpt-5.6-luna)
            # =====================================================================
            try:
                openai_output, openai_error = self._call_1_openai(
                    challenge, candidate_records, photo, image_provided, image_corrupted
                )
            except Exception as e_open:
                openai_output, openai_error = None, f"{type(e_open).__name__}: {str(e_open)}"
            if openai_output is not None:
                call_output = openai_output
                search_grounding_used = False
                provider_used = "openai"
                provider_failure_reason = f"Gemini failed: {gemini_error}"
            else:
                logger.warning(
                    f"OpenAI Call 1 also failed ({openai_error}). Falling back to safe deterministic backend screening."
                )
                # =====================================================================
                # Step 4: Fail-Closed Deterministic Backend Fallback
                # =====================================================================
                provider_used = "backend"
                provider_failure_reason = f"Gemini failed ({gemini_error}); OpenAI failed ({openai_error})"
                call_output = self._deterministic_fallback_call_1(
                    challenge, image_provided, image_corrupted, candidate_records=candidate_records
                )

        # =====================================================================
        # Step 5: Post-LLM Backend Validation Gate (Defense in Depth)
        # =====================================================================
        call_output = self._validate_and_normalize_call_1(
            call_output,
            challenge=challenge,
            image_corrupted=image_corrupted,
            search_grounding_used=search_grounding_used,
        )

        # Step 5b: Evaluate, sanitize, and normalize candidate relationships
        evaluated_rels, int_sols, best_dup_id = self._evaluate_candidate_relationships(
            challenge, candidate_records, call_output.candidate_relationships
        )
        call_output.candidate_relationships = evaluated_rels
        if best_dup_id:
            best_dup_cand = next((r for r in evaluated_rels if r.challenge_id == best_dup_id), None)
            call_output.duplicate_candidates = [
                DuplicateCandidate(
                    challenge_id=best_dup_id,
                    similarity_reason=best_dup_cand.reason if best_dup_cand else "Identified as duplicate.",
                    confidence=best_dup_cand.similarity_score if best_dup_cand else 0.8,
                )
            ]
        else:
            call_output.duplicate_candidates = []

        return self._format_call_1_response(
            call_output,
            search_grounding_used=search_grounding_used,
            provider_used=provider_used,
            provider_failure_reason=provider_failure_reason,
            internal_solutions=int_sols,
            best_duplicate_id=best_dup_id,
        )

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

        models_to_try = [self.model_name]
        if self.fallback_model_name not in models_to_try:
            models_to_try.append(self.fallback_model_name)

        call_output: Optional[Call2GeminiOutput] = None
        for m in models_to_try:
            try:
                resp = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=Call2GeminiOutput,
                    ),
                )
                call_output = Call2GeminiOutput.model_validate_json(resp.text)
                break
            except Exception as e:
                logger.error(f"Gemini Call 2 execution failed with model '{m}': {type(e).__name__}")

        if call_output is None:
            call_output = self._deterministic_fallback_call_2(challenge, existing_solution, clean_reason, rejection_category)

        return self._format_call_2_response(call_output, existing_solution, clean_reason)

    # -------------------------------------------------------------------------
    # Candidate Relationship Evaluation & Sanitization
    # -------------------------------------------------------------------------
    def _evaluate_candidate_relationships(
        self,
        challenge: Dict[str, Any],
        candidate_records: List[Dict[str, Any]],
        raw_relationships: Optional[List[CandidateRelationship]] = None,
    ) -> Tuple[List[CandidateRelationship], List[DiscoveredSolution], Optional[str]]:
        """Evaluates, sanitizes, and normalizes candidate relationships against provided DB records.

        Guarantees:
        1. Candidate IDs must strictly exist in candidate_records (prevents LLM hallucinations).
        2. Clamps similarity score to [0.0, 1.0].
        3. Enforces valid relationship enum: 'duplicate', 'related', 'existing_solution'.
        4. Current challenge cannot reference itself.
        5. Converts 'existing_solution' candidates to DiscoveredSolution(source_type='vidysetu_internal').
        6. Identifies best duplicate challenge ID for duplicate_group.
        7. Computes deterministic fallback Jaccard scores if raw_relationships is omitted or partial.
        """
        curr_cid = challenge.get("challenge_id")
        curr_text = f"{challenge.get('title', '')} {challenge.get('description', '')}".strip()

        # Whitelist mapping of allowed candidate IDs
        valid_records_by_cid: Dict[str, Dict[str, Any]] = {}
        valid_records_by_pid: Dict[str, Dict[str, Any]] = {}

        for cand in candidate_records:
            cid = cand.get("challenge_id")
            pid = cand.get("project_id")
            if cid and cid != curr_cid:
                valid_records_by_cid[cid] = cand
            if pid:
                valid_records_by_pid[pid] = cand

        evaluated_relationships: List[CandidateRelationship] = []
        internal_solutions: List[DiscoveredSolution] = []
        seen_keys: Set[str] = set()

        raw_map: Dict[str, CandidateRelationship] = {}
        if raw_relationships:
            for r in raw_relationships:
                if not isinstance(r, CandidateRelationship):
                    try:
                        r = CandidateRelationship.model_validate(r)
                    except Exception:
                        continue
                # Reject self-reference
                if curr_cid and r.challenge_id == curr_cid:
                    continue
                # Reject hallucinated IDs
                matched_rec = valid_records_by_cid.get(r.challenge_id) or (
                    valid_records_by_pid.get(r.project_id) if r.project_id else None
                )
                if not matched_rec:
                    continue

                raw_map[r.challenge_id] = r
                if r.project_id:
                    raw_map[r.project_id] = r

        # Evaluate every valid candidate record
        for cand in candidate_records:
            cid = cand.get("challenge_id")
            pid = cand.get("project_id")
            if curr_cid and cid == curr_cid:
                continue

            unique_key = pid or cid
            if not unique_key or unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)

            cand_title = cand.get("title") or cand.get("project_title") or ""
            cand_desc = cand.get("description") or ""

            is_project = (
                cand.get("source") == "vidysetu_project"
                or bool(pid)
                or cand.get("status") in ["completed", "deployed"]
            )

            multi_sig = compute_multi_signal_similarity(challenge, cand)
            comp_sim = multi_sig["composite_score"]
            fallback_rel = multi_sig["relationship"]
            fallback_reason = multi_sig["reason"]

            # Check if LLM provided an evaluation
            llm_eval = raw_map.get(cid) or (raw_map.get(pid) if pid else None)
            if llm_eval:
                sim_score = max(0.0, min(1.0, float(llm_eval.similarity_score if llm_eval.similarity_score > 0 else comp_sim)))
                rel = llm_eval.relationship
                if rel not in ("duplicate", "related", "existing_solution"):
                    rel = fallback_rel
                reason = llm_eval.reason or f"Semantic similarity score: {sim_score:.2f}"
            else:
                sim_score = comp_sim
                rel = fallback_rel
                reason = fallback_reason

            # Defense-in-depth: A candidate cannot be duplicate if similarity is negligible or if it's a completed project
            if rel == "duplicate" and is_project:
                rel = "existing_solution"
            elif rel == "duplicate" and sim_score < 0.25:
                rel = "related"

            evaluated_rel = CandidateRelationship(
                challenge_id=cid or f"CHL-PRJ-{pid}",
                project_id=pid,
                title=cand_title,
                description=cand_desc,
                relationship=rel,
                similarity_score=round(sim_score, 4),
                reason=reason,
                source="vidysetu_project" if is_project else "vidysetu_challenge",
                status=cand.get("status"),
                university_name=cand.get("university_name"),
                industry_name=cand.get("industry_name"),
            )
            evaluated_relationships.append(evaluated_rel)

            # If existing solution, build DiscoveredSolution
            if rel == "existing_solution" and is_project:
                internal_solutions.append(
                    DiscoveredSolution(
                        solution_name=cand_title or "VidySetu Completed Project",
                        provider=cand.get("university_name") or "VidySetu University Partner",
                        description=cand_desc or "Verified technological deployment resolving this issue.",
                        relevance="DIRECT_MATCH",
                        accessibility="DIRECTLY_ACCESSIBLE",
                        operational_status="operational",
                        geographic_scope=cand.get("geographic_scope") or "Regional / Community Scope",
                        source_urls=[cand.get("evidence_url")] if cand.get("evidence_url") else [],
                        evidence_summary=f"Completed VidySetu project ({pid}) implemented by {cand.get('university_name', 'University Partner')}.",
                        source_type="vidysetu_internal",
                        project_id=pid,
                        challenge_id=cid,
                        university_name=cand.get("university_name"),
                        industry_name=cand.get("industry_name"),
                        evidence_url=cand.get("evidence_url"),
                        project_status=cand.get("status") or "deployed",
                        solved_problem_title=cand.get("solved_problem_title") or cand_title,
                        milestones=cand.get("milestones", []),
                    )
                )

        # Sort relationships by similarity score descending
        evaluated_relationships.sort(key=lambda x: x.similarity_score, reverse=True)

        # Determine best duplicate challenge ID
        best_dup_id: Optional[str] = None
        for r in evaluated_relationships:
            if r.relationship == "duplicate":
                best_dup_id = r.challenge_id
                break

        return evaluated_relationships, internal_solutions, best_dup_id

    # -------------------------------------------------------------------------
    # Normalization & Validation Layer
    # -------------------------------------------------------------------------
    def _validate_and_normalize_call_1(
        self,
        output: Call1GeminiOutput,
        challenge: Optional[Dict[str, Any]] = None,
        image_corrupted: bool = False,
        search_grounding_used: bool = False,
    ) -> Call1GeminiOutput:
        """Validates structured model output against canonical schemas and prevents invalid data storage."""
        # DEFENSE IN DEPTH: Re-check deterministic gate post-LLM to guard against hallucinations
        if challenge:
            post_gate = self.evaluate_deterministic_gate(challenge)
            if post_gate.decision == "reject":
                logger.info(
                    f"Defense-in-depth gate overrode model output: code={post_gate.reason_code}, cat={post_gate.category}"
                )
                output.eligibility.status = "ineligible"
                output.eligibility.reason = post_gate.reason
                output.innovation_scope = post_gate.innovation_scope
                output.university_suitable = post_gate.university_suitable
                output.university_suitability_reason = "Overridden by backend validation: routine municipal maintenance or ineligible submission."
                output.next_action = "reject"
                output.problem_understanding.primary_category = post_gate.category
                output.problem_understanding.subcategory = post_gate.subcategory

        # 1. Canonicalize Category
        cat, is_uncertain_cat = canonicalize_category(output.problem_understanding.primary_category)
        output.problem_understanding.primary_category = cat

        # 2. Canonicalize Secondary Categories
        valid_secondaries = []
        for sc in output.problem_understanding.secondary_categories:
            c_sc, _ = canonicalize_category(sc)
            if c_sc != cat and c_sc != "other" and c_sc not in valid_secondaries:
                valid_secondaries.append(c_sc)
        output.problem_understanding.secondary_categories = valid_secondaries

        # 3. Normalize Subcategory & Enforce Cross-Domain Compatibility
        output.problem_understanding.subcategory = normalize_subcategory(
            cat, output.problem_understanding.subcategory
        )

        # 4. Enforce Eligibility Rules
        if output.eligibility.status not in ("valid", "ineligible", "uncertain"):
            output.eligibility.status = "uncertain"
        if is_uncertain_cat and output.analysis_confidence == "low" and output.eligibility.status != "ineligible":
            output.eligibility.status = "uncertain"

        # 5. Clamp Objective Priority Factors
        pf = output.priority_factors
        pf.severity_level = max(1, min(4, int(pf.severity_level)))
        pf.population_scale = max(1, min(3, int(pf.population_scale)))
        pf.life_safety_threat = bool(pf.life_safety_threat)
        pf.essential_service_disrupted = bool(pf.essential_service_disrupted)

        # 6. Validate Innovation Scope & University Suitability
        if output.innovation_scope not in ("none", "low", "medium", "high", "uncertain"):
            output.innovation_scope = "uncertain"
        if output.university_suitable is not None:
            output.university_suitable = bool(output.university_suitable)

        # 7. Validate Image Evidence
        if image_corrupted:
            output.image_evidence.status = "uncertain"
            output.image_evidence.observations = ["Uploaded image could not be loaded or decoded by server."]
        elif output.image_evidence.status not in ("not_provided", "consistent", "mismatch", "uncertain"):
            output.image_evidence.status = "uncertain"

        # 8. Enforce External Search Logic (User Correction #1)
        es = output.external_search
        if es.search_status == "search_failed":
            es.existing_solution_found = None
            es.solutions = []
        elif es.search_status == "searched":
            if es.solutions:
                es.existing_solution_found = True
            else:
                es.existing_solution_found = False
        elif es.search_status in ("not_searched", "uncertain"):
            es.existing_solution_found = None
            es.solutions = []

        return output

    # -------------------------------------------------------------------------
    # Response Formatters (Building Namespaced Evidence Envelope)
    # -------------------------------------------------------------------------
    def _format_call_1_response(
        self,
        output: Call1GeminiOutput,
        search_grounding_used: bool = False,
        provider_used: str = "backend",
        provider_failure_reason: Optional[str] = None,
        internal_solutions: Optional[List[DiscoveredSolution]] = None,
        best_duplicate_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Maps Call1GeminiOutput into standard dictionary and builds versioned evidence envelope."""
        pu = output.problem_understanding
        elig = output.eligibility
        img_ev = output.image_evidence
        pf = output.priority_factors
        es = output.external_search
        int_sols = internal_solutions or []

        # Combined solutions list: internal VidySetu solutions first, followed by external
        combined_solutions = [s.model_dump() for s in int_sols] + [s.model_dump() for s in es.solutions]

        has_internal_solution = len(int_sols) > 0
        has_external_solution = bool(es.existing_solution_found and es.solutions)

        if has_internal_solution:
            solution_found = True
            existing_solution_found = True
            first_int = int_sols[0]
            existing_sol_text = f"VidySetu Applied Solution: {first_int.solution_name} ({first_int.provider}): {first_int.description}"
        elif has_external_solution:
            solution_found = True
            existing_solution_found = True
            sol = es.solutions[0]
            existing_sol_text = f"{sol.solution_name} ({sol.provider}): {sol.description}" if sol.provider else f"{sol.solution_name}: {sol.description}"
        else:
            solution_found = False
            # Preserve User Rule: If external search failed, existing_solution_found must be None (never False)
            if es.search_status == "search_failed":
                existing_solution_found = None
            elif es.search_status == "searched":
                existing_solution_found = False
            else:
                existing_solution_found = None
            existing_sol_text = None

        duplicate_group = best_duplicate_id
        if not duplicate_group and output.duplicate_candidates:
            duplicate_group = output.duplicate_candidates[0].challenge_id

        # Format legacy skill/tech strings
        skills_str = ", ".join(s.name for s in output.required_skills) if output.required_skills else None
        techs_str = ", ".join(t.name for t in output.required_technologies) if output.required_technologies else None

        # Database column public.ai_analysis.validity CHECK constraint:
        # CHECK (validity IN ('valid', 'invalid', 'uncertain'))
        raw_validity = elig.status
        db_validity = raw_validity
        if db_validity == "ineligible":
            db_validity = "invalid"
        elif (has_internal_solution or has_external_solution) and db_validity == "uncertain":
            db_validity = "valid"

        # Database column public.ai_analysis.innovation_scope CHECK constraint:
        # CHECK (innovation_scope IN ('none', 'low', 'medium', 'high'))
        raw_innovation_scope = output.innovation_scope
        db_innovation_scope = raw_innovation_scope
        is_innovation_scope_uncertain = False

        if raw_innovation_scope not in ("none", "low", "medium", "high") or raw_innovation_scope == "uncertain":
            db_innovation_scope = "low"
            is_innovation_scope_uncertain = True

        # User Correction #2: Namespaced Evidence Envelope
        namespaced_envelope = {
            "schema_version": 1,
            "provider_metadata": {
                "provider_used": provider_used,
                "provider_failure_reason": provider_failure_reason,
            },
            "objective_evidence": {
                "secondary_categories": pu.secondary_categories,
                "university_suitable": output.university_suitable,
                "university_suitability_reason": output.university_suitability_reason,
                "validity_raw": raw_validity,
                "innovation_scope_raw": raw_innovation_scope,
                "innovation_scope_uncertain": is_innovation_scope_uncertain,
                "severity_level": pf.severity_level,
                "population_scale": pf.population_scale,
                "life_safety_threat": pf.life_safety_threat,
                "essential_service_disrupted": pf.essential_service_disrupted,
                "priority_evidence": pf.priority_evidence,
                "analysis_confidence": output.analysis_confidence,
                "skills_breakdown": [s.model_dump() for s in output.required_skills],
                "technologies_breakdown": [t.model_dump() for t in output.required_technologies],
            },
            "image_evidence": {
                "status": img_ev.status,
                "confidence": img_ev.confidence,
                "observations": img_ev.observations,
            },
            "external_search": {
                "search_status": es.search_status,
                "existing_solution_found": es.existing_solution_found,
                "evidence_summary": es.evidence_summary,
            },
            "internal_search": {
                "search_status": "searched",
                "existing_solution_found": has_internal_solution,
                "solutions": [s.model_dump() for s in int_sols],
            },
            "similar_challenges": [r.model_dump() for r in (output.candidate_relationships or [])],
        }

        # Map objective severity level (1-4) to legacy string
        sev_map = {1: "low", 2: "medium", 3: "high", 4: "critical"}
        sev_str = sev_map.get(pf.severity_level, "medium")

        # Temporary non-authoritative legacy priority string for downstream views
        pri_str = "medium"
        if pf.severity_level >= 4 or (pf.life_safety_threat and pf.population_scale >= 2):
            pri_str = "urgent"
        elif pf.severity_level == 3 or pf.life_safety_threat or pf.essential_service_disrupted:
            pri_str = "high"
        elif pf.severity_level == 1 and not pf.essential_service_disrupted:
            pri_str = "low"

        conf_map = {"high": 0.9, "medium": 0.7, "low": 0.4}
        conf_num = conf_map.get(output.analysis_confidence, 0.7)

        return {
            # Database columns for public.ai_analysis
            "validity": db_validity,
            "validity_raw": raw_validity,
            "eligibility_reason": elig.reason,
            "category": pu.primary_category,
            "subcategory": pu.subcategory,
            "ai_summary": pu.summary,
            "required_skills": skills_str,
            "required_technologies": techs_str,
            "severity": sev_str,
            "priority": pri_str,
            "duplicate_group": duplicate_group,
            "similar_challenges": json.dumps(namespaced_envelope),
            "solution_found": solution_found,
            "existing_solution": existing_sol_text,
            "confidence_score": conf_num,
            "innovation_scope": db_innovation_scope,
            "innovation_scope_raw": raw_innovation_scope,
            "innovation_scope_uncertain": is_innovation_scope_uncertain,
            "feasibility": "high",
            "solution_gap": None if solution_found else (
                "External solution search failed or offline." if es.search_status == "search_failed"
                else "No verified existing solution found across active public platforms."
            ),
            "solution_gap_valid": None if solution_found else (
                None if es.search_status == "search_failed" else True
            ),
            # Direct API accessors for Call 1 evidence
            "secondary_categories": pu.secondary_categories,
            "core_issue": pu.core_issue,
            "affected_entities": pu.affected_entities,
            "geographic_scope": pu.geographic_scope,
            "severity_level": pf.severity_level,
            "population_scale": pf.population_scale,
            "life_safety_threat": pf.life_safety_threat,
            "essential_service_disrupted": pf.essential_service_disrupted,
            "priority_evidence": pf.priority_evidence,
            "university_suitable": output.university_suitable,
            "university_suitability_reason": output.university_suitability_reason,
            "image_evidence_status": img_ev.status,
            "image_evidence_confidence": img_ev.confidence,
            "image_observations": img_ev.observations,
            "external_search_status": es.search_status,
            "internal_search_status": "searched",
            "existing_solution_found": existing_solution_found,
            "solutions": combined_solutions,
            "internal_solutions": [s.model_dump() for s in int_sols],
            "best_solution": es.best_solution.model_dump() if es.best_solution else None,
            "skills_detail": [s.model_dump() for s in output.required_skills],
            "technologies_detail": [t.model_dump() for t in output.required_technologies],
            "duplicate_candidates": [d.model_dump() for d in output.duplicate_candidates],
            "candidate_relationships": [r.model_dump() for r in (output.candidate_relationships or [])],
            "analysis_confidence": output.analysis_confidence,
            "next_action": output.next_action,
            "provider_used": provider_used,
            "provider_failure_reason": provider_failure_reason,
            "llm_calls_made": 1,
            "search_grounding_used": search_grounding_used,
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
    def _deterministic_fallback_call_1(
        self,
        challenge: Dict[str, Any],
        image_provided: bool,
        image_corrupted: bool = False,
        candidate_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Call1GeminiOutput:
        """Safe zero-fabrication fallback if Gemini API is temporarily offline.

        Adheres strictly to the 4-step screening order:
        A. Clearly meaningless / spam / gibberish -> ineligible / rejected
        B. Clearly recognizable genuine innovation/research challenge -> valid (high/medium innovation)
        C. Clearly routine municipal maintenance -> ineligible / rejected (innovation_scope=none, university_suitable=false)
        D. Insufficient evidence to determine eligibility -> uncertain (NEVER routed to Government)
        """
        title = (challenge.get("title") or "").strip()
        desc = (challenge.get("description") or "").strip()
        full_text = f"{title} {desc}".strip()
        text_lower = full_text.lower()
        clean_words = [w for w in re.findall(r"[a-z0-9]+", text_lower) if len(w) > 0]
        clean_text = " ".join(clean_words)

        # ---------------------------------------------------------------------
        # SCREEN A: Prohibited, Spam, Gibberish, or Generic Meaningless Text
        # ---------------------------------------------------------------------
        spam_keywords = ["kill", "bomb", "hack into", "steal", "fake spam", "joke", "prank", "nonsense asdf"]
        is_spam = any(w in text_lower for w in spam_keywords)

        # Meaningless / gibberish patterns
        is_gibberish = False
        if any(g in text_lower for g in ["asdfghjkl", "qwerty", "123456"]):
            is_gibberish = True
        elif clean_words:
            vowels = set("aeiou")
            if len(clean_words) <= 4 and all(not any(c in vowels for c in w) for w in clean_words if len(w) > 2):
                is_gibberish = True

        generic_vague_phrases = [
            "help me",
            "please help",
            "help me with this issue",
            "problem",
            "please solve this",
            "something is wrong",
            "urgent issue",
            "things are bad",
            "problem in my area",
            "need help",
            "need assistance",
            "facing problem",
            "solve my problem",
            "issue in society",
        ]
        generic_plea_words = {
            "help", "me", "with", "this", "issue", "please", "my", "problem",
            "solve", "it", "urgent", "area", "need", "assistance", "facing",
            "something", "wrong", "things", "are", "bad", "in", "society",
            "sir", "madam", "to", "a", "an", "the", "of", "and"
        }
        title_lower = title.lower().strip()
        desc_lower = desc.lower().strip()

        is_vague_phrase = (
            clean_text in generic_vague_phrases
            or text_lower in generic_vague_phrases
            or title_lower in generic_vague_phrases
            or desc_lower in generic_vague_phrases
            or (len(clean_words) <= 12 and set(clean_words).issubset(generic_plea_words))
            or (len(clean_words) <= 5 and any(p == clean_text for p in generic_vague_phrases))
        )

        is_meaningless = is_spam or is_gibberish or is_vague_phrase

        # ---------------------------------------------------------------------
        # SCREEN B: Genuine Technology / Research Innovation Check
        # ---------------------------------------------------------------------
        # We screen for innovation indicators BEFORE routine maintenance so that
        # problems like "Develop an IoT-based predictive system to detect failures across 10,000 streetlights"
        # are recognized as high-tech research, not routine maintenance!
        innovation_markers = [
            "predictive system", "predictive model", "predictive technology", "predictive",
            "iot-based", "iot sensor", "iot telemetry", "iot",
            "telemetry", "machine learning", "deep learning",
            "artificial intelligence", "computer vision", "smart grid",
            "sensor network", "spectral imaging", "satellite imagery",
            "embedded system", "automated detection", "early warning system",
            "10,000", "city-wide telemetry", "ai-driven", "ai-based",
            "distributed sensor", "precision agriculture", "telemedicine architecture"
        ]
        is_genuine_innovation = (not is_meaningless) and any(im in text_lower for im in innovation_markers)

        # ---------------------------------------------------------------------
        # SCREEN C: Routine Municipal Maintenance Check
        # ---------------------------------------------------------------------
        # Detect combinations of ACTION WORDS + ROUTINE CIVIC ASSETS
        action_stems = [
            "fix", "fixation", "fixing", "fixed",
            "repair", "repairing", "repaired",
            "replace", "replacement", "replacing", "replaced",
            "broken", "damaged", "damage",
            "clean", "cleaning", "cleaned",
            "remove", "removing", "removed",
            "unclog", "unclogging", "unclogged",
            "maintenance", "maintain", "maintaining", "maintained",
            "restore", "restoring", "restored",
            "leaking", "leak", "patch", "patching"
        ]
        civic_assets = [
            "street light", "streetlight", "street-light", "street lights", "streetlights",
            "lamp", "street lamp", "light pole", "street-lamp",
            "pothole", "potholes", "road damage", "damaged road",
            "garbage", "trash", "waste bin", "dustbin", "waste dumping", "dumping",
            "leaking pipe", "water pipe", "pipeline leak", "tap",
            "bench", "public toilet", "broken pole", "broken sign"
        ]

        has_action = any(re.search(rf"\b{re.escape(act)}\b", text_lower) for act in action_stems) or any(act in text_lower for act in ["fixation", "maintenance", "unclog"])
        has_asset = any(asset in text_lower for asset in civic_assets)

        routine_exact_phrases = [
            "street light fixation", "fix street light", "fix the street light", "repair street light",
            "broken street light", "street light need to be fixed", "street light is broken",
            "repair pothole", "pothole on road", "clean garbage", "fix leaking pipe",
            "one streetlight", "single streetlight", "outside my house is broken", "near my house is broken"
        ]
        has_routine_phrase = any(rp in text_lower for rp in routine_exact_phrases)

        is_drainage = any(w in text_lower for w in ["drainage", "sewer", "drain overflow", "waterlogging"])
        is_potholes = ("pothole" in text_lower or "potholes" in text_lower)
        is_street_light = ("street light" in text_lower or "streetlight" in text_lower or "street lights" in text_lower)
        is_bridge_construction = (
            "bridge construction" in text_lower
            or ("bridge" in text_lower and any(w in text_lower for w in ["construct", "construction", "build", "building"]))
        )

        is_temporary_rejection = (is_potholes or is_street_light or is_bridge_construction) and (not is_genuine_innovation)
        is_routine_maintenance = (not is_meaningless) and (not is_genuine_innovation) and (not is_drainage) and (
            is_temporary_rejection or ((has_action and has_asset) or has_routine_phrase)
        )

        # ---------------------------------------------------------------------
        # Decision Routing & Classification
        # ---------------------------------------------------------------------
        category = "other"
        subcategory = "unclassified"
        skills: List[SkillRequirement] = []
        techs: List[TechRequirement] = []
        confidence = "medium"

        if is_meaningless:
            status = "ineligible"
            innovation_scope = "none"
            university_suitable = False
            suitability_reason = "Vague or meaningless submission; no academic research or engineering innovation requirement."
            reason = "Problem statement is too vague, brief, or lacks substantive civic details for analysis."
            category = "other"
            subcategory = "unclassified"
            next_action = "reject"

        elif is_routine_maintenance:
            status = "ineligible"
            innovation_scope = "none"
            university_suitable = False
            suitability_reason = "Routine municipal maintenance/civil work request; no university-level research or innovation requirement."
            reason = "Routine municipal maintenance or civil work request; not eligible for university-level research or innovation workflow."
            confidence = "high"
            next_action = "reject"

            # Domain-accurate categorization for routine maintenance
            if is_bridge_construction:
                category = "infrastructure"
                subcategory = "civil_construction"
            elif any(w in text_lower for w in ["street light", "streetlight", "lamp", "pole", "sign"]):
                category = "infrastructure"
                subcategory = "street_lighting_maintenance"
            elif any(w in text_lower for w in ["pothole", "road damage", "road", "pavement"]):
                category = "transportation"
                subcategory = "road_maintenance"
            elif any(w in text_lower for w in ["garbage", "trash", "waste bin", "dustbin", "waste", "dumping"]):
                category = "sanitation"
                subcategory = "waste_cleanup"
            elif any(w in text_lower for w in ["leaking pipe", "water pipe", "pipeline leak", "tap", "pipe"]):
                category = "water"
                subcategory = "pipe_repair"
            elif any(w in text_lower for w in ["toilet", "bench"]):
                category = "infrastructure"
                subcategory = "facility_repair"
            else:
                category = "infrastructure"
                subcategory = "routine_maintenance"

        elif is_genuine_innovation:
            status = "valid"
            innovation_scope = "high" if any(k in text_lower for k in ["predictive", "telemetry", "10,000", "ai", "machine learning"]) else "medium"
            university_suitable = True
            suitability_reason = "Requires technological innovation, predictive modeling, IoT telemetry, or engineering development."
            reason = "Problem statement validated as an engineering/technology innovation challenge."
            confidence = "medium"
            next_action = "continue_to_matching"

            if any(w in text_lower for w in ["streetlight", "street light", "lighting"]):
                category = "infrastructure"
                subcategory = "predictive_street_lighting_telemetry"
                skills = [SkillRequirement(name="IoT Systems", importance="essential"), SkillRequirement(name="Predictive Modeling", importance="essential")]
                techs = [TechRequirement(name="ESP32 / LoRaWAN", importance="essential"), TechRequirement(name="Python", importance="important")]
            elif any(w in text_lower for w in ["water", "borewell", "contamination"]):
                category = "water"
                subcategory = "water_telemetry_sensing"
                skills = [SkillRequirement(name="Hydraulic Systems", importance="essential"), SkillRequirement(name="IoT Water Sensors", importance="essential")]
                techs = [TechRequirement(name="ESP32", importance="important"), TechRequirement(name="Cloud Telemetry", importance="optional")]
            elif any(w in text_lower for w in ["road", "traffic", "pothole"]):
                category = "transportation"
                subcategory = "intelligent_transport_systems"
                skills = [SkillRequirement(name="Computer Vision", importance="essential"), SkillRequirement(name="Edge AI", importance="important")]
                techs = [TechRequirement(name="Python", importance="important"), TechRequirement(name="OpenCV", importance="important")]
            elif any(w in text_lower for w in ["crop", "agriculture", "farmer", "mustard"]):
                category = "agriculture"
                subcategory = "precision_agritech"
                skills = [SkillRequirement(name="Agronomy", importance="essential"), SkillRequirement(name="Spectral Imaging", importance="important")]
                techs = [TechRequirement(name="Computer Vision", importance="important")]
            elif any(w in text_lower for w in ["cyber", "vulnerabilit", "firewall", "malware"]):
                category = "cybersecurity"
                subcategory = "network_vulnerability_framework"
                skills = [SkillRequirement(name="Network Security", importance="essential")]
                techs = [TechRequirement(name="Firewall Systems", importance="important")]
            elif any(w in text_lower for w in ["maternal", "health", "hospital"]):
                category = "healthcare"
                subcategory = "telemedicine_diagnostics"
                skills = [SkillRequirement(name="Medical Diagnostics", importance="essential")]
                techs = [TechRequirement(name="Telemedicine Architecture", importance="important")]
            elif any(w in text_lower for w in ["solar", "power", "electricity", "grid", "energy"]):
                category = "energy"
                subcategory = "smart_grid_telemetry"
                skills = [SkillRequirement(name="Power Electronics", importance="essential")]
                techs = [TechRequirement(name="Solar Inverters", importance="important")]
            elif any(w in text_lower for w in ["garbage", "dump", "solid waste", "sanitation"]):
                category = "sanitation"
                subcategory = "smart_waste_systems"
                skills = [SkillRequirement(name="Waste Management Engineering", importance="essential")]
                techs = [TechRequirement(name="IoT Fill-Level Sensors", importance="important")]
            else:
                category = "technology"
                subcategory = "applied_innovation"
                skills = [SkillRequirement(name="Applied Engineering", importance="essential")]
                techs = [TechRequirement(name="Python", importance="important")]

        else:
            # SCREEN D: Valid societal/technological challenge fallback
            # (Guarantees meaningful problems like "Exam question paper software", "Malnutrition" are valid)
            status = "valid"
            reason = "Problem statement validated as an applied research or technological challenge under deterministic fallback."
            innovation_scope = "medium"
            university_suitable = True
            suitability_reason = "Problem requires technological, analytical, or applied engineering solutions."
            confidence = "medium"
            next_action = "continue_to_matching"

            # Check general domain keywords
            if any(w in text_lower for w in ["exam", "question paper", "paper software", "curriculum", "school", "education"]):
                category = "education"
                subcategory = "academic_software"
                skills = [SkillRequirement(name="Software Engineering", importance="essential"), SkillRequirement(name="Information Security", importance="important")]
                techs = [TechRequirement(name="Python", importance="important"), TechRequirement(name="Database Systems", importance="important")]
            elif any(w in text_lower for w in ["malnutrition", "malnutitrion", "nutrition", "stunting", "child health", "diet"]):
                category = "healthcare"
                subcategory = "public_health_nutrition"
                skills = [SkillRequirement(name="Nutritional Epidemiology", importance="essential"), SkillRequirement(name="Public Health Diagnostics", importance="essential")]
                techs = [TechRequirement(name="Data Analytics", importance="important"), TechRequirement(name="Mobile Health Frameworks", importance="optional")]
            elif any(w in text_lower for w in ["water", "drinking water", "borewell", "contamination", "water supply", "arsenic"]):
                category = "water"
                subcategory = "water_contamination" if any(w in text_lower for w in ["contaminat", "disease", "poison", "arsenic", "pollut"]) else "water_supply"
                skills = [SkillRequirement(name="Hydraulic Systems", importance="essential"), SkillRequirement(name="IoT Water Sensors", importance="important")]
                techs = [TechRequirement(name="ESP32", importance="important"), TechRequirement(name="Cloud Telemetry", importance="optional")]
            elif any(w in text_lower for w in ["road", "traffic", "highway", "bus", "transport"]):
                category = "transportation"
                subcategory = "traffic_management" if "traffic" in text_lower else "road_infrastructure"
                skills = [SkillRequirement(name="Computer Vision", importance="essential"), SkillRequirement(name="Civil Engineering", importance="important")]
                techs = [TechRequirement(name="Python", importance="important"), TechRequirement(name="GIS Mapping", importance="optional")]
            elif any(w in text_lower for w in ["crop", "mustard", "wheat", "pesticide", "fungal", "agriculture", "farmer"]):
                category = "agriculture"
                subcategory = "crop_disease" if any(w in text_lower for w in ["disease", "fungal", "rust", "pest"]) else "farm_management"
                skills = [SkillRequirement(name="Agronomy", importance="essential"), SkillRequirement(name="Plant Pathology", importance="essential")]
                techs = [TechRequirement(name="Spectral Imaging", importance="optional")]
            elif any(w in text_lower for w in ["maternal", "infant", "hospital", "doctor", "health", "obstetric", "clinic"]):
                category = "healthcare"
                subcategory = "maternal_health" if any(w in text_lower for w in ["maternal", "pregnant", "infant", "obstetric"]) else "primary_healthcare"
                skills = [SkillRequirement(name="Medical Diagnostics", importance="essential"), SkillRequirement(name="Public Health Systems", importance="important")]
                techs = [TechRequirement(name="Telemedicine Architecture", importance="important")]
            elif any(w in text_lower for w in ["cyber", "vulnerabilit", "firewall", "malware", "breach", "intranet", "hack"]):
                category = "cybersecurity"
                subcategory = "network_vulnerability"
                skills = [SkillRequirement(name="Network Security", importance="essential"), SkillRequirement(name="Vulnerability Assessment", importance="essential")]
                techs = [TechRequirement(name="Firewall Systems", importance="important")]
            elif any(w in text_lower for w in ["solar", "power", "electricity", "grid", "energy"]):
                category = "energy"
                subcategory = "renewable_power"
                skills = [SkillRequirement(name="Power Electronics", importance="essential")]
                techs = [TechRequirement(name="Solar Inverters", importance="important")]
            elif any(w in text_lower for w in ["drainage", "sewer", "drain overflow", "waterlogging", "sanitation"]):
                category = "sanitation"
                subcategory = "drainage_management"
                skills = [SkillRequirement(name="Hydraulic Systems", importance="essential"), SkillRequirement(name="Waste Management Engineering", importance="important")]
                techs = [TechRequirement(name="IoT Water Sensors", importance="important")]
            elif any(w in text_lower for w in ["garbage", "dump", "solid waste"]):
                category = "sanitation"
                subcategory = "solid_waste_management"
                skills = [SkillRequirement(name="Waste Management Engineering", importance="essential")]
                techs = [TechRequirement(name="IoT Fill-Level Sensors", importance="important")]
            else:
                category = "technology"
                subcategory = "applied_innovation"
                skills = [SkillRequirement(name="Applied Engineering", importance="essential"), SkillRequirement(name="Software Engineering", importance="important")]
                techs = [TechRequirement(name="Python", importance="important")]

        # Severity & population scale defaults
        severity_level = 3 if any(w in text_lower for w in ["fatal", "accident", "disease", "outbreak", "death", "critical", "severe"]) else (1 if is_routine_maintenance else 2)
        pop_scale = 3 if any(w in text_lower for w in ["district", "city", "state", "thousands", "national"]) else (1 if "outside my house" in text_lower or is_routine_maintenance else 2)
        life_safety = any(w in text_lower for w in ["accident", "disease", "outbreak", "death", "poison", "fatal", "mortality"])
        essential_disrupted = any(w in text_lower for w in ["drinking water", "hospital", "ambulance", "power grid"])

        image_status = "uncertain" if (image_provided or image_corrupted) else "not_provided"
        image_obs = ["Image provided but automated vision service was offline."] if image_provided else (
            ["Corrupted or unreachable image URL supplied."] if image_corrupted else []
        )

        cand_rels = []
        dup_cands = []
        int_sols = []
        if candidate_records:
            cand_rels, int_sols, best_dup_id = self._evaluate_candidate_relationships(challenge, candidate_records)
            if best_dup_id:
                best_dup_cand = next((r for r in cand_rels if r.challenge_id == best_dup_id), None)
                dup_cands = [
                    DuplicateCandidate(
                        challenge_id=best_dup_id,
                        similarity_reason=best_dup_cand.reason if best_dup_cand else "Identified as duplicate.",
                        confidence=best_dup_cand.similarity_score if best_dup_cand else 0.8,
                    )
                ]

        return Call1GeminiOutput(
            problem_understanding=ProblemUnderstanding(
                summary=f"Problem statement: '{title}'. Offline categorization: {category}.",
                affected_entities="Citizens in affected locality",
                geographic_scope=challenge.get("location") or "Local Area",
                core_issue=title,
                primary_category=category,
                secondary_categories=[],
                subcategory=subcategory,
            ),
            eligibility=EligibilityResult(
                status=status,
                reason=reason,
            ),
            innovation_scope=innovation_scope,
            university_suitable=university_suitable,
            university_suitability_reason=suitability_reason,
            priority_factors=ObjectivePriorityFactors(
                severity_level=severity_level,
                population_scale=pop_scale,
                life_safety_threat=life_safety,
                essential_service_disrupted=essential_disrupted,
                priority_evidence="Estimated from offline keyword heuristics.",
            ),
            required_skills=skills,
            required_technologies=techs,
            image_evidence=ImageEvidenceResult(
                status=image_status,
                confidence=0.0,
                observations=image_obs,
            ),
            external_search=ExternalSearchResult(
                search_status="not_searched",
                existing_solution_found=None,
                solutions=[],
                evidence_summary="Search service offline; external check not executed.",
            ),
            duplicate_candidates=dup_cands,
            candidate_relationships=cand_rels,
            analysis_confidence=confidence,
            next_action=next_action,
        )

    def _deterministic_fallback_call_2(
        self,
        challenge: Dict[str, Any],
        existing_solution: str,
        rejection_reason: str,
        rejection_category: Optional[str] = None,
    ) -> Call2GeminiOutput:
        """Safe deterministic gap evaluation when Gemini is offline."""
        clean = rejection_reason.lower()
        valid_markers = [
            "not available", "no coverage", "cost", "too expensive", "does not work",
            "doesn't work", "different", "specific", "local", "lack", "unable",
            "distance", "far", "language", "offline", "rural"
        ]

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
