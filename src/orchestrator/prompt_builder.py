class PromptBuilder:
    @staticmethod
    def build_project_context(metadata: dict) -> str:
        if not metadata:
            return ""
        lines = [
            "## CONTEXTO DO PROJETO",
            f"- Sistema: {metadata.get('system_name', '')}",
            f"- Descrição: {metadata.get('system_description', '')}",
            f"- Responsável: {metadata.get('owner_name', '')} ({metadata.get('owner_email', '')})",
            f"- Área: {metadata.get('area', '')}",
        ]
        ctx = metadata.get("additional_context") or {}
        if ctx.get("sigla"):
            lines.append(f"- Sigla: {ctx['sigla']}")
        elif metadata.get("organization"):
            lines.append(f"- Organização: {metadata['organization']}")
        if metadata.get("stack_hint"):
            lines.append(f"- Preferência de stack: {metadata['stack_hint']}")
        timeline = ctx.get("timeline")
        if isinstance(timeline, dict) and timeline.get("estimated_duration_label"):
            lines.append(
                f"- Prazo estimado para conclusão: {timeline['estimated_duration_label']} "
                f"(até {timeline.get('estimated_completion_at', '')})"
            )
        ctx_display = {k: v for k, v in ctx.items() if k != "timeline"}
        if ctx_display:
            lines.append(f"- Contexto adicional: {ctx_display}")
        return "\n".join(lines)

    @staticmethod
    def build_enriched_demand(message: str, metadata: dict) -> str:
        ctx = PromptBuilder.build_project_context(metadata)
        return f"{ctx}\n\n## DEMANDA TÉCNICA\n{message}"

    @staticmethod
    def _format_list_section(title: str, items: list[str]) -> str:
        if not items:
            return ""
        lines = [f"\n## {title}"]
        lines.extend(f"- {item}" for item in items)
        return "\n".join(lines)

    @staticmethod
    def build_system_prompt(
        persona: str,
        *,
        rag_context: str = "",
        extra_context: str = "",
        instructions_context: str = "",
        skills_context: str = "",
        constraints: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        reject_if: list[str] | None = None,
    ) -> str:
        parts = [persona]
        if instructions_context:
            parts.append(f"\n\n{instructions_context}")
        parts.append(PromptBuilder._format_list_section("CONSTRAINTS", constraints or []))
        parts.append(PromptBuilder._format_list_section("ACCEPTANCE_CRITERIA", acceptance_criteria or []))
        parts.append(PromptBuilder._format_list_section("REJECT_IF", reject_if or []))
        parts.extend([
            "\n\nIMPORTANTE: Responda APENAS com JSON válido conforme o schema definido acima.",
            "Não inclua texto fora do JSON.",
            "Se não puder cumprir os critérios, retorne JSON com campo `error` explicando o bloqueio.",
        ])
        if skills_context:
            parts.append(f"\n\n{skills_context}")
        if rag_context:
            parts.append(f"\n\n--- CONTEXTO RAG ---\n\n{rag_context}")
        if extra_context:
            parts.append(f"\n\n--- CONTEXTO ADICIONAL ---\n\n{extra_context}")
        return "\n".join(parts)

    @staticmethod
    def build_agent_message(
        demand: str,
        state_snapshot: dict,
        agent_name: str,
    ) -> str:
        import json

        return (
            f"Demanda: {demand}\n\n"
            f"Agente atual: {agent_name}\n\n"
            f"Estado do workflow:\n{json.dumps(state_snapshot, ensure_ascii=False, default=str)[:8000]}"
        )

    @staticmethod
    def build_validation_retry_message(original_message: str, errors: list[str]) -> str:
        error_text = "\n".join(f"- {e}" for e in errors)
        return (
            f"{original_message}\n\n"
            f"## CORREÇÃO NECESSÁRIA\n"
            f"Sua resposta anterior falhou na validação:\n{error_text}\n\n"
            f"Corrija e responda novamente APENAS com JSON válido."
        )
