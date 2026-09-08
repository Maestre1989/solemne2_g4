# SOLEMNE II - Análisis de Inversión Histórica del MOP
# Grupo 4
# Fuente: datos.gob.cl - Dataset "Detalle inversión histórica MOP 2011-2020"
#
# Librerías usadas: requests, json, pandas, matplotlib, streamlit
# La app consulta la API con GET, procesa los datos con pandas,
# permite filtrar por región/comuna y muestra gráficos con matplotlib
# sobre la inversión del MOP.

import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# *******************************
# Configuración del proyecto
# *********************************
RESOURCE_ID = "4a493e53-ecd7-477a-ab8b-9d3bcd542e07"
LIMIT = 14000
URL_API = f"https://datos.gob.cl/api/3/action/datastore_search?resource_id={RESOURCE_ID}&limit={LIMIT}"

st.set_page_config(page_title="Inversión MOP", page_icon="🏗️", layout="wide")

st.title("🏗️ Inversión Histórica del Ministerio de Obras Públicas")
st.write(
    "Análisis de la inversión del MOP entre 2011 y 2020, usando datos abiertos "
    "del gobierno de Chile (datos.gob.cl)."
)

with st.expander("ℹ️ Sobre el dataset"):
    st.write("**Dataset:** Detalle inversión histórica MOP 2011-2020")
    st.write("**Fuente:** Portal de Datos Abiertos del Gobierno de Chile")
    st.write(f"**Resource ID:** {RESOURCE_ID}")


# **********************************
# Función para pedir los datos a la API (GET + JSON)
# **********************************
@st.cache_data
def cargar_datos():
    try:
        respuesta = requests.get(URL_API, timeout=15)
        respuesta.raise_for_status()
        datos = json.loads(respuesta.text)

        if datos.get("success"):
            registros = datos["result"]["records"]
            return pd.DataFrame(registros)
        else:
            st.error("La API no devolvió datos correctamente.")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error al conectar con la API: {e}")
        return pd.DataFrame()


df = cargar_datos()

if df.empty:
    st.warning("No se pudieron cargar los datos. Revisa tu conexión a internet.")
    st.stop()
if "_id" in df.columns:
    df = df.drop(columns=["_id"])


# **********************************
# Las columnas de este dataset vienen en MAYÚSCULAS:
# ANO, REGION, SERVICIO, PROVINCIA, COMUNA, BIP, NOMBRE, y una columna de monto.
# Buscamos cada columna sin importar mayúsculas/minúsculas para que
# el código no falle si la API cambia el formato del nombre.
# **********************************
def buscar_columna(nombre):
    for c in df.columns:
        if c.strip().upper() == nombre.upper():
            return c
    return None


col_anio = buscar_columna("ANO")
col_region = buscar_columna("REGION")
col_provincia = buscar_columna("PROVINCIA")
col_comuna = buscar_columna("COMUNA")
col_servicio = buscar_columna("SERVICIO")
col_nombre = buscar_columna("NOMBRE")
col_bip = buscar_columna("BIP")

# La columna de monto no siempre se llama igual, así que buscamos
# entre las columnas restantes cuál se puede convertir a número.
columnas_conocidas = [c for c in [col_anio, col_region, col_provincia, col_comuna,
                                   col_servicio, col_nombre, col_bip] if c is not None]

col_monto = None
for c in df.columns:
    if c in columnas_conocidas:
        continue
    convertido = pd.to_numeric(df[c], errors="coerce")
    if convertido.notna().mean() > 0.5:  # más de la mitad de los valores son numéricos
        col_monto = c
        break

if col_monto:
    df[col_monto] = pd.to_numeric(df[col_monto], errors="coerce")

if col_anio:
    df[col_anio] = df[col_anio].astype(str)

# **********************************
# Filtros en la barra lateral
# **********************************
st.sidebar.header("🎛️ Filtros")

df_filtrado = df.copy()

if col_region:
    regiones = ["Todas"] + sorted(df[col_region].dropna().unique().tolist())
    region_elegida = st.sidebar.selectbox("Región:", regiones)
    if region_elegida != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_region] == region_elegida]

