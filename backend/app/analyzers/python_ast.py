import ast
from app.schemas import Finding


def analyze_python(code: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as exc:
        line = exc.lineno or 1
        findings.append(Finding(
            id=f"ast-syntax-{line}", title="Python syntax error", category="Syntax",
            severity="Critical", message=exc.msg or "The parser could not understand this statement.",
            file=filename, line=line, source=["Python AST"], confidence=1.0,
            snippet=(code.splitlines()[line-1] if len(code.splitlines()) >= line else ""),
            recommendation="Correct the syntax at this location, then run the analysis again."
        ))
        return findings

    lines = code.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            findings.append(Finding(
                id=f"ast-dynamic-{node.lineno}", title=f"Use of {node.func.id}()", category="Security",
                severity="High", message=f"{node.func.id}() evaluates dynamically supplied code and can execute attacker-controlled input.",
                file=filename, line=node.lineno, source=["Python AST"], confidence=0.98,
                snippet=lines[node.lineno-1].strip(), recommendation="Avoid dynamic code execution. Use explicit parsing or a safe mapping of allowed operations."
            ))
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(Finding(
                id=f"ast-bare-except-{node.lineno}", title="Bare except clause", category="Reliability",
                severity="Medium", message="A bare except catches almost every exception, including system-exiting exceptions, and can hide unexpected failures.",
                file=filename, line=node.lineno, source=["Python AST"], confidence=0.95,
                snippet=lines[node.lineno-1].strip(), recommendation="Catch the specific exception types the code can reasonably handle."
            ))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(Finding(
                        id=f"ast-mutable-default-{node.lineno}", title="Mutable default argument", category="Correctness",
                        severity="High", message="A mutable default object is created once when the function is defined and is shared across calls. This can cause state to leak between calls.",
                        file=filename, line=node.lineno, source=["Python AST"], confidence=0.99,
                        snippet=lines[node.lineno-1].strip(), recommendation="Use None as the default and create a new list, dictionary, or set inside the function."
                    ))
                    break
    # Avoid repeated findings with the same stable identifier.
    unique: dict[str, Finding] = {}
    for finding in findings:
        unique[finding.id] = finding
    return list(unique.values())
