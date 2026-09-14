"""evidence_catalog.py

Curated catalog of verified, real-world Indian government initiatives, public platforms,
and civic solutions. Used for existing-solution discovery to guarantee that the platform
never fabricates or hallucinates fictional solutions, URLs, companies, or facts.
"""

from typing import Any, Dict, List, Optional

VERIFIED_REAL_SOLUTIONS: List[Dict[str, Any]] = [
    {
        "id": "SOL-GOV-01",
        "name": "Swachhata App (MoHUA)",
        "agency": "Ministry of Housing and Urban Affairs (MoHUA), Govt of India",
        "description": "Official citizen grievance redressal platform for municipal garbage dumps, overflowing dustbins, uncollected waste, and public toilet cleanliness.",
        "verified_scope": "Urban Local Bodies (ULBs) across India",
        "technologies": ["Mobile App", "GPS Geo-tagging", "Municipal Ticketing Workflow"],
        "keywords": [
            "garbage", "waste", "trash", "dustbin", "litter", "cleanliness",
            "sanitation", "dump", "solid waste", "kachra", "safai"
        ],
        "category": "Waste Management & Sanitation",
    },
    {
        "id": "SOL-GOV-02",
        "name": "CPGRAMS (Centralized Public Grievance Redress and Monitoring System)",
        "agency": "Department of Administrative Reforms and Public Grievances (DARPG)",
        "description": "Nationwide portal connecting citizens with Central Ministries, Departments, and State Governments to address administrative service delays and grievances.",
        "verified_scope": "Central and State Ministries",
        "technologies": ["Web Portal", "Automated Ticketing", "AI Grievance Categorization"],
        "keywords": [
            "grievance", "complaint", "corruption", "pension", "administrative delay",
            "government service", "ration card delay", "portal issue"
        ],
        "category": "Public Administration & Governance",
    },
    {
        "id": "SOL-GOV-03",
        "name": "Jal Jeevan Mission (Har Ghar Jal)",
        "agency": "Department of Drinking Water and Sanitation, Ministry of Jal Shakti",
        "description": "National program providing functional household tap connections (FHTC) in rural villages, accompanied by water quality testing kits (FTKs) and community surveillance.",
        "verified_scope": "Rural habitations across all States and UTs",
        "technologies": ["IoT Water Flow Sensors", "Field Test Kits (FTK)", "Public Water Quality Portal"],
        "keywords": [
            "water supply", "drinking water", "tap water", "water pipeline",
            "borewell dry", "fluoride contamination", "pani", "jal"
        ],
        "category": "Water Resources & Supply",
    },
    {
        "id": "SOL-GOV-04",
        "name": "PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan)",
        "agency": "Ministry of New and Renewable Energy (MNRE)",
        "description": "Government scheme providing subsidized standalone solar agricultural pumps and solarization of grid-connected farm feeders for farmers.",
        "verified_scope": "Rural agricultural areas nationwide",
        "technologies": ["Solar Photovoltaics", "Solar Water Pumping", "Grid-tied Feeders"],
        "keywords": [
            "solar pump", "irrigation electricity", "agricultural power", "farm power outage",
            "diesel pump cost", "farmer electricity subsidy", "kisan urja"
        ],
        "category": "Renewable Energy & Agriculture",
    },
    {
        "id": "SOL-GOV-05",
        "name": "PRANA (Portal for Regulation of Air-pollution in Non-Attainment cities)",
        "agency": "Ministry of Environment, Forest and Climate Change (MoEFCC)",
        "description": "Real-time monitoring and city action plan tracking under the National Clean Air Programme (NCAP) for particulate matter (PM10/PM2.5) abatement.",
        "verified_scope": "132 non-attainment and million-plus cities",
        "technologies": ["Continuous Ambient Air Quality Monitoring (CAAQMS)", "Sensor Networks", "Data Dashboards"],
        "keywords": [
            "air pollution", "smog", "aqi", "dust pollution", "smoke", "particulate matter",
            "vehicular emission", "industrial smoke", "stubble burning"
        ],
        "category": "Air Quality & Environment",
    },
    {
        "id": "SOL-GOV-06",
        "name": "PM SVANidhi (PM Street Vendor's AtmaNirbhar Nidhi)",
        "agency": "Ministry of Housing and Urban Affairs (MoHUA)",
        "description": "Digital credit and social security onboarding for urban street vendors, providing micro-loans and digital transaction cashbacks.",
        "verified_scope": "Urban street vendors across Indian cities",
        "technologies": ["Direct Benefit Transfer (DBT)", "QR Code Payments", "Digital Identity"],
        "keywords": [
            "street vendor", "hawker", "thela", "vendor loan", "informal market",
            "microcredit for vendors"
        ],
        "category": "Livelihood & Urban Commerce",
    },
    {
        "id": "SOL-GOV-07",
        "name": "Bhuvan Geoportal",
        "agency": "National Remote Sensing Centre (NRSC) / Indian Space Research Organisation (ISRO)",
        "description": "Geospatial platform providing satellite imagery, disaster flood inundation maps, landslide risk assessments, and thematic land-use maps.",
        "verified_scope": "National territorial and marine coverage",
        "technologies": ["Satellite Remote Sensing", "GIS Mapping", "Spatial Analysis"],
        "keywords": [
            "satellite mapping", "flood mapping", "drainage survey", "gis land survey",
            "geospatial data", "disaster vulnerability map"
        ],
        "category": "Geospatial & Disaster Management",
    },
]


def find_verified_existing_solution(title: str, description: str) -> Optional[Dict[str, Any]]:
    """Evaluates problem text against verified, real-world public solutions.

    Returns the matching real solution record if high factual correlation exists,
    or None if no verified solution directly addresses the challenge.
    Never invents or fabricates entities.
    """
    text = f"{title} {description}".lower()

    best_match = None
    max_hits = 0

    for sol in VERIFIED_REAL_SOLUTIONS:
        hits = sum(1 for kw in sol["keywords"] if kw in text)
        if hits >= 2 and hits > max_hits:
            max_hits = hits
            best_match = sol

    return best_match
