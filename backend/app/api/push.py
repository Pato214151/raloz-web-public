"""
Notificaciones Web Push al panel (PWA).

El navegador se suscribe (con permiso del usuario) y guarda su suscripción aquí.
Cuando llega un mensaje de WhatsApp entrante, el backend le envía un push
("nuevo mensaje de …") aunque la app esté cerrada.

Config por variables de entorno (en Render):
  VAPID_PRIVATE_KEY  → clave privada en PEM (secreta)
  VAPID_PUBLIC_KEY   → clave pública en base64url (la usa el navegador)
  VAPID_SUBJECT      → 'mailto:tucorreo@dominio.com' (opcional)

Si no están configuradas, la función queda inerte (no rompe nada).
"""
import os

from flask import Blueprint, request, jsonify

from app import db
from app.models import PushSubscription
from app.utils.decorators import rol_requerido, get_current_identity

push_bp = Blueprint('push', __name__)


def _vapid():
    # La privada es un PEM multilínea; se admite pegada en una sola línea con "\n".
    priv = os.getenv('VAPID_PRIVATE_KEY', '').strip().replace('\\n', '\n')
    pub = os.getenv('VAPID_PUBLIC_KEY', '').strip()
    sub = os.getenv('VAPID_SUBJECT', 'mailto:jramirezramirez2005@gmail.com').strip()
    return priv, pub, sub


def push_configurado():
    priv, pub, _ = _vapid()
    return bool(priv and pub)


def enviar_push_a_todos(titulo, cuerpo, url='/whatsapp', tag=None):
    """Envía una notificación a todas las suscripciones. Best-effort:
    nunca lanza excepción hacia el llamador; borra las suscripciones muertas."""
    priv, pub, sub = _vapid()
    if not (priv and pub):
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        return 0

    import json
    payload = json.dumps({'title': titulo, 'body': cuerpo, 'url': url, 'tag': tag or 'wa'})
    enviados = 0
    for s in PushSubscription.query.all():
        try:
            webpush(
                subscription_info=s.to_webpush(),
                data=payload,
                vapid_private_key=priv,
                vapid_claims={'sub': sub},
                timeout=10,
            )
            enviados += 1
        except WebPushException as e:
            # 404/410 = suscripción caduca → limpiarla
            code = getattr(getattr(e, 'response', None), 'status_code', None)
            if code in (404, 410):
                db.session.delete(s)
        except Exception:
            pass
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return enviados


# ─────────────────────────── Endpoints ───────────────────────────
@push_bp.route('/public-key', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def public_key():
    _, pub, _ = _vapid()
    return jsonify({'public_key': pub, 'configured': bool(pub)})


@push_bp.route('/subscribe', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def subscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    p256dh, auth = keys.get('p256dh'), keys.get('auth')
    if not (endpoint and p256dh and auth):
        return jsonify({'error': 'suscripción incompleta'}), 400

    usuario = (get_current_identity() or {}).get('usuario')
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if sub:
        sub.p256dh, sub.auth, sub.usuario = p256dh, auth, usuario
    else:
        db.session.add(PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth, usuario=usuario))
    db.session.commit()
    return jsonify({'ok': True})


@push_bp.route('/unsubscribe', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.query.filter_by(endpoint=endpoint).delete()
        db.session.commit()
    return jsonify({'ok': True})


@push_bp.route('/test', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def test():
    if not push_configurado():
        return jsonify({'error': 'push no configurado en el servidor'}), 400
    n = enviar_push_a_todos('RALOZ · Prueba', 'Las notificaciones están activas ✅', url='/whatsapp')
    return jsonify({'ok': True, 'enviados': n})
