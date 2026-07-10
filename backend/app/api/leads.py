"""
API de Leads — gestión de solicitudes de cotización desde la tienda web.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app import db
from app.models import Lead
from app.utils.decorators import get_current_identity

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/', methods=['GET'])
@jwt_required()
def listar_leads():
    """
    Lista todos los leads (admin).
    Query params:
        - estado: filtrar por estado ('pendiente', 'contactado', 'convertido', 'descartado')
        - limite: cuántos devolver (default 50)
    """
    identity = get_current_identity()
    estado = request.args.get('estado', '').strip()
    limite = min(int(request.args.get('limite', 50)), 200)

    q = Lead.query.order_by(Lead.creada.desc())
    if estado:
        q = q.filter_by(estado=estado)

    leads = q.limit(limite).all()

    return jsonify({
        'leads': [l.to_dict() for l in leads],
        'total': q.count(),
    }), 200


@leads_bp.route('/<int:id_lead>', methods=['GET'])
@jwt_required()
def obtener_lead(id_lead):
    """Detalle de un lead."""
    lead = Lead.query.get_or_404(id_lead)
    return jsonify(lead.to_dict()), 200


@leads_bp.route('/<int:id_lead>/estado', methods=['PATCH'])
@jwt_required()
def cambiar_estado_lead(id_lead):
    """Actualiza el estado de un lead."""
    data = request.get_json() or {}
    nuevo_estado = data.get('estado', '').strip()
    estados_validos = {'pendiente', 'contactado', 'convertido', 'descartado'}
    if nuevo_estado not in estados_validos:
        return jsonify({'error': f'Estado inválido. Use: {", ".join(estados_validos)}'}), 400

    lead = Lead.query.get_or_404(id_lead)
    lead.estado = nuevo_estado
    db.session.commit()
    return jsonify(lead.to_dict()), 200


@leads_bp.route('/resumen', methods=['GET'])
@jwt_required()
def resumen_leads():
    """Resumen rápido de leads para el panel."""
    hoy = db.func.current_date()
    inicio_mes = db.func.current_date()

    pendientes = Lead.query.filter_by(estado='pendiente').count()
    contactados = Lead.query.filter_by(estado='contactado').count()
    convertidos = Lead.query.filter_by(estado='convertido').count()
    total = Lead.query.count()

    return jsonify({
        'pendientes': pendientes,
        'contactados': contactados,
        'convertidos': convertidos,
        'total': total,
    }), 200
