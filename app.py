import streamlit as st
import pandas as pd
import json
import requests
import gspread
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from datetime import datetime
from google.oauth2 import service_account

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Empleos Neuquén", layout="wide")

# --- CONEXIÓN GOOGLE SHEETS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1aMqWtGswFmqUhOPrfveAfj137SUDzpr0ENcERsZdu90/edit?usp=drivesdk"

@st.cache_resource
def obtener_conexion_sheets():
    # Asegurate de que en Streamlit Cloud > Secrets hayas pegado el JSON con la clave 'google_credentials'
    cred_dict = json.loads(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        cred_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds).open_by_url(SHEET_URL).sheet1

# --- LÓGICA DE SCRAPING COMPUTRABAJO ---
def scraping_computrabajo(termino):
    ofertas = []
    try:
        url = f"https://ar.computrabajo.com/trabajo-de-{termino.replace(' ', '-')}-en-neuquen?pubdate=7"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for art in soup.find_all('article', class_='bClick')[:15]:
            title_elem = art.find('a', class_='js-o-link')
            if title_elem:
                ofertas.append({
                    'Título': title_elem.text.strip(),
                    'Empresa': art.find('a', class_='fc_base').text.strip() if art.find('a', class_='fc_base') else "Confidencial",
                    'Enlace': "https://ar.computrabajo.com" + title_elem['href'],
                    'Ubicación': "Neuquén Capital",
                    'Fuente': "computrabajo",
                    'Fecha': datetime.now().strftime('%Y-%m-%d')
                })
    except: pass
    return ofertas

# --- INTERFAZ ---
st.title("📍 Bolsa de Trabajo Conectada - Neuquén")
menu = st.sidebar.radio("Navegación", ["🔍 Buscador Portales", "👥 Avisos Comunidad", "🛠️ Panel Admin"])

# --- 1. BUSCADOR PORTALES ---
if menu == "🔍 Buscador Portales":
    st.subheader("Buscador de ofertas en la web")
    puesto = st.text_input("¿Qué puesto buscás?", placeholder="Ej: Cajero, Administrativo...")
    if st.button("Buscar"):
        with st.spinner("Escaneando..."):
            # JobSpy
            try:
                jobs = scrape_jobs(site_name=["linkedin", "indeed"], search_term=puesto, location="Neuquén, Argentina")
                ct_data = scraping_computrabajo(puesto)
                
                if not jobs.empty: st.dataframe(jobs[['title', 'company', 'job_url']])
                if ct_data: st.table(pd.DataFrame(ct_data))
                if jobs.empty and not ct_data: st.info("No se encontraron resultados.")
            except Exception as e:
                st.error("Error al buscar. Intentá de nuevo.")

# --- 2. AVISOS COMUNIDAD ---
elif menu == "👥 Avisos Comunidad":
    st.subheader("Avisos Locales")
    try:
        hoja = obtener_conexion_sheets()
        avisos = hoja.get_all_records()
        if avisos:
            for aviso in avisos:
                st.info(f"**{aviso['puesto']}** en *{aviso['empresa']}* \n\n 📩 Contacto: {aviso['contacto']}")
        else:
            st.write("No hay avisos cargados.")
    except Exception as e:
        st.error("Error al conectar con la planilla. Revisá los permisos de edición.")

# --- 3. PANEL ADMIN ---
elif menu == "🛠️ Panel Admin":
    st.subheader("Carga y Gestión")
    with st.form("carga"):
        p = st.text_input("Puesto"); e = st.text_input("Empresa"); c = st.text_input("Contacto")
        if st.form_submit_button("Guardar"):
            hoja = obtener_conexion_sheets()
            # Guardamos: ID (basado en cantidad de filas), Puesto, Empresa, "", Contacto, "", Fecha
            hoja.append_row([str(len(hoja.get_all_records())+1), p, e, "", c, "", str(datetime.now())])
            st.success("Guardado en Google Sheets")
            st.rerun()
            
    st.write("---")
    st.write("### Borrar Avisos")
    hoja = obtener_conexion_sheets()
    for fila in hoja.get_all_records():
        if st.button(f"🗑️ Borrar {fila['puesto']}", key=str(fila['id'])):
            # Eliminamos por fila
            idx = hoja.find(str(fila['id'])).row
            hoja.delete_rows(idx)
            st.rerun()
            
