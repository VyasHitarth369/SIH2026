"""analysis.py

Pydantic schemas for structured Gemini AI analysis, gap validation,
and database persistence in Concordia / Samadhan Setu.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Canonical Categories (Strictly 20 Allowed Domains)
# =============================================================================

CANONICAL_CATEGORIES: Tuple[str, ...] = (
    "healthcare",
    "education",
    "transportation",
    "infrastructure",
    "environment",
    "agriculture",
    "public_safety",
    "sanitation",
    "water",
    "energy",
    "accessibility",
    "governance",
    "employment",
    "disaster",
    "rural_development",
    "urban_development",
    "social_welfare",
    "cybersecurity",
    "digital_services",
    "other",
)

CanonicalCategory = Literal[
    "healthcare",
    "education",
    "transportation",
    "infrastructure",
    "environment",
    "agriculture",
    "public_safety",
    "sanitation",
    "water",
    "energy",
    "accessibility",
    "governance",
    "employment",
    "disaster",
    "rural_development",
    "urban_development",
    "social_welfare",
    "cybersecurity",
    "digital_services",
    "other",
]


# =============================================================================
# Evidence-Extraction Schemas (Call 1)
# =============================================================================

class DeterministicGateResult(BaseModel):
    """Result of provider-independent pre-LLM deterministic screening gate."""
    decision: Literal["reject", "continue", "uncertain"]
    reason_code: str
    reason: str
    category: str = "other"
    subcategory: str = "unclassified"
    innovation_scope: Literal["none", "low", "medium", "high", "uncertain"] = "uncertain"
    university_suitable: Optional[bool] = None

    model_config = ConfigDict(extra="ignore")


class EligibilityResult(BaseModel):
    """Assessment of whether the problem statement represents a genuine civic/societal issue."""
    status: Literal["valid", "ineligible", "uncertain"] = "uncertain"
    reason: str = ""

    model_config = ConfigDict(extra="ignore")


class ImageEvidenceResult(BaseModel):
    """Multi-modal image consistency verification against problem description."""
    status: Literal["not_provided", "consistent", "mismatch", "uncertain"] = "not_provided"
    confidence: float = 0.0
    observations: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class ObjectivePriorityFactors(BaseModel):
    """Objective civic and safety evidence factors. Gemini does NOT compute a final score."""
    severity_level: int = Field(ge=1, le=4, default=2, description="1=minor, 2=moderate, 3=major, 4=critical")
    population_scale: int = Field(ge=1, le=3, default=1, description="1=individual/localized, 2=community/ward/village, 3=city/district/large")
    life_safety_threat: bool = False
    essential_service_disrupted: bool = False
    priority_evidence: str = ""

    model_config = ConfigDict(extra="ignore")


class SkillRequirement(BaseModel):
    """Relevant skill required to address the challenge with importance rating."""
    name: str
    importance: Literal["essential", "important", "optional"] = "important"

    model_config = ConfigDict(extra="ignore")


class TechRequirement(BaseModel):
    """Relevant technology required to address the challenge with importance rating."""
    name: str
    importance: Literal["essential", "important", "optional"] = "important"

    model_config = ConfigDict(extra="ignore")


class ProblemUnderstanding(BaseModel):
    """Core understanding and classification extracted from the citizen submission."""
    summary: str = ""
    affected_entities: str = ""
    geographic_scope: str = ""
    core_issue: str = ""
    primary_category: str = "other"
    secondary_categories: List[str] = Field(default_factory=list)
    subcategory: str = "general"

    model_config = ConfigDict(extra="ignore")


class DiscoveredSolution(BaseModel):
    """Real-world scheme, program, or existing deployment discovered via Google Search grounding."""
    solution_name: str
    provider: str = ""
    description: str = ""
    relevance: Literal["DIRECT_MATCH", "PARTIAL_MATCH", "RELATED_ALTERNATIVE", "NOT_RELEVANT"] = "DIRECT_MATCH"
    accessibility: Literal["DIRECTLY_ACCESSIBLE", "ACCESSIBLE_NEARBY", "LIMITED_ACCESS", "NOT_ACCESSIBLE", "UNKNOWN"] = "UNKNOWN"
    operational_status: Literal["operational", "inactive", "unknown"] = "unknown"
    geographic_scope: str = "national"
    source_urls: List[str] = Field(default_factory=list)
    evidence_summary: str = ""

    source_type: Optional[str] = "external"  # "vidysetu_internal" | "external"
    project_id: Optional[str] = None
    challenge_id: Optional[str] = None
    university_name: Optional[str] = None
    industry_name: Optional[str] = None
    evidence_url: Optional[str] = None
    project_status: Optional[str] = None
    solved_problem_title: Optional[str] = None
    milestones: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class BestSolutionResult(BaseModel):
    """The most directly applicable solution discovered."""
    solution_name: str
    reason: str

    model_config = ConfigDict(extra="ignore")


class ExternalSearchResult(BaseModel):
    """Outcome of Google Search Grounding for existing public/government solutions."""
    search_status: Literal["searched", "not_searched", "search_failed", "uncertain"] = "not_searched"
    existing_solution_found: Optional[bool] = None
    solutions: List[DiscoveredSolution] = Field(default_factory=list)
    best_solution: Optional[BestSolutionResult] = None
    evidence_summary: str = ""

    model_config = ConfigDict(extra="ignore")


class DuplicateCandidate(BaseModel):
    """Potential duplicate challenge identified from provided candidates."""
    challenge_id: str
    similarity_reason: str
    confidence: float = 0.5

    model_config = ConfigDict(extra="ignore")


class CandidateRelationship(BaseModel):
    """Evaluated relationship between current submission and an existing challenge or project."""
    challenge_id: str
    project_id: Optional[str] = None
    title: str = ""
    description: str = ""
    relationship: Literal["duplicate", "related", "existing_solution", "new"] = "related"
    similarity_score: float = Field(0.0, ge=0.0, le=1.0)
    reason: str = ""
    source: Literal["vidysetu_challenge", "vidysetu_project"] = "vidysetu_challenge"
    status: Optional[str] = None
    university_name: Optional[str] = None
    industry_name: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# Legacy compatibility schema for Call 2 and backward-compatible references
class InitialAnalysisResult(BaseModel):
    """Structured classification and requirement extraction (legacy / synthesized view)."""
    category: str = "infrastructure"
    subcategory: str = "General Civic Infrastructure"
    summary: str = ""
    required_skills: List[str] = Field(default_factory=list)
    required_technologies: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    innovation_scope: Literal["high", "medium", "low", "none", "uncertain"] = "medium"
    feasibility: Literal["high", "medium", "low", "uncertain"] = "high"
    confidence_score: float = 0.85

    model_config = ConfigDict(extra="ignore")


class Call1GeminiOutput(BaseModel):
    """Complete Call 1 structured output payload returned by Gemini."""
    problem_understanding: ProblemUnderstanding = Field(default_factory=ProblemUnderstanding)
    eligibility: EligibilityResult = Field(default_factory=EligibilityResult)
    innovation_scope: Literal["none", "low", "medium", "high", "uncertain"] = "uncertain"
    university_suitable: Optional[bool] = None
    university_suitability_reason: str = ""
    priority_factors: ObjectivePriorityFactors = Field(default_factory=ObjectivePriorityFactors)
    required_skills: List[SkillRequirement] = Field(default_factory=list)
    required_technologies: List[TechRequirement] = Field(default_factory=list)
    image_evidence: ImageEvidenceResult = Field(default_factory=ImageEvidenceResult)
    external_search: ExternalSearchResult = Field(default_factory=ExternalSearchResult)
    duplicate_candidates: List[DuplicateCandidate] = Field(default_factory=list)
    candidate_relationships: List[CandidateRelationship] = Field(default_factory=list)
    analysis_confidence: Literal["high", "medium", "low"] = "medium"
    next_action: Literal[
        "show_solution",
        "request_gap",
        "continue_to_matching",
        "request_better_image",
        "reject",
        "uncertain_review",
    ] = "continue_to_matching"

    model_config = ConfigDict(extra="ignore")

    # -------------------------------------------------------------------------
    # Backwards-Compatibility Accessors
    # -------------------------------------------------------------------------
    @property
    def existing_solution_found(self) -> Optional[bool]:
        return self.external_search.existing_solution_found if self.external_search else None

    @property
    def solutions(self) -> List[DiscoveredSolution]:
        return self.external_search.solutions if self.external_search else []

    @property
    def best_solution(self) -> Optional[BestSolutionResult]:
        return self.external_search.best_solution if self.external_search else None

    @property
    def initial_analysis(self) -> InitialAnalysisResult:
        """Synthesizes legacy InitialAnalysisResult for existing tests and consumers."""
        cat = self.problem_understanding.primary_category if self.problem_understanding else "other"
        sub = self.problem_understanding.subcategory if self.problem_understanding else "general"
        summary = self.problem_understanding.summary if self.problem_understanding else ""
        skills = [s.name for s in self.required_skills]
        techs = [t.name for t in self.required_technologies]

        # Map objective severity level (1-4) to legacy string
        sev_map = {1: "low", 2: "medium", 3: "high", 4: "critical"}
        sev_str = sev_map.get(self.priority_factors.severity_level, "medium") if self.priority_factors else "medium"

        # Temporary non-authoritative legacy priority string for downstream views
        # (Authoritative source is priority_factors)
        pri_str = "medium"
        if self.priority_factors:
            if self.priority_factors.severity_level >= 4 or (self.priority_factors.life_safety_threat and self.priority_factors.population_scale >= 2):
                pri_str = "urgent"
            elif self.priority_factors.severity_level == 3 or self.priority_factors.life_safety_threat or self.priority_factors.essential_service_disrupted:
                pri_str = "high"
            elif self.priority_factors.severity_level == 1 and not self.priority_factors.essential_service_disrupted:
                pri_str = "low"

        conf_map = {"high": 0.9, "medium": 0.7, "low": 0.4}
        conf_num = conf_map.get(self.analysis_confidence, 0.7)

        return InitialAnalysisResult(
            category=cat,
            subcategory=sub,
            summary=summary,
            required_skills=skills,
            required_technologies=techs,
            severity=sev_str,
            priority=pri_str,
            innovation_scope=self.innovation_scope,
            feasibility="high",
            confidence_score=conf_num,
        )


# Provider-neutral alias for Call 1 structured output payload
Call1Output = Call1GeminiOutput


# =============================================================================
# Call 2: Gap Validation Schemas
# =============================================================================

class GapValidationResult(BaseModel):
    """Call 2 evaluation of citizen's rejection reason against the existing solution."""
    status: Literal["VALID_GAP", "INVALID_GAP", "UNCERTAIN_GAP"] = "VALID_GAP"
    reason: str = ""

    model_config = ConfigDict(extra="ignore")


