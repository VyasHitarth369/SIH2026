from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Gemini Structured Output Schemas (Call 1 & Call 2)
# =============================================================================

class EligibilityResult(BaseModel):
    """Assessment of whether the problem statement represents an eligible civic/societal issue."""
    status: Literal["eligible", "ineligible", "uncertain"] = "eligible"
    reason: str = ""

    model_config = ConfigDict(extra="ignore")


class ImageEvidenceResult(BaseModel):
    """Multi-modal image consistency verification against problem description."""
    status: Literal["consistent", "uncertain", "mismatch", "not_provided"] = "not_provided"
    observations: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class DiscoveredSolution(BaseModel):
    """Real-world scheme, program, or existing deployment discovered via Google Search grounding."""
    solution_name: str
    provider: str
    description: str
    relevance: Literal["DIRECT_MATCH", "PARTIAL_MATCH", "RELATED_ALTERNATIVE", "NOT_RELEVANT"] = "DIRECT_MATCH"
    accessibility: Literal["DIRECTLY_ACCESSIBLE", "ACCESSIBLE_NEARBY", "LIMITED_ACCESS", "NOT_ACCESSIBLE", "UNKNOWN"] = "UNKNOWN"
    operational_status: Literal["operational", "inactive", "unknown"] = "unknown"
    geographic_scope: str = "national"
    source_urls: List[str] = Field(default_factory=list)
    evidence_summary: str = ""

    model_config = ConfigDict(extra="ignore")


class BestSolutionResult(BaseModel):
    """The most directly applicable solution discovered."""
    solution_name: str
    reason: str

    model_config = ConfigDict(extra="ignore")


class InitialAnalysisResult(BaseModel):
    """Structured classification and requirement extraction produced in Call 1 (or refined in Call 2)."""
    category: str = "infrastructure"
    subcategory: str = "General Civic Infrastructure"
    summary: str
    required_skills: List[str] = Field(default_factory=list)
    required_technologies: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    innovation_scope: Literal["high", "medium", "low", "none"] = "medium"
    feasibility: Literal["high", "medium", "low", "uncertain"] = "high"
    confidence_score: float = 0.85

    model_config = ConfigDict(extra="ignore")


class DuplicateCandidate(BaseModel):
    """Potential duplicate challenge identified from provided candidates."""
    challenge_id: str
    similarity_reason: str
    confidence: float = 0.5

    model_config = ConfigDict(extra="ignore")


class Call1GeminiOutput(BaseModel):
    """Complete Call 1 structured output payload returned by Gemini 3.8 Flash."""
    eligibility: EligibilityResult = Field(default_factory=EligibilityResult)
    image_evidence: ImageEvidenceResult = Field(default_factory=ImageEvidenceResult)
    existing_solution_found: bool = False
    solutions: List[DiscoveredSolution] = Field(default_factory=list)
    best_solution: Optional[BestSolutionResult] = None
    problem_fully_addressed: bool = False
    initial_analysis: InitialAnalysisResult
    duplicate_candidates: List[DuplicateCandidate] = Field(default_factory=list)
    next_action: Literal["show_solution", "request_gap", "continue_to_matching", "request_better_image", "reject"] = "continue_to_matching"

    model_config = ConfigDict(extra="ignore")


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
    validity: Optional[str] = "valid"  # valid / invalid / uncertain
    innovation_scope: Optional[str] = "medium"  # high / medium / low / none
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
