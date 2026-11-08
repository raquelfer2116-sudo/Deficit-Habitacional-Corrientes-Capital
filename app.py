from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Configuración ----------
CARPETA = Path("datos")
FECHA_DESCARGA = "07/11/2026"
ARCHIVOS = {
    "h1": "c2022_corrientes_hogares_c1_7.xlsx",
    "h2": "c2022_corrientes_hogares_c2_7.xlsx",
    "h3": "c2022_corrientes_hogares_c3_7.xlsx",
    "h5": "c2022_corrientes_hogares_c5_7.xlsx",
    "h6": "c2022_corrientes_hogares_c6_7.xlsx",
    "v2": "c2022_corrientes_vivienda_c2_7.xlsx",
    "v3": "c2022_corrientes_vivienda_c3_7.xlsx",
}
CUADROS = (
    "Hogares 1.7, 2.7, 3.7, 5.7 y 6.7; Viviendas 2.7 y 3.7 "
    "(Provincia de Corrientes, por departamento)"
)
PALETA = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]

st.set_page_config(page_title="Déficit habitacional - Corrientes", layout="wide")


def fmt(n, dec=0):
    """Punto de miles, coma decimal."""
    s = f"{n:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fallar(msg):
    st.error(msg)
    st.stop()


# ---------- Lectura y cálculo (los 25 departamentos) ----------
def norm(x):
    """Texto en minúsculas y sin espacios raros (el INDEC usa espacios no separables)."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return " ".join(str(x).replace("\xa0", " ").split()).lower()


def num(x):
    """Número entero. Las celdas vacías o con '-' o '///' se toman como 0."""
    try:
        if x is None or pd.isna(x):
            return 0
        return int(x)
    except (TypeError, ValueError):
        return 0


@st.cache_data
def leer_deptos(ruta):
    """Cuadros con una solapa por departamento: devuelve {departamento: tabla}."""
    xls = pd.ExcelFile(ruta)
    out = {}
    for nombre in xls.sheet_names:
        if re.fullmatch(r"cuadro \d\.7\.\d+", norm(nombre)):
            df = xls.parse(nombre, header=None)
            m = re.search(r"departamento (.+?)\. total", norm(df.iloc[1, 0]))
            if m:
                out[m.group(1)] = df
    if not out:
        raise ValueError(f"No se encontraron solapas por departamento en {Path(ruta).name}")
    return out


@st.cache_data
def leer_unica(ruta):
    """Cuadros con una sola hoja (un departamento por fila)."""
    xls = pd.ExcelFile(ruta)
    for nombre in xls.sheet_names:
        if norm(nombre).startswith("cuadro"):
            return xls.parse(nombre, header=None)
    raise ValueError(f"No se encontró la hoja del cuadro en {Path(ruta).name}")


def fila(df, etiqueta, col_etiqueta=0):
    for i in range(len(df)):
        if norm(df.iloc[i, col_etiqueta]) == norm(etiqueta):
            return i
    raise ValueError(f"No se encontró la fila '{etiqueta}'")


def columnas(df, titulo, hasta_fila=7):
    out = []
    for j in range(df.shape[1]):
        for i in range(hasta_fila):
            if norm(df.iloc[i, j]).startswith(norm(titulo)):
                out.append(j)
                break
    if not out:
        raise ValueError(f"No se encontró la columna '{titulo}'")
    return out


@st.cache_data
def calcular(pares):
    """Indicadores de los 25 departamentos. Devuelve una tabla con una fila por departamento."""
    ruta = dict(pares)
    h1 = leer_deptos(ruta["h1"])
    h2 = leer_deptos(ruta["h2"])
    h3 = leer_deptos(ruta["h3"])
    h5 = leer_deptos(ruta["h5"])
    h6 = leer_unica(ruta["h6"])
    v2 = leer_unica(ruta["v2"])
    v3 = leer_unica(ruta["v3"])
    ini_v3 = columnas(v3, "Total de hogares")[0]
    c_tot_h6 = columnas(h6, "Total de hogares")[0]
    c_sindoc = columnas(h6, "No tiene documentación")[0]
    c_prest = columnas(h6, "Prestada")[0]
    c_otra = columnas(h6, "Otra situación")[0]
    c_tipo = {t: [j for j in columnas(v3, t) if j > ini_v3][0]
              for t in ("Rancho", "Casilla", "Local no construido para habitación", "Vivienda móvil")}

    nombres = {norm(x): str(x).strip() for x in h6.iloc[:, 1] if norm(x)}

    filas = []
    for dep in h2:  # el orden de las solapas es el de los departamentos
        # Hogares 1.7 · pisos
        d = h1[dep]
        r = fila(d, "Total")
        total_h1 = num(d.iloc[r, columnas(d, "Total de hogares")[0]])
        piso = num(d.iloc[r, columnas(d, "Tierra o ladrillo suelto")[0]])
        # Hogares 2.7 · agua
        d = h2[dep]
        r = fila(d, "Total")
        total_h2 = num(d.iloc[r, columnas(d, "Total de hogares")[0]])
        agua_can = num(d.iloc[r, columnas(d, "Por cañería dentro de la vivienda")[0]])
        agua = total_h2 - agua_can
        # Hogares 3.7 · saneamiento
        d = h3[dep]
        c = columnas(d, "Total de hogares")[0]
        total_h3 = num(d.iloc[fila(d, "Total"), c])
        pozo = num(d.iloc[fila(d, "Solo a pozo ciego"), c])
        hoyo = num(d.iloc[fila(d, "A hoyo, excavación en la tierra, etc."), c])
        sin_bano = num(d.iloc[fila(d, "No tiene"), c])
        sanea = pozo + hoyo + sin_bano
        # Hogares 5.7 · una sola habitación
        d = h5[dep]
        c = columnas(d, "Total de hogares")[0]
        total_h5 = num(d.iloc[fila(d, "Total"), c])
        una_hab = num(d.iloc[fila(d, "1"), c])
        # Hogares 6.7 · tenencia
        r = fila(h6, dep, col_etiqueta=1)
        total_h6 = num(h6.iloc[r, c_tot_h6])
        sin_doc = num(h6.iloc[r, c_sindoc])
        prestada = num(h6.iloc[r, c_prest])
        otra_sit = num(h6.iloc[r, c_otra])
        tenencia = sin_doc + prestada + otra_sit
        # Viviendas 2.7 · allegamiento
        r = fila(v2, dep, col_etiqueta=1)
        viviendas = num(v2.iloc[r, 2])
        hogares_v2 = num(v2.iloc[r, 3])
        alleg = hogares_v2 - viviendas
        # Viviendas 3.7 · irrecuperables
        r = fila(v3, dep, col_etiqueta=1)
        rancho, casilla, local, movil = (num(v3.iloc[r, c_tipo[t]]) for t in
                                         ("Rancho", "Casilla", "Local no construido para habitación", "Vivienda móvil"))
        irrec = rancho + casilla + local + movil

        totales = {total_h1, total_h2, total_h3, total_h5, total_h6, hogares_v2}
        if len(totales) != 1:
            raise ValueError(f"{dep}: el total de hogares no coincide entre cuadros: {sorted(totales)}")
        filas.append(dict(
            Departamento=nombres.get(dep, dep.title()), Hogares=total_h2, Irrecuperables=irrec, Allegados=alleg,
            Piso=piso, Agua=agua, Agua_canieria=agua_can, Saneamiento=sanea,
            Pozo=pozo, Hoyo=hoyo, Sin_bano=sin_bano,
            Tenencia=tenencia, Sin_doc=sin_doc, Prestada=prestada, Otra_sit=otra_sit,
            Una_hab=una_hab, Viviendas=viviendas,
            Rancho=rancho, Casilla=casilla, Local=local, Movil=movil,
        ))
    t = pd.DataFrame(filas)
    t["DQ"] = t["Irrecuperables"] + t["Allegados"]
    t["DQ_pct"] = t["DQ"] / t["Hogares"] * 100
    t["DC_min"] = t[["Piso", "Agua", "Saneamiento"]].max(axis=1)
    t["DC_max"] = t["Piso"] + t["Agua"] + t["Saneamiento"]
    t["DHT_min"] = t["DQ"] + t["DC_min"]
    t["DHT_max"] = t["DQ"] + t["DC_max"]
    t["DHT_pct_min"] = t["DHT_min"] / t["Hogares"] * 100
    # La suma de carencias se superpone: puede superar el total de hogares. Se topea en 100%.
    t["DHT_pct_max_bruto"] = t["DHT_max"] / t["Hogares"] * 100
    t["DHT_pct_max"] = t["DHT_pct_max_bruto"].clip(upper=100)
    t["Supera_100"] = t["DHT_pct_max_bruto"] > 100
    return t


# ---------- Carga ----------
def buscar(nombre):
    """Acepta el nombre exacto o con '.xlsx' repetido (pasa al renombrar en Windows)."""
    for candidato in (CARPETA / nombre, CARPETA / (nombre + ".xlsx")):
        if candidato.exists():
            return candidato
    return None


faltan = [n for n in ARCHIVOS.values() if buscar(n) is None]
if faltan:
    fallar(
        "Faltan archivos en la carpeta datos/: " + ", ".join(faltan)
        + ". Descárguenlos de censo.gob.ar y súbanlos al repositorio."
    )

ruta = tuple((k, buscar(v)) for k, v in ARCHIVOS.items())
try:
    tabla = calcular(ruta)
except Exception as e:
    fallar(f"No se pudo leer un cuadro del INDEC: {e}")

# ---------- Selector de departamento ----------
nombres = list(tabla["Departamento"])
st.sidebar.title("Departamento")
elegido = st.sidebar.selectbox("Elegir departamento", nombres, index=nombres.index("Capital"))
f = tabla[tabla["Departamento"] == elegido].iloc[0]

total = int(f["Hogares"])
irrec, alleg = int(f["Irrecuperables"]), int(f["Allegados"])
piso, agua, sanea = int(f["Piso"]), int(f["Agua"]), int(f["Saneamiento"])
tenencia, una_hab = int(f["Tenencia"]), int(f["Una_hab"])
dq, dq_pct = int(f["DQ"]), f["DQ_pct"]
dc_min, dc_max = int(f["DC_min"]), int(f["DC_max"])
dht_min = int(f["DHT_min"])
dht_max = min(int(f["DHT_max"]), total)  # no puede superar el total de hogares
dht_pct_min, dht_pct_max = f["DHT_pct_min"], f["DHT_pct_max"]
supera = bool(f["Supera_100"])

# ---------- Encabezado ----------
st.title("Déficit habitacional en Corrientes")
st.subheader(f"Departamento {elegido} · Censo 2022 (INDEC)")
st.caption(f"Fuente: Censo 2022 (INDEC) · Cuadros: {CUADROS} · Descargados el {FECHA_DESCARGA}")

st.divider()

# ---------- Tarjetas ----------
a, b = st.columns(2)
a.metric("Hogares totales", fmt(total))
b.metric("Déficit cuantitativo", fmt(dq))
b.caption(f"{fmt(dq_pct, 2)}% de los hogares")

st.markdown("**Déficit cualitativo (rango)**")
c1, c2 = st.columns(2)
c1.metric("Mínimo", fmt(dc_min))
c2.metric("Máximo", fmt(dc_max))

st.markdown("**Déficit habitacional total (rango)**")
d1, d2 = st.columns(2)
d1.metric("Mínimo", f"{fmt(dht_pct_min, 1)}%")
d1.caption(f"{fmt(dht_min)} hogares")
d2.metric("Máximo", f"{fmt(dht_pct_max, 1)}%")
d2.caption(f"{fmt(dht_max)} hogares")
punto_medio = (dht_pct_min + dht_pct_max) / 2
veces = round(100 / punto_medio)
if dht_pct_min >= 50:
    st.caption("Equivale a más de la mitad de los hogares.")
elif veces < 2:
    st.caption("Equivale a la mitad o más de los hogares.")
else:
    st.caption(f"Equivale a aproximadamente 1 de cada {veces} hogares.")
if supera:
    st.caption(
        "El máximo se limita al 100%: la suma de carencias supera el total de hogares "
        "porque una misma vivienda puede tener varias. Para este departamento conviene "
        "leer el mínimo como cifra de referencia."
    )

st.divider()


# ---------- Gráficos ----------
def barras(datos, x, y, horizontal=False, paleta=PALETA):
    datos = datos.copy()
    datos["Etiqueta"] = datos["Hogares"].apply(fmt)
    categoria = y if horizontal else x
    fig = px.bar(
        datos, x=x, y=y, text="Etiqueta",
        orientation="h" if horizontal else "v",
        color=categoria,
        color_discrete_sequence=paleta,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=380, showlegend=False, separators=",.")
    return fig


g1, g2 = st.columns(2)

with g1:
    st.subheader("Composición del déficit cuantitativo")
    d_dq = pd.DataFrame({"Componente": ["Irrecuperables", "Allegados"], "Hogares": [irrec, alleg]})
    st.plotly_chart(barras(d_dq, "Componente", "Hogares"), use_container_width=True)

with g2:
    st.subheader("Carencias que componen el déficit cualitativo")
    d_dc = pd.DataFrame({
        "Dimensión": ["Saneamiento inadecuado", "Agua inadecuada", "Piso precario"],
        "Hogares": [sanea, agua, piso],
    }).sort_values("Hogares")
    st.plotly_chart(barras(d_dc, "Hogares", "Dimensión", horizontal=True), use_container_width=True)

st.subheader("Dimensiones complementarias (no suman al déficit)")
d_comp = pd.DataFrame({
    "Dimensión": ["Tenencia insegura", "Hogares de una sola habitación"],
    "Hogares": [tenencia, una_hab],
}).sort_values("Hogares")
st.plotly_chart(
    barras(d_comp, "Hogares", "Dimensión", horizontal=True, paleta=["#9467BD", "#17BECF"]),
    use_container_width=True,
)

st.divider()

# ---------- Comparación entre los 25 departamentos ----------
st.header("Comparación entre los 25 departamentos")
st.caption(
    "Déficit habitacional total como porcentaje de los hogares de cada departamento. "
    "Ordenado de menor a mayor déficit mínimo."
)
orden = tabla.sort_values("DHT_pct_min")
largo = pd.concat([
    pd.DataFrame({"Departamento": orden["Departamento"], "Valor": orden["DHT_pct_min"], "Cota": "Mínimo"}),
    pd.DataFrame({"Departamento": orden["Departamento"], "Valor": orden["DHT_pct_max"], "Cota": "Máximo (tope 100%)"}),
])
largo["Etiqueta"] = largo["Valor"].apply(lambda v: fmt(v, 1) + "%")
fig_comp = px.bar(
    largo, x="Valor", y="Departamento", color="Cota", orientation="h", barmode="group",
    text="Etiqueta", color_discrete_map={"Mínimo": "#1F77B4", "Máximo (tope 100%)": "#FF7F0E"},
)
fig_comp.update_traces(textposition="outside")
fig_comp.update_yaxes(categoryorder="array", categoryarray=list(orden["Departamento"]))
fig_comp.update_layout(
    height=900, separators=",.", xaxis_title="% de los hogares", yaxis_title="",
    xaxis_range=[0, 115], legend_title_text="",
)
st.plotly_chart(fig_comp, use_container_width=True)

tabla_vista = orden[["Departamento", "Hogares", "DQ", "DC_min", "DC_max", "DHT_pct_min", "DHT_pct_max"]].copy()
tabla_vista["Hogares"] = tabla_vista["Hogares"].apply(fmt)
tabla_vista["DQ"] = tabla_vista["DQ"].apply(fmt)
tabla_vista["DC_min"] = tabla_vista["DC_min"].apply(fmt)
tabla_vista["DC_max"] = tabla_vista["DC_max"].apply(fmt)
tabla_vista["DHT_pct_min"] = tabla_vista["DHT_pct_min"].apply(lambda v: fmt(v, 1) + "%")
tabla_vista["DHT_pct_max"] = [
    fmt(v, 1) + "%" + ("*" if s else "")
    for v, s in zip(orden["DHT_pct_max"], orden["Supera_100"])
]
tabla_vista.columns = [
    "Departamento", "Hogares", "Déf. cuantitativo (hogares)",
    "Déf. cualitativo mínimo", "Déf. cualitativo máximo",
    "Déf. total mínimo", "Déf. total máximo",
]
st.dataframe(tabla_vista, use_container_width=True, hide_index=True)
if bool(orden["Supera_100"].any()):
    st.caption(
        "* La suma de carencias supera el total de hogares (una misma vivienda puede tener varias "
        "carencias), por eso el máximo se limita al 100%. En esos departamentos la cifra de referencia es el mínimo."
    )

st.divider()

# ---------- Nota metodológica ----------
st.subheader("Nota metodológica")
st.markdown(f"""
Los valores que se detallan abajo corresponden al departamento seleccionado ({elegido}). Los mismos cálculos se aplican a los 25 departamentos.

