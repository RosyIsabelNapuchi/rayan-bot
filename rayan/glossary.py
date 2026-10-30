"""Respuestas conceptuales locales (sin IA): definiciones de negocio que el bot puede explicar siempre."""
GLOSARIO = {
    "margen": "El margen es la venta menos el costo. En porcentaje: margen / venta. Te dice cuánto queda de cada dólar vendido para cubrir gastos y utilidad.",
    "nota de credito": "Una nota de crédito anula o reduce una factura (devolución, descuento). Por eso resta en la venta.",
    "libro mayor": "El libro mayor es el registro contable oficial. Rayan lo usa como fuente de la venta oficial; el detalle comercial solo se usa para documentos que están en el mayor.",
    "ticket": "El ticket promedio es la venta dividida entre el número de documentos (facturas).",
    "conciliacion": "Conciliar es comparar, documento por documento, la venta oficial del mayor con el detalle comercial para encontrar diferencias.",
}


def responder(texto: str) -> str | None:
    for clave, definicion in GLOSARIO.items():
        if clave in texto:
            return definicion
    return None
