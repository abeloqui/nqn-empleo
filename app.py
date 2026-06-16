import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
import json

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Empleos Neuquén", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1aMqWtGswFmqUhOPrfveAfj137SUDzpr0ENcERsZdu90/edit" # CAMBIÁ ESTO POR TU URL

@st.cache_resource
def obtener_conexion_sheets():
    # Usamos los secretos que configuraste en Streamlit Cloud
    cred_dict = json.loads(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        cred_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    cliente = gspread.authorize(creds)
    return cliente.open_by_url(SHEET_URL).sheet1

def cargar_datos():
    hoja = obtener_conexion_sheets()
    return hoja.get_all_records()

def guardar_datos(datos):
    hoja = obtener_conexion_sheets()
    hoja.append_row([datos['id'], datos['puesto'], datos['empresa'], datos['lugar'], datos['contacto'], datos['descripcion'], datos['fecha_carga']])

def eliminar_datos(id_unico):
    hoja = obtener_conexion_sheets()
    registros = hoja.get_all_records()
    for i, fila in enumerate(registros):
        if str(fila['id']) == str(id_unico):
            hoja.delete_rows(i + 2) # +2 por encabezado y base 0
            break

# --- INTERFAZ ---
st.title("💼 Empleos Neuquén - Panel")

menu = st.sidebar.radio("Navegación", ["Ver Avisos", "Administrador (Carga/Borrado)"])

if menu == "Ver Avisos":
    st.subheader("Ofertas Laborales Actuales")
    data = cargar_datos()
    if data:
        df = pd.DataFrame(data)
        st.table(df)
    else:
        st.write("No hay avisos cargados.")

elif menu == "Administrador (Carga/Borrado)":
    st.subheader("Panel de Gestión")
    
    # Formulario de carga
    with st.form("nuevo_aviso"):
        puesto = st.text_input("Puesto")
        empresa = st.text_input("Empresa")
        lugar = st.text_input("Lugar")
        contacto = st.text_input("Contacto")
        descripcion = st.text_area("Descripción")
        enviar = st.form_submit_button("Guardar Aviso")
        
        if enviar:
            nuevo_id = str(len(cargar_datos()) + 1)
            guardar_datos({
                'id': nuevo_id, 'puesto': puesto, 'empresa': empresa, 
                'lugar': lugar, 'contacto': contacto, 'descripcion': descripcion, 
                'fecha_carga': "2026-06-15"
            })
            st.success("Guardado con éxito")
            st.rerun()

    # Sección de borrado
    st.divider()
    st.write("### Borrar avisos existentes")
    avisos = cargar_datos()
    for aviso in avisos:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{aviso['puesto']}** en {aviso['empresa']}")
        if col2.button("🗑️ Borrar", key=aviso['id']):
            eliminar_datos(aviso['id'])
            st.rerun()
            
