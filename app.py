from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Configuración ----------
ARCHIVO = Path("Ciudad_Corrientes_Capital_Deficit_Habitacional_2022 (4).xlsx")
FECHA_DESCARGA = "07/11/2026"
CUADROS = "Cuadros 1.7, 2.7, 3.7, 5.7 y 6.7 de hogares (Corrientes, Capital); cuadros de viviendas 2.7 y 3.7"

COLUMNAS = [
    "Total_Hogares", "DQ_Irrecuperable", "DQ_Allegamiento",
    "DC_Piso_Precario", "DC_Agua_Inadecuada", "DC_Saneamiento_Inadecuado",
    "DC_Tenencia_Insegura", "DC_Hacinamiento",
]

PALETA = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]

st.set_page_config(page_title="Déficit habitacional - Corrientes Capital", layout="wide")


def fmt(n, dec=0):
    """Punto de miles, coma decimal."""
    s = f"{n:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def cargar(ruta):
    return pd.read_excel(ruta)


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


# ---------- Carga: si falta algo, se detiene con error visible ----------
if not ARCHIVO.exists():
    st.error(f"Falta el archivo {ARCHIVO}. Súbanlo al repositorio.")
    st.stop()

df = cargar(ARCHIVO)
faltan = [c for c in COLUMNAS if c not in df.columns]
if faltan:
    st.error(f"Al archivo le faltan estas columnas: {', '.join(faltan)}")
    st.stop()

f = df.iloc[0]
total = int(f["Total_Hogares"])
irrec = int(f["DQ_Irrecuperable"])
alleg = int(f["DQ_Allegamiento"])
piso = int(f["DC_Piso_Precario"])
agua = int(f["DC_Agua_Inadecuada"])
sanea = int(f["DC_Saneamiento_Inadecuado"])
tenencia = int(f["DC_Tenencia_Insegura"])
hacin = int(f["DC_Hacinamiento"])

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
st.caption(f"Fuente: Censo 2022 (INDEC) · Cuadros: {CUADROS} · Descargado el {FECHA_DESCARGA}")

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
    "Hogares": [tenencia, hacin],
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
- **Total de hogares:** Cuadro 2.7, solapa Cuadro 2.7.3 (Capital), fila Total, columna Total de hogares.
- **Agua inadecuada:** total de hogares menos los hogares con agua por cañería dentro de la vivienda (Cuadro 2.7, solapa 2.7.3, fila Total).
- **Saneamiento inadecuado:** hogares cuyo baño desagua solo a pozo ciego, a hoyo o excavación, o que no tienen baño: 14.393 + 925 + 1.730 = 17.048 (Cuadro 3.7, solapa 3.7.3, filas "Solo a pozo ciego", "A hoyo, excavación en la tierra, etc." y "No tiene"). Se considera adecuado el desagüe a red pública y a cámara séptica.
- **Piso precario:** hogares con piso de tierra o ladrillo suelto = 2.682 (Cuadro 1.7, solapa 1.7.3, fila "Total", columna "Tierra o ladrillo suelto").
- **Tenencia insegura:** hogares con vivienda propia sin documentación, prestada u otra situación: 11.254 + 6.580 + 11.107 = 28.941 (Cuadro 6.7, hoja única,
fila "Capital", columnas "Propia - No tiene documentación", "Prestada" y "Otra situación"). No se cuentan como inseguras la propiedad con escritura, boleto u otra
documentación, la vivienda alquilada ni la cedida por trabajo.
- **Hogares de una sola habitación:** 19.617 hogares con una habitación (Cuadro 5.7, solapa 5.7.3, fila "1" de habitaciones, columna "Total de hogares"). Es una aproximación: el cuadro no informa cuántas personas viven en cada hogar, por lo que no mide hacinamiento (personas por cuarto).
- Fuente: Censo 2022 (INDEC). Descarga: {FECHA_DESCARGA}.
""")

with st.expander("Ver datos de origen"):
    st.dataframe(df, use_container_width=True)