class Call2GeminiOutput(BaseModel):
    """Complete Call 2 structured output payload for gap validation and refined classification."""
    gap_validation: GapValidationResult = Field(default_factory=GapValidationResult)
    analysis: InitialAnalysisResult
    duplicate_candidates: List[DuplicateCandidate] = Field(default_factory=list)
    next_action: Literal["continue_to_matching", "request_gap_clarification", "stop"] = "continue_to_matching"

    model_config = ConfigDict(extra="ignore")


# =============================================================================
# Database & API Schemas
# =============================================================================

class AIAnalysisResponse(BaseModel):
    """Pydantic representation matching the 20 columns of the Supabase ai_analysis table."""

    analysis_id: Optional[int] = None
    challenge_id: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    ai_summary: Optional[str] = None
    required_skills: Optional[str] = None
    required_technologies: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    duplicate_group: Optional[str] = None
    similar_challenges: Optional[str] = None
    solution_found: bool = False
    existing_solution: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: Optional[str] = None
    validity: Optional[str] = "valid"  # valid / ineligible / uncertain
    innovation_scope: Optional[str] = "medium"  # high / medium / low / none / uncertain
    feasibility: Optional[str] = "high"  # high / medium / low / uncertain
    solution_gap: Optional[str] = None
    solution_gap_valid: Optional[bool] = None

    model_config = ConfigDict(extra="ignore")


