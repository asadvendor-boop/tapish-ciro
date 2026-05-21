"""
PSER (Punjab Socio-Economic Registry) tool — fetches vulnerability data per neighborhood.
Called by Analyst and Strategist Agents for equity-weighted decisions.
"""

import json
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"


def get_pser_vulnerability(neighborhood: str) -> str:
    """Get PSER socioeconomic vulnerability data for a Lahore neighborhood.
    Returns poverty score, vulnerability index, population density, AC penetration, and demographics.
    
    Args:
        neighborhood: The neighborhood to check (e.g. 'walled_city', 'dha_phase_5')
    """
    try:
        with open(MOCK_DIR / "pser_data.json") as f:
            data = json.load(f)
        
        neighborhood_key = neighborhood.lower().replace(" ", "_").replace("-", "_")
        neighborhood_data = data.get("neighborhoods", {}).get(neighborhood_key)
        
        if not neighborhood_data:
            for key in data.get("neighborhoods", {}):
                if neighborhood_key in key or key in neighborhood_key:
                    neighborhood_data = data["neighborhoods"][key]
                    neighborhood_key = key
                    break
        
        if not neighborhood_data:
            return json.dumps({"error": f"No PSER data for '{neighborhood}'", "available": list(data.get("neighborhoods", {}).keys())})
        
        return json.dumps({
            "neighborhood": neighborhood_key,
            **neighborhood_data,
            "interpretation": _interpret_vulnerability(neighborhood_data),
        })
    except Exception as e:
        return json.dumps({"error": "PSER_FETCH_FAILURE", "details": str(e)})


def _interpret_vulnerability(data: dict) -> str:
    """Human-readable interpretation of PSER data for agent reasoning."""
    score = data.get("vulnerability_score", 0.5)
    ac = data.get("ac_penetration_pct", 50)
    density = data.get("population_density_per_sqkm", 10000)
    
    if score > 0.8:
        return f"EXTREMELY VULNERABLE. Poverty score {data.get('pser_poverty_score')}/100 (lower=poorer). Only {ac}% AC penetration. {density} people/sq km. Priority: MAXIMUM."
    elif score > 0.6:
        return f"HIGH VULNERABILITY. Poverty score {data.get('pser_poverty_score')}/100. {ac}% AC penetration. {density} people/sq km. Priority: HIGH."
    elif score > 0.4:
        return f"MODERATE VULNERABILITY. Poverty score {data.get('pser_poverty_score')}/100. {ac}% AC penetration. Priority: STANDARD."
    else:
        return f"LOW VULNERABILITY. Poverty score {data.get('pser_poverty_score')}/100. {ac}% AC penetration. Community has resources for self-response."
