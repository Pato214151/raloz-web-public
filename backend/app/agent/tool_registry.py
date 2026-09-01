"""Registro declarativo de herramientas del Agent Core.

Este módulo no ejecuta consultas ni muta la base de datos. Describe las
capacidades disponibles para que el asistente pueda generar el prompt y
validar la forma mínima de las solicitudes desde una única fuente de verdad.
La ejecución continúa en ``app.api.asistente`` durante la Fase 1.
"""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ToolSpec:
    """Contrato de una herramienta que el agente puede solicitar."""

    name: str
    description: str
    parameters: str
    category: str = "lectura"
    risk: str = "bajo"
    read_only: bool = True
    simulable: bool = False
    reversible: bool = False
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ActionSpec:
    """Contrato mínimo de una acción que puede proponerse al administrador."""

    name: str
    description: str
    example: str
    required: tuple[str, ...] = ()
    risk: str = "medio"
    reversible: bool = False
    requires_confirmation: bool = True

    def validate(self, payload: Mapping[str, Any]) -> bool:
        """Valida solo la forma estructural; la semántica queda en el handler."""
        return all(payload.get(field) not in (None, "") for field in self.required)


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "buscar_prenda",
        "Consulta precio y stock de una prenda por colegio.",
        '{"tipo":"buscar_prenda","colegio":"<colegio>","texto":"<prenda>"}',
    ),
    ToolSpec(
        "movimientos",
        "Consulta el kardex: entradas, salidas, ajustes y stock antes/después.",
        '{"tipo":"movimientos","colegio":"<colegio>","texto":"<prenda>","talla":"<talla o vacío>"}',
    ),
    ToolSpec(
        "buscar_factura",
        "Consulta una factura y verifica sus descuentos de inventario.",
        '{"tipo":"buscar_factura","referencia":"<número, RALOZ-... o ultima>"}',
    ),
    ToolSpec(
        "pedidos_cliente",
        "Consulta pedidos de un cliente por teléfono.",
        '{"tipo":"pedidos_cliente","telefono":"<número>"}',
    ),
    ToolSpec(
        "ventas_periodo",
        "Consulta ventas agrupadas en un periodo.",
        '{"tipo":"ventas_periodo","mes":<1-12>,"anio":<año>}',
    ),
    ToolSpec(
        "top_productos",
        "Consulta las prendas más vendidas por unidades y valor.",
        '{"tipo":"top_productos","limite":<n>}',
    ),
    ToolSpec(
        "simular_precio",
        "Simula precio, margen y utilidad sin modificar datos.",
        '{"tipo":"simular_precio","colegio":"<colegio o vacío>","prenda":"<prenda o vacío>","porcentaje":<número>}',
        category="análisis",
        simulable=True,
    ),
    ToolSpec(
        "bitacora",
        "Consulta acciones ejecutadas, verificación y posibilidad de reversión.",
        '{"tipo":"bitacora","limite":<n>}',
    ),
    ToolSpec(
        "home",
        "Genera el briefing general del negocio con alertas priorizadas.",
        '{"tipo":"home"}',
        category="análisis",
    ),
    ToolSpec(
        "calendario",
        "Cuenta días de la semana dentro de un rango.",
        '{"tipo":"calendario","desde":"YYYY-MM-DD","hasta":"YYYY-MM-DD","dias":["lunes","sabado"]}',
        category="análisis",
    ),
    ToolSpec(
        "ventas_por_dia",
        "Calcula ventas por día de la semana para comparar escenarios.",
        '{"tipo":"ventas_por_dia","dias":["lunes","sabado"]}',
        category="análisis",
        simulable=True,
    ),
    ToolSpec(
        "gastos",
        "Consulta gastos agrupados por categoría en un periodo.",
        '{"tipo":"gastos","desde":"YYYY-MM-DD","hasta":"YYYY-MM-DD"}',
    ),
    ToolSpec(
        "flujo_caja",
        "Calcula cobros reales menos gastos en un periodo.",
        '{"tipo":"flujo_caja","desde":"YYYY-MM-DD","hasta":"YYYY-MM-DD"}',
        category="análisis",
    ),
    ToolSpec(
        "simular_devolucion",
        "Simula salida de caja, retorno de stock y pérdida de utilidad.",
        '{"tipo":"simular_devolucion","referencia":"<número o RALOZ-...>"}',
        category="análisis",
        simulable=True,
    ),
    ToolSpec(
        "observar",
        "Revisa el negocio completo y prioriza alertas.",
        '{"tipo":"observar"}',
        category="análisis",
    ),
    ToolSpec(
        "whatsapp_pendientes",
        "Lista los chats de WhatsApp con mensajes SIN LEER (clientes esperando respuesta). Úsalo para '¿tengo mensajes sin ver?', '¿algún cliente sin responder?'.",
        '{"tipo":"whatsapp_pendientes","limite":<n>}',
        category="análisis",
    ),
    ToolSpec(
        "festivos",
        "Festivos oficiales de Colombia del año. Combínalo con calendario para NO contar días festivos en turnos/pagos, y para avisar días sin atención.",
        '{"tipo":"festivos","anio":<año>}',
        category="análisis",
    ),
)


ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec(
        "cambiar_estado_pedido",
        "Cambiar el estado de entrega de un pedido o factura.",
        '{"tipo":"cambiar_estado_pedido","factura":"<número o RALOZ-...>","estado":"<EMPACADO|LISTO_LLAMAR|ENTREGADA>"}',
        required=("factura", "estado"),
    ),
    ActionSpec(
        "crear_tarea",
        "Crear un recordatorio o tarea con fecha opcional.",
        '{"tipo":"crear_tarea","titulo":"<qué recordar>","fecha":"<YYYY-MM-DD o vacío>","descripcion":"<detalle opcional>"}',
        required=("titulo",),
        risk="bajo",
        reversible=True,
    ),
    ActionSpec(
        "ajustar_stock",
        "Sumar, restar o fijar unidades de una talla.",
        '{"tipo":"ajustar_stock","colegio":"<colegio>","prenda":"<prenda>","talla":"<talla>","modo":"<sumar|restar|fijar>","cantidad":<número>}',
        required=("colegio", "prenda", "talla", "modo", "cantidad"),
        risk="alto",
        reversible=True,
    ),
    ActionSpec(
        "fijar_costo",
        "Cambiar el costo registrado de una prenda.",
        '{"tipo":"fijar_costo","colegio":"<colegio>","prenda":"<prenda>","costo":<número>}',
        required=("colegio", "prenda", "costo"),
        risk="alto",
        reversible=True,
    ),
    ActionSpec(
        "revertir",
        "Revertir una acción reversible de la bitácora.",
        '{"tipo":"revertir","id_accion":<id>}',
        required=("id_accion",),
        risk="alto",
    ),
    ActionSpec(
        "crear_regla",
        "Guardar una regla o política empresarial.",
        '{"tipo":"crear_regla","categoria":"<categoría>","texto":"<regla>","parametros":{}}',
        required=("texto",),
        risk="medio",
        reversible=True,
    ),
    ActionSpec(
        "crear_objetivo",
        "Guardar una meta empresarial.",
        '{"tipo":"crear_objetivo","descripcion":"<meta>","meta":<número>,"anio":<año>,"mes":<1-12>}',
        required=("meta", "anio"),
        risk="bajo",
        reversible=True,
    ),
    ActionSpec(
        "crear_memoria",
        "Guardar una preferencia o contexto empresarial.",
        '{"tipo":"crear_memoria","tipo_memoria":"<tipo>","texto":"<memoria>"}',
        required=("texto",),
        risk="bajo",
        reversible=True,
    ),
    ActionSpec(
        "estimar_costos",
        "Completar costos estimados para referencias sin costo.",
        '{"tipo":"estimar_costos","factor":0.6}',
        risk="alto",
        reversible=True,
    ),
)


