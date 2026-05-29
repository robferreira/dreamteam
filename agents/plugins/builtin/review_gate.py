from plugins.base import PluginContext, PluginResult


async def review_gate(ctx: PluginContext) -> PluginResult:
    """Força approved=false se houver issues de severidade high."""
    if ctx.agent_name != "reviewer":
        return PluginResult(output=dict(ctx.output))

    output = dict(ctx.output)
    issues = output.get("issues", [])
    if not isinstance(issues, list):
        return PluginResult(output=output)

    has_high = any(
        isinstance(issue, dict) and str(issue.get("severity", "")).lower() == "high"
        for issue in issues
    )
    modified = False
    if has_high and output.get("approved"):
        output["approved"] = False
        modified = True
        output.setdefault("notes", "")
        output["notes"] = (
            str(output["notes"]) + " [review_gate: aprovação revertida por issues high]"
        ).strip()

    if has_high and not output.get("refactor_requests"):
        high_issues = [
            i for i in issues
            if isinstance(i, dict) and str(i.get("severity", "")).lower() == "high"
        ]
        output["refactor_requests"] = [
            {
                "agent": issue.get("agent", "backend"),
                "reason": issue.get("description", "Issue high pendente"),
            }
            for issue in high_issues
        ]
        modified = True

    return PluginResult(output=output, modified=modified)
