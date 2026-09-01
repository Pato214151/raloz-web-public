"""Contrato declarativo del Tool Registry (no requiere base de datos)."""

from app.agent.tool_registry import (
    ACTIONS,
    TOOLS,
    get_action,
    get_tool,
    render_actions_prompt,
    render_tools_prompt,
)


def test_todas_las_herramientas_tienen_nombres_unicos_y_prompt():
    nombres = [t.name for t in TOOLS]
    assert len(nombres) == len(set(nombres))
    prompt = render_tools_prompt()
    for herramienta in TOOLS:
        assert f'"tipo":"{herramienta.name}"' in prompt


def test_acciones_tienen_contrato_y_prompt():
    nombres = [a.name for a in ACTIONS]
    assert len(nombres) == len(set(nombres))
    prompt = render_actions_prompt()
    for accion in ACTIONS:
        assert f'ACCION_JSON: {accion.example}' in prompt


def test_validacion_estructural_no_reemplaza_la_semantica():
    assert get_action("crear_tarea").validate({"tipo": "crear_tarea", "titulo": "Llamar"})
    assert not get_action("crear_tarea").validate({"tipo": "crear_tarea"})
    assert get_tool("simular_devolucion").simulable is True
    assert get_tool("observar").simulable is False

