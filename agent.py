import os
import json
import hashlib
import logging
import redis

from decimal import Decimal
from models import AgentOutput
from typing import Any, Dict, Optional
from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.chains import SimpleSequentialChain

from config import (
    REDIS_HOST,
    REDIS_PORT, 
    REDIS_DB,
    BTC_RISK_KEY
)

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

OPENAI_API_KEY = os.getenv("OPENAI_KEY")
AGENT_CACHE_TTL = int(os.getenv("AGENT_CACHE_TTL", "3600"))

llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2, openai_api_key=OPENAI_API_KEY, max_tokens=800)

PROMPT_TEMPLATE = """
You are a professional quantitative risk analyst. I will provide:
1) a JSON object "snapshot" containing user's asset fields and numbers,
2) a JSON object "results" containing computed metrics (total_assets_usd, total_savings_usd, available_liquidity_ratio, gold_ratio, btc_ratio, weighted_risk_score, speculative_ratio),
3) context info (like dynamic BTC risk factor and recent market notes).

Task:
- Provide a short "verdict": one of ["ok","warning","danger"].
- Provide a short "summary" (1-3 sentences).
- Provide "suggested_adjustments" as key/value pairs mapping config keys to recommended numeric values (e.g. {"RISK_WEIGHTS.gold":5.0, "RISK_WEIGHTS.btc":6.5}). Only suggest when you are reasonably confident.
- Provide "explanations" for each suggestion.
- Provide "confidence" as a number between 0 and 1.

Important:
- Output MUST be valid JSON, match the schema below exactly, and nothing else.
- All numeric outputs should be floats with at most 2 decimal digits.
- Do NOT include any extra commentary outside the JSON.

Schema:
{
  "verdict": "ok|warning|danger",
  "summary": "string",
  "suggested_adjustments": {"string": float},
  "explanations": {"string": "string"},
  "confidence": float
}

Now analyze the following inputs:

SNAPSHOT:
{snapshot}

RESULTS:
{results}

CONTEXT:
{context}
"""

prompt = PromptTemplate(
    input_variables=["snapshot", "results", "context"],
    template=PROMPT_TEMPLATE
)

chain = LLMChain(llm=llm, prompt=prompt)

def _make_cache_key(snapshot: Dict[str, Any], results: Dict[str, Any]) -> str:
    payload = json.dumps({"snapshot": snapshot, "results": results}, sort_keys=True, default=str)
    return "ASSET_AGENT:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

def analyze_snapshot_and_results(snapshot: Dict[str, Any], results: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
    """
    Main function to call LLM, parse result, and cache in Redis.
    Returns AgentOutput (pydantic) or raises Exception on parse error.
    """
    context = context or {}
    