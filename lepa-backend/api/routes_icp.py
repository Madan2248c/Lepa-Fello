"""
ICP Profile and Business Profile API routes.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Header
from pydantic import BaseModel

logger = logging.getLogger("lepa.api.icp")

router = APIRouter(tags=["icp"])


class ICPProfileRequest(BaseModel):
    target_industries: List[str] = []
    target_locations: List[str] = []
    target_company_sizes: List[str] = []
    target_roles: List[str] = []


class BusinessProfileRequest(BaseModel):
    business_name: str = ""
    business_description: str = ""
    product_service: str = ""
    value_proposition: str = ""


@router.post("/icp")
async def save_icp(
    profile: ICPProfileRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import save_icp_profile
    await save_icp_profile(
        tenant_id,
        profile.target_industries,
        profile.target_locations,
        profile.target_company_sizes,
        profile.target_roles,
    )
    # Also update in-memory cache
    from services.icp_profile import store_icp_profile
    store_icp_profile(tenant_id, profile.model_dump())
    return {"status": "success"}


@router.get("/icp")
async def get_icp(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import get_icp_profile
    profile = await get_icp_profile(tenant_id)
    return {"profile": profile or {"target_industries": [], "target_locations": [], "target_company_sizes": [], "target_roles": []}}


@router.post("/business-profile")
async def save_business(
    profile: BusinessProfileRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import save_business_profile
    await save_business_profile(
        tenant_id,
        profile.business_name,
        profile.business_description,
        profile.product_service,
        profile.value_proposition,
    )
    return {"status": "success"}


@router.get("/business-profile")
async def get_business(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import get_business_profile
    profile = await get_business_profile(tenant_id)
    return {"profile": profile or {"business_name": "", "business_description": "", "product_service": "", "value_proposition": ""}}
