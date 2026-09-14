"""matching_engine.py

Pure deterministic numerical matching engine for universities and industries.
Adheres strictly to the percentage weights defined in CONCORDIA_BACKEND_CONTEXT.md:

University Weights (Sum = 100%):
- skills = 25%
- technologies = 25%
- research_areas = 15%
- domain = 10%
- primary_focus = 10%
- departments = 5%
- facilities = 3%
- past_projects = 2%

Industry Weights (Sum = 100%):
- skills = 22%
- technologies = 22%
- domain = 15%
- deployment_capabilities = 12%
- resource_capabilities = 10%
- products_services = 8%
- geography = 5%
- csr_areas = 3%
- past_projects = 3%

Zero fabrication: Uses only actual database records and fields.
Backend is the final numerical authority. Matching is strictly reproducible.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


# Semantic equivalent canonical mappings (CONCORDIA_BACKEND_CONTEXT.md Section 11 F)
CANONICAL_SYNONYMS: Dict[str, str] = {
    "ml": "machine learning",
    "machine learning": "machine learning",
    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    "iot": "internet of things",
    "internet of things": "internet of things",
    "gis": "geographic information systems",
    "geographic information systems": "geographic information systems",
    "data analysis": "data analytics",
    "data analytics": "data analytics",
    "cv": "computer vision",
    "computer vision": "computer vision",
    "nlp": "natural language processing",
    "natural language processing": "natural language processing",
    "pv": "photovoltaic",
    "photovoltaic": "photovoltaic",
    "bms": "battery management system",
    "battery management": "battery management system",
    "rf": "radio frequency",
}


def normalize_token(token: str) -> str:
    """Normalizes an individual token or acronym into lower-case canonical form."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", token).strip().lower()
    clean = re.sub(r"\s+", " ", clean)
    return CANONICAL_SYNONYMS.get(clean, clean)


def extract_tokens(text: Optional[str]) -> List[str]:
    """Splits a comma, semicolon, or slash separated string into a list of normalized tokens."""
    if not text or not isinstance(text, str):
        return []
    raw_items = re.split(r"[,;/|•\n]+", text)
    tokens = []
    for item in raw_items:
        norm = normalize_token(item)
        if norm and len(norm) > 1:
            tokens.append(norm)
    return tokens


def calculate_overlap_ratio(
    required_tokens: List[str], candidate_tokens: List[str]
) -> Tuple[float, List[str]]:
    """Calculates deterministic overlap ratio between required items and candidate capabilities.

    Returns (ratio: float in [0.0, 1.0], matched_items: List[str]).
    """
    if not required_tokens:
        return 1.0, []
    if not candidate_tokens:
        return 0.0, []

    matched = []
    total_score = 0.0

    for req in required_tokens:
        best_match = 0.0
        match_label = None

        for cand in candidate_tokens:
            if req == cand:
                best_match = 1.0
                match_label = req
                break
            elif req in cand or cand in req:
                if 0.8 > best_match:
                    best_match = 0.8
                    match_label = f"{req}~{cand}"
            else:
                # Partial word overlap
                req_words = set(req.split())
                cand_words = set(cand.split())
                common = req_words.intersection(cand_words)
                if common and len(common) >= 1:
                    score = len(common) / max(len(req_words), 1) * 0.5
                    if score > best_match:
                        best_match = score
                        match_label = f"{req} (partial)"

        if best_match > 0.0:
            total_score += min(best_match, 1.0)
            if match_label and match_label not in matched:
                matched.append(match_label)

    ratio = min(total_score / len(required_tokens), 1.0)
    return ratio, matched


