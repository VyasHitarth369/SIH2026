from app.services.base import BaseService
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.evidence_catalog import find_verified_existing_solution, VERIFIED_REAL_SOLUTIONS
from app.services.matching_engine import (
    score_university_candidate,
    score_industry_candidate,
    rank_universities,
    rank_industries,
)
from app.services.matching_service import MatchingService
from app.services.university_workflow_service import UniversityWorkflowService
from app.services.project_workflow_service import ProjectWorkflowService
from app.services.industry_workflow_service import IndustryWorkflowService
from app.services.government_service import GovernmentService
from app.services.feedback_service import FeedbackService

__all__ = [
    "BaseService",
    "AuthService",
    "AuthenticatedUser",
    "AIService",
    "ChallengeService",
    "find_verified_existing_solution",
    "VERIFIED_REAL_SOLUTIONS",
    "score_university_candidate",
    "score_industry_candidate",
    "rank_universities",
    "rank_industries",
    "MatchingService",
    "UniversityWorkflowService",
    "ProjectWorkflowService",
    "IndustryWorkflowService",
    "GovernmentService",
    "FeedbackService",
]