class ExistingSolutionDecisionRequest(BaseModel):
    """Payload for citizen decision on discovered existing solution.

    Supports both current `{ accepted, rejection_reason }` and legacy `{ decision, local_gap_reason }`.
    """

    accepted: Optional[bool] = None
    decision: Optional[str] = Field(None, description="'accept' or 'reject'")
    rejection_reason: Optional[str] = Field(
        None,
        description="Mandatory explanation if citizen rejects existing solution (explains local gap)",
    )
    local_gap_reason: Optional[str] = Field(
        None,
        description="Alias for rejection_reason",
    )
    rejection_category: Optional[str] = Field(
        None,
        description="Optional category: local_unavailability, poor_coverage, cost_capacity, missing_functionality, accessibility",
    )

    model_config = ConfigDict(extra="ignore")

    @property
    def is_accepted(self) -> bool:
        if self.accepted is not None:
            return bool(self.accepted)
        if self.decision is not None:
            return self.decision.strip().lower() in ("accept", "works", "yes", "true")
        return False

    @property
    def effective_rejection_reason(self) -> str:
        return (self.rejection_reason or self.local_gap_reason or "").strip()


class DuplicateGateDecisionRequest(BaseModel):
    """Payload for citizen decision on duplicate candidate in Citizen Duplicate Gate."""

    action: Literal["support_existing", "claim_different"] = Field(
        ...,
        description="'support_existing' to upvote existing challenge and merge duplicate; 'claim_different' to explain distinct local gap",
    )
    existing_challenge_id: Optional[str] = Field(
        None,
        description="ID of the existing challenge candidate being supported or referenced",
    )
    gap_reason: Optional[str] = Field(
        None,
        description="Explanation of how the problem differs or what gap remains if claiming different",
    )

    model_config = ConfigDict(extra="ignore")


class AnalyzeChallengeResponse(BaseModel):
    """API response returned when /api/challenges/{id}/analyze or /existing-solution-response is called."""

    challenge_id: str
    status: str
    action_taken: str
    llm_calls_made: int
    solution_found: bool
    existing_solution: Optional[str] = None
    solution_gap_valid: Optional[bool] = None
    analysis: Optional[Dict[str, Any]] = None
    message: str
    search_grounding_used: bool = False
    image_evidence_status: Optional[str] = None

    model_config = ConfigDict(extra="ignore")
