"""
Validaciones de entrada para la API
"""

import re
import bleach
from datetime import datetime


def sanitize_string(value, max_length=500):
    """Limpiar strings de HTML/scripts maliciosos"""
    if not value:
        return value
    cleaned = bleach.clean(str(value).strip(), tags=[], strip=True)
    return cleaned[:max_length]


def validate_email(email):
    """Validar formato de email"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone):
    """Validar formato de teléfono colombiano"""
    if not phone:
        return True  # Opcional
    cleaned = re.sub(r'[\s\-\+\(\)]', '', phone)
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def validate_date(date_str, fmt='%Y-%m-%d'):
    """Validar y parsear fecha"""
    try:
        return datetime.strptime(date_str, fmt).date()
    except (ValueError, TypeError):
        return None


def validate_positive_number(value):
    """Validar que sea un número positivo"""
    try:
        num = float(value)
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_required_fields(data, fields):
    """Validar que todos los campos requeridos existan"""
    missing = [f for f in fields if not data.get(f)]
    if missing:
        return False, f"Campos requeridos faltantes: {', '.join(missing)}"
    return True, None
