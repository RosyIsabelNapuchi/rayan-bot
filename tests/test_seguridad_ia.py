import json

import pandas as pd
from fastapi.testclient import TestClient

from rayan.access import validar
from rayan.config import Settings
from rayan.llm import LLM, validar_json


def test_control_de_acceso():
    usuarios = pd.DataFrame({"usuario": ["demo", "inactivo"], "nombre": ["D", "I"], "activo": [True, False]})
    assert validar("@Demo", usuarios)["autorizado"]
    assert validar("inactivo", usuarios)["motivo"] == "usuario inactivo"
    assert not validar("intruso", usuarios)["autorizado"]


def test_llm_solo_recibe_la_pregunta(bot):
    enviado = {}

    def transporte_falso(url, headers, payload, timeout):
        enviado.update(payload)
        return {"choices": [{"message": {"content": json.dumps(
            {"intent": "venta_entidad", "texto_entidad": "la condor", "tipo_entidad": "cliente", "anio": 2025})}}]}

    llm = LLM(Settings(llm_api_key="clave-de-prueba"), transport=transporte_falso)
    c = llm.interpretar("oye cuanto le vendimos a la condor el 2025", bot.catalogo)
    assert c.entidad == "Minera Cóndor de Plata" and c.anio == 2025 and c.origen == "llm"
    texto_enviado = json.dumps(enviado["messages"], ensure_ascii=False)
    assert "US$" not in texto_enviado and "Minera Cóndor de Plata" not in texto_enviado   # ni cifras ni catálogo


def test_json_invalido_del_llm_se_rechaza(bot):
    assert validar_json({"intent": "borrar_base_de_datos"}, bot.catalogo) is None
    c = validar_json({"intent": "top", "anio": "dos mil", "mes": 15, "limite": 999}, bot.catalogo)
    assert c.anio is None and c.mes is None and c.limite == 10


def test_sin_clave_no_se_usa_ia():
    assert not LLM(Settings(llm_api_key="TU_API_KEY")).disponible


def test_api_exige_usuario_autorizado():
    from rayan.api import app
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    ok = client.post("/preguntar", json={"texto": "venta 2025", "usuario": "demo"}).json()
    assert "Venta oficial" in ok["respuesta"]
    no = client.post("/preguntar", json={"texto": "venta 2025", "usuario": "intruso"}).json()
    assert "No tienes acceso" in no["respuesta"]
