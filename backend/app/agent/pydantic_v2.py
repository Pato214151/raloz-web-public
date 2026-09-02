"""Adaptador experimental de PydanticAI para RALOZ.

Fase 2: convive con el endpoint legacy y solo permite consultas de lectura.
La bandera ``ASISTENTE_PYDANTIC=1`` se evalúa en el endpoint; este módulo no
se importa al arrancar la aplicación para que PydanticAI siga siendo opcional
durante la transición.
"""

import os
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.agent.tool_registry import TOOLS, render_tools_prompt


class ConsultaTool(BaseModel):
    """Solicitud estructurada de una consulta registrada."""

    tipo: Literal[tuple(spec.name for spec in TOOLS)]
    parametros: dict[str, Any] = Field(default_factory=dict)


def _modelo_configurado():
    """Construye el modelo PydanticAI usando el proveedor disponible."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        modelo = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        # Modelos 2.x fueron retirados por Google (404); usa 3.x.
        if modelo in ("gemini-2.5-flash", "gemini-2.5-flash-lite",
                      "gemini-2.0-flash", "gemini-2.0-flash-lite"):
            modelo = "gemini-3.5-flash-lite"
        return GoogleModel(modelo, provider=GoogleProvider(api_key=gemini_key))

    grok_key = os.getenv("GROK_API_KEY", "").strip()
    if grok_key:
        return OpenAIChatModel(
            os.getenv("GROK_MODEL", "grok-3").strip(),
            provider=OpenAIProvider(base_url="https://api.x.ai/v1", api_key=grok_key),
        )

    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        return OpenAIChatModel(
            os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            provider=OpenAIProvider(base_url="https://api.deepseek.com", api_key=deepseek_key),
        )

    raise RuntimeError("No hay un proveedor de IA configurado")


def build_agent(model=None) -> Agent:
    """Crea un agente de lectura; ``model`` permite pruebas con TestModel."""
    agent = Agent(
        model or _modelo_configurado(),
        name="raloz-assistant-v2",
        output_type=str,
        system_prompt=(
            "Eres RALOZ, el copiloto empresarial interno. Responde en español, "
            "con datos reales, separando dato, cálculo, estimación y recomendación. "
            "No inventes. Este agente es SOLO LECTURA: no cambies precios, stock, "
            "tareas ni estados. Para obtener datos usa consultar_datos. "
            "No uses observar salvo que el usuario pida una revisión general.\n\n"
            + render_tools_prompt()
        ),
        retries=2,
    )

    @agent.tool
    def consultar_datos(ctx: RunContext[dict[str, Any]], consulta: ConsultaTool) -> dict[str, Any]:
        """Consulta una capacidad del registro y devuelve datos sin PII."""
        from app.api.asistente import _ejecutar_busqueda, _es_revision, _sin_pii

        payload = {"tipo": consulta.tipo, **consulta.parametros}
        if consulta.tipo == "observar" and not _es_revision(ctx.deps.get("pregunta", "")):
            return {"bloqueado": True, "mensaje": "La revisión general no corresponde a esta pregunta."}
        return _sin_pii(_ejecutar_busqueda(payload))

    return agent


def run_readonly(pregunta: str) -> str:
    """Ejecuta una consulta experimental con el Agent Core tipado."""
    from app.api.asistente import _contexto_datos, _sin_pii, MANUAL

    agent = build_agent()
    prompt = (
        f"DATOS REALES DEL SISTEMA:\n{_sin_pii(_contexto_datos())}\n\n"
        f"MANUAL:\n{MANUAL}\n\n"
        f"PREGUNTA DEL JEFE:\n{pregunta}"
    )
    return agent.run_sync(prompt, deps={"pregunta": pregunta}).output
