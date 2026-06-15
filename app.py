import streamlit as st
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Empleos Neuquén Capital",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .job-card {
        background-color: white;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 18px;
        border-left: 6px solid #0083B0;
    }
    .job-title { color: #004B6E; font-size: 20px; font-weight: bold; margin-bottom: 6px; }
    .job-meta { color: #4B5563; font-size: 14px; margin-bottom: 12px; }
    .source-badge {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)


# --- LÓGICA DE EXTRACCIÓN LOCAL CON FILTRADO ---
@st.cache_data(show_spinner="Escaneando portales en busca de ofertas para Neuquén...", ttl=600)
def buscar_ofertas_locales(sitios, termino, resultados_por_sitio, incluir_remoto):
    try:
        # Forzamos la ubicación a Neuquén, Argentina directamente en la API de JobSpy
        jobs = scrape_jobs(
            site_name=sitios,
            search_term=termino,
            location="Neuquén, Argentina",
            results_per_sheet=resultados_por_sitio,
            hours_old=168,  # Ampliamos a los últimos 7 días ya que el mercado local se mueve a otro ritmo que el global
        )
        
        if jobs is None or jobs.empty:
            return pd.DataFrame()
            
        columnas_interes = {
            'title': 'Título',
            'company': 'Empresa',
            'job_url': 'Enlace',
            'location': 'Ubicación',
            'site': 'Fuente',
            'date_posted': 'Fecha',
            'is_remote': 'Remoto'
        }
        
        columnas_existentes = [col for col in columnas_interes.keys() if col in jobs.columns]
        df_limpio = jobs[columnas_existentes].rename(columns={k: v for k, v in columnas_interes.items() if k in columnas_existentes})
        
        if 'Fecha' in df_limpio.columns:
            df_limpio['Fecha'] = pd.to_datetime(df_limpio['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_limpio['Fecha'] = df_limpio['Fecha'].fillna("Reciente")

        # --- FILTRADO ESTRICTO DE LOCALIZACIÓN ---
        # Nos aseguramos de que solo pasen ofertas que digan "Neuquén" en la ubicación
        # Opcionalmente dejamos pasar las "Remoto" si el usuario activó la casilla
        if 'Ubicación' in df_limpio.columns:
            filtro_neuquen = df_limpio['Ubicación'].str.contains('Neuquén|Neuquen', case=False, na=False)
            
            if incluir_remoto and 'Remoto' in df_limpio.columns:
                filtro_remoto = df_limpio['Remoto'] == True
                df_limpio = df_limpio[filtro_neuquen | filtro_remoto]
            else:
                df_limpio = df_limpio[filtro_neuquen]

        return df_limpio

    except Exception as e:
        st.sidebar.error("Nota: Hubo una limitación temporal con un portal externo.")
        return pd.DataFrame()


# --- INTERFAZ DE USUARIO LOCAL ---
st.title("📍 Bolsa de Trabajo Conectada - Neuquén Capital")
st.subheader("Buscador unificado de ofertas laborales exclusivas para la región")
st.write("Esta herramienta centraliza anuncios de múltiples portales web filtrando automáticamente para Neuquén.")

# --- BARRA LATERAL ---
st.sidebar.header("🔍 Filtros de Búsqueda")

puesto = st.sidebar.text_input(
    "¿Qué estás buscando?", 
    value="", 
    placeholder="Ej: Cajero, Repositor, Desarrollador, Administrativo"
)

permitir_remoto = st.sidebar.checkbox("Incluir también ofertas 100% Remotas", value=False)

st.sidebar.divider()
st.sidebar.subheader("⚙️ Portales activos")

portales_disponibles = ["linkedin", "indeed", "zip_recruiter"]
portales_seleccionados = st.sidebar.multiselect(
    "Buscar en:", 
    options=portales_disponibles, 
    default=["linkedin", "indeed"]
)

# En mercados locales es mejor pedir más resultados para no perderse nada relevante
limite_resultados = st.sidebar.slider("Rango máximo de rastreo:", min_value=10, max_value=50, value=30)

btn_buscar = st.sidebar.button("Buscar en Neuquén", type="primary")

# --- PANEL PRINCIPAL (RESULTADOS) ---
if btn_buscar:
    if not puesto.strip():
        st.warning("⚠️ Por favor, ingresá una palabra clave o puesto para empezar a buscar.")
    elif not portales_seleccionados:
        st.warning("⚠️ Seleccioná al menos un portal de empleo en la barra lateral.")
    else:
        df_resultados = buscar_ofertas_locales(
            sitios=portales_seleccionados,
            termino=puesto,
            resultados_por_sitio=limite_resultados,
            incluir_remoto=permitir_remoto
        )

        if not df_resultados.empty:
            # Métricas locales
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Ofertas encontradas para vos", len(df_resultados))
            col_m2.metric("Zona de cobertura", "Neuquén Capital y alrededores")
            
            st.divider()

            for _, fila in df_resultados.iterrows():
                url = fila['Enlace'] if pd.notna(fila['Enlace']) else "#"
                ubicacion_oferta = fila.get('Ubicación', 'Neuquén')
                fecha_oferta = fila.get('Fecha', 'Reciente')
                
                st.markdown(f"""
                    <div class="job-card">
                        <div class="job-title">{fila['Título']}</div>
                        <div class="job-meta">
                            🏢 <b>{fila['Empresa']}</b> | 📍 {ubicacion_oferta} | 📅 Publicado: {fecha_oferta}
                        </div>
                        <span class="source-badge">🌐 Vía {fila['Fuente'].upper()}</span>
                        <br><br>
                        <a href="{url}" target="_blank" style="text-decoration: none;">
                            <button style="background-color: #0083B0; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">
                                Postularse / Ver Detalle ↗
                            </button>
                        </a>
                    </div>
                """, unsafe_allow_html=True)
                
            # Exportador de datos
            st.sidebar.divider()
            st.sidebar.subheader("💾 Guardar Búsqueda")
            csv = df_resultados.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="Descargar listado (CSV)",
                data=csv,
                file_name=f"empleos_nqn_{puesto.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
            )
        else:
            st.info("No se encontraron anuncios recientes con esa palabra clave específica en Neuquén. Probá usando términos más generales (ej: si buscaste 'Cajero de supermercado', probá con 'Cajero' o 'Atención al cliente').")
else:
    st.info("💡 Ingresá el puesto que te interesa a la izquierda (ej: *Administrativo*, *Vendedor*, *Soporte*) y hacé clic en **'Buscar en Neuquén'**.")
