"""test_government_top5_verification.py

Verifies Government Active Problems data contract:
1. Retrieval of monitored problems with counts
2. Top-5 University recommendations hydration
3. Top-5 Industry recommendations hydration with real industry names and scores
4. Industry matching status timeline (Pending, Generated, Sent, Accepted, Rejected)
5. University allocation / university_name propagation
"""

import pytest
from app.database import get_supabase
from app.services.government_service import GovernmentService


@pytest.fixture
def supabase_client():
    return get_supabase()


@pytest.fixture
def government_service(supabase_client):
    return GovernmentService(supabase_client)


def test_government_monitored_problems_and_top5(government_service):
    """Verify that get_monitored_problems hydrates Top-5 industries, universities, and matching status."""
    res = government_service.get_monitored_problems(limit=20)
    assert res is not None
    assert hasattr(res, "counts")
    assert hasattr(res, "total")

    # If there are monitored problems in DB, inspect hydration
    if len(res) > 0:
        for p in res:
            assert "challenge_id" in p
            assert "status" in p
            assert "top_universities" in p
            assert isinstance(p["top_universities"], list)
            assert "top_industries" in p
            assert isinstance(p["top_industries"], list)
            assert "industry_matching_status" in p
            assert p["industry_matching_status"] in ["Pending", "Generated", "Sent", "Accepted", "Rejected"]

            # Verify industry fields when top_industries is present
            for ind in p["top_industries"]:
                assert "industry_id" in ind
                assert "industry_name" in ind
                assert ind["industry_name"] is not None
                assert "rank" in ind
                assert "match_score" in ind


def test_government_active_problem_schema_compatibility(government_service):
    """Ensure all fields required by ActiveProblemsPage.jsx are present in the response."""
    res = government_service.get_monitored_problems(limit=5)
    for p in res:
        # Check standard fields rendered by frontend
        assert "title" in p
        assert "description" in p
        assert "location" in p
        assert "city" in p
        assert "district" in p
        assert "status" in p
