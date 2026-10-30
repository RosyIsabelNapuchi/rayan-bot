"""Guardia de regresión: la comprensión no debe empeorar en los conjuntos de desarrollo y prueba."""
from pathlib import Path

from evaluate import evaluar

DATA = Path(__file__).parents[1] / "data"


def test_desarrollo(bot):
    _, r = evaluar(bot, DATA / "preguntas_desarrollo.csv")
    assert r["exactas"] >= 0.95


def test_prueba(bot):
    _, r = evaluar(bot, DATA / "preguntas_prueba.csv")
    assert r["exactas"] >= 0.90


def test_dificiles_entidades(bot):
    _, r = evaluar(bot, DATA / "preguntas_dificiles.csv")
    assert r["entidad_acierto"] >= 0.90          # la intención aún falla en frases coloquiales (ver README)
