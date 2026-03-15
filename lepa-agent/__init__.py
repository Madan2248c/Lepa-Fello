"""
LEPA Research Agent — Multi-agent graph for deep account intelligence.

Graph topology:
  company_agent (entry)
      ├── linkedin_agent   (parallel)
      │       └── persons_agent
      └── contacts_agent   (parallel)
                    └── synthesis_agent  (waits for persons + contacts)
"""

import sys
import os

# Allow importing shared clients from the backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lepa-backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "lepa-backend", ".env"))
