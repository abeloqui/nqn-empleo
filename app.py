import streamlit as st
import pandas as pd
import requests
import json # Asegurate de que json esté importado
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from datetime import datetime
import gspread
from google.oauth2 import service_account

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Empleos Neuquén Capital",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONTRASENIA DEL PANEL ADMINISTRADOR ---
# Cambiá "nqn2026" por la contraseña que vos quieras usar
ADMIN_PASSWORD = "nqn2026"

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

# --- GESTIÓN DE BASE DE DATOS LOCAL (AVISOS COMUNITARIOS JSON) ---








# --- GESTIÓN DE BASE DE DATOS (GOOGLE SHEETS) ---
# Pegá acá la URL completa de tu planilla de Google
SHEET_URL = "https://docs.google.com/spreadsheets/d/1aMqWtGswFmqUhOPrfveAfj137SUDzpr0ENcERsZdu90/edit"

@st.cache_resource
def obtener_conexion_sheets():
    """Autentica y devuelve la conexión a la hoja de cálculo."""
    cred_dict = json.loads(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        cred_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    cliente = gspread.authorize(creds)
    return cliente.open_by_url(SHEET_URL).sheet1

def cargar_avisos_locales():
    try:
        hoja = obtener_conexion_sheets()
        registros = hoja.get_all_records()
        # Invertimos la lista para mostrar primero lo último que cargaste
        return list(reversed(registros)) 
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return []

def guardar_aviso_local(nuevo_aviso):
    hoja = obtener_conexion_sheets()
    if not hoja.get_all_values():
        hoja.append_row(["id", "puesto", "empresa", "lugar", "contacto", "descripcion", "fecha_carga"])
    
    # Mapea los valores según las columnas existentes para evitar desorden
    encabezados = hoja.row_values(1)
    fila = [str(nuevo_aviso.get(col, "")) for col in encabezados]
    hoja.append_row(fila)

def borrar_aviso_en_sheets(id_a_borrar):
    hoja = obtener_conexion_sheets()
    registros = hoja.get_all_records()
    for i, aviso in enumerate(registros):
        # Buscamos el registro que coincida con el ID
        if str(aviso['id']) == str(id_a_borrar):
            hoja.delete_rows(i + 2) # +2: 1 por el encabezado, 1 por base 1 de gspread
            break
            



















# --- SCRAPER MODULAR PARA COMPUTRABAJO NEUQUÉN (CORREGIDO) ---
def scraping_computrabajo(termino):
    """Rastrea ofertas activas de Computrabajo filtrando anuncios expirados."""
    ofertas = []
    try:
        palabra_clave = termino.replace(" ", "-").lower()
        # pubdate=7 fuerza a traer solo ofertas de la última semana
        url = f"https://ar.computrabajo.com/trabajo-de-{palabra_clave}-en-neuquen?pubdate=7"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ofertas

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selector estricto para ofertas interactivas vigentes
        articulos = soup.find_all('article', class_='bClick')
        if not articulos:
            articulos = soup.find_all('article', class_='box_offer')

        for art in articulos[:15]:
            try:
                title_elem = art.find('a', class_='js-o-link')
                if not title_elem: 
                    continue
                
                titulo = title_elem.text.strip()
                enlace = "https://ar.computrabajo.com" + title_elem['href']
                
                # Validación de temporalidad para evitar anuncios fantasma
                fecha_elem = art.find('p', class_='fc_aux')
                txt_fecha = fecha_elem.text.lower() if fecha_elem else ""
                
                if "finalizado" in txt_fecha or "urgente" in txt_fecha and len(txt_fecha) < 10:
                    if not any(palabra in txt_fecha for palabra in ["hoy", "ayer", "días", "dia", "hora", "horas"]):
                        continue

                emp_elem = art.find('a', class_='fc_base') or art.find('p', class_='fc_base')
                empresa = emp_elem.text.strip() if emp_elem else "Confidencial"
                
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

    if "computrabajo" in sitios:
        ofertas_ct = scraping_computrabajo(termino)
        if ofertas_ct:
            df_ct = pd.DataFrame(ofertas_ct)
            df_final = pd.concat([df_final, df_ct], ignore_index=True)

    if not df_final.empty and 'Ubicación' in df_final.columns:
        filtro_neuquen = df_final['Ubicación'].str.contains('Neuquén|Neuquen|computrabajo', case=False, na=False)
        if incluir_remoto and 'Remoto' in df_final.columns:
            df_final = df_final[filtro_neuquen | (df_final['Remoto'] == True)]
        else:
            df_final = df_final[filtro_neuquen]
            
    return df_final


# --- INTERFAZ DE USUARIO PRINCIPAL ---
st.title("📍 Bolsa de Trabajo Conectada - Neuquén Capital")
st.write("Centralizador de portales digitales y avisos barriales compartidos por la comunidad.")

# --- MANEJO DE SESIÓN PARA AUTENTICACIÓN ADMIN ---
if "admin_autenticado" not in st.session_state:
    st.session_state["admin_autenticado"] = False

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración del Rastreador")
portales_disponibles = ["linkedin", "indeed", "computrabajo"]
portales_seleccionados = st.sidebar.multiselect(
    "Portales web a escanear:", 
    options=portales_disponibles, 
    default=["linkedin", "indeed", "computrabajo"]
)
limite_resultados = st.sidebar.slider("Escaneo máximo por portal:", min_value=10, max_value=40, value=25)

st.sidebar.divider()
st.sidebar.subheader("🔒 Acceso Administración")

if not st.session_state["admin_autenticado"]:
    input_password = st.sidebar.text_input("Contraseña de Admin:", type="password")
    if st.sidebar.button("Iniciar Sesión"):
        if input_password == ADMIN_PASSWORD:
            st.session_state["admin_autenticado"] = True
            st.sidebar.success("🔑 Autenticado con éxito")
            st.rerun()
        else:
            st.sidebar.error("Contraseña incorrecta")
else:
    st.sidebar.info("Modo Administrador Activo")
    if st.sidebar.button("Cerrar Sesión Admin"):
        st.session_state["admin_autenticado"] = False
        st.rerun()


# --- DEFINICIÓN DE PESTAÑAS SEGÚN ROL ---
# Si está autenticado, se habilitan las pestañas de carga y gestión
if st.session_state["admin_autenticado"]:
    tab_busqueda, tab_comunidad, tab_panel_carga, tab_gestion = st.tabs([
        "🔍 Buscador de Portales", 
        "👥 Avisos de la Comunidad / Redes", 
        "📤 Cargar Aviso Local",
        "🛠️ Gestionar / Borrar Avisos"
    ])
else:
    tab_busqueda, tab_comunidad = st.tabs([
        "🔍 Buscador de Portales", 
        "👥 Avisos de la Comunidad / Redes"
    ])


# --- PESTAÑA 1: BUSCADOR DE PORTALES DIGITALES ---
with tab_busqueda:
    st.caption("Filtra y extrae información en tiempo real de LinkedIn, Indeed y Computrabajo de forma limpia.")
    
    col_p1, col_p2 = st.columns([3, 1])
    puesto = col_p1.text_input("¿Qué puesto buscás?", placeholder="Ej: Administrativo, Vendedor, Cajero, Repositor", key="puesto_bus")
    permitir_remoto = col_p2.checkbox("Incluir ofertas 100% Remotas", value=False, key="chk_remoto")
    
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
                st.info("No encontramos resultados automáticos vigentes en los portales para ese término exacto hoy. ¡Revisá la pestaña de la comunidad!")


# --- PESTAÑA 2: VISUALIZADOR DE AVISOS DE LA COMUNIDAD ---
with tab_comunidad:
    st.subheader("📢 Ofertas de comercios y redes locales")
    st.write("Datos rescatados de carteles en la calle, grupos de Facebook y avisos vecinales de Neuquén.")
    
    avisos_comunidad = cargar_avisos_locales()
    
    if avisos_comunidad:
        st.info(f"💡 Hay {len(avisos_comunidad)} avisos vigentes verificados por la administración.")
        for aviso in avisos_comunidad:
            st.markdown(f"""
                <div class="community-card">
                    <div class="job-title">{aviso['puesto']}</div>
                    <div class="job-meta">
                        🏢 <b>Comercio/Empresa:</b> {aviso['empresa']} | 📍 <b>Dirección/Zona:</b> {aviso['lugar']} | 📅 <b>Cargado:</b> {aviso['fecha_carga']}
                    </div>
                    <div style="background:#fdfdfd; padding:12px; border-radius:6px; margin-bottom:12px; border:1px solid #f2f2f2; font-size:15px; color:#1f2937; white-space: pre-wrap;">
                        {aviso['descripcion']}
                    </div>
                    <div style="font-size:14px; color:#059669; margin-bottom:10px;">
                        📩 <b>Cómo postularse:</b> {aviso['contacto']}
                    </div>
                    <span class="community-badge">📌 AVISO LOCAL / GRUPOS</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aún no hay avisos manuales cargados en esta sección para mostrarle a la comunidad.")


# --- PESTAÑAS EXCLUSIVAS DEL ADMINISTRADOR AUTENTICADO ---
if st.session_state["admin_autenticado"]:
    
    # PESTAÑA 3: FORMULARIO DE CARGA DE AVISOS
    with tab_panel_carga:
        st.subheader("📤 Cargar información recolectada de la calle o Facebook")
        st.write("Transcribí los anuncios detectados en grupos locales para ponerlos a disposición de los usuarios de Neuquén.")
        
        with st.form("form_carga_admin", clear_on_submit=True):
            puesto_c = st.text_input("Título del puesto requerido:", placeholder="Ej: Mozo de fin de semana, Empleada administrativa")
            empresa_c = st.text_input("Nombre del Comercio / Empresa:", placeholder="Ej: Tienda de ropa centro, Panadería zona oeste")
            lugar_c = st.text_input("Dirección o Zona de Neuquén Capital:", placeholder="Ej: Perito Moreno al 300, Calle San Martín")
            contacto_c = st.text_input("Método de contacto para el postulante:", placeholder="Ej: Dejar CV en el local / WhatsApp: 299xxxxxx / mail@ejemplo.com")
            
            descripcion_c = st.text_area(
                "Detalle del aviso o transcripción del posteo:", 
                placeholder="Pegá el texto completo de Facebook o los requisitos del cartel de la vidriera..."
            )
            
            btn_registrar = st.form_submit_button("Publicar en la Plataforma", type="primary")
            
            if btn_registrar:
                if not puesto_c or not contacto_c or not descripcion_c:
                    st.error("⚠️ Los campos 'Puesto', 'Contacto' y 'Detalle del aviso' son obligatorios.")
                else:
                    # Generamos un ID basado en timestamp para poder gestionarlo de forma única
                    id_aviso = str(int(datetime.now().timestamp()))
                    nuevo_registro = {
                        "id": id_aviso,
                        "puesto": puesto_c.strip(),
                        "empresa": empresa_c.strip() if empresa_c else "Particular / Comercio Chico",
                        "lugar": lugar_c.strip() if lugar_c else "Neuquén Capital",
                        "contacto": contacto_c.strip(),
                        "descripcion": descripcion_c.strip(),
                        "fecha_carga": datetime.now().strftime('%Y-%m-%d %H:%M')
                    }
                    guardar_aviso_local(nuevo_registro)
                    st.success(f"🎉 ¡Éxito! El aviso para '{puesto_c}' fue publicado.")
                    st.balloons()
                    
    # PESTAÑA 4: PANEL DE GESTIÓN Y BAJA DE AVISOS
    with tab_gestion:
        st.subheader("🛠️ Panel de Control de Avisos Locales")
        st.write("Eliminá las publicaciones comunitarias cuyos puestos ya hayan sido cubiertos para mantener limpia la plataforma.")
        
        avisos_gestion = cargar_avisos_locales()
        
        if avisos_gestion:
            for idx, aviso in enumerate(avisos_gestion):
                col_info, col_accion = st.columns([5, 1])
                
                # Para registros antiguos sin ID, usamos el índice temporalmente
                id_unico = aviso.get("id", str(idx))
                
                with col_info:
                    st.markdown(f"**Puesto:** {aviso['puesto']} | **Comercio:** {aviso['empresa']} *(Cargado el: {aviso['fecha_carga']})*")
                
                with col_accion:
                    
                    if st.button("🗑️ Borrar", key=f"btn_del_{id_unico}"):
                      borrar_aviso_en_sheets(id_unico)
                      st.rerun()
                      
                    else:
                     st.info("No hay avisos manuales activos en el sistema para dar de baja.")
    
