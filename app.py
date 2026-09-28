import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(
    page_title="Déficit Habitacional - Censo",
    page_icon="🏠",
    layout="wide"
)

# Título y Subtítulo principal
st.title("📊 Análisis e Indicadores del Déficit Habitacional")
st.markdown("""
**Equipo 4:** Maria Itali Lopez Fernandez y Raquel Elizabeth Fernandez  
**Tema:** Cuantificación del Déficit Habitacional con Datos Censales  
---
""")

# 2. Carga de datos (con caché para mejorar rendimiento)
@st.cache_data
def cargar_datos():
    # Reemplaza 'tus_datos_censo.csv' por la ruta o URL directa de tu archivo CSV/Excel
    df = pd.read_csv('tus_datos_censo.csv')
    return df

try:
    df = cargar_datos()
except Exception as e:
    st.info("💡 Sube tu archivo de datos para previsualizar el dashboard dinámico.")
    # Datos de prueba para que la aplicación muestre estructura visual de inmediato
    df = pd.DataFrame({
        'Jurisdiccion': ['Zona Norte', 'Zona Sur', 'Zona Este', 'Zona Oeste', 'Centro'],
        'Hogares_Totales': [12000, 15000, 9800, 11200, 18000],
        'Deficit_Cuantitativo': [1500, 2300, 800, 1100, 950],
        'Deficit_Cualitativo': [3200, 4100, 2100, 2900, 1800]
    })

# 3. Barra lateral (Filtros interactivos)
st.sidebar.header("🔍 Filtros de Búsqueda")
jurisdicciones = df['Jurisdiccion'].unique()
seleccion_jurisdiccion = st.sidebar.multiselect(
    "Seleccionar Región / Jurisdicción:",
    options=jurisdicciones,
    default=jurisdicciones
)

# Filtrar DataFrame según selección
df_filtrado = df[df['Jurisdiccion'].isin(seleccion_jurisdiccion)]

# 4. Métricas clave (Tarjetas KPI)
st.subheader("📌 Indicadores Clave de Vivienda")

col1, col2, col3 = st.columns(3)

total_hogares = df_filtrado['Hogares_Totales'].sum()
total_cuantitativo = df_filtrado['Deficit_Cuantitativo'].sum()
total_cualitativo = df_filtrado['Deficit_Cualitativo'].sum()

col1.metric("Hogares Analizados", f"{total_hogares:,}")
col2.metric("Déficit Cuantitativo (Viviendas Nuevas)", f"{total_cuantitativo:,}", delta_color="inverse")
col3.metric("Déficit Cualitativo (Mejoras/Hacinamiento)", f"{total_cualitativo:,}", delta_color="inverse")

st.markdown("---")

# 5. Gráficos interactivos con Plotly
st.subheader("📈 Diagnóstico del Déficit por Región")

col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.markdown("### Déficit Cuantitativo vs Cualitativo")
    fig_barras = px.bar(
        df_filtrado, 
        x='Jurisdiccion', 
        y=['Deficit_Cuantitativo', 'Deficit_Cualitativo'],
        barmode='group',
        labels={'value': 'Cantidad de Hogares', 'variable': 'Tipo de Déficit'},
        color_discrete_sequence=['#EF553B', '#FFA15A']
    )
    st.plotly_chart(fig_barras, use_container_width=True)

with col_graf2:
    st.markdown("### Proporción del Déficit Total")
    df_filtrado['Deficit_Total'] = df_filtrado['Deficit_Cuantitativo'] + df_filtrado['Deficit_Cualitativo']
    fig_pie = px.pie(
        df_filtrado, 
        names='Jurisdiccion', 
        values='Deficit_Total',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# 6. Tabla de datos detallada
with st.expander("📋 Ver Tabla de Datos Filtrada"):
    st.dataframe(df_filtrado, use_container_width=True)