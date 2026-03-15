import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lepa-backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "lepa-backend", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from graph import research_company

app = FastAPI(title="LEPA Research Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    company_name: str
    domain: str = ""
    tenant_id: str = "default"
    sender_name: str = ""
    force: bool = False

@app.get("/health")
def health():
    return {"status": "ok", "service": "lepa-agent"}

@app.post("/research")
async def research(req: ResearchRequest):
    return await research_company(req.company_name, req.domain, req.tenant_id, req.sender_name, req.force)