TOOL_BY_NAME = {spec.name: spec for spec in TOOLS}
ACTION_BY_NAME = {spec.name: spec for spec in ACTIONS}


def get_tool(name: str) -> ToolSpec | None:
    return TOOL_BY_NAME.get(str(name or "").strip())


def get_action(name: str) -> ActionSpec | None:
    return ACTION_BY_NAME.get(str(name or "").strip())


def render_tools_prompt() -> str:
    """Genera el bloque BUSCAR que recibe el motor actual."""
    lines = [
        "\n\n=== BÚSQUEDA (para datos puntuales) ===",
        "Si necesitas un dato real, responde ÚNICAMENTE con una línea BUSCAR y nada más.",
        "Una sola BÚSQUEDA por turno; puedes encadenar varias hasta completar el objetivo.",
    ]
    for spec in TOOLS:
        lines.append(f"BUSCAR: {spec.parameters}  → {spec.description}")
    lines.extend([
        "Usa observar SOLO para una revisión general ('¿cómo está el negocio?', 'revisa todo').",
        "Si la respuesta ya está en el resumen, NO uses BUSCAR.",
    ])
    return "\n".join(lines)


def render_actions_prompt() -> str:
    """Genera el contrato de acciones y sus ejemplos para el prompt."""
    lines = [
        "\n\n=== ACCIONES (con confirmación) ===",
        "Si el usuario pide modificar datos, propón la acción y agrega el ACCION_JSON en la última línea.",
        "Nunca afirmes que la ejecutaste antes de recibir confirmación explícita.",
        "Las preguntas y simulaciones no son órdenes: no agregues ACCION_JSON en esos casos.",
        "Para cambiar estados usa EMPACADO, LISTO_LLAMAR o ENTREGADA; para revertir, consulta primero la bitácora.",
        "Antes de proponer: verifica objetivo, datos reales, reglas, alcance, duplicación y posibilidad de verificación.",
    ]
    for spec in ACTIONS:
        lines.append(f"{spec.description} Ejemplo: ACCION_JSON: {spec.example}")
    lines.append("Si el usuario NO pide una acción, responde normal y NO agregues ACCION_JSON.")
    return "\n".join(lines)
