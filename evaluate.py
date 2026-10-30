"""Mide qué tan bien entiende Rayan las preguntas (sin IA): intención, entidad, período y límite.

Tres conjuntos: `preguntas_desarrollo.csv` (se usaron para ajustar las reglas), `preguntas_prueba.csv`
(escritas aparte, sin ajustar después) y `preguntas_dificiles.csv` (frases coloquiales y ambiguas, evaluadas
una sola vez y sin ajustar las reglas). El número más honesto es el de las difíciles.
Uso: python evaluate.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from rayan.bot import Rayan

ROOT = Path(__file__).parent
CAMPOS = ["intent", "entidad", "dimension", "anio", "mes", "limite"]


def _norm(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return str(v)


def evaluar(bot: Rayan, archivo: Path) -> tuple[pd.DataFrame, dict]:
    casos = pd.read_csv(archivo, dtype=str).fillna("")
    filas = []
    for caso in casos.itertuples(index=False):
        c = bot.entender(caso.pregunta).dict()
        fila = {"pregunta": caso.pregunta}
        ok_total = True
        for campo in CAMPOS:
            esperado = _norm(getattr(caso, campo))
            obtenido = _norm(c.get(campo))
            if campo == "limite" and esperado is None:          # el límite solo se evalúa si se especifica
                continue
            if campo in ("dimension",) and esperado is None:
                continue
            ok = esperado == obtenido
            fila[f"{campo}_ok"] = ok
            fila[f"{campo}_obtenido"] = obtenido
            ok_total &= ok
        fila["todo_ok"] = ok_total
        filas.append(fila)
    df = pd.DataFrame(filas)
    resumen = {"preguntas": len(df), "exactas": round(float(df.todo_ok.mean()), 3),
               **{f"{c}_acierto": round(float(df[f"{c}_ok"].dropna().mean()), 3) for c in CAMPOS if f"{c}_ok" in df}}
    return df, resumen


def main() -> None:
    bot = Rayan(exigir_usuario=False)
    out = {}
    (ROOT / "reports").mkdir(exist_ok=True)
    for nombre in ("desarrollo", "prueba", "dificiles"):
        df, resumen = evaluar(bot, ROOT / "data" / f"preguntas_{nombre}.csv")
        df.to_csv(ROOT / "reports" / f"evaluacion_{nombre}.csv", index=False)
        out[nombre] = resumen
        fallas = df[~df.todo_ok]
        print(f"\n=== {nombre}: {resumen}")
        for f in fallas.itertuples():
            print("  ✗", f.pregunta)
    (ROOT / "reports" / "evaluacion.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
