"""Entender la pregunta: intención + entidades + período, con reglas transparentes.

La salida es siempre una `Consulta` estructurada. Las cifras NUNCA salen de aquí: la consulta se ejecuta
después con funciones predefinidas sobre los datos (queries.py).
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field

INTENTS = ("saludo", "agradecimiento", "despedida", "ayuda", "identidad", "venta_total", "venta_entidad", "top",
           "que_compro", "margen", "resumen", "conciliacion", "comparar", "conceptual", "desconocido")
DIMENSIONES = ("clientes", "vendedores", "lineas", "marcas", "productos")
TIPOS = ("cliente", "vendedor", "linea", "marca")

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
         "ene": 1, "feb": 2, "mar": 3, "abr": 4, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10,
         "nov": 11, "dic": 12}
NUMEROS = {"tres": 3, "cinco": 5, "diez": 10, "quince": 15, "veinte": 20}
TYPOS = {"ventaz": "ventas", "bentas": "ventas", "venat": "venta", "cuanot": "cuanto", "clietnes": "clientes",
         "vendedorres": "vendedores", "marjen": "margen", "margn": "margen", "top10": "top 10", "top5": "top 5"}
STOP = set("""a al algo alguna como con cual cuales cuanto cuanta cuantos cuantas de del dame dime durante el
en es esta este fue fueron hemos hay la las le les lo los me mes mi muestrame muestra nos para por que quiero
quisiera saber se sobre su sus tal total un una y ya ano anos vs versus frente cada""".split())
INTENT_WORDS = set("""venta ventas vendimos vendio vendido vendieron vende facturamos facturado factura compro
compraron compra compras margen margenes rentabilidad ganancia top ranking principales mejores clientes cliente
vendedor vendedores linea lineas marca marcas producto productos articulo articulos resumen compara compara
comparar comparacion crecimiento crecio analiza detalle cuanto quien quienes mas pasado actual""".split())
GENERIC_NAME = {"sac", "sa", "s", "a", "de", "del", "la", "los", "las", "y", "e", "compania", "servicios",
                "operaciones", "ingenieria", "obras", "talla"}


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[¿?¡!,;:()\"']", " ", t)
    t = " ".join(TYPOS.get(w, w) for w in t.split())
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Consulta:
    intent: str
    entidad: str | None = None
    tipo_entidad: str | None = None
    dimension: str | None = None
    anio: int | None = None
    mes: int | None = None
    anio_comparacion: int | None = None
    limite: int = 10
    texto_entidad: str | None = None
    sugerencias: list[str] = field(default_factory=list)
    origen: str = "reglas"

    def dict(self) -> dict:
        return asdict(self)


class Catalogo:
    """Nombres válidos por tipo de entidad, para resolver lo que escribe el usuario (con errores incluidos)."""

    def __init__(self, nombres: dict[str, list[str]]):
        self.nombres = {t: sorted(set(map(str, v))) for t, v in nombres.items()}
        freq = Counter(tok for vals in self.nombres.values() for n in vals for tok in set(normalizar(n).split()))
        self.genericos = {tok for tok, c in freq.items() if c >= 3} | GENERIC_NAME

    def _tokens(self, nombre: str) -> list[str]:
        return [t for t in normalizar(nombre).split() if t not in self.genericos and len(t) > 1]

    @staticmethod
    def _match(tok: str, palabras: list[str]) -> bool:
        if tok in palabras:
            return True
        if len(tok) < 4:
            return False
        return any(difflib.SequenceMatcher(None, tok, p).ratio() >= 0.84 for p in palabras if len(p) >= 4)

    def resolver(self, texto: str, preferir: str | None = None) -> tuple[str | None, str | None, list[str]]:
        palabras = [w for w in normalizar(texto).split() if w not in STOP]
        scored = []
        for tipo, nombres in self.nombres.items():
            for nombre in nombres:
                toks = self._tokens(nombre) or normalizar(nombre).split()
                hits = sum(self._match(t, palabras) for t in toks)
                if hits:
                    score = hits / len(toks) + (0.15 if tipo == preferir else 0.0)
                    scored.append((score, hits, tipo, nombre))
        if not scored:
            return None, None, []
        scored.sort(key=lambda x: (-x[0], -x[1], x[3]))
        best = scored[0]
        if best[0] < 0.5:
            return None, None, [s[3] for s in scored[:3]]
        empatados = [s for s in scored if abs(s[0] - best[0]) < 1e-9 and s[1] == best[1]]
        if len(empatados) > 1:                                      # ambiguo: pedir aclaración
            return None, None, [s[3] for s in empatados[:4]]
        return best[3], best[2], []


def _periodo(t: str, anio_max: int, mes_max: int) -> tuple[int | None, int | None, int | None]:
    anios = [int(a) for a in re.findall(r"\b(20\d{2})\b", t)]
    if "este ano" in t or "ano actual" in t:
        anios.append(anio_max)
    if "ano pasado" in t:
        anios.append(anio_max - 1)
    mes = None
    m = re.search(r"\b(0?[1-9]|1[0-2])\s*[/-]\s*(20\d{2})\b", t)
    if m:
        mes = int(m.group(1))
    else:
        for nombre, num in MESES.items():
            if re.search(rf"\b{nombre}\b", t):
                mes = num
                break
    if "mes pasado" in t:
        mes, anios = (mes_max - 1 or 12), anios or [anio_max if mes_max > 1 else anio_max - 1]
    if "este mes" in t:
        mes, anios = mes_max, anios or [anio_max]
    anio = anios[0] if anios else None
    comp = anios[1] if len(anios) > 1 else None
    return anio, mes, comp


def _limite(t: str) -> int:
    m = re.search(r"\b(?:top|primeros|primeras|mejores|principales)\s+(\d{1,2})\b", t) or \
        re.search(r"\b(\d{1,2})\s+(?:mejores|principales|primeros|clientes|vendedores|productos|marcas)\b", t)
    if m:
        return max(1, min(50, int(m.group(1))))
    for w, n in NUMEROS.items():
        if re.search(rf"\b(?:top|los|las)\s+{w}\b", t):
            return n
    return 10


def _dimension(t: str) -> str | None:
    for pat, dim in ((r"\bclientes?\b", "clientes"), (r"\bvendedor(es)?\b", "vendedores"), (r"\blineas?\b", "lineas"),
                     (r"\bmarcas?\b", "marcas"), (r"\b(productos?|articulos?|items?|repuestos?)\b", "productos")):
        if re.search(pat, t):
            return dim
    return None


def _tiene(t: str, *pats: str) -> bool:
    return any(re.search(p, t) for p in pats)


def interpretar(texto: str, catalogo: Catalogo, anio_max: int, mes_max: int) -> Consulta:
    t = normalizar(texto)
    anio, mes, comp = _periodo(t, anio_max, mes_max)
    base = dict(anio=anio, mes=mes, anio_comparacion=comp, limite=_limite(t))
    palabras = t.split()

    if not t:
        return Consulta("ayuda")
    if len(palabras) <= 4 and _tiene(t, r"^(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|que tal)\b"):
        return Consulta("saludo")
    if _tiene(t, r"^(gracias|muchas gracias|genial gracias|ok gracias)"):
        return Consulta("agradecimiento")
    if _tiene(t, r"^(chau|adios|hasta luego|nos vemos)"):
        return Consulta("despedida")
    if _tiene(t, r"^(ayuda|/help|/start|menu|opciones)$", r"que puedes hacer", r"como te uso", r"que te puedo preguntar"):
        return Consulta("ayuda")
    if _tiene(t, r"quien eres", r"como te llamas", r"que eres"):
        return Consulta("identidad")
    if _tiene(t, r"^(que es|que significa|como se calcula|explica(me)?|para que sirve)\b") and \
            not _tiene(t, r"\b20\d{2}\b"):
        return Consulta("conceptual", texto_entidad=t)
    if _tiene(t, r"concilia", r"cuadra", r"comercial vs financiero", r"diferencias? (entre )?(el )?mayor",
              r"diagnostico"):
        return Consulta("conciliacion", **base)
    if _tiene(t, r"\bresumen\b", r"como vamos", r"dashboard", r"estado general"):
        return Consulta("resumen", **base)

    dim = _dimension(t)
    preferir = {"clientes": "cliente", "vendedores": "vendedor", "lineas": "linea", "marcas": "marca"}.get(dim or "")
    entidad, tipo, sugerencias = catalogo.resolver(t, preferir)

    if _tiene(t, r"\bcompar", r"\bvs\b", r"versus", r"crecimiento", r"\bcrecio\b", r"crecimos", r"variacion"):
        return Consulta("comparar", entidad=entidad, tipo_entidad=tipo, sugerencias=sugerencias, **base)
    if entidad and tipo == "cliente" and dim == "productos" and _tiene(t, r"\btop\b", r"principales", r"mas compr", r"ranking"):
        return Consulta("que_compro", entidad=entidad, tipo_entidad=tipo, **base)
    if _tiene(t, r"\btop\b", r"ranking", r"\bprincipales\b", r"\bmejores\b", r"mas vendid", r"quienes? (nos )?compra",
              r"compran mas", r"vende(n)? mas", r"vendio mas") and not entidad:
        return Consulta("top", dimension=dim or "clientes", **base)
    if _tiene(t, r"que (nos )?compr", r"que le vendimos", r"que productos", r"que articulos", r"detalle de compra",
              r"que se llevo"):
        return Consulta("que_compro", entidad=entidad, tipo_entidad=tipo, sugerencias=sugerencias,
                        texto_entidad=None if entidad else t, **base)
    if _tiene(t, r"\bmargen", r"rentab", r"ganancia", r"utilidad"):
        return Consulta("margen", entidad=entidad, tipo_entidad=tipo, sugerencias=sugerencias, **base)
    es_venta = _tiene(t, r"\bvent", r"\bvend", r"factur", r"\bcompr", r"\bcuanto\b", r"ingres")
    if entidad:
        return Consulta("venta_entidad", entidad=entidad, tipo_entidad=tipo, **base)
    if es_venta and sugerencias and any(w not in STOP | INTENT_WORDS and not w.isdigit() and w not in MESES for w in palabras):
        return Consulta("venta_entidad", sugerencias=sugerencias, texto_entidad=t, **base)
    if es_venta:
        return Consulta("venta_total", **base)
    return Consulta("desconocido", sugerencias=sugerencias, texto_entidad=t, **base)
