"""Orquestador: acceso → interpretación (reglas, y LLM solo si las reglas no entienden) → consulta predefinida."""
from __future__ import annotations

from .access import validar
from .data import Fuentes, fuentes
from .glossary import responder as glosario
from .llm import LLM
from .nlu import Catalogo, Consulta, interpretar
from . import queries as q

AYUDA = ("Puedo responder, por ejemplo:\n• venta 2025\n• venta de Minera Cóndor de Plata en marzo 2026\n"
         "• top 5 clientes 2025\n• top marcas este año\n• qué compró Pesquera Delfín Azul en 2025\n"
         "• margen de la línea Bombas 2025\n• compara 2025 vs 2024\n• resumen\n• concilia el mayor con el detalle de 2025")
NECESITA_ENTIDAD = {"venta_entidad", "que_compro"}


class Rayan:
    def __init__(self, f: Fuentes | None = None, llm: LLM | None = None, exigir_usuario: bool = True):
        self.f = f or fuentes()
        self.llm = llm or LLM()
        self.exigir_usuario = exigir_usuario
        self.catalogo = Catalogo({
            "cliente": self.f.mayor.cliente.unique().tolist(),
            "vendedor": self.f.mayor.vendedor.unique().tolist(),
            "linea": self.f.mayor.linea.unique().tolist(),
            "marca": [m for m in self.f.detalle_valido.marca.unique().tolist() if m != "Servicio propio"],
        })
        ultimo = self.f.mayor.fecha.max()
        self.anio_max, self.mes_max = int(ultimo.year), int(ultimo.month)

    def entender(self, texto: str) -> Consulta:
        c = interpretar(texto, self.catalogo, self.anio_max, self.mes_max)
        if c.intent == "desconocido" and self.llm.disponible:
            c = self.llm.interpretar(texto, self.catalogo) or c
        return c

    def responder(self, texto: str, usuario: str | None = None) -> q.Respuesta:
        if self.exigir_usuario:
            acceso = validar(usuario, self.f.usuarios)
            if not acceso["autorizado"]:
                return q.Respuesta(f"No tienes acceso a Rayan ({acceso['motivo']}). Pide tu alta al administrador.",
                                   {"autorizado": False})
        c = self.entender(texto)
        r = self._ejecutar(c, texto)
        r.datos["consulta"] = c.dict()
        return r

    def _ejecutar(self, c: Consulta, texto: str) -> q.Respuesta:
        fijas = {"saludo": "¡Hola! Soy Rayan 🐱. Pregúntame por ventas, clientes, márgenes o rankings.",
                 "agradecimiento": "¡Con gusto! ¿Algo más?", "despedida": "¡Hasta luego!",
                 "identidad": "Soy Rayan, un asistente comercial. Las cifras salen de consultas fijas sobre los datos; "
                              "la IA solo me ayuda a entender la pregunta.",
                 "ayuda": AYUDA}
        if c.intent in fijas:
            return q.Respuesta(fijas[c.intent])
        if c.intent == "conceptual":
            local = glosario(c.texto_entidad or texto)
            if local:
                return q.Respuesta(local)
            if self.llm.disponible:
                return q.Respuesta(self.llm.explicar(texto) or "No pude responder eso ahora.", {"origen": "llm"})
            return q.Respuesta("Aún no tengo esa definición. " + AYUDA)
        if c.intent in NECESITA_ENTIDAD and not c.entidad:
            if c.sugerencias:
                return q.Respuesta("¿A cuál te refieres?\n" + "\n".join(f"• {s}" for s in c.sugerencias), {"aclaracion": True})
            return q.Respuesta("No encontré ese cliente, vendedor, línea o marca. Revisa el nombre o escribe 'ayuda'.",
                               {"aclaracion": True})
        if c.intent == "venta_total":
            return q.venta_total(self.f, c)
        if c.intent == "venta_entidad":
            return q.venta_entidad(self.f, c)
        if c.intent == "top":
            return q.top(self.f, c)
        if c.intent == "que_compro":
            return q.que_compro(self.f, c)
        if c.intent == "margen":
            return q.margen(self.f, c)
        if c.intent == "comparar":
            return q.comparar(self.f, c, self.anio_max)
        if c.intent == "resumen":
            return q.resumen(self.f, c, self.anio_max)
        if c.intent == "conciliacion":
            return q.conciliacion(self.f, c)
        return q.Respuesta("No entendí la pregunta. " + AYUDA, {"no_entendida": True})
