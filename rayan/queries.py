"""Consultas predefinidas. Cada una devuelve texto para el chat y `datos` para auditar/probar las cifras."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .data import Fuentes
from .nlu import Consulta

MESES_TXT = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]
COL = {"cliente": "cliente", "vendedor": "vendedor", "linea": "linea"}


@dataclass
class Respuesta:
    texto: str
    datos: dict = field(default_factory=dict)


def usd(v: float) -> str:
    return f"US$ {v:,.0f}" if abs(v) >= 1000 else f"US$ {v:,.2f}"


def periodo_txt(c: Consulta) -> str:
    if c.anio and c.mes:
        return f" en {MESES_TXT[c.mes]} {c.anio}"
    if c.anio:
        return f" en {c.anio}"
    return " (todo el histórico)" if not c.mes else f" en {MESES_TXT[c.mes]} (todos los años)"


def filtrar(df: pd.DataFrame, c: Consulta, anio: int | None = None) -> pd.DataFrame:
    anio = anio if anio is not None else c.anio
    if anio:
        df = df[df.fecha.dt.year == anio]
    if c.mes:
        df = df[df.fecha.dt.month == c.mes]
    return df


def _mayor_entidad(f: Fuentes, c: Consulta) -> pd.DataFrame:
    """Documentos oficiales de la entidad (para marca: los documentos donde aparece la marca)."""
    if c.tipo_entidad == "marca":
        docs = set(f.detalle_valido.loc[f.detalle_valido.marca == c.entidad, "documento"])
        return f.mayor[f.mayor.documento.isin(docs)]
    return f.mayor[f.mayor[COL[c.tipo_entidad]] == c.entidad]


def venta_total(f: Fuentes, c: Consulta) -> Respuesta:
    m = filtrar(f.mayor, c)
    if m.empty:
        return Respuesta(f"No encontré ventas oficiales{periodo_txt(c)}.", {"venta_usd": 0.0})
    total = float(m.venta_usd.sum())
    return Respuesta(f"Venta oficial{periodo_txt(c)}: {usd(total)}\n• Documentos: {m.documento.nunique():,}\n"
                     f"• Clientes con compra: {m.cliente.nunique():,}",
                     {"venta_usd": total, "documentos": int(m.documento.nunique())})


def venta_entidad(f: Fuentes, c: Consulta) -> Respuesta:
    if c.tipo_entidad == "marca":                               # la marca solo existe en el detalle
        d = filtrar(f.detalle_valido[f.detalle_valido.marca == c.entidad], c)
        total = float(d.total_usd.sum())
        return Respuesta(f"Venta de la marca {c.entidad}{periodo_txt(c)}: {usd(total)}\n"
                         f"• Unidades: {d.cantidad.sum():,.0f} · Documentos: {d.documento.nunique():,}",
                         {"venta_usd": total})
    m = filtrar(_mayor_entidad(f, c), c)
    total = float(m.venta_usd.sum())
    if m.empty:
        return Respuesta(f"No encontré ventas oficiales de {c.entidad}{periodo_txt(c)}.", {"venta_usd": 0.0})
    otro = {"cliente": "linea", "vendedor": "cliente", "linea": "cliente"}[c.tipo_entidad]
    top = m.groupby(otro).venta_usd.sum().sort_values(ascending=False).head(3)
    detalle = "\n".join(f"{i}. {k}: {usd(v)}" for i, (k, v) in enumerate(top.items(), 1))
    titulo = {"linea": "Principales líneas", "cliente": "Principales clientes"}[otro]
    return Respuesta(f"Venta oficial de {c.entidad}{periodo_txt(c)}: {usd(total)}\n"
                     f"• Documentos: {m.documento.nunique():,}\n\n{titulo}:\n{detalle}",
                     {"venta_usd": total, "documentos": int(m.documento.nunique())})


def top(f: Fuentes, c: Consulta) -> Respuesta:
    dim = c.dimension or "clientes"
    if dim in ("marcas", "productos"):
        d = filtrar(f.detalle_valido, c)
        if dim == "marcas":
            d = d[d.marca != "Servicio propio"]                    # los servicios no son una marca
        col = "marca" if dim == "marcas" else "descripcion"
        rank = d.groupby(col).total_usd.sum()
    else:
        rank = filtrar(f.mayor, c).groupby({"clientes": "cliente", "vendedores": "vendedor", "lineas": "linea"}[dim]).venta_usd.sum()
    rank = rank.sort_values(ascending=False).head(c.limite)
    if rank.empty:
        return Respuesta(f"No encontré datos para el ranking{periodo_txt(c)}.", {"ranking": []})
    filas = "\n".join(f"{i}. {k}: {usd(v)}" for i, (k, v) in enumerate(rank.items(), 1))
    return Respuesta(f"Top {len(rank)} {dim}{periodo_txt(c)}:\n{filas}",
                     {"ranking": [(k, float(v)) for k, v in rank.items()]})


def que_compro(f: Fuentes, c: Consulta) -> Respuesta:
    docs = set(filtrar(_mayor_entidad(f, c), c).documento)
    d = f.detalle_valido[f.detalle_valido.documento.isin(docs)]
    if d.empty:
        return Respuesta(f"No encontré artículos facturados a {c.entidad}{periodo_txt(c)}.", {"articulos": []})
    rank = d.groupby("descripcion")[["cantidad", "total_usd"]].sum().sort_values("total_usd", ascending=False).head(c.limite)
    filas = "\n".join(f"{i}. {k} · {r.cantidad:,.0f} und · {usd(r.total_usd)}" for i, (k, r) in enumerate(rank.iterrows(), 1))
    return Respuesta(f"Lo que más compró {c.entidad}{periodo_txt(c)}:\n{filas}",
                     {"articulos": [(k, float(r.total_usd)) for k, r in rank.iterrows()]})


def margen(f: Fuentes, c: Consulta) -> Respuesta:
    d = f.detalle_valido
    if c.entidad:
        if c.tipo_entidad == "marca":
            d = d[d.marca == c.entidad]
        elif c.tipo_entidad == "linea":
            d = d[d.linea == c.entidad]
        else:
            d = d[d.documento.isin(set(_mayor_entidad(f, c).documento))]
    d = filtrar(d, c)
    venta, mg = float(d.total_usd.sum()), float(d.margen_usd.sum())
    if venta == 0:
        return Respuesta(f"No encontré ventas con margen para {c.entidad or 'ese período'}{periodo_txt(c)}.", {"margen_pct": None})
    sujeto = c.entidad or "la empresa"
    return Respuesta(f"Margen de {sujeto}{periodo_txt(c)}: {usd(mg)} ({mg / venta:.1%} sobre la venta de {usd(venta)})",
                     {"margen_usd": mg, "venta_usd": venta, "margen_pct": mg / venta})


def comparar(f: Fuentes, c: Consulta, anio_max: int) -> Respuesta:
    a1 = c.anio or anio_max
    a0 = c.anio_comparacion or (a1 - 1)
    a0, a1 = sorted((a0, a1))
    base = _mayor_entidad(f, c) if c.entidad and c.tipo_entidad != "marca" else f.mayor
    if c.entidad and c.tipo_entidad == "marca":
        det = f.detalle_valido[f.detalle_valido.marca == c.entidad]
        v0, v1 = (float(filtrar(det, c, a).total_usd.sum()) for a in (a0, a1))
    else:
        v0, v1 = (float(filtrar(base, c, a).venta_usd.sum()) for a in (a0, a1))
    meses_a1 = filtrar(f.mayor, c, a1).fecha.dt.month.max()
    nota = ""
    if not c.mes and a1 == anio_max and meses_a1 and meses_a1 < 12:      # año en curso: comparar mismo período
        v0 = float(base[(base.fecha.dt.year == a0) & (base.fecha.dt.month <= meses_a1)].venta_usd.sum()) \
            if not (c.entidad and c.tipo_entidad == "marca") else \
            float(det[(det.fecha.dt.year == a0) & (det.fecha.dt.month <= meses_a1)].total_usd.sum())
        nota = f" (comparando enero–{MESES_TXT[int(meses_a1)]} de ambos años)"
    var = (v1 / v0 - 1) if v0 else None
    sujeto = c.entidad or "Venta total"
    var_txt = f"{var:+.1%}" if var is not None else "sin base de comparación"
    return Respuesta(f"{sujeto}: {a0} {usd(v0)} → {a1} {usd(v1)} · variación {var_txt}{nota}",
                     {"anio_base": a0, "anio": a1, "venta_base": v0, "venta": v1, "variacion": var})


def resumen(f: Fuentes, c: Consulta, anio_max: int) -> Respuesta:
    anio = c.anio or anio_max
    m = f.mayor[f.mayor.fecha.dt.year == anio]
    d = f.detalle_valido[f.detalle_valido.fecha.dt.year == anio]
    total = float(m.venta_usd.sum())
    top_c = m.groupby("cliente").venta_usd.sum().nlargest(1)
    top_l = m.groupby("linea").venta_usd.sum().nlargest(1)
    mg = float(d.margen_usd.sum()) / max(float(d.total_usd.sum()), 1e-9)
    return Respuesta(f"Resumen {anio}:\n• Venta oficial: {usd(total)}\n• Clientes con compra: {m.cliente.nunique()}\n"
                     f"• Margen: {mg:.1%}\n• Cliente principal: {top_c.index[0]} ({usd(top_c.iloc[0])})\n"
                     f"• Línea principal: {top_l.index[0]} ({usd(top_l.iloc[0])})",
                     {"venta_usd": total, "margen_pct": mg})


def conciliacion(f: Fuentes, c: Consulta) -> Respuesta:
    """Venta oficial (mayor) vs. detalle comercial, documento por documento."""
    m = filtrar(f.mayor, c).groupby("documento").venta_usd.sum()
    d_all = filtrar(f.detalle, c).groupby("documento").total_usd.sum()
    d = d_all[d_all.index.isin(m.index)]
    comp = pd.concat([m.rename("mayor"), d.rename("detalle")], axis=1).fillna(0.0)
    comp["dif"] = comp.mayor - comp.detalle
    dif = comp[comp.dif.abs() > 1.0]
    fuera = d_all[~d_all.index.isin(m.index)]
    filas = "\n".join(f"• {doc}: mayor {usd(r.mayor)} vs detalle {usd(r.detalle)}"
                      for doc, r in dif.reindex(dif.dif.abs().sort_values(ascending=False).index).head(5).iterrows())
    return Respuesta(f"Conciliación{periodo_txt(c)}:\n• Venta oficial (mayor): {usd(comp.mayor.sum())}\n"
                     f"• Detalle comercial de esos documentos: {usd(comp.detalle.sum())}\n"
                     f"• Documentos con diferencia > US$ 1: {len(dif)} de {len(comp)}\n"
                     f"• Documentos del detalle que no están en el mayor (excluidos): {len(fuera)}"
                     + (f"\n\nMayores diferencias:\n{filas}" if filas else ""),
                     {"docs_con_diferencia": int(len(dif)), "docs_fuera_del_mayor": int(len(fuera)),
                      "diferencia_usd": float(comp.dif.sum())})
