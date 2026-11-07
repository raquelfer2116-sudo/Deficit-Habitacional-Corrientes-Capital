from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Configuración ----------
ARCHIVO = Path("Ciudad_Corrientes_Capital_Deficit_Habitacional_2022.xlsx")  # confirmen el nombre real
FECHA_DESCARGA = "COMPLETAR (dd/mm/aaaa)"
CUADROS = "COMPLETAR (nombres de los cuadros del INDEC)"

COLUMNAS = [
    "Total_Hogares", "DQ_Irrecuperable", "DQ_Allegamiento",
    "DC_Piso_Precario", "DC_Agua_Inadecuada", "DC_Saneamiento_Inadecuado",
    "DC_Tenencia_Insegura", "DC_Hacinamiento",
]

st.set_page_config(page_title="Déficit habitacional - Corrientes Capital", layout="wide")


def fmt(n, dec=0):
    """Punto de miles, coma decimal."""
    s = f"{n:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def cargar(ruta):
    return pd.read_excel(ruta)


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
def barras(datos, x, y, horizontal=False, color="#1F77B4"):
    datos = datos.copy()
    datos["Etiqueta"] = datos["Hogares"].apply(fmt)
    fig = px.bar(
        datos, x=x, y=y, text="Etiqueta",
        orientation="h" if horizontal else "v",
        color_discrete_sequence=[color],
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
    "Dimensión": ["Tenencia insegura", "Hacinamiento"],
    "Hogares": [tenencia, hacin],
}).sort_values("Hogares")
st.plotly_chart(barras(d_comp, "Hogares", "Dimensión", horizontal=True, color="#7F7F7F"), use_container_width=True)

st.divider()

# ---------- Nota metodológica ----------
st.subheader("Nota metodológica")
st.markdown(f"""
- **Déficit cuantitativo** = viviendas irrecuperables + hogares allegados ({fmt(irrec)} + {fmt(alleg)} = {fmt(dq)}).
- **Déficit cualitativo** = rango. El mínimo es la carencia más extendida entre piso, agua y saneamiento ({fmt(dc_min)}). El máximo es la suma de las tres ({fmt(dc_max)}).
- **Déficit total** = cuantitativo + cualitativo, expresado como rango: {fmt(dht_pct_min, 1)}% a {fmt(dht_pct_max, 1)}% de los hogares.
- **Tenencia insegura y hacinamiento** se muestran aparte como dimensiones complementarias. No se incluyen en el déficit.
- **Cuadros y filas de origen de cada número:** COMPLETAR (ejemplo: Cuadro X, fila Y → irrecuperables).
- Fuente: Censo 2022 (INDEC). Descarga: {FECHA_DESCARGA}.
""")

with st.expander("Ver datos de origen"):
    st.dataframe(df, use_container_width=True)
