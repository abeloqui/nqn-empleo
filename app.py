import streamlit as st
import pandas as pd
import json
import os
import requests
from bs4 import BeautifulSoup
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
    .community-card {
        background-color: #FFFBEB;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 18px;
        border-left: 6px solid #F59E0B;
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
    .community-badge {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE BASE DE DATOS LOCAL (AVISOS COMUNITARIOS) ---
DB_FILE = "avisos_comunidad.json"

def cargar_avisos_locales():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_aviso_local(nuevo_aviso):
    avisos = cargar_avisos_locales()
    avisos.insert(0, nuevo_aviso)  # Los más nuevos primero
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(avisos, f, ensure_ascii=False, indent=4)

# --- SCRAPER MODULAR PARA COMPUTRABAJO NEUQUÉN ---
def scraping_computrabajo(termino):
    """Rastrea de manera segura ofertas de Computrabajo específicas para Neuquén."""
    ofertas = []
    try:
        palabra_clave = termino.replace(" ", "-").lower()
        url = f"https://ar.computrabajo.com/trabajo-de-{palabra_clave}-en-neuquen"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ofertas

        soup = BeautifulSoup(response.text, 'html.parser')
        # Buscamos los contenedores de artículos de empleo estándar de Computrabajo
        articulos = soup.find_all('article', class_='box_offer')

        for art in art_limit := articulos[:15]:
            try:
                title_elem = art.find('a', class_='js-o-link')
                if not title_elem: continue
                
                titulo = title_elem.text.strip()
                enlace = "https://ar.computrabajo.com" + title_elem['href']
                
                emp_elem = art.find('a', class_='fc_base')
                empresa = emp_elem.text.strip() if emp_elem else "Confidencial"
                
                # Verificación estricta de que pertenezca a Neuquén
                loc_elem = art.find('p', class_='fs14')
                loc_text = loc_elem.text.strip() if loc_elem else "Neuquén"
                
                if "neuquén" in loc_text.lower() or "neuquen" in loc_text.lower():
                    ofertas.append({
                        'Título': titulo,
                        'Empresa': empresa,
                        'Enlace': enlace,
                        'Ubicación': "Neuquén Capital (Computrabajo)",
                        'Fuente': "computrabajo",
                        'Fecha': datetime.now().strftime('%Y-%m-%d')
                    })
            except:
                continue
    except:
        pass
    return ofertas

# --- LÓGICA DE EXTRACCIÓN GLOBAL (JOBSPY + COMPUTRABAJO) ---
@st.cache_data(show_spinner="Escaneando redes y portales en busca de ofertas...", ttl=600)
def buscar_ofertas_globales(sitios, termino, resultados_por_sitio, incluir_remoto):
    df_final = pd.DataFrame()
    sitios_jobspy = [s for s in sitios if s in ["linkedin", "indeed", "zip_recruiter"]]
    
    # 1. Ejecutar JobSpy si aplica
    if sitios_jobspy:
        try:
            jobs = scrape_jobs(
                site_name=sitios_jobspy,
                search_term=termino,
                location="Neuquén, Argentina",
                country_indeed="argentina",
                results_per_sheet=resultados_por_sitio,
                hours_old=168,  
            )
            if jobs is not None and not jobs.empty:
                columnas_interes = {'title': 'Título', 'company': 'Empresa', 'job_url': 'Enlace', 'location': 'Ubicación', 'site': 'Fuente', 'date_posted': 'Fecha', 'is_remote': 'Remoto'}
                columnas_existentes = [col for col in columnas_interes.keys() if col in jobs.columns]
                df_final = jobs[columnas_existentes].rename(columns={k: v for k, v in columnas_interes.items() if k in columnas_existentes})
                if 'Fecha' in df_final.columns:
                    df_final['Fecha'] = pd.to_datetime(df_final['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d').fillna("Reciente")
        except:
            pass

    # 2. Ejecutar Computrabajo de forma nativa si está seleccionado
    if "computrabajo" in sitios:
        ofertas_ct = scraping_computrabajo(termino)
        if ofertas_ct:
            df_ct = pd.DataFrame(ofertas_ct)
            df_final = pd.concat([df_final, df_ct], ignore_index=True)

    # 3. Filtrado de localización estricto
    if not df_final.empty and 'Ubicación' in df_final.columns:
        filtro_neuquen = df_final['Ubicación'].str.contains('Neuquén|Neuquen|computrabajo', case=False, na=False)
        if incluir_remoto and 'Remoto' in df_final.columns:
            df_final = df_final[filtro_neuquen | (df_final['Remoto'] == True)]
        else:
            df_final = df_final[filtro_neuquen]
            
    return df_final


# --- INTERFAZ DE USUARIO ---
st.title("📍 Bolsa de Trabajo Conectada - Neuquén Capital")
st.write("Centralizador de portales digitales y avisos barriales compartidos por la comunidad.")

# Estructura de Pestañas Principales
tab_busqueda, tab_comunidad, tab_panel_carga = st.tabs([
    "🔍 Buscador de Portales", 
    "👥 Avisos de la Comunidad / Redes", 
    "📤 Cargar Aviso Local (Admin)"
])

# --- BARRA LATERAL (COMPARTIDA) ---
st.sidebar.header("⚙️ Configuración del Rastreador")
portales_disponibles = ["linkedin", "indeed", "computrabajo"]
portales_seleccionados = st.sidebar.multiselect(
    "Portales web a escanear:", 
    options=portales_disponibles, 
    default=["linkedin", "indeed", "computrabajo"]
)
limite_resultados = st.sidebar.slider("Escaneo máximo por portal:", min_value=10, max_value=40, value=25)


# --- PESTAÑA 1: BUSCADOR DE PORTALES DIGITALES ---
with tab_busqueda:
    st.caption("Filtra y extrae información en tiempo real de LinkedIn, Indeed y Computrabajo.")
    
    col_p1, col_p2 = st.columns([3, 1])
    puesto = col_p1.text_input("¿Qué puesto buscás?", placeholder="Ej: Administrativo, Vendedor, Cajero, Repositor", key="puesto_bus")
    permitir_remoto = col_p2.checkbox("Incluir ofertas 100% Remotas", value=False, style="margin-top:25px;")
    
    btn_buscar = st.button("Buscar en Portales Digitales", type="primary")

    if btn_buscar:
        if not puesto.strip():
            st.warning("⚠️ Escribí una palabra clave para iniciar el rastreo.")
        elif not portales_seleccionados:
            st.warning("⚠️ Seleccioná al menos un portal en la barra lateral.")
        else:
            df_res = buscar_ofertas_globales(portales_seleccionados, puesto, limite_resultados, permitir_remoto)

            if not df_res.empty:
                st.metric("Anuncios consolidados en internet", len(df_res))
                st.divider()

                for _, fila in df_res.iterrows():
                    url = fila['Enlace'] if pd.notna(fila['Enlace']) else "#"
                    st.markdown(f"""
                        <div class="job-card">
                            <div class="job-title">{fila['Título']}</div>
                            <div class="job-meta">
                                🏢 <b>{fila['Empresa']}</b> | 📍 {fila['Ubicación']} | 📅 Detectado: {fila['Fecha']}
                            </div>
                            <span class="source-badge">🌐 Vía {fila['Fuente'].upper()}</span>
                            <br><br>
                            <a href="{url}" target="_blank" style="text-decoration: none;">
                                <button style="background-color: #0083B0; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">
                                    Ver Oferta Original ↗
                                </button>
                            </a>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No encontramos resultados automáticos en los portales para ese término exacto hoy. ¡Revisá la pestaña de la comunidad por si se cargó manualmente!")


# --- PESTAÑA 2: VISUALIZADOR DE AVISOS DE LA COMUNIDAD ---
with tab_comunidad:
    st.subheader("📢 Ofertas detectadas en comercios y redes locales")
    st.write("Datos rescatados de carteles en la calle, grupos de Facebook y avisos vecinales de Neuquén.")
    
    avisos_comunidad = cargar_avisos_locales()
    
    if avisos_comunidad:
        st.info(f"💡 Hay {len(avisos_comunidad)} avisos cargados manualmente por la administración.")
        for aviso in avisos_comunidad:
            st.markdown(f"""
                <div class="community-card">
                    <div class="job-title">{aviso['puesto']}</div>
                    <div class="job-meta">
                        🏢 <b>Comercio/Empresa:</b> {aviso['empresa']} | 📍 <b>Dirección/Zona:</b> {aviso['lugar']} | 📅 <b>Cargado el:</b> {aviso['fecha_carga']}
                    </div>
                    <div style="background:#fdfdfd; padding:12px; border-radius:6px; margin-bottom:12px; border:1px solid #f2f2f2; font-size:15px; color:#1f2937; white-space: pre-wrap;">
                        {aviso['descripcion']}
                    </div>
                    <div style="font-size:14px; color:#059669; margin-bottom:10px;">
                        📩 <b>Cómo postularse:</b> {aviso['contacto']}
                    </div>
                    <span class="community-badge">📌 AVISO BARRIAL / GRUPOS</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aún no hay avisos manuales cargados en esta sección. ¡Usa la siguiente pestaña para cargar el primero!")


# --- PESTAÑA 3: PANEL DE CARGA EXCLUSIVO ADMIN ---
with tab_panel_carga:
    st.subheader("📤 Cargar información recolectada de la calle o Facebook")
    st.write("Utilizá este formulario para transcribir los anuncios que veas en grupos locales o carteles públicos en el centro de Neuquén.")
    
    with st.form("form_carga_admin", clear_on_submit=True):
        puesto_c = st.text_input("Título del puesto requerido:", placeholder="Ej: Mozo de fin de semana, Empleada administrativa")
        empresa_c = st.text_input("Nombre del Comercio / Empresa:", placeholder="Ej: Tienda de ropa centro, Panadería zona oeste")
        lugar_c = st.text_input("Dirección o Zona de Neuquén Capital:", placeholder="Ej: Perito Moreno al 300, Calle San Martín")
        contacto_c = st.text_input("Método de contacto para el postulante:", placeholder="Ej: Dejar CV en el local / WhatsApp: 299xxxxxx / mail@ejemplo.com")
        
        descripcion_c = st.text_area(
            "Detalle del aviso o transcripción del posteo:", 
            placeholder="Pegá acá el texto completo del grupo de Facebook o los requisitos del cartel de la vidriera..."
        )
        
        btn_registrar = st.form_submit_button("Publicar en la Plataforma", type="primary")
        
        if btn_registrar:
            if not puesto_c or not contacto_c or not descripcion_c:
                st.error("⚠️ Los campos 'Puesto', 'Contacto' y 'Detalle del aviso' son completamente obligatorios para no confundir a los usuarios.")
            else:
                nuevo_registro = {
                    "puesto": puesto_c.strip(),
                    "empresa": empresa_c.strip() if empresa_c else "Particular / Comercio Chico",
                    "lugar": lugar_c.strip() if lugar_c else "Neuquén Capital",
                    "contacto": contacto_c.strip(),
                    "descripcion": descripcion_c.strip(),
                    "fecha_carga": datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                guardar_aviso_local(nuevo_registro)
                st.success(f"🎉 ¡Éxito! El aviso para '{puesto_c}' fue guardado y ya figura en la pestaña comunitaria.")
                st.balloons()
