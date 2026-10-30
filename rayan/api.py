"""API REST.   Ejecutar: uvicorn rayan.api:app --reload   →   http://127.0.0.1:8000/docs"""
from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .bot import Rayan
from .data import refrescar

app = FastAPI(title="Rayan Bot API (datos sintéticos)", version="1.0.0")


class Pregunta(BaseModel):
    texto: str = Field(min_length=1, max_length=500, examples=["top 5 clientes 2025"])
    usuario: str = Field(examples=["demo"])


@lru_cache
def _bot() -> Rayan:
    return Rayan()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ia_disponible": _bot().llm.disponible}


@app.post("/preguntar")
def preguntar(p: Pregunta) -> dict:
    r = _bot().responder(p.texto, usuario=p.usuario)
    return {"respuesta": r.texto, "datos": r.datos}


@app.post("/refrescar")
def refrescar_datos() -> dict:
    refrescar()
    _bot.cache_clear()
    return {"status": "datos recargados"}
