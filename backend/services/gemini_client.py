"""
services/gemini_client.py
--------------------------
Gemini 2.5 Flash LLM client using LangChain.
Provides structured JSON calls and plain text calls.
"""

import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings
from tenacity import retry, stop_after_attempt, wait_exponential


# ─── LLM Instance ────────────────────────────────────────────────────────────

def get_llm(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature
    )


# ─── Core Call ────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """
    Call Gemini with a system + user prompt.
    Returns raw string response.
    """
    llm = get_llm(temperature=temperature)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    return response.content


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
    """
    Call Gemini expecting a JSON response.
    Strips markdown fences and parses JSON.
    Returns parsed dict.
    """
    full_system = (
        system_prompt
        + "\n\nCRITICAL: Respond ONLY with valid JSON. "
        "No markdown, no code fences, no explanation. "
        "Just the raw JSON object."
    )
    raw = call_llm(full_system, user_prompt, temperature=temperature)
    return parse_json_response(raw)


def parse_json_response(raw: str) -> dict:
    """
    Safely parse JSON from LLM response.
    Handles markdown fences, trailing text, etc.
    """
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    cleaned = cleaned.strip("`").strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in response
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try to find JSON array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return {"items": json.loads(match.group())}
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {raw[:300]}")