# -----------------------------------------------------------------------------
# University Matching
# -----------------------------------------------------------------------------
def score_university_candidate(
    challenge: Dict[str, Any],
    analysis: Dict[str, Any],
    university: Dict[str, Any],
) -> Tuple[float, Dict[str, float], str]:
    """Calculates deterministic score (0-100) for a single university.

    Weights:
    skills = 25
    technologies = 25
    research = 15
    domain = 10
    primary_focus = 10
    departments = 5
    facilities = 3
    past_projects = 2
    """
    req_skills = extract_tokens(analysis.get("required_skills"))
    req_techs = extract_tokens(analysis.get("required_technologies"))
    req_domain = extract_tokens(analysis.get("category"))
    req_focus = extract_tokens(analysis.get("subcategory"))

    # Extract candidate fields directly from database row
    uni_skills = extract_tokens(university.get("skills"))
    uni_techs = extract_tokens(university.get("technologies"))
    uni_research = extract_tokens(university.get("research_areas"))
    uni_domain = extract_tokens(university.get("domain"))
    uni_focus = extract_tokens(university.get("primary_focus"))
    uni_depts = extract_tokens(university.get("departments"))
    uni_facilities = extract_tokens(university.get("facilities"))
    uni_past_projects = extract_tokens(university.get("past_project_ids"))

    # 1. Skills (25%)
    skill_ratio, matched_skills = calculate_overlap_ratio(req_skills, uni_skills)
    score_skills = round(25.0 * skill_ratio, 2)

    # 2. Technologies (25%)
    tech_ratio, matched_techs = calculate_overlap_ratio(req_techs, uni_techs)
    score_techs = round(25.0 * tech_ratio, 2)

    # 3. Research Areas (15%)
    research_ratio, _ = calculate_overlap_ratio(req_domain + req_focus, uni_research)
    score_research = round(15.0 * research_ratio, 2)

    # 4. Domain (10%)
    domain_ratio, _ = calculate_overlap_ratio(req_domain, uni_domain)
    score_domain = round(10.0 * domain_ratio, 2)

    # 5. Primary Focus (10%)
    focus_ratio, _ = calculate_overlap_ratio(req_focus, uni_focus)
    score_focus = round(10.0 * focus_ratio, 2)

    # 6. Departments (5%)
    dept_ratio, _ = calculate_overlap_ratio(req_domain, uni_depts)
    score_depts = round(5.0 * dept_ratio, 2)

    # 7. Facilities (3%)
    score_facilities = 3.0 if uni_facilities else 0.0

    # 8. Past Projects (2%)
    score_past_projects = 2.0 if uni_past_projects else 0.0

    raw_total = (
        score_skills
        + score_techs
        + score_research
        + score_domain
        + score_focus
        + score_depts
        + score_facilities
        + score_past_projects
    )

    # Essential capability gap penalty: if both core skills & techs are 0, penalize heavily
    if skill_ratio == 0.0 and tech_ratio == 0.0:
        raw_total = raw_total * 0.5

    final_score = round(min(max(raw_total, 0.0), 100.0), 2)

    breakdown = {
        "skills": score_skills,
        "technologies": score_techs,
        "research": score_research,
        "domain": score_domain,
        "primary_focus": score_focus,
        "departments": score_depts,
        "facilities": score_facilities,
        "past_projects": score_past_projects,
    }

    # Deterministic qualitative verdict label
    if final_score >= 90.0:
        verdict = "Exceptional Match"
    elif final_score >= 80.0:
        verdict = "Very Strong Match"
    elif final_score >= 70.0:
        verdict = "Strong Match"
    elif final_score >= 60.0:
        verdict = "Moderate Match"
    elif final_score >= 50.0:
        verdict = "Weak Match"
    else:
        verdict = "Low Alignment"

    skills_text = f"Matched skills: {', '.join(matched_skills[:3])}." if matched_skills else "No direct skills overlap."
    techs_text = f"Matched technologies: {', '.join(matched_techs[:3])}." if matched_techs else "No direct tech overlap."
    reason = (
        f"{verdict} ({final_score}/100). {skills_text} {techs_text} "
        f"Domain alignment: {score_domain}/10, Research overlap: {score_research}/15."
    )

    return final_score, breakdown, reason


