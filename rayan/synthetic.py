"""Genera datos SINTÉTICOS de una distribuidora B2B: libro mayor (venta oficial), detalle comercial por
artículo y usuarios autorizados. Clientes, vendedores y marcas son inventados."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CLIENTES = {
    "MINERIA": ["Minera Cóndor de Plata", "Compañía Minera Vicuña Dorada", "Minera Quebrada Azul",
                "Operaciones Mineras Puna Alta", "Minera Cerro Turquesa", "Servicios Mineros Huaylas"],
    "PESCA": ["Pesquera Delfín Azul", "Pesquera Bahía Serena", "Armadores Punta Brava", "Conservera Lobo Marino",
              "Pesquera Corvina Real"],
    "INDUSTRIA": ["Metalmecánica Los Olivos", "Plásticos Ribera", "Alimentos Valle Verde", "Textil Algodonera Sur",
                  "Papelera del Rímac", "Envases Pacífico Norte"],
    "CONSTRUCCION": ["Constructora Horizonte Andino", "Concretos Tres Ríos", "Ingeniería y Obras Kallpa"],
}
VENDEDORES = ["Ana Torres", "Bruno Salazar", "Carla Mendoza", "Diego Huamán", "Elena Rojas", "Felipe Castro"]
LINEAS = {
    "Bombas": ("Hidrotek", ["Bomba centrífuga", "Bomba de engranajes", "Kit de reparación de bomba"], 900),
    "Rodamientos": ("RotoPlus", ["Rodamiento de rodillos", "Rodamiento de bolas", "Chumacera"], 120),
    "Valvulas": ("FlowMax", ["Válvula de bola", "Válvula de alivio", "Válvula direccional"], 350),
    "Sellos": ("Sellomar", ["Kit de sellos", "Sello mecánico", "O-ring industrial"], 60),
    "Filtros": ("Filtrex", ["Filtro hidráulico", "Elemento filtrante", "Filtro de aire"], 45),
    "Transmision": ("Andes Power", ["Reductor de velocidad", "Acoplamiento", "Faja de transmisión"], 600),
    "Refrigeracion": ("MarineCool", ["Compresor de frío", "Evaporador", "Kit de refrigerante"], 700),
    "Servicios tecnicos": ("Servicio propio", ["Mantenimiento preventivo", "Reparación en taller", "Diagnóstico en campo"], 1200),
}


def make_data(seed: int = 11) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    clientes = pd.DataFrame([(f"CLI-{i:03d}", n, s) for i, (s, n) in
                             enumerate([(s, n) for s, ns in CLIENTES.items() for n in ns], start=1)],
                            columns=["cliente_id", "cliente", "sector"])
    productos = []
    for linea, (marca, items, precio) in LINEAS.items():
        for item in items:
            for size, factor in (("Serie 100", .6), ("Serie 200", 1.0), ("Serie 300", 1.7)):
                nivel = {"Serie 100": "básico", "Serie 200": "estándar", "Serie 300": "integral"}[size]
                desc = f"{item} ({nivel})" if linea == "Servicios tecnicos" else f"{item} {marca} {size}"
                productos.append((f"ART-{len(productos) + 1:04d}", desc, marca, linea,
                                  round(precio * factor * rng.uniform(.8, 1.2), 2)))
    productos = pd.DataFrame(productos, columns=["articulo", "descripcion", "marca", "linea", "precio"])
    cartera = {c: rng.choice(VENDEDORES) for c in clientes.cliente_id}           # cada cliente tiene un vendedor
    size = {c: rng.lognormal(0, 0.9) for c in clientes.cliente_id}
    afinidad = {r.cliente_id: rng.dirichlet(np.ones(len(LINEAS)) * 0.6) for r in clientes.itertuples()}

    mayor, detalle = [], []
    doc = 0
    for fecha in pd.date_range("2024-01-01", "2026-09-30", freq="D"):
        if fecha.weekday() >= 5:
            continue
        for _ in range(rng.poisson(6)):
            doc += 1
            cid = rng.choice(clientes.cliente_id, p=np.array(list(size.values())) / sum(size.values()))
            linea = rng.choice(list(LINEAS), p=afinidad[cid])
            nc = rng.random() < 0.03                                              # notas de crédito
            items = productos[productos.linea == linea].sample(int(rng.integers(1, 4)), random_state=int(rng.integers(1e9)))
            total_doc = 0.0
            for it in items.itertuples():
                qty = int(rng.integers(1, 12))
                total = round(qty * it.precio * rng.uniform(.9, 1.0), 2)
                costo = round(total * rng.uniform(.55, .8), 2)
                sign = -1 if nc else 1
                detalle.append((f"F{doc:07d}", "NC" if nc else "FA", fecha, cid, it.articulo, it.descripcion, it.marca,
                                linea, sign * qty, sign * total, sign * costo, sign * round(total - costo, 2)))
                total_doc += sign * total
            if rng.random() < 0.02:                                               # diferencia mayor vs detalle (p.ej. flete)
                total_doc += round(rng.uniform(50, 400), 2)
            mayor.append((f"F{doc:07d}", fecha, cid, cartera[cid], linea, round(total_doc, 2)))
    mayor = pd.DataFrame(mayor, columns=["documento", "fecha", "cliente_id", "vendedor", "linea", "venta_usd"])
    mayor = mayor.merge(clientes[["cliente_id", "cliente"]], on="cliente_id")
    detalle = pd.DataFrame(detalle, columns=["documento", "tipo_doc", "fecha", "cliente_id", "articulo", "descripcion",
                                             "marca", "linea", "cantidad", "total_usd", "costo_usd", "margen_usd"])
    # 1 % de documentos comerciales que NO llegaron al libro mayor (se deben excluir)
    huerfanos = detalle.documento.drop_duplicates().sample(frac=0.01, random_state=1)
    mayor = mayor[~mayor.documento.isin(huerfanos)]
    usuarios = pd.DataFrame({"usuario": ["demo", "ross_demo", "gerencia_demo"], "nombre": ["Demo", "Ross", "Gerencia"],
                             "activo": [True, True, False]})
    return {"libro_mayor": mayor.sort_values(["fecha", "documento"]).reset_index(drop=True),
            "detalle_ventas": detalle, "clientes": clientes, "usuarios": usuarios}


def write(data_dir: Path, seed: int = 11) -> dict[str, pd.DataFrame]:
    data_dir.mkdir(parents=True, exist_ok=True)
    data = make_data(seed)
    for name, df in data.items():
        df.to_csv(data_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    return data
