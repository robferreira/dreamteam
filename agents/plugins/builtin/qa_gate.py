from plugins.base import PluginContext, PluginResult


async def qa_gate(ctx: PluginContext) -> PluginResult:
    """Força approved=false se qa_result indicar falha E2E."""
    if ctx.agent_name != "reviewer":
        return PluginResult(output=dict(ctx.output))

    qa_result = ctx.extra.get("qa_result") or {}
    if not qa_result:
        return PluginResult(output=dict(ctx.output))

    e2e_passed = qa_result.get("e2e_passed")
    if e2e_passed is not False:
        return PluginResult(output=dict(ctx.output))

    output = dict(ctx.output)
    modified = False

    if output.get("approved"):
        output["approved"] = False
        modified = True

    execution = qa_result.get("execution") or []
    failure_msgs: list[str] = []
    refactor_agent = "backend"

    for run in execution:
        if not isinstance(run, dict) or run.get("passed"):
            continue
        suite = run.get("suite", "unknown")
        failed = run.get("failed", 0)
        failure_msgs.append(f"Suite {suite}: {failed} teste(s) falharam")
        for fail in run.get("failures") or []:
            if isinstance(fail, dict):
                agent = fail.get("agent")
                if agent in ("frontend", "backend"):
                    refactor_agent = agent
                msg = fail.get("message") or fail.get("test") or str(fail)
                failure_msgs.append(str(msg))

    summary = "; ".join(failure_msgs[:5]) or "Testes E2E falharam"
    qa_issue = {
        "severity": "high",
        "description": f"QA E2E reprovado: {summary}",
        "agent": refactor_agent,
    }

    issues = list(output.get("issues") or [])
    if not any(
        isinstance(i, dict) and "QA E2E reprovado" in str(i.get("description", ""))
        for i in issues
    ):
        issues.append(qa_issue)
        output["issues"] = issues
        modified = True

    refactor_requests = list(output.get("refactor_requests") or [])
    if not any(
        isinstance(r, dict) and "E2E" in str(r.get("reason", ""))
        for r in refactor_requests
    ):
        refactor_requests.append({"agent": refactor_agent, "reason": summary})
        output["refactor_requests"] = refactor_requests
        modified = True

    output.setdefault("notes", "")
    if modified:
        output["notes"] = (
            str(output["notes"]) + " [qa_gate: reprovado por falha E2E]"
        ).strip()

    return PluginResult(output=output, modified=modified)
