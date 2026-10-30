"""Control de acceso: solo usuarios activos de la lista pueden consultar."""
from __future__ import annotations

import pandas as pd


def normalizar_usuario(u: str | None) -> str:
    return str(u or "").strip().lstrip("@").lower()


def validar(usuario: str | None, usuarios: pd.DataFrame) -> dict:
    u = normalizar_usuario(usuario)
    tabla = usuarios.assign(_u=usuarios.usuario.map(normalizar_usuario))
    fila = tabla[tabla._u == u]
    if not u or fila.empty:
        return {"autorizado": False, "motivo": "usuario no registrado"}
    if not bool(fila.activo.iloc[0]):
        return {"autorizado": False, "motivo": "usuario inactivo"}
    return {"autorizado": True, "usuario": u, "nombre": str(fila.nombre.iloc[0])}
