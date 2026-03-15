"""
ICP (Ideal Customer Profile) management.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone

# In-memory storage for ICP profiles
_icp_profiles: Dict[str, Dict[str, Any]] = {}

def store_icp_profile(tenant_id: str, profile: Dict[str, List[str]]) -> None:
    """Store ICP profile for a tenant."""
    _icp_profiles[tenant_id] = {
        "profile": profile,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

def get_icp_profile(tenant_id: str) -> Dict[str, List[str]]:
    """Get ICP profile for a tenant."""
    stored = _icp_profiles.get(tenant_id, {})
    return stored.get("profile", {
        "target_industries": [],
        "target_locations": [],
        "target_company_sizes": [],
        "target_roles": []
    })

def calculate_icp_fit_score(tenant_id: str, company_data: Dict[str, Any]) -> float:
    """Calculate how well a company fits the ICP (0-10 scale)."""
    icp = get_icp_profile(tenant_id)
    score = 0.0
    max_score = 0.0
    
    # Industry match (25% weight)
    if icp["target_industries"]:
        max_score += 2.5
        company_industry = company_data.get("industry", "").lower()
        for target_industry in icp["target_industries"]:
            if target_industry.lower() in company_industry or company_industry in target_industry.lower():
                score += 2.5
                break
    
    # Location match (25% weight)
    if icp["target_locations"]:
        max_score += 2.5
        company_location = company_data.get("location", "").lower()
        for target_location in icp["target_locations"]:
            if target_location.lower() in company_location or company_location in target_location.lower():
                score += 2.5
                break
    
    # Company size match (25% weight)
    if icp["target_company_sizes"]:
        max_score += 2.5
        company_size = company_data.get("employees", "")
        # Simple size matching logic
        for target_size in icp["target_company_sizes"]:
            if target_size.lower() in str(company_size).lower():
                score += 2.5
                break
    
    # Role match (25% weight) - check if any buying committee members match target roles
    if icp["target_roles"]:
        max_score += 2.5
        buying_committee = company_data.get("buying_committee", [])
        for member in buying_committee:
            member_title = member.get("title", "").lower()
            for target_role in icp["target_roles"]:
                if target_role.lower() in member_title or member_title in target_role.lower():
                    score += 2.5
                    break
            else:
                continue
            break
    
    # Return score out of 10, or 5.0 if no ICP criteria set
    if max_score == 0:
        return 5.0
    
    return min(10.0, (score / max_score) * 10.0)
