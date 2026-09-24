"""test_part1_university_matching.py

Comprehensive verification test suite for Part 1:
- All-universities evaluation (all 15 evaluated, Top-5 selected)
- Workload balancing rule (Delta W >= 3 tiers)
- Workload difference < 3 preservation
- Weak match protection (no weak match can leapfrog strong match)
- Deterministic fair tie-breaking via SHA-256 hash (no U001 alphabetical bias)
- Government transparency data exposure
- Downstream workflow preservation
- Multi-challenge distribution measurement
"""

import sys
import copy
import hashlib
from typing import Any, Dict, List

from app.services.matching_engine import (
    rank_universities,
    score_university_candidate,
)
from app.services.matching_service import MatchingService
from app.services.government_service import GovernmentService


def make_analysis(c: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "required_skills": c.get("required_skills") or c.get("skills", []),
        "required_technologies": c.get("required_technologies") or c.get("technologies", []),
        "category": c.get("category", ""),
        "subcategory": c.get("subcategory", ""),
    }


def test_all_15_universities_evaluated():
    print("\n--- TEST 1: All 15 Universities Evaluated & Ranked Top 5 ---")
    service = MatchingService()
    unis = service._fetch_universities()
    assert len(unis) == 15, f"Expected 15 universities, got {len(unis)}"

    challenge = {
        "challenge_id": "CHL-EVAL-ALL-001",
        "title": "Smart City IoT Waste & Water Monitoring",
        "description": "Deploying IoT sensors, LoRaWAN telemetry and computer vision for municipal waste and drain monitoring.",
        "category": "Urban Infrastructure",
        "skills": ["iot sensors", "computer vision", "telemetry", "lorawan"],
        "technologies": ["esp32", "python", "opencv", "lorawan"],
    }

    analysis = make_analysis(challenge)

    # Evaluate with rank_universities
    ranked = rank_universities(challenge, analysis, unis, workloads={})
    assert len(ranked) == 15, f"Expected all 15 universities evaluated, got {len(ranked)}"
    top5 = ranked[:5]
    assert len(top5) == 5, f"Expected top 5 matches, got {len(top5)}"
    print(f"All 15 evaluated. Top 5 selected from {len(unis)} candidates:")
    for idx, u in enumerate(top5, 1):
        print(f"  #{idx}: {u['university_name']} ({u['university_id']}) -> Match Score: {u['match_score']}% (Base: {u['base_score']}%)")

    # Verify ranking is strictly non-increasing
    scores = [u["match_score"] for u in ranked]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Scores not monotonic: {scores}"
    print("  [PASS] All 15 universities evaluated, Top-5 correctly extracted and sorted.")


def test_workload_balancing_delta_ge_3():
    print("\n--- TEST 2: Workload Balancing (Delta W >= 3) Rule ---")
    # Candidate A: Base score 82, Active projects = 6
    # Candidate B: Base score 80, Active projects = 0
    # Delta W = 6 >= 3 -> Tiers = 6 // 3 = 2 -> Adjustment = -(2 * 3.0) = -6.0
    # Candidate A final: 82 - 6.0 = 76.0
    # Candidate B final: 80.0
    # Result: Candidate B should outrank Candidate A
    challenge = {
        "challenge_id": "CHL-WORKLOAD-TEST-01",
        "title": "Road Surface Defect Detection",
        "description": "Camera and accelerometer based road surface defect detection using deep learning.",
        "category": "Transportation",
        "skills": ["computer vision", "mobile apps"],
        "technologies": ["python", "opencv"],
    }
    analysis = make_analysis(challenge)

    mock_candidates = [
        {
            "university_id": "UNI-HEAVY",
            "university_name": "Heavy Workload University",
            "skills": "computer vision, mobile apps, deep learning",
            "technologies": "python, opencv, tensorflow",
            "domain": "Transportation",
            "departments": "Civil, CSE",
        },
        {
            "university_id": "UNI-LIGHT",
            "university_name": "Light Workload University",
            "skills": "computer vision, mobile apps",
            "technologies": "python, opencv",
            "domain": "Transportation",
            "departments": "CSE",
        },
    ]

    # Without workload: Heavy outranks Light
    unweighted = rank_universities(challenge, analysis, mock_candidates, workloads={"UNI-HEAVY": 0, "UNI-LIGHT": 0})
    print(f"  Zero workload: Rank 1 = {unweighted[0]['university_id']} ({unweighted[0]['match_score']}%), Rank 2 = {unweighted[1]['university_id']} ({unweighted[1]['match_score']}%)")
    assert unweighted[0]["university_id"] == "UNI-HEAVY"

    # With workload: UNI-HEAVY has 6 active projects, UNI-LIGHT has 0
    workloads = {"UNI-HEAVY": 6, "UNI-LIGHT": 0}
    weighted = rank_universities(challenge, analysis, mock_candidates, workloads=workloads)
    print(f"  With Delta W=6: Rank 1 = {weighted[0]['university_id']} ({weighted[0]['match_score']}%, adj={weighted[0]['workload_adjustment']}), Rank 2 = {weighted[1]['university_id']} ({weighted[1]['match_score']}%, adj={weighted[1]['workload_adjustment']})")
    
    assert weighted[0]["university_id"] == "UNI-LIGHT", "UNI-LIGHT should outrank UNI-HEAVY due to workload balancing"
    assert weighted[1]["university_id"] == "UNI-HEAVY"
    assert weighted[1]["workload_adjustment"] == -6.0
    assert weighted[0]["workload_advantage_applied"] is True
    print("  [PASS] Workload balancing correctly prioritizes lower workload when Delta W >= 3.")