def rank_universities(
    challenge: Dict[str, Any],
    analysis: Dict[str, Any],
    universities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Deterministically scores, ranks, and sorts all candidate universities."""
    scored_candidates = []

    challenge_id = challenge.get("challenge_id", "")

    for u in universities:
        score, breakdown, reason = score_university_candidate(challenge, analysis, u)
        scored_candidates.append({
            "challenge_id": challenge_id,
            "university_id": u["university_id"],
            "university_name": u.get("university_name") or u.get("name"),
            "city": u.get("city"),
            "district": u.get("district"),
            "match_score": score,
            "score_breakdown": breakdown,
            "match_reason": reason,
            "status": "recommended",
        })

    # Sort strictly descending by match_score; break ties deterministically by university_id
    scored_candidates.sort(key=lambda x: (-x["match_score"], x["university_id"]))

    # Assign rank 1, 2, 3...
    for i, c in enumerate(scored_candidates, start=1):
        c["rank"] = i

    return scored_candidates


# -----------------------------------------------------------------------------
# Industry Matching
# -----------------------------------------------------------------------------
def score_industry_candidate(
    challenge: Dict[str, Any],
    analysis: Dict[str, Any],
    industry: Dict[str, Any],
) -> Tuple[float, Dict[str, float], str]:
    """Calculates deterministic score (0-100) for a single industry candidate.

    Weights:
    skills = 22
    technologies = 22
    domain = 15
    deployment = 12
    resources = 10
    products_services = 8
    geography = 5
    CSR = 3
    past_projects = 3
    """
    req_skills = extract_tokens(analysis.get("required_skills"))
    req_techs = extract_tokens(analysis.get("required_technologies"))
    req_domain = extract_tokens(analysis.get("category"))

    challenge_city = normalize_token(challenge.get("city") or "")
    challenge_district = normalize_token(challenge.get("district") or "")

    # Extract industry fields directly from database row
    ind_skills = extract_tokens(industry.get("skills"))
    ind_techs = extract_tokens(industry.get("technologies"))
    ind_domain = extract_tokens(industry.get("domain"))
    ind_deploy = extract_tokens(industry.get("deployment_capabilities"))
    ind_resources = extract_tokens(industry.get("resource_capabilities"))
    ind_products = extract_tokens(industry.get("products_services"))
    ind_csr = extract_tokens(industry.get("csr_areas"))
    ind_past_projects = extract_tokens(industry.get("past_project_ids"))
    ind_city = normalize_token(industry.get("city") or "")
    ind_district = normalize_token(industry.get("district") or "")

    # 1. Skills (22%)
    skill_ratio, matched_skills = calculate_overlap_ratio(req_skills, ind_skills)
    score_skills = round(22.0 * skill_ratio, 2)

    # 2. Technologies (22%)
    tech_ratio, matched_techs = calculate_overlap_ratio(req_techs, ind_techs)
    score_techs = round(22.0 * tech_ratio, 2)

    # 3. Domain (15%)
    domain_ratio, _ = calculate_overlap_ratio(req_domain, ind_domain)
    score_domain = round(15.0 * domain_ratio, 2)

    # 4. Deployment Capabilities (12%)
    score_deploy = 12.0 if ind_deploy else 0.0

    # 5. Resource Capabilities (10%)
    score_resources = 10.0 if ind_resources else 0.0

    # 6. Products & Services (8%)
    product_ratio, _ = calculate_overlap_ratio(req_domain, ind_products)
    score_products = round(8.0 * product_ratio, 2)

    # 7. Geography (5%)
    if challenge_city and ind_city and challenge_city == ind_city:
        score_geo = 5.0
        geo_note = "Local presence in same city"
    elif challenge_district and ind_district and challenge_district == ind_district:
        score_geo = 4.0
        geo_note = "Presence in same district"
    else:
        score_geo = 1.0
        geo_note = "Regional/national operational coverage"

    # 8. CSR (3%)
    csr_ratio, _ = calculate_overlap_ratio(req_domain, ind_csr)
    score_csr = round(3.0 * csr_ratio, 2) if ind_csr else (1.5 if "csr" in (industry.get("industry_name") or "").lower() else 0.0)

    # 9. Past Projects (3%)
    score_past_projects = 3.0 if ind_past_projects else 0.0

    raw_total = (
        score_skills
        + score_techs
        + score_domain
        + score_deploy
        + score_resources
        + score_products
        + score_geo
        + score_csr
        + score_past_projects
    )

    # Essential capability gap penalty
    if skill_ratio == 0.0 and tech_ratio == 0.0:
        raw_total = raw_total * 0.5

    final_score = round(min(max(raw_total, 0.0), 100.0), 2)

    breakdown = {
        "skills": score_skills,
        "technologies": score_techs,
        "domain": score_domain,
        "deployment": score_deploy,
        "resources": score_resources,
        "products_services": score_products,
        "geography": score_geo,
        "CSR": score_csr,
        "past_projects": score_past_projects,
    }

    if final_score >= 90.0:
        verdict = "Exceptional Industry Partner"
    elif final_score >= 80.0:
        verdict = "Very Strong Industry Partner"
    elif final_score >= 70.0:
        verdict = "Strong Industry Partner"
    elif final_score >= 60.0:
        verdict = "Moderate Industry Partner"
    else:
        verdict = "Low Alignment"

    skills_text = f"Matched skills: {', '.join(matched_skills[:3])}." if matched_skills else "No direct skills overlap."
    reason = (
        f"{verdict} ({final_score}/100). {skills_text} "
        f"Domain alignment: {score_domain}/15. Deployment capability: {score_deploy}/12. {geo_note}."
    )

    return final_score, breakdown, reason


def rank_industries(
    challenge: Dict[str, Any],
    analysis: Dict[str, Any],
    industries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Deterministically scores, ranks, and sorts all candidate industries."""
    scored_candidates = []

    challenge_id = challenge.get("challenge_id", "")

    for ind in industries:
        score, breakdown, reason = score_industry_candidate(challenge, analysis, ind)
        scored_candidates.append({
            "challenge_id": challenge_id,
            "industry_id": ind["industry_id"],
            "industry_name": ind.get("industry_name") or ind.get("name"),
            "city": ind.get("city"),
            "district": ind.get("district"),
            "domain": ind.get("domain"),
            "match_score": score,
            "score_breakdown": breakdown,
            "match_reason": reason,
            "status": "recommended",
        })

    # Sort strictly descending by match_score; break ties deterministically by industry_id
    scored_candidates.sort(key=lambda x: (-x["match_score"], x["industry_id"]))

    # Assign rank 1, 2, 3...
    for i, c in enumerate(scored_candidates, start=1):
        c["rank"] = i

    return scored_candidates
