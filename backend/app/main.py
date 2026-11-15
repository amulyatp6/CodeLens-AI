from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import AnalyzeRequest, AnalysisReport, AnalysisSummary, Finding, ChatRequest
from app.analyzers.python_ast import analyze_python
from app.analyzers.tool_runner import run_python_tools
from app.ai import ai_findings, chat_answer

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = FastAPI(title="CodeLens AI API", version="1.0.0", description="Hybrid static and AI-assisted code analysis")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
HISTORY: list[AnalysisReport] = []

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CodeLens AI API"}

@app.get("/api/history")
async def history():
    return [item.model_dump() for item in HISTORY[:50]]

@app.post("/api/analyze", response_model=AnalysisReport)
async def analyze(request: AnalyzeRequest):
    if request.language.lower() not in {"python", "py"}:
        raise HTTPException(400, "The current MVP performs deep analysis for Python. Other languages are not yet enabled.")
    start = perf_counter()
    filename = Path(request.filename).name or "submitted_code.py"
    findings = analyze_python(request.code, filename)
    tool_findings, tools = run_python_tools(request.code, filename)
    findings.extend(tool_findings)
    # Merge exact/near duplicates while preserving detector provenance.
    merged: dict[tuple, Finding] = {}
    for item in findings:
        key = (item.category.lower(), (item.line or 0), item.title.lower()[:35])
        if key in merged:
            current = merged[key]
            current.source = sorted(set(current.source + item.source))
            current.confidence = max(current.confidence, item.confidence)
        else:
            merged[key] = item
    findings = list(merged.values())
    ai_status = "Not requested"
    ai_enabled = False
    if request.include_ai:
        ai_items, ai_status = await ai_findings(request.code, filename, findings)
        for index, item in enumerate(ai_items):
            severity = item.get("severity", "Medium")
            if severity not in {"Critical", "High", "Medium", "Low", "Info"}:
                severity = "Medium"
            line = item.get("line")
            if not isinstance(line, int) or line < 1 or line > max(1, len(request.code.splitlines())):
                line = None
            findings.append(Finding(
                id=f"ai-{index}-{uuid4().hex[:6]}", title=str(item.get("title", "Potential issue"))[:120],
                category=str(item.get("category", "AI review"))[:60], severity=severity,
                message=str(item.get("message", "Potential issue identified by AI."))[:1200], file=filename,
                line=line, source=["LLM"], confidence=max(0.0, min(1.0, float(item.get("confidence", 0.65)))),
                snippet=str(item.get("snippet", ""))[:500], recommendation=str(item.get("recommendation", "Review this finding."))[:1000],
                fixed_code=str(item.get("fixed_code", ""))[:4000]
            ))
        ai_enabled = ai_status == "Connected"
    counts = {severity: sum(1 for f in findings if f.severity == severity) for severity in ["Critical", "High", "Medium", "Low", "Info"]}
    # Transparent heuristic: deductions are capped; this is not a correctness proof.
    penalty = counts["Critical"] * 25 + counts["High"] * 12 + counts["Medium"] * 5 + counts["Low"] * 2
    score = max(0, min(100, 100 - penalty))
    duration = int((perf_counter() - start) * 1000)
    report = AnalysisReport(
        id=uuid4().hex[:12], filename=filename, language="Python", created_at=datetime.now(timezone.utc).isoformat(), duration_ms=duration,
        summary=AnalysisSummary(total=len(findings), critical=counts["Critical"], high=counts["High"], medium=counts["Medium"], low=counts["Low"], info=counts["Info"], quality_score=score),
        findings=findings, tools={**tools, "AI reasoning": ai_status}, ai_enabled=ai_enabled,
        overview=(f"Analysis completed with {len(findings)} finding(s). " + ("AI reasoning was included." if ai_enabled else "Static analysis was performed; configure an LLM provider to enable AI reasoning."))
    )
    HISTORY.insert(0, report)
    return report

@app.post("/api/chat")
async def chat(request: ChatRequest):
    answer = await chat_answer(request.question, request.report.model_dump(), request.finding_id)
    return {"answer": answer}

@app.get("/api/settings/provider")
async def provider_status():
    configured = bool(os.getenv("LLM_BASE_URL") and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL"))
    return {"configured": configured, "provider": "OpenAI-compatible", "model": os.getenv("LLM_MODEL", "Not configured") if configured else "Not configured"}