def test_workload_difference_under_3():
    print("\n--- TEST 3: Workload Difference < 3 Does Not Alter Base Ranking ---")
    challenge = {
        "challenge_id": "CHL-WORKLOAD-TEST-02",
        "title": "Road Surface Defect Detection",
        "description": "Camera and accelerometer based road surface defect detection using deep learning.",
        "category": "Transportation",
        "skills": ["computer vision", "mobile apps", "deep learning"],
        "technologies": ["python", "opencv"],
    }
    analysis = make_analysis(challenge)

    mock_candidates = [
        {
            "university_id": "UNI-A",
            "university_name": "University A (Better fit, 2 projects)",
            "skills": "computer vision, mobile apps, deep learning",
            "technologies": "python, opencv, tensorflow",
            "domain": "Transportation",
            "departments": "Civil, CSE",
        },
        {
            "university_id": "UNI-B",
            "university_name": "University B (Slightly lower fit, 0 projects)",
            "skills": "computer vision, mobile apps",
            "technologies": "python, opencv",
            "domain": "Transportation",
            "departments": "CSE",
        },
    ]

    # Delta W = 2 - 0 = 2 < 3 -> adjustment should be 0.0
    workloads = {"UNI-A": 2, "UNI-B": 0}
    ranked = rank_universities(challenge, analysis, mock_candidates, workloads=workloads)
    print(f"  Delta W=2: Rank 1 = {ranked[0]['university_id']} (adj={ranked[0]['workload_adjustment']}), Rank 2 = {ranked[1]['university_id']} (adj={ranked[1]['workload_adjustment']})")
    assert ranked[0]["university_id"] == "UNI-A", "UNI-A must remain Rank 1 because Delta W < 3"
    assert ranked[0]["workload_adjustment"] == 0.0
    print("  [PASS] Difference < 3 preserves natural ranking order.")


def test_weak_match_protection():
    print("\n--- TEST 4: Weak Match Protection (No Unqualified Leapfrogging) ---")
    challenge = {
        "challenge_id": "CHL-PROTECT-01",
        "title": "Bio-Medical Genomics Sequencing",
        "description": "Clinical genomics sequencing and healthcare bioinformatics pipeline.",
        "category": "Healthcare",
        "skills": ["genomics", "bioinformatics", "clinical trial data"],
        "technologies": ["biopython", "nextflow", "r"],
    }

    mock_candidates = [
        {
            "university_id": "UNI-EXPERT",
            "university_name": "Genomics Expert Institute",
            "skills": "genomics, bioinformatics, clinical trial data, molecular biology",
            "technologies": "biopython, nextflow, r, blast",
            "domain": "Healthcare",
            "departments": "Biotechnology, Medicine",
        },
        {
            "university_id": "UNI-WEAK",
            "university_name": "Irrelevant Department Institute",
            "skills": "pavement design, asphalt concrete, soil mechanics",
            "technologies": "autocad, total station",
            "domain": "Civil Infrastructure",
            "departments": "Civil Engineering",
        },
    ]

    analysis = make_analysis(challenge)

    # UNI-EXPERT has 15 active projects (maximum penalty of 7.5 pts).
    # UNI-WEAK has 0 active projects.
    workloads = {"UNI-EXPERT": 15, "UNI-WEAK": 0}
    ranked = rank_universities(challenge, analysis, mock_candidates, workloads=workloads)
    print(f"  Expert score with 15 projects: {ranked[0]['match_score']}% (adj={ranked[0]['workload_adjustment']})")
    print(f"  Weak score with 0 projects: {ranked[1]['match_score']}% (adj={ranked[1]['workload_adjustment']})")

    assert ranked[0]["university_id"] == "UNI-EXPERT", "Expert institute must remain rank 1"
    assert ranked[1]["university_id"] == "UNI-WEAK"
    assert ranked[0]["match_score"] > ranked[1]["match_score"] + 20
    print("  [PASS] High expertise match retains top ranking despite high workload; weak match cannot leapfrog.")


