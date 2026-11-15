import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from app.schemas import Finding


def _run(command: list[str], cwd: str, timeout: int = 12) -> tuple[int, str, str]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=False)
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, "", str(exc)


def run_python_tools(code: str, filename: str) -> tuple[list[Finding], dict[str, str]]:
    findings: list[Finding] = []
    status = {"Ruff": "Not run", "Mypy": "Not run", "Bandit": "Not run"}
    with tempfile.TemporaryDirectory(prefix="codelens-") as tmp:
        safe_name = Path(filename).name
        if not safe_name.endswith(".py"):
            safe_name += ".py"
        file_path = Path(tmp) / safe_name
        file_path.write_text(code, encoding="utf-8")

        if shutil.which("ruff"):
            rc, out, err = _run(["ruff", "check", "--output-format", "json", str(file_path)], tmp)
            try:
                data = json.loads(out or "[]")
                for item in data:
                    line = (item.get("location") or {}).get("row")
                    findings.append(Finding(
                        id=f"ruff-{item.get('code')}-{line}-{item.get('message','')[:20]}",
                        title=f"{item.get('code', 'Lint')} · {item.get('message', 'Code issue')[:65]}",
                        category="Code quality", severity="Low" if str(item.get("code", "")).startswith("E") else "Medium",
                        message=item.get("message", "Static analysis finding."), file=safe_name, line=line,
                        source=["Ruff"], confidence=0.99,
                        snippet=(code.splitlines()[line-1].strip() if line and len(code.splitlines()) >= line else ""),
                        recommendation="Review the lint diagnostic and apply the suggested code-quality correction."
                    ))
                status["Ruff"] = f"Completed · {len(data)} findings"
            except json.JSONDecodeError:
                status["Ruff"] = "Completed with unparsed output" if not err else "Unavailable"
        else:
            status["Ruff"] = "Not installed"

        if shutil.which("mypy"):
            rc, out, err = _run(["mypy", "--show-column-numbers", "--no-error-summary", str(file_path)], tmp)
            count = 0
            for raw in (out + "\n" + err).splitlines():
                # file.py:12: error: message [code]
                import re
                match = re.search(r":(\d+)(?::\d+)?:\s+(error|warning|note):\s+(.*)", raw)
                if match and match.group(2) != "note":
                    line, kind, message = int(match.group(1)), match.group(2), match.group(3)
                    findings.append(Finding(
                        id=f"mypy-{line}-{message[:24]}", title="Type-checking issue", category="Type safety",
                        severity="Medium" if kind == "error" else "Low", message=message, file=safe_name,
                        line=line, source=["Mypy"], confidence=0.96,
                        snippet=(code.splitlines()[line-1].strip() if len(code.splitlines()) >= line else ""),
                        recommendation="Add or correct type annotations and ensure values match the declared types."
                    )); count += 1
            status["Mypy"] = f"Completed · {count} findings"
        else:
            status["Mypy"] = "Not installed"

        if shutil.which("bandit"):
            rc, out, err = _run(["bandit", "-f", "json", str(file_path)], tmp)
            try:
                data = json.loads(out or "{}")
                results = data.get("results", [])
                for item in results:
                    line = item.get("line_number")
                    severity = item.get("issue_severity", "LOW").title()
                    findings.append(Finding(
                        id=f"bandit-{item.get('test_id')}-{line}", title=item.get("test_name", "Security finding").replace("_", " ").title(),
                        category="Security", severity=severity if severity in {"High", "Medium", "Low"} else "Low",
                        message=item.get("issue_text", "Potential security issue."), file=safe_name, line=line,
                        source=["Bandit"], confidence=0.95,
                        snippet=(code.splitlines()[line-1].strip() if line and len(code.splitlines()) >= line else item.get("code", "").strip()),
                        recommendation="Review the security diagnostic and replace unsafe operations with safer alternatives."
                    ))
                status["Bandit"] = f"Completed · {len(results)} findings"
            except json.JSONDecodeError:
                status["Bandit"] = "Completed with unparsed output" if not err else "Unavailable"
        else:
            status["Bandit"] = "Not installed"
    return findings, status
