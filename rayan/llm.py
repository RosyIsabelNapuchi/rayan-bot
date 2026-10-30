"""Cliente LLM opcional, compatible con la API de Chat Completions (DeepSeek, OpenAI y similares).

Principio de diseño: al modelo SOLO se le envía la pregunta del usuario y la lista de intenciones válidas.
Nunca se le envían ventas, clientes ni cifras. El modelo devuelve un JSON con la intención y los datos
de la pregunta; ese JSON se valida y las cifras se calculan con las consultas predefinidas.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from .config import Settings, settings
from .nlu import DIMENSIONES, INTENTS, TIPOS, Catalogo, Consulta

SYSTEM_INTERPRETAR = (
    "Eres el intérprete de un asistente comercial. Convierte la pregunta en JSON con estas claves: "
    "intent (una de: {intents}), texto_entidad (nombre de cliente, vendedor, línea o marca tal como lo escribió "
    "el usuario, o null), tipo_entidad (una de: {tipos}, o null), dimension (una de: {dims}, o null), "
    "anio (entero o null), mes (1-12 o null), anio_comparacion (entero o null), limite (entero, por defecto 10). "
    "Responde SOLO el JSON, sin texto adicional. No inventes cifras."
)
SYSTEM_EXPLICAR = ("Eres Rayan, asistente comercial. Explica conceptos de negocio en español, en 3 líneas como máximo. "
                   "No des cifras de la empresa: no tienes acceso a ellas.")

Transport = Callable[[str, dict, dict, int], dict]


def _http_transport(url: str, headers: dict, payload: dict, timeout: int) -> dict:
    import requests

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class LLM:
    def __init__(self, cfg: Settings = settings, transport: Transport | None = None):
        self.cfg = cfg
        self.transport = transport or _http_transport

    @property
    def disponible(self) -> bool:
        return self.cfg.llm_enabled

    def _chat(self, system: str, user: str) -> str:
        url = f"{self.cfg.llm_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.cfg.llm_api_key}", "Content-Type": "application/json"}
        payload = {"model": self.cfg.llm_model, "temperature": 0,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        data = self.transport(url, headers, payload, self.cfg.llm_timeout)
        return data["choices"][0]["message"]["content"].strip()

    def interpretar(self, pregunta: str, catalogo: Catalogo) -> Consulta | None:
        system = SYSTEM_INTERPRETAR.format(intents=", ".join(INTENTS), tipos=", ".join(TIPOS), dims=", ".join(DIMENSIONES))
        try:
            raw = self._chat(system, pregunta)
            obj = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        except Exception:                                           # noqa: BLE001 - si falla, el bot sigue sin IA
            return None
        return validar_json(obj, catalogo)

    def explicar(self, pregunta: str) -> str | None:
        try:
            return self._chat(SYSTEM_EXPLICAR, pregunta)
        except Exception:                                           # noqa: BLE001
            return None


def validar_json(obj: dict, catalogo: Catalogo) -> Consulta | None:
    """Nada de lo que devuelve el modelo se usa sin validar: intención, tipos y rangos."""
    intent = obj.get("intent")
    if intent not in INTENTS:
        return None

    def entero(v, lo, hi):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return None
        return v if lo <= v <= hi else None

    c = Consulta(intent, dimension=obj.get("dimension") if obj.get("dimension") in DIMENSIONES else None,
                 anio=entero(obj.get("anio"), 2000, 2100), mes=entero(obj.get("mes"), 1, 12),
                 anio_comparacion=entero(obj.get("anio_comparacion"), 2000, 2100),
                 limite=entero(obj.get("limite"), 1, 50) or 10, origen="llm")
    texto = obj.get("texto_entidad")
    if texto:
        preferir = obj.get("tipo_entidad") if obj.get("tipo_entidad") in TIPOS else None
        c.entidad, c.tipo_entidad, c.sugerencias = catalogo.resolver(str(texto), preferir)   # se resuelve LOCALMENTE
        c.texto_entidad = None if c.entidad else str(texto)
    return c