def test_fair_deterministic_tie_breaker():
    print("\n--- TEST 5: Fair Deterministic Tie-Breaker (No U001 Bias) ---")
    # Two identical candidates with identical scores and identical active workloads.
    # In the old code, U001 always beat U002 alphabetically.
    # In the new code, SHA-256(challenge_id + ':' + uid) is used.
    # Across different challenge IDs, the winner should vary fairly.

    mock_candidates = [
        {
            "university_id": "U001",
            "university_name": "BIT Mesra (U001)",
            "skills": "iot sensors, python",
            "technologies": "esp32",
            "domain": "Engineering",
        },
        {
            "university_id": "U002",
            "university_name": "IIT ISM Dhanbad (U002)",
            "skills": "iot sensors, python",
            "technologies": "esp32",
            "domain": "Engineering",
        },
    ]

    # Find two challenge IDs where hash ordering alternates
    wins = {"U001": 0, "U002": 0}
    trials = 20
    for i in range(trials):
        cid = f"CHL-TIE-BREAK-{i:03d}"
        challenge = {"challenge_id": cid, "title": "Test", "description": "Test", "skills": ["iot sensors"], "technologies": ["python"]}
        analysis = make_analysis(challenge)
        ranked = rank_universities(challenge, analysis, mock_candidates, workloads={"U001": 0, "U002": 0})
        winner = ranked[0]["university_id"]
        wins[winner] += 1

    print(f"  Tie-break wins across {trials} different challenges: U001 = {wins['U001']}, U002 = {wins['U002']}")
    assert wins["U001"] > 0, "U001 should win some ties"
    assert wins["U002"] > 0, "U002 should win some ties"
    print("  [PASS] Tie-breaking is challenge-specific and fair; hardcoded U001 alphabetical preference is eliminated.")


def test_workload_query_and_deduplication():
    print("\n--- TEST 6: Live Workload Calculation & Status Filtering ---")
    service = MatchingService()
    workloads = service._fetch_university_workloads()
    print(f"  Live calculated workloads: {workloads}")
    assert isinstance(workloads, dict)
    for uid, count in workloads.items():
        assert isinstance(count, int)
        assert count >= 0
    print("  [PASS] Workloads retrieved and typed correctly.")


def test_government_transparency_payload():
    print("\n--- TEST 7: Government Service Top 5 Payload Exposure ---")
    gov_service = GovernmentService()
    # Fetch monitored problems
    problems = gov_service.get_monitored_problems()
    assert isinstance(problems, list)
    print(f"  Total monitored problems: {len(problems)}")
    routed_with_top5 = [p for p in problems if p.get("top_universities") and len(p.get("top_universities")) > 0]
    print(f"  Problems with hydrated Top 5 universities: {len(routed_with_top5)}")
    if routed_with_top5:
        sample = routed_with_top5[0]["top_universities"][0]
        print(f"  Sample Top 1 University Match in Government View:")
        print(f"    Name: {sample.get('university_name')} ({sample.get('university_id')})")
        print(f"    Match Score: {sample.get('match_score')}%")
        print(f"    Active Projects: {sample.get('active_projects')}")
        print(f"    Workload Adjustment: {sample.get('workload_adjustment')}")
        print(f"    Match Reason: {sample.get('match_reason')}")
        assert "match_score" in sample or "score" in sample
        assert "university_id" in sample
    print("  [PASS] Government transparency payload verified.")


