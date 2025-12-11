import os
import json
import hashlib
import logging
import redis

from models import AgentOutput
from typing import Any, Dict, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from models import AssetSnapshot

from config import (
    REDIS_HOST,
    REDIS_PORT, 
    REDIS_DB,
)

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

OPENAI_API_KEY = os.getenv("OPENAI_KEY")
AGENT_CACHE_TTL = int(os.getenv("AGENT_CACHE_TTL", "3600"))

llm = ChatOpenAI(
    model_name="gpt-4o-mini", 
    temperature=0.2, 
    openai_api_key=OPENAI_API_KEY, 
    max_tokens=800,
    model_kwargs={"response_format": {"type": "json_object"}}
)

parser = JsonOutputParser(pydantic_object=AgentOutput)

PROMPT_TEMPLATE = """
You are a professional quantitative risk analyst. I will provide:
1) a JSON object "snapshot" containing user's asset fields and numbers,
2) a JSON object "results" containing computed metrics (total_assets_usd, total_savings_usd, available_liquidity_ratio, gold_ratio, btc_ratio, weighted_risk_score, speculative_ratio),
3) context info (like dynamic BTC risk factor and recent market notes).

Task:
- Provide a short "verdict": one of ["ok","warning","danger"].
- Provide a short "summary" (1-3 sentences).
- Provide "suggested_adjustments" as key/value pairs mapping config keys to recommended numeric values. Only suggest when you are reasonably confident.
- Provide "explanations" for each suggestion.
- Provide "confidence" as a number between 0 and 1.

Important:
- Output MUST be valid JSON, match the schema below exactly, and nothing else.
- All numeric outputs should be floats with at most 2 decimal digits.
- Do NOT include any extra commentary outside the JSON.

Schema:
{format_instructions}

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
    partial_variables={"format_instructions": parser.get_format_instructions()},
    template=PROMPT_TEMPLATE
)

chain = prompt | llm | parser

def _make_cache_key(snapshot: Dict[str, Any], results: Dict[str, Any]) -> str:
    payload = json.dumps({"snapshot": snapshot, "results": results}, sort_keys=True, default=str)
    return "ASSET_AGENT:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

def analyze_snapshot_and_results(snapshot: Dict[str, Any], results: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
    """
    Main function to call LLM, parse result, and cache in Redis.
    Returns AgentOutput (pydantic) or raises Exception on parse error.
    """
    context = context or {}
    cache_key = _make_cache_key(snapshot, results)
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logging.info("Hitting Redis cache for Agent analysis")
            payload = json.loads(cached.decode("utf-8"))
            return AgentOutput(**payload)
    except Exception:
        logging.exception("Redis cache read failed")

    snapshot_str = json.dumps(snapshot, default=str, ensure_ascii=False)
    results_str = json.dumps(results, default=str, ensure_ascii=False)
    context_str = json.dumps(context, default=str, ensure_ascii=False)

    try:
        parsed_dict = chain.invoke({
            "snapshot": snapshot_str,
            "results": results_str,
            "context": context_str
        })
        agent_out = AgentOutput(**parsed_dict)
        try:
            redis_client.setex(cache_key, AGENT_CACHE_TTL, agent_out.model_dump_json())
        except Exception:
            logging.exception("Redis cache write failed")
        return agent_out
    except Exception as e:
        logging.error(f"Agent LLM call or parse failed: {e}")
    return AgentOutput(
        verdict="ok", 
        summary="Agent unavailable; no suggesstion.", 
        suggested_adjustments={}, 
        explanations={}, 
        confidence=0.0
    )

def snapshot_to_dict(asset_snapshot: AssetSnapshot) -> Dict[str, Any]:
    try:
        return asset_snapshot.model_dump()
    except Exception:
        return json.loads(asset_snapshot.model_dump_json())