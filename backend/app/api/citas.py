"""
API de Citas.

  - El BOT crea citas con el secreto compartido X-Bot-Token (WA_LOG_TOKEN).
  - El PANEL lista y cambia el estado de las citas con JWT (admin/vendedor/cajero).
"""

import os

from flask import Blueprint, request, jsonify

from app import db
from app.models import Cita
from app.utils.decorators import rol_requerido

citas_bp = Blueprint('citas', __name__)

ESTADOS = ('pendiente', 'confirmada', 'atendida', 'cancelada')


def _bot_autorizado():
    esperado = os.getenv('WA_LOG_TOKEN', '')
    return bool(esperado) and request.headers.get('X-Bot-Token', '') == esperado


@citas_bp.route('/nueva', methods=['POST'])
def crear_cita():
    """El bot registra una solicitud de cita."""
    if not _bot_autorizado():
        return jsonify({'error': 'no autorizado'}), 401
    data = request.get_json(silent=True) or {}
    cita = Cita(
        chat_id=(data.get('chat_id') or '')[:40],
        nombre=(data.get('nombre') or '')[:160],
        dia=(data.get('dia') or '')[:120],
        hora=(data.get('hora') or '')[:60],
        colegio=(data.get('colegio') or '')[:120],
        estado='pendiente',
    )
    db.session.add(cita)
    db.session.commit()
    return jsonify({'ok': True, 'id_cita': cita.id_cita})


@citas_bp.route('', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def listar_citas():
    q = Cita.query
    estado = request.args.get('estado')
    if estado in ESTADOS:
        q = q.filter_by(estado=estado)
    citas = q.order_by(Cita.creada.desc()).limit(300).all()
    return jsonify([c.to_dict() for c in citas])


@citas_bp.route('/pendientes/conteo', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def conteo_pendientes():
    n = Cita.query.filter_by(estado='pendiente').count()
    return jsonify({'pendientes': n})


@citas_bp.route('/<int:id_cita>/estado', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def cambiar_estado(id_cita):
    data = request.get_json(silent=True) or {}
    nuevo = (data.get('estado') or '').strip()
    if nuevo not in ESTADOS:
        return jsonify({'error': f'estado debe ser uno de {ESTADOS}'}), 400
    cita = db.session.get(Cita, id_cita)
    if not cita:
        return jsonify({'error': 'cita no encontrada'}), 404
    cita.estado = nuevo
    db.session.commit()
    return jsonify({'ok': True, 'estado': nuevo})