- **Déficit cuantitativo** = viviendas irrecuperables + hogares allegados ({fmt(irrec)} + {fmt(alleg)} = {fmt(dq)}).
- **Déficit cualitativo** = rango. El mínimo es la carencia más extendida entre piso, agua y saneamiento ({fmt(dc_min)}). El máximo es la suma de las tres ({fmt(dc_max)}). Es un rango porque una misma vivienda puede tener más de una carencia y los cuadros no indican cuántas se superponen.
- **Déficit total** = cuantitativo + cualitativo, expresado como rango: {fmt(dht_pct_min, 1)}% a {fmt(dht_pct_max, 1)}% de los hogares. Si la suma supera el 100% de los hogares, el máximo se limita al 100%.
- **Tenencia insegura y hogares de una sola habitación** se muestran aparte como dimensiones complementarias. No se incluyen en el déficit.
- **Total de hogares:** {fmt(total)} (Cuadro 2.7 de hogares, solapa del departamento, fila "Total"). El mismo total figura en todos los cuadros usados, y el tablero verifica que coincidan en cada departamento.
- **Agua inadecuada:** hogares sin agua por cañería dentro de la vivienda = total de hogares − "Por cañería dentro de la vivienda" = {fmt(total)} − {fmt(int(f["Agua_canieria"]))} = {fmt(agua)} (Cuadro 2.7 de hogares, fila "Total").
- **Saneamiento inadecuado:** hogares cuyo baño desagua solo a pozo ciego, a hoyo o excavación, o que no tienen baño: {fmt(int(f["Pozo"]))} + {fmt(int(f["Hoyo"]))} + {fmt(int(f["Sin_bano"]))} = {fmt(sanea)} (Cuadro 3.7 de hogares, filas "Solo a pozo ciego", "A hoyo, excavación en la tierra, etc." y "No tiene"). Se considera adecuado el desagüe a red pública y a cámara séptica.
- **Piso precario:** hogares con piso de tierra o ladrillo suelto = {fmt(piso)} (Cuadro 1.7 de hogares, fila "Total", columna "Tierra o ladrillo suelto").
- **Allegamiento:** hogares que comparten la vivienda con otro hogar = hogares − viviendas particulares ocupadas = {fmt(total)} − {fmt(int(f["Viviendas"]))} = {fmt(alleg)} (Cuadro 2.7 de viviendas, hoja única, fila del departamento, columnas "Total").
- **Viviendas irrecuperables:** hogares que viven en rancho, casilla, local no construido para habitación o vivienda móvil: {fmt(int(f["Rancho"]))} + {fmt(int(f["Casilla"]))} + {fmt(int(f["Local"]))} + {fmt(int(f["Movil"]))} = {fmt(irrec)} (Cuadro 3.7 de viviendas, hoja única, fila del departamento, bloque "Total de hogares"). No se cuentan las casas, los departamentos ni las piezas en inquilinato, hotel familiar o pensión.
- **Tenencia insegura:** hogares con vivienda propia sin documentación, prestada u otra situación: {fmt(int(f["Sin_doc"]))} + {fmt(int(f["Prestada"]))} + {fmt(int(f["Otra_sit"]))} = {fmt(tenencia)} (Cuadro 6.7 de hogares, hoja única, fila del departamento). No se cuentan como inseguras la propiedad con escritura, boleto u otra documentación, la vivienda alquilada ni la cedida por trabajo.
- **Hogares de una sola habitación:** {fmt(una_hab)} hogares con una habitación (Cuadro 5.7 de hogares, solapa del departamento, fila "1" de habitaciones). Es una aproximación: el cuadro no informa cuántas personas viven en cada hogar, por lo que no mide hacinamiento (personas por cuarto).
- Fuente: Censo 2022 (INDEC), resultados definitivos. Descarga: {FECHA_DESCARGA}.
""")

with st.expander("Ver valores calculados"):
    vista = pd.DataFrame({
        "Indicador": [
            "Total de hogares", "Viviendas irrecuperables", "Hogares allegados",
            "Piso precario", "Agua inadecuada", "Saneamiento inadecuado",
            "Tenencia insegura", "Hogares de una sola habitación",
        ],
        "Hogares": [total, irrec, alleg, piso, agua, sanea, tenencia, una_hab],
    })
    vista["Hogares"] = vista["Hogares"].apply(fmt)
    st.dataframe(vista, use_container_width=True, hide_index=True)
