"""
Tests para el endpoint POST /api/tienda/lead
"""
import pytest
from unittest.mock import patch


class TestLeadEndpoint:
    def test_lead_exito(self, tienda_client):
        """Envío completo con todos los campos."""
        with patch('app.api.tienda.publico.enviar_email_lead') as mock_email:
            mock_email.return_value = True
            resp = tienda_client.post('/api/tienda/lead', json={
                'nombre':   'María López',
                'telefono': '3001234567',
                'email':    'maria@test.com',
                'mensaje':  'Necesito cotización para Manyanet, talla 10.',
            })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['ok'] is True

    def test_lead_minimo(self, tienda_client):
        """Solo teléfono y mensaje (los demás opcionales)."""
        with patch('app.api.tienda.publico.enviar_email_lead'):
            resp = tienda_client.post('/api/tienda/lead', json={
                'telefono': '3001234567',
                'mensaje':  '¿Tienen blazer para Marillac?',
            })
        assert resp.status_code == 201

    def test_lead_sin_telefono(self, tienda_client):
        """Teléfono es requerido."""
        resp = tienda_client.post('/api/tienda/lead', json={
            'telefono': '',
            'mensaje':  'Hola',
        })
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'telefono_requerido'

    def test_lead_sin_mensaje(self, tienda_client):
        """Mensaje es requerido."""
        resp = tienda_client.post('/api/tienda/lead', json={
            'telefono': '3001234567',
            'mensaje':  '',
        })
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'mensaje_requerido'

    def test_lead_telefono_corto(self, tienda_client):
        """Teléfono con menos de 7 dígitos es inválido."""
        resp = tienda_client.post('/api/tienda/lead', json={
            'telefono': '123',
            'mensaje':  'Hola',
        })
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'telefono_invalido'

    def test_lead_sin_body(self, tienda_client):
        """Sin body JSON debe retornar 400."""
        resp = tienda_client.post('/api/tienda/lead')
        assert resp.status_code == 400

    def test_lead_guarda_en_base(self, tienda_client):
        """El lead debe quedar guardado en la base de datos."""
        from app.models import Lead
        with patch('app.api.tienda.publico.enviar_email_lead'):
            resp = tienda_client.post('/api/tienda/lead', json={
                'nombre':   'Carlos Ruiz',
                'telefono': '3109876543',
                'email':    'carlos@test.com',
                'mensaje':  'Quiero saber el precio del uniforme Manyanet.',
            })
        assert resp.status_code == 201
        lead = Lead.query.filter_by(telefono='3109876543').first()
        assert lead is not None
        assert lead.nombre == 'Carlos Ruiz'
        assert lead.email == 'carlos@test.com'
        assert lead.mensaje == 'Quiero saber el precio del uniforme Manyanet.'
        assert lead.estado == 'pendiente'
        assert lead.origen == 'web'

    def test_lead_email_falla_no_bloquea_respuesta(self, tienda_client):
        """Si el email falla, el lead igual se guarda y retorna 201."""
        from app.models import Lead
        with patch('app.api.tienda.publico.enviar_email_lead') as mock_email:
            mock_email.side_effect = Exception('SMTP down')
            resp = tienda_client.post('/api/tienda/lead', json={
                'telefono': '3150001111',
                'mensaje':  'Prueba de error de email.',
            })
        assert resp.status_code == 201
        lead = Lead.query.filter_by(telefono='3150001111').first()
        assert lead is not None
