"""
Analysis API routes for visitor and company intelligence.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from schemas.input_models import VisitorSignalInput, CompanySeedInput
from schemas.output_models import AnalyzeResponse

logger = logging.getLogger("lepa.api")

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post(
    "/visitor",
    response_model=AnalyzeResponse,
    summary="Analyze website visitor",
    description="""
Analyze a website visitor's behavior to generate account intelligence.

**Input**: Visitor signals including:
- Pages visited (e.g., /pricing, /docs, /case-studies)
- Time on site
- Number of visits this week
- IP address (for company identification)
- Referral source

**Output**: Complete account intelligence including:
- Company identification from IP
- Visitor persona inference
- Buying intent score
- AI-generated summary
- Recommended sales actions
    """,
)
async def analyze_visitor(input_data: VisitorSignalInput) -> AnalyzeResponse:
    """Analyze a website visitor to generate account intelligence."""
    from services.pipeline import run_visitor_pipeline
    
    start_time = time.time()
    logger.info(f"Starting visitor analysis: {input_data.visitor_id}")
    
    try:
        result = await run_visitor_pipeline(input_data)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Visitor analysis complete: {input_data.visitor_id} "
            f"(account={result.account_name}, confidence={result.overall_confidence:.0%}, "
            f"elapsed={elapsed:.2f}s)"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error in visitor analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Visitor analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)[:200]}",
        )


@router.post(
    "/company",
    response_model=AnalyzeResponse,
    summary="Analyze company by name",
    description="""
Analyze a company by name to generate account intelligence.

**Input**: Company information including:
- Company name (required)
- Partial domain hint (optional)

**Output**: Complete account intelligence including:
- Enriched company profile (industry, size, HQ, etc.)
- Default persona (no visitor behavior available)
- Default intent score
- AI-generated summary
- Recommended sales actions

**Data Sources**:
- Apollo.io for company enrichment
- Company website scraping
- Strands AI agent for research synthesis
    """,
)
async def analyze_company(input_data: CompanySeedInput) -> AnalyzeResponse:
    """Analyze a company by name to generate account intelligence."""
    from services.pipeline import run_company_pipeline
    
    start_time = time.time()
    logger.info(f"Starting company analysis: {input_data.company_name}")
    
    try:
        result = await run_company_pipeline(input_data)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Company analysis complete: {input_data.company_name} "
            f"(domain={result.domain}, confidence={result.overall_confidence:.0%}, "
            f"elapsed={elapsed:.2f}s)"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error in company analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Company analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)[:200]}",
        )


@router.get(
    "/health",
    summary="Analysis service health check",
)
async def health_check():
    """Health check for the analysis service."""
    return {
        "status": "healthy",
        "service": "analyze",
    }
