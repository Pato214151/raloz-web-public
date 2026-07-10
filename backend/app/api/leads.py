"""
API de Leads — gestión de solicitudes de cotización desde la tienda web.
Solo para el equipo de ventas (administrador / vendedor).
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models import Lead
from app.utils.decorators import rol_requerido

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/', methods=['GET'])
@rol_requerido('administrador', 'vendedor')
def listar_leads():
    """
    Lista todos los leads.
    Query params:
        - estado: filtrar por estado ('pendiente', 'contactado', 'convertido', 'descartado')
        - limite: cuántos devolver (default 50, máx 200)
    """
    estado = request.args.get('estado', '').strip()
    origen = request.args.get('origen', '').strip()
    limite = min(int(request.args.get('limite', 50)), 200)

    q = Lead.query.order_by(Lead.creada.desc())
    if estado:
        q = q.filter_by(estado=estado)
    if origen in ('web', 'whatsapp'):
        q = q.filter_by(origen=origen)

    leads = q.limit(limite).all()

    return jsonify({
        'leads': [l.to_dict() for l in leads],
        'total': q.count(),
    }), 200


@leads_bp.route('/<int:id_lead>', methods=['GET'])
@rol_requerido('administrador', 'vendedor')
def obtener_lead(id_lead):
    """Detalle de un lead."""
    lead = Lead.query.get_or_404(id_lead)
    return jsonify(lead.to_dict()), 200


@leads_bp.route('/<int:id_lead>/estado', methods=['PATCH'])
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
def resumen_leads():
    """Resumen rápido de leads para el panel."""
    pendientes = Lead.query.filter_by(estado='pendiente').count()
    contactados = Lead.query.filter_by(estado='contactado').count()
    convertidos = Lead.query.filter_by(estado='convertido').count()
    total = Lead.query.count()

    # Desglose por origen (solo pendientes)
    de_web = Lead.query.filter_by(estado='pendiente', origen='web').count()
    de_wa  = Lead.query.filter_by(estado='pendiente', origen='whatsapp').count()

    return jsonify({
        'pendientes': pendientes,
        'contactados': contactados,
        'convertidos': convertidos,
        'total': total,
        'pendientes_web': de_web,
        'pendientes_whatsapp': de_wa,
    }), 200
