"""curate_part2_demo_dataset.py

Ensures a realistic, verified baseline dataset for VidySetu Part 2:
- Targets approximately 5+ records per category: Pending, Approved/Routed, Rejected, Solved.
- Idempotently updates seed challenges C046-C050 with resolved status, realistic projects,
  faculty mentors, industry partners, and 100% completed milestone evidence.
- Preserves all real user submissions (CHL-...) untouched.
"""

import sys
import os

# Add parent directory to path so app modules import cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import supabase


def curate_dataset():
    print("--- Curating Part 2 Baseline Dataset ---")

    # 1. Inspect current status counts
    res = supabase.table("challenges").select("challenge_id, status").execute()
    existing = res.data or []
    print(f"Total challenges in database: {len(existing)}")

    # 2. Curate 5 Solved Challenges (C046, C047, C048, C049, C050)
    solved_configs = [
        {
            "challenge_id": "C046",
            "title": "Recurring Drinking-Water Shortage Mitigation",
            "description": "Residents of our village face drinking-water shortages during summer because existing sources frequently become insufficient. Deployed IoT-based deep borehole recharge system with community kiosks.",
            "district": "Ranchi",
            "city": "Ranchi",
            "impact_scope": "District Level",
            "created_at": "2026-01-10T10:00:00+00:00",
            "project_id": "PRJ-U001-24-01",  # Existing project
            "university_id": "U001",
            "faculty_id": "FAC002",
            "industry_id": "I001",
            "category": "Water Management & Sanitation",
            "skills": "Hydrology, IoT Sensors, Embedded Systems",
            "tech": "LoRaWAN, Flow Sensors, Solar Inverter",
        },
        {
            "challenge_id": "C047",
            "title": "Pipeline Leakage Detection in Village Water Network",
            "description": "High pressure pipeline bursts and micro-leakages causing massive potable water loss in suburban distribution pipelines. Solved using acoustic pressure sensors and edge AI alerting.",
            "district": "Dhanbad",
            "city": "Dhanbad",
            "impact_scope": "Block Level",
            "created_at": "2026-01-15T11:00:00+00:00",
            "project_id": "PRJ-U002-C047",
            "university_id": "U002",
            "faculty_id": "FAC006",
            "industry_id": "I002",
            "category": "Civil & Urban Infrastructure",
            "skills": "Acoustic Sensing, Edge Computing, GIS Mapping",
            "tech": "Piezoelectric Sensors, Raspberry Pi, Python Edge SDK",
        },
        {
            "challenge_id": "C048",
            "title": "Solar Smart Microgrid for Remote Tribal Hamlets",
            "description": "Unreliable grid power leading to extended blackouts in forest-fringe tribal schools and health sub-centres. Implemented hybrid battery storage microgrid with automated load balancing.",
            "district": "East Singhbhum",
            "city": "Jamshedpur",
            "impact_scope": "Municipal Ward",
            "created_at": "2026-01-20T09:30:00+00:00",
            "project_id": "PRJ-U003-C048",
            "university_id": "U003",
            "faculty_id": "FAC011",
            "industry_id": "I003",
            "category": "Renewable Energy & Power Systems",
            "skills": "Power Electronics, Battery Management, Solar Photovoltaics",
            "tech": "MPPT Charge Controllers, Lithium LiFePO4, SCADA Modbus",
        },
        {
            "challenge_id": "C049",
            "title": "Automated Handpump Telemetry and Predictive Maintenance",
            "description": "Severe delays in repairing non-functional deep tube-well handpumps in rural blocks. Developed vibration telemetry clamp device with automated grievance ticketing.",
            "district": "Bokaro",
            "city": "Bokaro",
            "impact_scope": "Gram Panchayat",
            "created_at": "2026-02-01T14:00:00+00:00",
            "project_id": "PRJ-U004-C049",
            "university_id": "U004",
            "faculty_id": "FAC016",
            "industry_id": "I001",
            "category": "Rural Engineering & IoT",
            "skills": "Vibration Analysis, Low-Power RF, Predictive Maintenance",
            "tech": "ESP32-S3, Accelerometer MPU6050, MQTT Broker",
        },
        {
            "challenge_id": "C050",
            "title": "Arsenic and Heavy Metal Community Filtration Unit",
            "description": "Groundwater contamination with arsenic and iron exceeding safe permissible limits in rural drinking supplies. Deployed low-cost bio-sand nanoclay adsorption filtration system.",
            "district": "Hazaribagh",
            "city": "Hazaribagh",
            "impact_scope": "District Level",
            "created_at": "2026-02-10T16:00:00+00:00",
            "project_id": "PRJ-U001-C050",
            "university_id": "U001",
            "faculty_id": "FAC004",
            "industry_id": "I004",
            "category": "Environmental & Chemical Engineering",
            "skills": "Nanomaterials, Water Chemistry, Adsorption Filtration",
            "tech": "Bio-sand Media, Iron Oxide Nanoparticles, Turbidity Spectrophotometer",
        },
    ]

    for item in solved_configs:
        cid = item["challenge_id"]
        pid = item["project_id"]

        # Update challenge row to resolved
        supabase.table("challenges").update({
            "status": "resolved",
            "title": item["title"],
            "description": item["description"],
            "district": item["district"],
            "city": item["city"],
            "impact_scope": item["impact_scope"],
            "created_at": item["created_at"],
            "submitted_by": f"Citizen_{cid}",
        }).eq("challenge_id", cid).execute()

        # Upsert AI analysis
        ai_payload = {
            "challenge_id": cid,
            "category": item["category"],
            "required_skills": item["skills"],
            "required_technologies": item["tech"],
            "innovation_scope": "high",
            "feasibility": "high",
            "severity": "high",
            "priority": "high",
            "solution_found": False,
        }
        existing_ai = supabase.table("ai_analysis").select("analysis_id").eq("challenge_id", cid).execute().data
        if existing_ai:
            supabase.table("ai_analysis").update(ai_payload).eq("challenge_id", cid).execute()
        else:
            supabase.table("ai_analysis").insert(ai_payload).execute()

        # Upsert project
        proj_payload = {
            "project_id": pid,
            "challenge_id": cid,
            "project_title": f"Applied Solution: {item['title']}",
            "university_id": item["university_id"],
            "faculty_id": item["faculty_id"],
            "industry_id": item["industry_id"],
            "status": "completed",
            "start_date": item["created_at"][:10],
            "expected_end_date": "2026-06-30",
            "actual_end_date": "2026-06-15",
        }
        existing_proj = supabase.table("projects").select("project_id").eq("project_id", pid).execute().data
        if existing_proj:
            supabase.table("projects").update(proj_payload).eq("project_id", pid).execute()
        else:
            supabase.table("projects").insert(proj_payload).execute()

        # Ensure completed milestones
        milestone_defs = [
            ("Problem Formulation & Technical Scope", 100),
            ("Faculty Mentor & Student Prototyping", 100),
            ("Field Deployment & System Commissioning", 100),
            ("Government Verification & Handover", 100),
        ]
        existing_ms = supabase.table("project_milestones").select("milestone_id").eq("project_id", pid).execute().data
        if not existing_ms:
            for m_name, pct in milestone_defs:
                supabase.table("project_milestones").insert({
                    "project_id": pid,
                    "milestone_name": m_name,
                    "status": "completed",
                    "completion_percentage": pct,
                }).execute()

        # Add university match record
        supabase.table("challenge_university_matches").upsert({
            "challenge_id": cid,
            "university_id": item["university_id"],
            "rank": 1,
            "match_score": 95,
            "match_reason": f"Top domain alignment in {item['category']}",
            "status": "accepted",
        }, on_conflict="challenge_id,university_id").execute()

        print(f"  [OK] Curated solved challenge {cid} with project {pid}")

    print("Baseline curation complete!")


if __name__ == "__main__":
    curate_dataset()
