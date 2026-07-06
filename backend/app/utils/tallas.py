"""
Utilidades para manejo de tallas
═════════════════════════════════════════════════════════════════

El sistema maneja dos tipos de tallas:
  1. INDIVIDUAL (talla_individual): 4, 6, 8, 10, 12, 14, 16, S, M, L, XL
  2. AGRUPADA (talla_grupo): 6-8, 10-12, 14-16, S-M, L, XL (para precios)

La conversión es necesaria para:
  - Mostrar precios: usar talla_grupo
  - Manejar stock individual: usar talla_individual
"""


# Mapeo de talla individual a talla agrupada
TALLA_INDIVIDUAL_A_GRUPO = {
    '4': '4',
    '6': '6-8',
    '8': '6-8',
    '10': '10-12',
    '12': '10-12',
    '14': '14-16',
    '16': '14-16',
    'S': 'S-M',
    'M': 'S-M',
    'L': 'L',
    'XL': 'XL',
}

# Tallas individuales válidas (para stock)
TALLAS_INDIVIDUALES = set(TALLA_INDIVIDUAL_A_GRUPO.keys())

# Tallas agrupadas válidas (para precios)
TALLAS_AGRUPADAS = set(TALLA_INDIVIDUAL_A_GRUPO.values())

# Inverso: talla grupo a tallas individuales que abarca
TALLA_GRUPO_A_INDIVIDUALES = {
    '4': ['4'],
    '6-8': ['6', '8'],
    '10-12': ['10', '12'],
    '14-16': ['14', '16'],
    'S-M': ['S', 'M'],
    'L': ['L'],
    'XL': ['XL'],
}


def convertir_a_grupo(talla_individual: str) -> str:
    """
    Convertir una talla individual a su grupo.

    Args:
        talla_individual: talla individual (6, 8, S, M, etc)

    Returns:
        talla_grupo correspondiente (6-8, S-M, etc)

    Raises:
        ValueError: si la talla no es válida
    """
    if talla_individual not in TALLA_INDIVIDUAL_A_GRUPO:
        raise ValueError(f"Talla individual no válida: {talla_individual}")
    return TALLA_INDIVIDUAL_A_GRUPO[talla_individual]


def convertir_a_individuales(talla_grupo: str) -> list:
    """
    Convertir una talla agrupada a sus tallas individuales.

    Args:
        talla_grupo: talla agrupada (6-8, S-M, etc)

    Returns:
        lista de tallas individuales que abarca

    Raises:
        ValueError: si la talla no es válida
    """
    if talla_grupo not in TALLA_GRUPO_A_INDIVIDUALES:
        raise ValueError(f"Talla agrupada no válida: {talla_grupo}")
    return TALLA_GRUPO_A_INDIVIDUALES[talla_grupo]


def validar_talla_individual(talla: str) -> bool:
    """Verificar si una talla individual es válida"""
    return str(talla) in TALLAS_INDIVIDUALES


def validar_talla_grupo(talla: str) -> bool:
    """Verificar si una talla agrupada es válida"""
    return str(talla) in TALLAS_AGRUPADAS


def obtener_tallas_individuales_validas() -> list:
    """Obtener lista de tallas individuales válidas"""
    return sorted(list(TALLAS_INDIVIDUALES))


def obtener_tallas_agrupadas_validas() -> list:
    """Obtener lista de tallas agrupadas válidas"""
    return sorted(list(TALLAS_AGRUPADAS))


# ═══════════════════════════════════════════════════════════════
# Regla de MEDIAS y expansión de grupos (compartida por el catálogo
# del panel — utils/inventario.py — y el de la tienda — api/tienda/publico.py)
# ═══════════════════════════════════════════════════════════════

def es_producto_medias(tipo_producto) -> bool:
    """Las medias se manejan por GRUPO (4-6, 6-8, 8-10, 10-12, 12-14): el grupo
    ES la talla y NO se expande, porque sus grupos chocan con los de ropa
    (6-8 → 6,8)."""
    return 'media' in (tipo_producto or '').lower()


def expandir_grupo_para_producto(tipo_producto, talla_grupo) -> list:
    """Tallas individuales que cubre un talla_grupo según el tipo de producto:
    para medias el grupo es la talla; para el resto se expande (6-8 → [6, 8]).
    Grupos desconocidos se devuelven tal cual (comportamiento tolerante que ya
    tenían ambos catálogos)."""
    if es_producto_medias(tipo_producto):
        return [talla_grupo]
    return TALLA_GRUPO_A_INDIVIDUALES.get(talla_grupo, [talla_grupo])
