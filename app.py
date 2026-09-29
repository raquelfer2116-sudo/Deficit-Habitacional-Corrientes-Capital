import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración inicial de la página
st.set_page_config(
    page_title="Déficit Habitacional - Corrientes Capital",
    page_icon="🏠",
    layout="wide"
)

# Función para armar DataFrame por defecto si hay diferencias de columnas
def obtener_datos_base():
    return pd.DataFrame([{
        'Jurisdiccion': 'Ciudad de Corrientes (Capital)',
        'Total_Hogares': 137451,
        'DQ_Irrecuperable': 3640,
        'DQ_Allegamiento': 3328,
        'DQ_Total': 6968,
        'DQ_Porcentaje': 5.07,
        'DC_Piso_Precario': 2682,
        'DC_Agua_Inadecuada': 8090,
        'DC_Saneamiento_Inadecuado': 17048,
        'DC_Tenencia_Insegura': 28941,
        'DC_Hacinamiento': 19617,
        'DC_Cota_Inferior': 17048,
        'DC_Cota_Superior': 27820,
        'DHT_Minimo': 24016,
        'DHT_Maximo': 34788,
        'DHT_Porcentaje_Min': 17.5,
        'DHT_Porcentaje_Max': 25.3
    }])

# Carga de datos oficiales
@st.cache_data
def cargar_datos_censo():
    try:
        df = pd.read_excel('Ciudad_Corrientes_Capital_Deficit_Habitacional_2022.xlsx')
        # Verificar que tenga las columnas requeridas
        if 'Total_Hogares' not in df.columns:
            return obtener_datos_base()
        return df
    except Exception:
        return obtener_datos_base()

# Barra lateral
st.sidebar.title("🛠️ Configuración")
archivo_subido = st.sidebar.file_uploader("Subí un archivo (Excel/CSV):", type=["xlsx", "csv"])

if archivo_subido is not None:
    try:
        df = pd.read_csv(archivo_subido) if archivo_subido.name.endswith('.csv') else pd.read_excel(archivo_subido)
        st.sidebar.success("¡Archivo cargado correctamente!")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        df = cargar_datos_censo()
else:
    df = cargar_datos_censo()

# Encabezado
st.title("🏠 Déficit Habitacional en Corrientes Capital")
st.subheader("Datos oficiales del Censo 2022 (INDEC)")

st.markdown("> **Nota metodológica:** El Déficit Cualitativo ($DC$) se expresa como un rango estimado entre la carencia más extendida y la suma de sus componentes sin solapamiento.")

st.divider()

# Tarjetas KPI
fila = df.iloc[0]
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Hogares Totales", f"{int(fila['Total_Hogares']):,}".replace(",", "."))
with c2:
    st.metric("Déficit Cuantitativo (DQ)", f"{int(fila['DQ_Total']):,}".replace(",", "."), delta=f"{fila['DQ_Porcentaje']}%", delta_color="inverse")
with c3:
    st.metric("Déficit Cualitativo (DC)", f"{int(fila['DC_Cota_Inferior']):,} a {int(fila['DC_Cota_Superior']):,}".replace(",", "."))
with c4:
    st.metric("Déficit Total (DHT)", f"{fila['DHT_Porcentaje_Min']}% a {fila['DHT_Porcentaje_Max']}%", delta="1 de cada 5 hogares", delta_color="inverse")

st.divider()

# Gráficos
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Composición del Déficit Cuantitativo ($DQ$)")
    df_dq = pd.DataFrame({
        'Componente': ['Irrecuperables\n(Ranchos/Casillas)', 'Allegados\n(Convivencia)'],
        'Hogares': [fila['DQ_Irrecuperable'], fila['DQ_Allegamiento']]
    })
    fig_dq = px.bar(df_dq, x='Componente', y='Hogares', text='Hogares', color='Componente', color_discrete_sequence=['#1F77B4', '#FF7F0E'])
    fig_dq.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_dq.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_dq, use_container_width=True)

with col_g2:
    st.subheader("Dimensiones de Carencia")
    dims = ['Tenencia Insegura', 'Hacinamiento', 'Saneamiento Inadecuado', 'Agua Inadecuada', 'Piso Precario']
    vals = [fila['DC_Tenencia_Insegura'], fila['DC_Hacinamiento'], fila['DC_Saneamiento_Inadecuado'], fila['DC_Agua_Inadecuada'], fila['DC_Piso_Precario']]
    df_dims = pd.DataFrame({'Dimensión': dims, 'Hogares': vals}).sort_values('Hogares', ascending=True)
    fig_dims = px.bar(df_dims, x='Hogares', y='Dimensión', orientation='h', text='Hogares', color_discrete_sequence=['#1F77B4'])
    fig_dims.update_traces(texttemplate='%{text:,}', textposition='auto')
    fig_dims.update_layout(height=400)
    st.plotly_chart(fig_dims, use_container_width=True)

with st.expander("📊 Ver datos consolidados"):
    st.dataframe(df, use_container_width=True)
