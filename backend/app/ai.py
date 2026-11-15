import os
import httpx
from app.schemas import Finding

SYSTEM_PROMPT = """You are CodeLens AI, a careful senior software engineer. Review only the supplied source code and tool findings. Return a JSON array of additional findings, each with title, category, severity (Critical/High/Medium/Low/Info), message, line, snippet, recommendation, fixed_code, confidence. Do not repeat existing findings. Do not invent line numbers: use null if uncertain. Report only actionable issues supported by code evidence. Do not claim code was executed."""

async def ai_findings(code: str, filename: str, existing: list[Finding]) -> tuple[list[dict], str]:
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    if not base_url or not model or not api_key:
        return [], "AI not configured"
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Filename: {filename}\nExisting findings (do not duplicate): {[f.model_dump() for f in existing]}\n\nSource code:\n```\n{code[:24000]}\n```"}
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"{base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        import json, re
        match = re.search(r"\[.*\]", content, re.S)
        if not match:
            return [], "AI returned an unsupported response format"
        data = json.loads(match.group(0))
        return [x for x in data if isinstance(x, dict)], "Connected"
    except Exception as exc:
        return [], f"AI unavailable: {type(exc).__name__}"

async def chat_answer(question: str, report: dict, finding_id: str | None) -> str:
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    if not (base_url and api_key and model):
        return "AI chat is not configured yet. Add LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL to backend/.env, then restart the backend. You can still inspect the static-analysis findings in this report."
    finding = next((x for x in report.get("findings", []) if x.get("id") == finding_id), None)
    prompt = f"Question: {question}\nSelected finding: {finding}\nAnalysis report summary: {report.get('summary')}\nFindings: {report.get('findings', [])[:30]}"
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"{base_url}/chat/completions", json={"model": model, "temperature": 0.2, "messages": [{"role": "system", "content": "You are CodeLens AI. Explain code issues accurately using only supplied evidence. Be concise, practical, and state uncertainty."}, {"role": "user", "content": prompt}]}, headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"The AI provider could not be reached ({type(exc).__name__}). Check the provider URL, model, API key, and backend logs."