if col_comuna:
    comunas = ["Todas"] + sorted(df_filtrado[col_comuna].dropna().unique().tolist())
    comuna_elegida = st.sidebar.selectbox("Comuna:", comunas)
    if comuna_elegida != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_comuna] == comuna_elegida]

if col_anio:
    años = ["Todos"] + sorted(df_filtrado[col_anio].dropna().unique().tolist())
    año_elegido = st.sidebar.selectbox("Año:", años)
    if año_elegido != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_anio] == año_elegido]

busqueda = st.sidebar.text_input("Buscar proyecto:")
if busqueda and col_nombre:
    df_filtrado = df_filtrado[
        df_filtrado[col_nombre].astype(str).str.contains(busqueda, case=False, na=False)
    ]

# **********************************
# KPIs (métricas rápidas)
# **********************************
st.markdown("---")
col1, col2, col3 = st.columns(3)

col1.metric("Proyectos", len(df_filtrado))

if col_monto:
    inversion_total = df_filtrado[col_monto].sum()
    col2.metric("Inversión total", f"${inversion_total:,.0f}")
else:
    col2.metric("Inversión total", "N/D")

if col_region:
    col3.metric("Regiones", df_filtrado[col_region].nunique())
else:
    col3.metric("Regiones", "N/D")

st.markdown("---")


# **********************************
# Tabla de datos + descarga CSV
# **********************************
st.subheader("📋 Datos de inversión")
st.dataframe(df_filtrado, use_container_width=True)

csv = df_filtrado.to_csv(index=False).encode("utf-8")
st.download_button("📥 Descargar CSV", data=csv, file_name="inversion_mop.csv", mime="text/csv")


# **********************************
# Gráfico 1: evolución de la inversión por año
# **********************************
st.markdown("---")
st.subheader("📈 Evolución de la inversión por año")

if col_anio and col_monto and not df_filtrado.empty:
    total_por_año = df_filtrado.groupby(col_anio)[col_monto].sum().sort_index()

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(total_por_año.index, total_por_año.values, marker="o")
    ax.set_xlabel("Año")
    ax.set_ylabel("Inversión ($)")
    ax.set_title("Inversión total del MOP por año")
    st.pyplot(fig)
else:
    st.info("No hay suficientes datos para este gráfico.")

# **********************************
# Gráfico 2: inversión por región
# **********************************
st.markdown("---")
st.subheader("🌎 Inversión por región")

if col_region and col_monto and not df_filtrado.empty:
    top_regiones = df_filtrado.groupby(col_region)[col_monto].sum().sort_values(ascending=False).head(10)

    fig2, ax2 = plt.subplots(figsize=(9, 5))
    top_regiones.sort_values().plot(kind="barh", ax=ax2, color="seagreen")
    ax2.set_xlabel("Inversión total ($)")
    ax2.set_title("Top 10 regiones con mayor inversión")
    st.pyplot(fig2)
else:
    st.info("No hay suficientes datos para este gráfico.")

# **********************************
# Conclusiones
# **********************************
st.markdown("---")
st.subheader("📝 Conclusiones")

if not df_filtrado.empty:
    st.write(f"- Se analizaron **{len(df_filtrado)} proyectos** con los filtros aplicados.")

    if col_anio and col_monto:
        año_max = df_filtrado.groupby(col_anio)[col_monto].sum().idxmax()
        st.write(f"- El año con mayor inversión fue **{año_max}**.")

    if col_region and col_monto:
        region_max = df_filtrado.groupby(col_region)[col_monto].sum().idxmax()
        st.write(f"- La región con mayor inversión acumulada es **{region_max}**.")

    st.write(
        "- Los filtros permiten comparar cómo se distribuye la inversión del MOP "
        "según región, comuna y año."
    )
else:
    st.write("No hay datos suficientes para generar conclusiones con los filtros actuales.")


st.markdown("---")
st.caption("Solemne II - Grupo 4 - Análisis de Datos Abiertos (MOP) - datos.gob.cl")

#***********************************
# Para ejecutar: python -m streamlit run solemne2_g4_mejorado.py
#***********************************