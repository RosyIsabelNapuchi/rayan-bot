"""Carga de fuentes y regla de oro: el libro mayor es la venta oficial; el detalle comercial solo se usa
para documentos que existen en el libro mayor."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .config import settings

MAYOR_COLS = ["documento", "fecha", "cliente_id", "cliente", "vendedor", "linea", "venta_usd"]
DETALLE_COLS = ["documento", "tipo_doc", "fecha", "articulo", "descripcion", "marca", "linea", "cantidad",
                "total_usd", "costo_usd", "margen_usd"]


@dataclass(frozen=True)
class Fuentes:
    mayor: pd.DataFrame            # venta oficial (finanzas)
    detalle: pd.DataFrame          # detalle comercial completo
    detalle_valido: pd.DataFrame   # detalle filtrado por documentos del mayor
    usuarios: pd.DataFrame


def _require(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {name}: {missing}")


def cargar(data_dir: Path | None = None) -> Fuentes:
    d = Path(data_dir or settings.data_dir)
    mayor = pd.read_csv(d / "libro_mayor.csv", parse_dates=["fecha"])
    detalle = pd.read_csv(d / "detalle_ventas.csv", parse_dates=["fecha"])
    usuarios = pd.read_csv(d / "usuarios.csv")
    _require(mayor, MAYOR_COLS, "libro_mayor")
    _require(detalle, DETALLE_COLS, "detalle_ventas")
    for df in (mayor, detalle):
        df["documento"] = df.documento.astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True)
    # Notas de crédito: si vienen positivas, se vuelven negativas (si ya son negativas, se respetan)
    nc = detalle.tipo_doc.str.upper().isin(["NC", "DV"])
    for col in ("cantidad", "total_usd", "costo_usd", "margen_usd"):
        detalle.loc[nc & (detalle[col] > 0), col] *= -1
    valido = detalle[detalle.documento.isin(set(mayor.documento))].copy()
    return Fuentes(mayor, detalle, valido, usuarios)


@lru_cache(maxsize=1)
def fuentes() -> Fuentes:
    return cargar()


def refrescar() -> None:
    fuentes.cache_clear()
