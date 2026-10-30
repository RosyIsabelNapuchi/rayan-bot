"""Las cifras del bot deben coincidir con un cálculo independiente en pandas."""
import pytest


def test_venta_total_anual(bot, fuentes):
    r = bot.responder("venta 2025")
    esperado = fuentes.mayor[fuentes.mayor.fecha.dt.year == 2025].venta_usd.sum()
    assert r.datos["venta_usd"] == pytest.approx(esperado)


def test_venta_cliente_mes(bot, fuentes):
    r = bot.responder("cuanto le vendimos a minera condor en marzo 2026")
    m = fuentes.mayor
    esperado = m[(m.cliente == "Minera Cóndor de Plata") & (m.fecha.dt.year == 2026) & (m.fecha.dt.month == 3)].venta_usd.sum()
    assert r.datos["venta_usd"] == pytest.approx(esperado)


def test_top_clientes_ordenado_y_correcto(bot, fuentes):
    r = bot.responder("top 5 clientes 2025")
    m = fuentes.mayor[fuentes.mayor.fecha.dt.year == 2025]
    esperado = m.groupby("cliente").venta_usd.sum().nlargest(5)
    assert [k for k, _ in r.datos["ranking"]] == list(esperado.index)


def test_detalle_solo_documentos_del_mayor(fuentes):
    """Regla de oro: el detalle comercial válido solo contiene documentos que existen en el libro mayor."""
    assert set(fuentes.detalle_valido.documento) <= set(fuentes.mayor.documento)
    assert len(fuentes.detalle) > len(fuentes.detalle_valido)         # hay documentos huérfanos excluidos


def test_notas_de_credito_restan(fuentes):
    nc = fuentes.detalle[fuentes.detalle.tipo_doc == "NC"]
    assert len(nc) > 0 and (nc.total_usd <= 0).all()


def test_margen_linea(bot, fuentes):
    r = bot.responder("margen de la linea bombas 2025")
    d = fuentes.detalle_valido
    d = d[(d.linea == "Bombas") & (d.fecha.dt.year == 2025)]
    assert r.datos["margen_pct"] == pytest.approx(d.margen_usd.sum() / d.total_usd.sum())


def test_comparacion_anio_en_curso_usa_mismo_periodo(bot, fuentes):
    r = bot.responder("compara 2026 vs 2025")
    m = fuentes.mayor
    ultimo_mes = m[m.fecha.dt.year == 2026].fecha.dt.month.max()
    base = m[(m.fecha.dt.year == 2025) & (m.fecha.dt.month <= ultimo_mes)].venta_usd.sum()
    assert r.datos["venta_base"] == pytest.approx(base)


def test_conciliacion_detecta_diferencias(bot):
    r = bot.responder("concilia el mayor con el detalle de 2025")
    assert r.datos["docs_con_diferencia"] > 0 and r.datos["docs_fuera_del_mayor"] > 0


def test_nombre_ambiguo_pide_aclaracion(bot):
    r = bot.responder("ventas de minera azul")
    assert r.datos.get("aclaracion") and "Minera Quebrada Azul" in r.texto


def test_no_inventa_cuando_no_entiende(bot):
    r = bot.responder("cual es el clima hoy")
    assert r.datos.get("no_entendida") and "US$" not in r.texto
