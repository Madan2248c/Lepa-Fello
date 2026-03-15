"""
LEPA Backend - AI Account Intelligence API

FastAPI application providing account intelligence and enrichment
for sales teams. Powered by Strands Agents SDK and Amazon Bedrock.
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("lepa")

from api.routes_analyze import router as analyze_router
from api.routes_batch import router as batch_router
from api.routes_crm import router as crm_router
from api.routes_icp import router as icp_router
from api.routes_contacts import router as contacts_router
from api.routes_history import router as history_router
from api.routes_tracker import router as tracker_router
from api.routes_tracker_keys import router as tracker_keys_router
from api.routes_hubspot_connection import router as hubspot_connection_router
from api.routes_assistant import router as assistant_router


def validate_config():
    """Validate required configuration on startup."""
    warnings = []
    
    if not os.getenv("AWS_PROFILE") and not os.getenv("AWS_ACCESS_KEY_ID"):
        warnings.append("AWS credentials not configured - Bedrock calls will fail")
    
    if not os.getenv("APOLLO_API_KEY"):
        warnings.append("APOLLO_API_KEY not set - Apollo enrichment disabled")
    
    if not os.getenv("IPINFO_TOKEN"):
        warnings.append("IPINFO_TOKEN not set - IP lookup disabled")

    if not os.getenv("EXA_API_KEY"):
        warnings.append("EXA_API_KEY not set - business signals and leadership discovery disabled")

    if not os.getenv("BUILTWITH_API_KEY"):
        warnings.append("BUILTWITH_API_KEY not set - BuiltWith tech stack detection disabled (page scan fallback active)")

    if not os.getenv("HUBSPOT_ACCESS_TOKEN"):
        warnings.append("HUBSPOT_ACCESS_TOKEN not set - CRM export to HubSpot disabled")
    
    for warning in warnings:
        logger.warning(warning)
    
    return warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("Starting LEPA Backend...")
    warnings = validate_config()
    if warnings:
        logger.info(f"Configuration warnings: {len(warnings)}")
    yield
    logger.info("Shutting down LEPA Backend...")


app = FastAPI(
    title="LEPA - Account Intelligence API",
    description="""
AI-powered account intelligence and enrichment system for sales teams.

## Features
- **Visitor Analysis**: Convert anonymous website visitors into sales intelligence
- **Company Research**: Deep company enrichment from minimal input
- **Persona Inference**: Identify likely visitor role from behavior
- **Intent Scoring**: Quantify buying intent from signals
- **Tech Stack Detection**: Detect CRM, marketing automation, analytics tools
- **Business Signals**: Surface funding, hiring, expansion, and launch news
- **Leadership Discovery**: Find likely decision-makers from public sources
- **AI Summaries**: Generate actionable account insights
- **Sales Recommendations**: Specific next-step actions
- **Batch Processing**: Analyze multiple accounts in one request
- **Account History**: Track intent trends and visit patterns over time
- **CRM Export**: Push intelligence to HubSpot

## Powered By
- Strands Agents SDK for agentic research
- Amazon Bedrock (Claude 4 Sonnet, Claude 3.5 Haiku)
- Apollo.io for company enrichment
- IPInfo for visitor identification
- Exa for business signals and leadership discovery
- BuiltWith for technology stack detection
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)


app.include_router(analyze_router)
app.include_router(batch_router)
app.include_router(crm_router)
app.include_router(icp_router)
app.include_router(contacts_router)
app.include_router(history_router)
app.include_router(tracker_router)
app.include_router(tracker_keys_router)
app.include_router(assistant_router)
app.include_router(hubspot_connection_router)


@app.get("/", tags=["root"])
def read_root():
    """Root endpoint with API information."""
    return {
        "service": "LEPA - Account Intelligence API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "analyze_company": "POST /analyze/company",
            "analyze_visitor": "POST /analyze/visitor",
            "batch_analyze": "POST /batch/analyze",
            "list_accounts": "GET /accounts",
            "list_pipeline_runs": "GET /pipeline_runs",
            "account_history": "GET /accounts/{account_id}",
            "crm_export": "POST /crm/export/{account_id}",
        },
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint."""
    from services.result_cache import list_cached_results

    config_status = {
        "aws": bool(os.getenv("AWS_PROFILE") or os.getenv("AWS_ACCESS_KEY_ID")),
        "apollo": bool(os.getenv("APOLLO_API_KEY")),
        "ipinfo": bool(os.getenv("IPINFO_TOKEN")),
        "exa": bool(os.getenv("EXA_API_KEY")),
        "builtwith": bool(os.getenv("BUILTWITH_API_KEY")),
        "hubspot": bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),
    }

    core_configured = config_status["aws"] and config_status["apollo"]
    
    return {
        "status": "healthy" if core_configured else "degraded",
        "service": "lepa-backend",
        "version": "2.0.0",
        "config": config_status,
        "cached_results": len(list_cached_results("default", limit=1000)),
    }


@app.get("/config", tags=["health"])
def config_status():
    """Check configuration status (for debugging)."""
    return {
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "aws_profile_set": bool(os.getenv("AWS_PROFILE")),
        "apollo_configured": bool(os.getenv("APOLLO_API_KEY")),
        "ipinfo_configured": bool(os.getenv("IPINFO_TOKEN")),
        "exa_configured": bool(os.getenv("EXA_API_KEY")),
        "builtwith_configured": bool(os.getenv("BUILTWITH_API_KEY")),
        "hubspot_configured": bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred",
        },
    )
