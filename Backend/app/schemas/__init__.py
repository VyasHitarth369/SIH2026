from app.schemas.auth import ProfileResponse, UserAuthResponse, UserRole
from app.schemas.challenge import ChallengeCreate, ChallengeResponse
from app.schemas.analysis import (
    AIAnalysisResponse,
    ExistingSolutionDecisionRequest,
    DuplicateGateDecisionRequest,
    AnalyzeChallengeResponse,
)
from app.schemas.matching import (
    UniversityMatchItem,
    IndustryMatchItem,
    UniversityMatchListResponse,
    IndustryMatchListResponse,
)
from app.schemas.project import (
    UniversityResponseRequest,
    FinalizeSelectionRequest,
    ProjectCreate,
    ProjectResponse,
    ProjectMemberAdd,
    ProjectMemberResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
)
from app.schemas.industry import (
    IndustryCollaborationResponse,
    EmployeeInterestCreate,
    EmployeeInterestUpdate,
    EmployeeInterestResponse,
)
from app.schemas.government import (
    ChallengesMetricSummary,
    ParticipationMetricSummary,
    ProjectsMetricSummary,
    MilestonesMetricSummary,
    OutcomesMetricSummary,
    GovernmentDashboardMetrics,
    GovernmentProblemItem,
    GovernmentFacultyItem,
    GovernmentStudentItem,
    GovernmentSolvedProjectItem,
)
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    ProjectStatusTransition,
    ProjectImpactResponse,
)

__all__ = [
    "UserRole",
    "ProfileResponse",
    "UserAuthResponse",
    "ChallengeCreate",
    "ChallengeResponse",
    "AIAnalysisResponse",
    "ExistingSolutionDecisionRequest",
    "AnalyzeChallengeResponse",
    "UniversityMatchItem",
    "IndustryMatchItem",
    "UniversityMatchListResponse",
    "IndustryMatchListResponse",
    "UniversityResponseRequest",
    "FinalizeSelectionRequest",
    "ProjectCreate",
    "ProjectResponse",
    "ProjectMemberAdd",
    "ProjectMemberResponse",
    "MilestoneCreate",
    "MilestoneUpdate",
    "MilestoneResponse",
    "IndustryCollaborationResponse",
    "EmployeeInterestCreate",
    "EmployeeInterestUpdate",
    "EmployeeInterestResponse",
    "ChallengesMetricSummary",
    "ParticipationMetricSummary",
    "ProjectsMetricSummary",
    "MilestonesMetricSummary",
    "OutcomesMetricSummary",
    "GovernmentDashboardMetrics",
    "GovernmentProblemItem",
    "GovernmentFacultyItem",
    "GovernmentStudentItem",
    "GovernmentSolvedProjectItem",
    "FeedbackCreate",
    "FeedbackResponse",
    "ProjectStatusTransition",
    "ProjectImpactResponse",
]