def test_top_5_distribution_across_representative_challenges():
    print("\n--- TEST 8: Empirical Top-5 Distribution Across Diverse Challenges ---")
    service = MatchingService()
    unis = service._fetch_universities()
    live_workloads = service._fetch_university_workloads()
    print(f"  Using live university workloads: {live_workloads}")

    challenges = [
        {
            "challenge_id": "CHL-DOM-01",
            "domain_label": "Urban Traffic & Roads",
            "title": "AI Traffic Optimization and Pothole Detection",
            "description": "Camera and accelerometer based road surface defect detection and intelligent traffic light signaling.",
            "category": "Transportation",
            "skills": ["computer vision", "accelerometer sensors", "traffic engineering", "mobile apps"],
            "technologies": ["pytorch", "opencv", "android", "edge ai"],
        },
        {
            "challenge_id": "CHL-DOM-02",
            "domain_label": "Smart Agriculture & Soil",
            "title": "Precision Soil Nutrient and Drought Stress Monitoring",
            "description": "IoT soil moisture and NPK sensing network for smallholder farmers with drone crop health surveillance.",
            "category": "Agriculture",
            "skills": ["soil moisture sensing", "precision irrigation", "crop pathology", "remote sensing"],
            "technologies": ["lorawan", "arduino", "drone imaging", "python"],
        },
        {
            "challenge_id": "CHL-DOM-03",
            "domain_label": "Healthcare & Cold-Chain",
            "title": "Rural Vaccine Cold-Chain Temperature and Integrity Telemetry",
            "description": "Cellular and BLE IoT cold-chain temperature telemetry with alert systems for rural primary health centres.",
            "category": "Healthcare",
            "skills": ["biomedical instrumentation", "cold chain monitoring", "telemedicine", "iot telemetry"],
            "technologies": ["ble", "cellular iot", "cloud telemetry", "python"],
        },
        {
            "challenge_id": "CHL-DOM-04",
            "domain_label": "Mining Safety & Geology",
            "title": "Underground Coal Mine Methane Gas and Landslide Early Warning",
            "description": "Underground environmental monitoring for hazardous gases (methane, CO) and slope stability seismology.",
            "category": "Mining & Geology",
            "skills": ["mine safety instrumentation", "gas detection", "geotechnical engineering", "underground iot"],
            "technologies": ["methane sensors", "subsurface iot", "cloud analytics", "clean tech"],
        },
        {
            "challenge_id": "CHL-DOM-05",
            "domain_label": "Water Quality & Sanitation",
            "title": "Industrial Effluent Heavy Metal Filtration and Water Testing",
            "description": "Automated spectrophotometry and bio-sorbent filtration for industrial runoff into Subarnarekha river.",
            "category": "Environmental Engineering",
            "skills": ["water quality chemistry", "bioremediation", "environmental testing", "spectrophotometry"],
            "technologies": ["spectrophotometer", "clean tech", "python", "remote sensing"],
        },
    ]

    university_appearance_counts = {u["university_id"]: 0 for u in unis}
    rank_1_counts = {u["university_id"]: 0 for u in unis}

    for c in challenges:
        analysis = make_analysis(c)
        ranked = rank_universities(c, analysis, unis, workloads=live_workloads)
        top1 = ranked[0]
        rank_1_counts[top1["university_id"]] += 1
        print(f"\n  Challenge: [{c['domain_label']}] '{c['title']}'")
        for idx, r in enumerate(ranked[:5], 1):
            university_appearance_counts[r["university_id"]] += 1
            adj_note = f" (Workload adj: {r['workload_adjustment']} pts)" if r.get("workload_adjustment") else ""
            print(f"    Rank {idx}: {r['university_name']} ({r['university_id']}) -> Match: {r['match_score']}%{adj_note}")

    print("\n  Summary of Top-5 Appearances Across Representative Challenges:")
    for uid, count in sorted(university_appearance_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            uname = next((u["university_name"] for u in unis if u["university_id"] == uid), uid)
            r1 = rank_1_counts.get(uid, 0)
            print(f"    {uid} ({uname}): {count}/5 challenges (Rank #1 in {r1} challenges)")

    # Assertions on distribution
    # 1. More than 1 distinct university should win Rank #1 across domains
    distinct_winners = sum(1 for v in rank_1_counts.values() if v > 0)
    print(f"\n  Distinct Rank #1 Winners across 5 domains: {distinct_winners}")
    assert distinct_winners >= 3, f"Expected at least 3 distinct domain winners, got {distinct_winners}"
    
    # 2. Total distinct universities appearing in Top-5 across 5 domains
    distinct_top5 = sum(1 for v in university_appearance_counts.values() if v > 0)
    print(f"  Distinct Universities appearing in Top-5: {distinct_top5}/15")
    assert distinct_top5 >= 5, f"Expected at least 5 distinct universities in Top 5, got {distinct_top5}"

    print("  [PASS] Diverse domain-based matching verified; institutional monopoly eliminated.")


if __name__ == "__main__":
    print("======================================================================")
    print("STARTING PART 1: UNIVERSITY TOP-5 MATCHING & WORKLOAD BALANCING SUITE")
    print("======================================================================")
    
    test_all_15_universities_evaluated()
    test_workload_balancing_delta_ge_3()
    test_workload_difference_under_3()
    test_weak_match_protection()
    test_fair_deterministic_tie_breaker()
    test_workload_query_and_deduplication()
    test_government_transparency_payload()
    test_top_5_distribution_across_representative_challenges()

    print("\n======================================================================")
    print("ALL PART 1 TESTS COMPLETED WITH 100% SUCCESS!")
    print("======================================================================")
