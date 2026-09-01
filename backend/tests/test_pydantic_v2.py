from pydantic import ValidationError
from pydantic_ai.models.test import TestModel
import pytest

from app.agent.pydantic_v2 import ConsultaTool, build_agent


def test_adaptador_pydantic_se_construye_con_modelo_de_prueba():
    agent = build_agent(TestModel())
    assert agent.name == 'raloz-assistant-v2'


def test_consulta_tool_solo_acepta_tools_registradas():
    consulta = ConsultaTool(tipo='ventas_periodo', parametros={'mes': 9})
    assert consulta.tipo == 'ventas_periodo'

    with pytest.raises(ValidationError):
        ConsultaTool(tipo='funcion_inventada', parametros={})
