from pathlib import Path

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
    "(Provincia de Corrientes, departamento Capital)"
)
PALETA = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]

st.set_page_config(page_title="Déficit habitacional - Corrientes Capital", layout="wide")


# ---------- Utilidades ----------
def fmt(n, dec=0):
    """Punto de miles, coma decimal."""
    s = f"{n:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def norm(x):
    """Texto en minúsculas, sin espacios raros (el INDEC usa espacios no separables)."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return " ".join(str(x).replace("\xa0", " ").split()).lower()


def fallar(msg):
    st.error(msg)
    st.stop()


@st.cache_data
def leer_hoja_capital(ruta):
    """Hoja de Capital en los cuadros con una solapa por departamento (terminan en .3)."""
    xls = pd.ExcelFile(ruta)
    for nombre in xls.sheet_names:
        if norm(nombre).endswith(".3"):
            df = xls.parse(nombre, header=None)
            if "departamento capital" in norm(df.iloc[1, 0]):
                return df
    raise ValueError(f"No se encontró la hoja de Capital en {Path(ruta).name}")


@st.cache_data
def leer_hoja_unica(ruta):
    """Cuadros con una sola hoja (todos los departamentos en filas)."""
    xls = pd.ExcelFile(ruta)
    for nombre in xls.sheet_names:
        if norm(nombre).startswith("cuadro"):
            return xls.parse(nombre, header=None)
    raise ValueError(f"No se encontró la hoja del cuadro en {Path(ruta).name}")


def fila(df, etiqueta, col_etiqueta=0):
    """Índice de la primera fila cuya etiqueta coincide."""
    for i in range(len(df)):
        if norm(df.iloc[i, col_etiqueta]) == norm(etiqueta):
            return i
    raise ValueError(f"No se encontró la fila '{etiqueta}'")


def columnas(df, titulo, hasta_fila=7):
    """Índices de las columnas cuyo encabezado empieza con el título."""
    out = []
    for j in range(df.shape[1]):
        for i in range(hasta_fila):
            if norm(df.iloc[i, j]).startswith(norm(titulo)):
                out.append(j)
                break
    if not out:
        raise ValueError(f"No se encontró la columna '{titulo}'")
    return out


def num(x):
    return int(x)


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

ruta = {k: buscar(v) for k, v in ARCHIVOS.items()}

try:
    # Hogares 1.7 - pisos
    d = leer_hoja_capital(ruta["h1"])
    r = fila(d, "Total")
    total_h1 = num(d.iloc[r, columnas(d, "Total de hogares")[0]])
    piso = num(d.iloc[r, columnas(d, "Tierra o ladrillo suelto")[0]])

    # Hogares 2.7 - agua
    d = leer_hoja_capital(ruta["h2"])
    r = fila(d, "Total")
    total_h2 = num(d.iloc[r, columnas(d, "Total de hogares")[0]])
    agua_canieria = num(d.iloc[r, columnas(d, "Por cañería dentro de la vivienda")[0]])
    agua = total_h2 - agua_canieria

    # Hogares 3.7 - saneamiento
    d = leer_hoja_capital(ruta["h3"])
    c = columnas(d, "Total de hogares")[0]
    total_h3 = num(d.iloc[fila(d, "Total"), c])
    pozo_ciego = num(d.iloc[fila(d, "Solo a pozo ciego"), c])
    hoyo = num(d.iloc[fila(d, "A hoyo, excavación en la tierra, etc."), c])
    sin_bano = num(d.iloc[fila(d, "No tiene"), c])
    sanea = pozo_ciego + hoyo + sin_bano

    # Hogares 5.7 - una sola habitación
    d = leer_hoja_capital(ruta["h5"])
    c = columnas(d, "Total de hogares")[0]
    total_h5 = num(d.iloc[fila(d, "Total"), c])
    una_hab = num(d.iloc[fila(d, "1"), c])

    # Hogares 6.7 - tenencia (hoja única, fila Capital)
    d = leer_hoja_unica(ruta["h6"])
    r = fila(d, "Capital", col_etiqueta=1)
    total_h6 = num(d.iloc[r, columnas(d, "Total de hogares")[0]])
    sin_doc = num(d.iloc[r, columnas(d, "No tiene documentación")[0]])
    prestada = num(d.iloc[r, columnas(d, "Prestada")[0]])
    otra_sit = num(d.iloc[r, columnas(d, "Otra situación")[0]])
    tenencia = sin_doc + prestada + otra_sit

    # Viviendas 2.7 - allegamiento (hoja única, fila Capital)
    d = leer_hoja_unica(ruta["v2"])
    r = fila(d, "Capital", col_etiqueta=1)
    viviendas = num(d.iloc[r, 2])  # Total: viviendas particulares ocupadas
    hogares_v2 = num(d.iloc[r, 3])  # Total: hogares
    if not (norm(d.iloc[4, 2]).startswith("viviendas") and norm(d.iloc[4, 3]).startswith("hogares")):
        raise ValueError("El cuadro de viviendas 2.7 cambió de formato")
    alleg = hogares_v2 - viviendas

    # Viviendas 3.7 - irrecuperables (bloque de hogares)
    d = leer_hoja_unica(ruta["v3"])
    r = fila(d, "Capital", col_etiqueta=1)
    inicio_hogares = columnas(d, "Total de hogares")[0]

    def tipo(titulo):
        js = [j for j in columnas(d, titulo) if j > inicio_hogares]
        return num(d.iloc[r, js[0]])

    rancho = tipo("Rancho")
    casilla = tipo("Casilla")
    local = tipo("Local no construido para habitación")
    movil = tipo("Vivienda móvil")
    irrec = rancho + casilla + local + movil
except Exception as e:
    fallar(f"No se pudo leer un cuadro del INDEC: {e}")

# Control cruzado: el total de hogares tiene que coincidir en todos los cuadros
totales = {
    "Hogares 1.7": total_h1, "Hogares 2.7": total_h2, "Hogares 3.7": total_h3,
    "Hogares 5.7": total_h5, "Hogares 6.7": total_h6, "Viviendas 2.7": hogares_v2,
}
if len(set(totales.values())) != 1:
    fallar("El total de hogares no coincide entre cuadros: " + str(totales))
total = total_h1

# ---------- Cálculos ----------
dq = irrec + alleg
dq_pct = dq / total * 100
dc_min = max(piso, agua, sanea)
dc_max = piso + agua + sanea
dht_min = dq + dc_min
dht_max = dq + dc_max
dht_pct_min = dht_min / total * 100
dht_pct_max = dht_max / total * 100

# ---------- Encabezado ----------
st.title("Déficit habitacional en Corrientes Capital")
st.subheader("Datos del Censo 2022 (INDEC)")
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
st.caption("Equivale a aproximadamente 1 de cada 5 hogares.")

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

# ---------- Nota metodológica ----------
st.subheader("Nota metodológica")
st.markdown(f"""
- **Déficit cuantitativo** = viviendas irrecuperables + hogares allegados ({fmt(irrec)} + {fmt(alleg)} = {fmt(dq)}).
- **Déficit cualitativo** = rango. El mínimo es la carencia más extendida entre piso, agua y saneamiento ({fmt(dc_min)}). El máximo es la suma de las tres ({fmt(dc_max)}).
- **Déficit total** = cuantitativo + cualitativo, expresado como rango: {fmt(dht_pct_min, 1)}% a {fmt(dht_pct_max, 1)}% de los hogares.
- **Tenencia insegura y hogares de una sola habitación** se muestran aparte como dimensiones complementarias. No se incluyen en el déficit.
- **Total de hogares:** {fmt(total)} (Cuadro 2.7 de hogares, solapa 2.7.3, fila "Total"). El mismo total figura en todos los cuadros usados, y el tablero verifica que coincidan.
- **Agua inadecuada:** hogares sin agua por cañería dentro de la vivienda = {fmt(total_h2)} − {fmt(agua_canieria)} = {fmt(agua)} (Cuadro 2.7 de hogares, solapa 2.7.3, fila "Total").
- **Saneamiento inadecuado:** hogares cuyo baño desagua solo a pozo ciego, a hoyo o excavación, o que no tienen baño: {fmt(pozo_ciego)} + {fmt(hoyo)} + {fmt(sin_bano)} = {fmt(sanea)} (Cuadro 3.7 de hogares, solapa 3.7.3, filas "Solo a pozo ciego", "A hoyo, excavación en la tierra, etc." y "No tiene"). Se considera adecuado el desagüe a red pública y a cámara séptica.
- **Piso precario:** hogares con piso de tierra o ladrillo suelto = {fmt(piso)} (Cuadro 1.7 de hogares, solapa 1.7.3, fila "Total", columna "Tierra o ladrillo suelto").
- **Allegamiento:** hogares que comparten la vivienda con otro hogar = hogares − viviendas particulares ocupadas = {fmt(hogares_v2)} − {fmt(viviendas)} = {fmt(alleg)} (Cuadro 2.7 de viviendas, hoja única, fila "Capital", columnas "Total").
- **Viviendas irrecuperables:** hogares que viven en rancho, casilla, local no construido para habitación o vivienda móvil: {fmt(rancho)} + {fmt(casilla)} + {fmt(local)} + {fmt(movil)} = {fmt(irrec)} (Cuadro 3.7 de viviendas, hoja única, fila "Capital", bloque "Total de hogares"). No se cuentan las casas, los departamentos ni las piezas en inquilinato, hotel familiar o pensión.
- **Tenencia insegura:** hogares con vivienda propia sin documentación, prestada u otra situación: {fmt(sin_doc)} + {fmt(prestada)} + {fmt(otra_sit)} = {fmt(tenencia)} (Cuadro 6.7 de hogares, hoja única, fila "Capital"). No se cuentan como inseguras la propiedad con escritura, boleto u otra documentación, la vivienda alquilada ni la cedida por trabajo.
- **Hogares de una sola habitación:** {fmt(una_hab)} hogares con una habitación (Cuadro 5.7 de hogares, solapa 5.7.3, fila "1" de habitaciones). Es una aproximación: el cuadro no informa cuántas personas viven en cada hogar, por lo que no mide hacinamiento (personas por cuarto).
- Fuente: Censo 2022 (INDEC), resultados definitivos. Descarga: {FECHA_DESCARGA}.
""")

with st.expander("Ver valores calculados"):
    tabla = pd.DataFrame({
        "Indicador": [
            "Total de hogares", "Viviendas irrecuperables", "Hogares allegados",
            "Piso precario", "Agua inadecuada", "Saneamiento inadecuado",
            "Tenencia insegura", "Hogares de una sola habitación",
        ],
        "Hogares": [total, irrec, alleg, piso, agua, sanea, tenencia, una_hab],
    })
    tabla["Hogares"] = tabla["Hogares"].apply(fmt)
    st.dataframe(tabla, use_container_width=True, hide_index=True)
