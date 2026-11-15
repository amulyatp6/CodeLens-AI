from pydantic import BaseModel, Field
from typing import Literal

Severity = Literal["Critical", "High", "Medium", "Low", "Info"]

class AnalyzeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100_000)
    language: str = "python"
    filename: str = "submitted_code.py"
    include_ai: bool = True

class Finding(BaseModel):
    id: str
    title: str
    category: str
    severity: Severity
    message: str
    file: str
    line: int | None = None
    end_line: int | None = None
    source: list[str] = []
    confidence: float = 0.8
    snippet: str = ""
    recommendation: str = ""
    fixed_code: str = ""

class AnalysisSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    quality_score: int

class AnalysisReport(BaseModel):
    id: str
    filename: str
    language: str
    created_at: str
    duration_ms: int
    summary: AnalysisSummary
    findings: list[Finding]
    tools: dict[str, str]
    ai_enabled: bool
    overview: str

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    report: AnalysisReport
    finding_id: str | None = None
