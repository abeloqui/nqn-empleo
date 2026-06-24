"""
Neuquén Labora - Plataforma de empleos para Neuquén Capital y zona Comahue
Desarrollada con Streamlit + Google Sheets + IA (Claude/GPT-4o)
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import re
from datetime import datetime
from io import BytesIO
from PIL import Image
import traceback

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Neuquén Labora",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Columnas del Google Sheet (deben coincidir exactamente)
SHEET_COLUMNS = [
    "ID", "Fecha_Publicación", "Título", "Empresa", "Ubicación",
    "Salario_Desde", "Salario_Hasta", "Tipo_Contrato", "Modalidad",
    "Descripción", "Requisitos", "Contacto", "Link_Postulacion",
    "Fuente", "Destacada"
]

# Nombre de la hoja dentro del spreadsheet
SHEET_NAME = "ofertas"

# ─────────────────────────────────────────────
# ESTILOS CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* Reset y base */
    .stApp {
        background: #0F0F1A;
        font-family: 'Inter', sans-serif;
    }

    /* Ocultar elementos default de Streamlit */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 0 !important; max-width: 1200px; }

    /* ── HEADER ── */
    .nq-header {
        background: linear-gradient(135deg, #0F0F1A 0%, #1A1A35 50%, #0F0F1A 100%);
        border-bottom: 1px solid rgba(99, 102, 241, 0.3);
        padding: 1.5rem 2rem 1rem;
        margin: -1rem -1rem 2rem -1rem;
        position: relative;
        overflow: hidden;
    }
    .nq-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -10%;
        width: 40%;
        height: 200%;
        background: radial-gradient(ellipse, rgba(99,102,241,0.08) 0%, transparent 70%);
        pointer-events: none;
    }
    .nq-header-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .nq-logo-area {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .nq-logo-icon {
        width: 48px; height: 48px;
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.4rem;
        box-shadow: 0 4px 20px rgba(99,102,241,0.4);
    }
    .nq-logo-text h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
        line-height: 1;
    }
    .nq-logo-text p {
        font-size: 0.75rem;
        color: #A78BFA;
        margin: 2px 0 0;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .nq-badge {
        background: rgba(99,102,241,0.15);
        border: 1px solid rgba(99,102,241,0.4);
        color: #A78BFA;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0.03em;
    }
    .nq-stats-bar {
        display: flex;
        gap: 2rem;
        margin-top: 1.25rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.06);
    }
    .nq-stat { text-align: center; }
    .nq-stat-num {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: #6366F1;
    }
    .nq-stat-label {
        font-size: 0.7rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── BUSCADOR ── */
    .nq-search-section {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .nq-search-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.75rem;
    }
    div[data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 12px !important;
        color: #F9FAFB !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 1rem !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }
    div[data-testid="stSelectbox"] > div, div[data-testid="stMultiSelect"] > div {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 12px !important;
        color: #F9FAFB !important;
    }

    /* ── TARJETAS DE OFERTA ── */
    .job-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s, transform 0.15s;
        position: relative;
        overflow: hidden;
    }
    .job-card:hover {
        border-color: rgba(99,102,241,0.4);
        transform: translateY(-2px);
    }
    .job-card.destacada {
        border-color: rgba(245,158,11,0.4);
        background: rgba(245,158,11,0.04);
    }
    .job-card.destacada::before {
        content: '⭐ DESTACADA';
        position: absolute;
        top: 0.6rem; right: 0.75rem;
        font-size: 0.65rem;
        font-weight: 700;
        color: #F59E0B;
        letter-spacing: 0.06em;
    }
    .job-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: #F9FAFB;
        margin-bottom: 0.25rem;
        padding-right: 6rem;
    }
    .job-company {
        font-size: 0.875rem;
        color: #A78BFA;
        font-weight: 500;
        margin-bottom: 0.6rem;
    }
    .job-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.75rem;
    }
    .job-tag {
        background: rgba(255,255,255,0.08);
        border-radius: 6px;
        padding: 0.15rem 0.5rem;
        font-size: 0.72rem;
        color: #9CA3AF;
        white-space: nowrap;
    }
    .job-tag.contract { background: rgba(99,102,241,0.15); color: #A78BFA; }
    .job-tag.salary { background: rgba(16,185,129,0.12); color: #6EE7B7; }
    .job-tag.modality { background: rgba(59,130,246,0.12); color: #93C5FD; }
    .job-desc {
        font-size: 0.83rem;
        color: #6B7280;
        line-height: 1.5;
        margin-bottom: 0.75rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .job-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .job-date { font-size: 0.7rem; color: #4B5563; }
    .job-contact {
        font-size: 0.78rem;
        color: #6366F1;
        font-weight: 500;
    }

    /* ── BOTONES ── */
    .stButton > button {
        background: linear-gradient(135deg, #6366F1, #7C3AED) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        padding: 0.5rem 1.25rem !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
    }

    /* ── PORTALES ── */
    .portals-section {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 1.5rem;
        margin-top: 2rem;
    }
    .portals-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: #E5E7EB;
        margin-bottom: 1rem;
    }
    .portal-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 0.75rem;
    }
    .portal-link {
        display: flex; align-items: center; gap: 0.5rem;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 0.6rem 0.8rem;
        text-decoration: none;
        color: #D1D5DB;
        font-size: 0.82rem;
        font-weight: 500;
        transition: border-color 0.2s, color 0.2s;
    }
    .portal-link:hover { border-color: #6366F1; color: #A78BFA; }

    /* ── ADMIN ── */
    .admin-header {
        background: linear-gradient(135deg, #1A1A2E, #16213E);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex; align-items: center; gap: 1rem;
    }
    .admin-icon { font-size: 1.5rem; }
    .admin-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem; font-weight: 700; color: #F9FAFB; margin: 0;
    }
    .admin-sub { font-size: 0.78rem; color: #6B7280; margin: 0; }

    /* ── SECCIÓN TÍTULO ── */
    .section-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        color: #6366F1;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 1rem;
        display: flex; align-items: center; gap: 0.5rem;
    }
    .section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(99,102,241,0.2);
    }

    /* ── FORMULARIO ── */
    div[data-testid="stTextArea"] textarea {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 12px !important;
        color: #F9FAFB !important;
    }
    div[data-testid="stNumberInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 12px !important;
        color: #F9FAFB !important;
    }

    /* ── LABELS ── */
    label, .stSelectbox label, .stTextInput label,
    .stTextArea label, .stNumberInput label {
        color: #9CA3AF !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }

    /* ── DIVIDER ── */
    hr { border-color: rgba(255,255,255,0.06) !important; }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #6B7280 !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: rgba(99,102,241,0.2) !important;
        color: #A78BFA !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 1.25rem; }

    /* ── EXPANDER ── */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 10px !important;
        color: #E5E7EB !important;
    }

    /* ── INFO / WARNING ── */
    .stAlert { border-radius: 10px !important; }

    /* ── JSON EXTRACCIÓN ── */
    .extraction-result {
        background: rgba(16,185,129,0.06);
        border: 1px solid rgba(16,185,129,0.25);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
    }
    .extraction-title {
        font-size: 0.75rem; font-weight: 700;
        color: #6EE7B7; text-transform: uppercase;
        letter-spacing: 0.08em; margin-bottom: 0.5rem;
    }

    /* ── EMPTY STATE ── */
    .empty-state {
        text-align: center; padding: 3rem 1rem;
        color: #4B5563;
    }
    .empty-state-icon { font-size: 3rem; margin-bottom: 0.75rem; }
    .empty-state-text { font-size: 0.95rem; }

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GOOGLE SHEETS — CONEXIÓN
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    """Conecta con Google Sheets usando Service Account desde st.secrets."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        # st.secrets["gcp_service_account"] contiene el JSON del Service Account
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Error conectando con Google Sheets: {e}")
        return None


def get_worksheet():
    """Obtiene (o crea) la hoja de trabajo."""
    client = get_gsheet_client()
    if client is None:
        return None
    try:
        spreadsheet = client.open(st.secrets["google_sheets"]["spreadsheet_name"])
        try:
            ws = spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)
            ws.append_row(SHEET_COLUMNS)
            _seed_example_data(ws)
        return ws
    except Exception as e:
        st.error(f"❌ Error accediendo a la hoja: {e}")
        return None


def _seed_example_data(ws):
    """Inserta ofertas de ejemplo al crear la hoja por primera vez."""
    examples = [
        ["1", "2025-06-01", "Vendedor/a Zona Comahue", "Distribuidora Del Sur S.A.",
         "Neuquén Capital", "350000", "500000", "Relación de dependencia", "Presencial",
         "Buscamos vendedor/a con experiencia en distribución para cubrir zona Neuquén Capital y alrededores. Vehículo propio excluyente.",
         "Secundario completo. Experiencia mínima 2 años en ventas. Licencia de conducir.",
         "RRHH: rrhh@distribuidoradelsur.com.ar", "", "LinkedIn", "FALSE"],

        ["2", "2025-06-02", "Desarrollador/a Web Full Stack Jr.", "Startup Patagónica",
         "Neuquén Capital / Remoto", "500000", "750000", "Freelance / Proyecto", "Híbrido",
         "Nos sumamos en busca de desarrolladores jr para proyectos web. Stack: React + Node.js o Python. Posibilidad de trabajo 100% remoto.",
         "Conocimientos en HTML/CSS/JS. Proyectos propios o universitarios. Inglés básico.",
         "CV a: jobs@startuppatagoncia.com", "", "Facebook Neuquén Labura", "TRUE"],

        ["3", "2025-06-03", "Encargado/a de Turno — Gastronomía", "Café del Parque",
         "Neuquén Capital", "400000", "500000", "Relación de dependencia", "Presencial",
         "Importante local gastronómico en el centro de Neuquén incorpora encargado/a de turno. Horario rotativo.",
         "Experiencia en gastronomía mínimo 1 año. Capacidad de liderazgo de equipo pequeño.",
         "WhatsApp: 299-4XXXXXX", "", "Computrabajo", "FALSE"],

        ["4", "2025-06-04", "Auxiliar Contable", "Estudio Contable Rioja & Asoc.",
         "Neuquén Capital", "380000", "480000", "Relación de dependencia", "Presencial",
         "Estudio contable incorpora auxiliar contable. Tareas de archivo, carga de comprobantes y atención a clientes.",
         "Estudiante avanzado o graduado en Ciencias Económicas. Manejo de Excel. Prolijidad.",
         "Enviar CV a estudio@riojaasoc.com.ar", "", "Bumeran", "FALSE"],

        ["5", "2025-06-05", "Maestro/a de Obra — Construcción", "Constructora Andina",
         "Zapala y zona", "600000", "800000", "Por obra", "Presencial",
         "Importante constructora requiere maestro/a de obra para proyectos en Zapala, Chos Malal y zona sur.",
         "Experiencia comprobable en dirección de obra. Disponibilidad para viajar. Conocimiento en lectura de planos.",
         "Contacto: RRHH 299-3XXXXXX", "", "Zonajobs", "FALSE"],
    ]
    ws.append_rows(examples)


@st.cache_data(ttl=60, show_spinner=False)
def load_offers():
    """Carga todas las ofertas desde Google Sheets como DataFrame."""
    ws = get_worksheet()
    if ws is None:
        return pd.DataFrame(columns=SHEET_COLUMNS)
    try:
        data = ws.get_all_records(expected_headers=SHEET_COLUMNS)
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=SHEET_COLUMNS)
        # Asegurar tipos
        df["Fecha_Publicación"] = pd.to_datetime(df["Fecha_Publicación"], errors="coerce")
        df["Destacada"] = df["Destacada"].astype(str).str.upper().isin(["TRUE", "1", "SÍ", "SI"])
        return df.sort_values("Fecha_Publicación", ascending=False, na_position="last")
    except Exception as e:
        st.error(f"❌ Error cargando ofertas: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)


def invalidate_cache():
    """Limpia el cache para forzar recarga desde Sheets."""
    load_offers.clear()


def get_next_id(ws):
    """Genera el próximo ID numérico para una nueva oferta."""
    try:
        records = ws.get_all_records(expected_headers=SHEET_COLUMNS)
        if not records:
            return 1
        ids = [int(r.get("ID", 0)) for r in records if str(r.get("ID", "")).isdigit()]
        return max(ids) + 1 if ids else 1
    except Exception:
        return 1


def save_offer(offer_data: dict):
    """Guarda una oferta nueva en Google Sheets."""
    ws = get_worksheet()
    if ws is None:
        return False
    try:
        next_id = get_next_id(ws)
        offer_data["ID"] = str(next_id)
        if not offer_data.get("Fecha_Publicación"):
            offer_data["Fecha_Publicación"] = datetime.now().strftime("%Y-%m-%d")
        row = [str(offer_data.get(col, "")) for col in SHEET_COLUMNS]
        ws.append_row(row)
        invalidate_cache()
        return True
    except Exception as e:
        st.error(f"❌ Error guardando oferta: {e}")
        return False


def update_offer(row_index: int, offer_data: dict):
    """Actualiza una oferta existente (row_index = índice en la hoja, 1-based, +1 por header)."""
    ws = get_worksheet()
    if ws is None:
        return False
    try:
        sheet_row = row_index + 2  # +1 header, +1 porque gspread empieza en 1
        row = [str(offer_data.get(col, "")) for col in SHEET_COLUMNS]
        ws.update(f"A{sheet_row}:{chr(64+len(SHEET_COLUMNS))}{sheet_row}", [row])
        invalidate_cache()
        return True
    except Exception as e:
        st.error(f"❌ Error actualizando oferta: {e}")
        return False


def delete_offer(offer_id: str):
    """Elimina una oferta por su ID."""
    ws = get_worksheet()
    if ws is None:
        return False
    try:
        cell = ws.find(str(offer_id), in_column=1)
        if cell:
            ws.delete_rows(cell.row)
            invalidate_cache()
            return True
        return False
    except Exception as e:
        st.error(f"❌ Error eliminando oferta: {e}")
        return False


# ─────────────────────────────────────────────
# INTELIGENCIA ARTIFICIAL — EXTRACCIÓN DE IMÁGENES
# ─────────────────────────────────────────────
EXTRACTION_PROMPT = """Eres un asistente experto en extraer información de ofertas laborales publicadas en grupos de Facebook, WhatsApp u otras redes sociales en Argentina, específicamente en la región de Neuquén/Comahue/Patagonia.

Analiza la imagen o texto proporcionado y extrae TODOS los datos disponibles sobre la oferta laboral.

Devuelve ÚNICAMENTE un objeto JSON válido con exactamente estas claves (usa cadena vacía "" si el dato no está disponible):

{
  "Título": "Título o puesto del trabajo",
  "Empresa": "Nombre de la empresa o empleador",
  "Ubicación": "Ciudad o zona (ej: Neuquén Capital, Zapala, Comahue)",
  "Salario_Desde": "Número sin puntos ni símbolo (ej: 350000) o vacío",
  "Salario_Hasta": "Número sin puntos ni símbolo (ej: 500000) o vacío",
  "Tipo_Contrato": "Uno de: Relación de dependencia / Freelance / Por obra / Temporal / Part-time / A convenir",
  "Modalidad": "Uno de: Presencial / Remoto / Híbrido",
  "Descripción": "Descripción completa del puesto y tareas",
  "Requisitos": "Requisitos, experiencia necesaria, perfil buscado",
  "Contacto": "WhatsApp, email, o forma de contacto indicada",
  "Link_Postulacion": "URL de postulación si existe, o vacío",
  "Fuente": "Facebook / WhatsApp / Instagram / LinkedIn / Otro",
  "Destacada": "FALSE"
}

INSTRUCCIONES IMPORTANTES:
- Si hay salario en formato "$ 350.000", extráelo como "350000"
- Si dice "a convenir" o "a tratar", deja vacío los campos de salario
- Para Tipo_Contrato y Modalidad, elige la opción más cercana de las disponibles
- La Descripción debe ser completa, no resumida
- Extrae el contacto exactamente como aparece (número de WhatsApp, email, etc.)
- Si la imagen no contiene una oferta laboral, devuelve un JSON con todos los campos vacíos y en "Fuente" pon "No identificada"
- NO incluyas texto antes ni después del JSON
- El JSON debe ser parseable directamente con json.loads()"""


def extract_with_claude(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Extrae información de una imagen usando Claude 3.5 Sonnet."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=st.secrets["ai_apis"]["anthropic_key"])
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT
                        }
                    ],
                }
            ],
        )
        raw = message.content[0].text.strip()
        # Limpiar markdown si viene envuelto
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        st.error(f"❌ La IA no devolvió JSON válido: {e}")
        return {}
    except Exception as e:
        st.error(f"❌ Error con Claude API: {e}")
        return {}


def extract_with_openai(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Extrae información de una imagen usando GPT-4o."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["ai_apis"]["openai_key"])
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{image_b64}"
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "high"}
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT
                        }
                    ]
                }
            ]
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        st.error(f"❌ La IA no devolvió JSON válido: {e}")
        return {}
    except Exception as e:
        st.error(f"❌ Error con OpenAI API: {e}")
        return {}


# ─────────────────────────────────────────────
# COMPONENTES UI
# ─────────────────────────────────────────────
def render_header(total_offers: int):
    areas = ["Ventas", "Tech", "Gastronomía", "Construcción", "Admin", "Salud"]
    st.markdown(f"""
    <div class="nq-header">
        <div class="nq-header-top">
            <div class="nq-logo-area">
                <div class="nq-logo-icon">💼</div>
                <div class="nq-logo-text">
                    <h1>Neuquén Labora</h1>
                    <p>Empleos • Comahue • Patagonia</p>
                </div>
            </div>
            <span class="nq-badge">🟢 Actualizado hoy</span>
        </div>
        <div class="nq-stats-bar">
            <div class="nq-stat">
                <div class="nq-stat-num">{total_offers}</div>
                <div class="nq-stat-label">Ofertas activas</div>
            </div>
            <div class="nq-stat">
                <div class="nq-stat-num">NQN</div>
                <div class="nq-stat-label">Ciudad principal</div>
            </div>
            <div class="nq-stat">
                <div class="nq-stat-num">🆓</div>
                <div class="nq-stat-label">100% Gratis</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_job_card(row: pd.Series):
    """Renderiza una tarjeta de oferta laboral."""
    es_destacada = row.get("Destacada", False)
    clase = "job-card destacada" if es_destacada else "job-card"
    salario = ""
    if row.get("Salario_Desde") or row.get("Salario_Hasta"):
        desde = f"${int(float(row['Salario_Desde'])):,}".replace(",", ".") if row.get("Salario_Desde") else ""
        hasta = f"${int(float(row['Salario_Hasta'])):,}".replace(",", ".") if row.get("Salario_Hasta") else ""
        if desde and hasta:
            salario = f"{desde} — {hasta}"
        elif desde:
            salario = f"Desde {desde}"
        elif hasta:
            salario = f"Hasta {hasta}"
    fecha = ""
    if pd.notna(row.get("Fecha_Publicación")):
        try:
            fecha = pd.to_datetime(row["Fecha_Publicación"]).strftime("%d/%m/%Y")
        except Exception:
            fecha = str(row.get("Fecha_Publicación", ""))
    link = row.get("Link_Postulacion", "")
    link_html = f'<a href="{link}" target="_blank" style="color:#6366F1;font-size:0.78rem;font-weight:500;">Ver postulación →</a>' if link else ""
    contacto = row.get("Contacto", "")
    contacto_html = f'<span class="job-contact">📬 {contacto}</span>' if contacto else ""
    st.markdown(f"""
    <div class="{clase}">
        <div class="job-title">{row.get('Título','Sin título')}</div>
        <div class="job-company">🏢 {row.get('Empresa','Empresa no especificada')}</div>
        <div class="job-meta">
            <span class="job-tag">📍 {row.get('Ubicación','')}</span>
            {"<span class='job-tag contract'>" + str(row.get('Tipo_Contrato','')) + "</span>" if row.get('Tipo_Contrato') else ""}
            {"<span class='job-tag modality'>" + str(row.get('Modalidad','')) + "</span>" if row.get('Modalidad') else ""}
            {"<span class='job-tag salary'>" + salario + "</span>" if salario else ""}
        </div>
        <div class="job-desc">{row.get('Descripción','')}</div>
        <div class="job-footer">
            <span class="job-date">📅 {fecha} · Fuente: {row.get('Fuente','')}</span>
            <div style="display:flex;gap:0.75rem;align-items:center;">
                {contacto_html}
                {link_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_portals():
    portales = [
        ("🔵 LinkedIn NQN", "https://www.linkedin.com/jobs/search/?location=Neuqu%C3%A9n%2C%20Argentina"),
        ("🟠 Computrabajo", "https://www.computrabajo.com.ar/trabajo-en-neuquen"),
        ("🔴 Indeed", "https://ar.indeed.com/jobs?l=Neuqu%C3%A9n%2C+Neuqu%C3%A9n"),
        ("🟡 Zonajobs", "https://www.zonajobs.com.ar/empleos-en-neuquen.html"),
        ("🟣 Bumeran", "https://www.bumeran.com.ar/empleos-en-neuquen.html"),
        ("🔵 Trabajando.com", "https://ar.trabajando.com/empleos?where=Neuqu%C3%A9n"),
        ("🟢 Facebook Grupos", "https://www.facebook.com/search/groups/?q=trabajo%20neuqu%C3%A9n"),
        ("⚪ Empleate", "https://www.empleate.com/ar/trabajo-en-neuquen"),
    ]
    links_html = "\n".join(
        f'<a class="portal-link" href="{url}" target="_blank">{nombre}</a>'
        for nombre, url in portales
    )
    st.markdown(f"""
    <div class="portals-section">
        <div class="portals-title">🌐 Otros portales — ofertas en Neuquén</div>
        <div class="portal-grid">{links_html}</div>
    </div>
    """, unsafe_allow_html=True)


def offer_form(prefill: dict = None, key_prefix: str = "new") -> dict:
    """Formulario reutilizable para agregar/editar oferta."""
    p = prefill or {}
    tipos = ["", "Relación de dependencia", "Freelance", "Por obra", "Temporal", "Part-time", "A convenir"]
    modalidades = ["", "Presencial", "Remoto", "Híbrido"]
    fuentes = ["Formulario manual", "Facebook", "WhatsApp", "Instagram", "LinkedIn", "Computrabajo", "Bumeran", "Zonajobs", "Indeed", "Otro"]

    c1, c2 = st.columns(2)
    with c1:
        titulo = st.text_input("Título del puesto *", value=p.get("Título", ""), key=f"{key_prefix}_titulo")
    with c2:
        empresa = st.text_input("Empresa", value=p.get("Empresa", ""), key=f"{key_prefix}_empresa")

    c3, c4 = st.columns(2)
    with c3:
        ubicacion = st.text_input("Ubicación", value=p.get("Ubicación", "Neuquén Capital"), key=f"{key_prefix}_ubic")
    with c4:
        tipo_c_val = p.get("Tipo_Contrato", "")
        tipo_c_idx = tipos.index(tipo_c_val) if tipo_c_val in tipos else 0
        tipo_contrato = st.selectbox("Tipo de contrato", tipos, index=tipo_c_idx, key=f"{key_prefix}_contrato")

    c5, c6, c7 = st.columns(3)
    with c5:
        try:
            sal_d = int(float(p.get("Salario_Desde", 0) or 0))
        except Exception:
            sal_d = 0
        salario_desde = st.number_input("Salario desde ($)", min_value=0, value=sal_d, step=50000, key=f"{key_prefix}_saldesde")
    with c6:
        try:
            sal_h = int(float(p.get("Salario_Hasta", 0) or 0))
        except Exception:
            sal_h = 0
        salario_hasta = st.number_input("Salario hasta ($)", min_value=0, value=sal_h, step=50000, key=f"{key_prefix}_salhasta")
    with c7:
        mod_val = p.get("Modalidad", "")
        mod_idx = modalidades.index(mod_val) if mod_val in modalidades else 0
        modalidad = st.selectbox("Modalidad", modalidades, index=mod_idx, key=f"{key_prefix}_modal")

    descripcion = st.text_area("Descripción del puesto", value=p.get("Descripción", ""), height=120, key=f"{key_prefix}_desc")
    requisitos = st.text_area("Requisitos / Perfil buscado", value=p.get("Requisitos", ""), height=100, key=f"{key_prefix}_req")

    c8, c9 = st.columns(2)
    with c8:
        contacto = st.text_input("Contacto (email / WhatsApp)", value=p.get("Contacto", ""), key=f"{key_prefix}_contacto")
    with c9:
        link = st.text_input("Link de postulación (opcional)", value=p.get("Link_Postulacion", ""), key=f"{key_prefix}_link")

    c10, c11 = st.columns(2)
    with c10:
        fuente_val = p.get("Fuente", "Formulario manual")
        fuente_idx = fuentes.index(fuente_val) if fuente_val in fuentes else 0
        fuente = st.selectbox("Fuente", fuentes, index=fuente_idx, key=f"{key_prefix}_fuente")
    with c11:
        destacada = st.checkbox("⭐ Marcar como destacada", value=bool(p.get("Destacada", False)), key=f"{key_prefix}_dest")

    return {
        "Título": titulo,
        "Empresa": empresa,
        "Ubicación": ubicacion,
        "Salario_Desde": str(salario_desde) if salario_desde else "",
        "Salario_Hasta": str(salario_hasta) if salario_hasta else "",
        "Tipo_Contrato": tipo_contrato,
        "Modalidad": modalidad,
        "Descripción": descripcion,
        "Requisitos": requisitos,
        "Contacto": contacto,
        "Link_Postulacion": link,
        "Fuente": fuente,
        "Destacada": str(destacada).upper(),
    }


# ─────────────────────────────────────────────
# PÁGINAS
# ─────────────────────────────────────────────
def page_public():
    df = load_offers()
    render_header(len(df))

    # ── Búsqueda y filtros ──
    st.markdown('<div class="nq-search-section">', unsafe_allow_html=True)
    st.markdown('<div class="nq-search-label">🔍 Buscar empleos</div>', unsafe_allow_html=True)
    busqueda = st.text_input("", placeholder="Ej: vendedor, desarrollador, gastronomía...", label_visibility="collapsed")
    
    with st.expander("🎛️ Filtros avanzados"):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            tipos_disp = ["Todos"] + [t for t in df["Tipo_Contrato"].dropna().unique() if t]
            filtro_tipo = st.selectbox("Tipo de contrato", tipos_disp)
        with fc2:
            mod_disp = ["Todos"] + [m for m in df["Modalidad"].dropna().unique() if m]
            filtro_modal = st.selectbox("Modalidad", mod_disp)
        with fc3:
            sal_max = int(df["Salario_Hasta"].replace("", 0).apply(
                lambda x: float(x) if str(x).replace(".","").isdigit() else 0).max()) or 2000000
            filtro_sal = st.slider("Salario máximo ($)", 0, sal_max, sal_max, step=50000,
                                   format="$%d")
        solo_destacadas = st.checkbox("⭐ Solo ofertas destacadas")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Aplicar filtros ──
    filtered = df.copy()
    if busqueda:
        mask = (
            filtered["Título"].str.contains(busqueda, case=False, na=False) |
            filtered["Empresa"].str.contains(busqueda, case=False, na=False) |
            filtered["Descripción"].str.contains(busqueda, case=False, na=False) |
            filtered["Requisitos"].str.contains(busqueda, case=False, na=False)
        )
        filtered = filtered[mask]
    if filtro_tipo != "Todos":
        filtered = filtered[filtered["Tipo_Contrato"] == filtro_tipo]
    if filtro_modal != "Todos":
        filtered = filtered[filtered["Modalidad"] == filtro_modal]
    if solo_destacadas:
        filtered = filtered[filtered["Destacada"] == True]
    # Filtro salario
    def sal_ok(row):
        try:
            hasta = float(row.get("Salario_Hasta") or 0)
            return hasta == 0 or hasta <= filtro_sal
        except Exception:
            return True
    filtered = filtered[filtered.apply(sal_ok, axis=1)]

    # ── Resultados ──
    col_main, col_side = st.columns([3, 1])
    with col_main:
        st.markdown(f'<div class="section-title">💼 {len(filtered)} oferta(s) encontrada(s)</div>', unsafe_allow_html=True)
        if filtered.empty:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-text">No encontramos ofertas con esos criterios.<br>Probá con otros términos o eliminá algunos filtros.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Destacadas primero
            dest = filtered[filtered["Destacada"] == True]
            resto = filtered[filtered["Destacada"] != True]
            for _, row in pd.concat([dest, resto]).iterrows():
                render_job_card(row)

    with col_side:
        st.markdown('<div class="section-title">📊 Resumen</div>', unsafe_allow_html=True)
        if not df.empty:
            st.metric("Total ofertas", len(df))
            st.metric("Destacadas", len(df[df["Destacada"] == True]))
            mods = df["Modalidad"].value_counts()
            if not mods.empty:
                st.markdown("**Por modalidad:**")
                for mod, cnt in mods.items():
                    if mod:
                        st.markdown(f"- {mod}: **{cnt}**")
        st.markdown("---")
        st.markdown("**🗓️ Actualización**")
        st.caption("Las ofertas se actualizan manualmente por el administrador del sitio.")

    render_portals()


def page_admin():
    st.markdown("""
    <div class="admin-header">
        <span class="admin-icon">⚙️</span>
        <div>
            <p class="admin-title">Panel de Administración</p>
            <p class="admin-sub">Neuquén Labora · Gestión de ofertas</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ Agregar oferta", "🤖 Extraer desde imagen", "📋 Gestionar ofertas"])

    # ── TAB 1: Formulario manual ──
    with tab1:
        st.markdown('<div class="section-title">Agregar oferta manualmente</div>', unsafe_allow_html=True)
        form_data = offer_form(key_prefix="manual")
        if st.button("💾 Guardar oferta", key="save_manual"):
            if not form_data["Título"]:
                st.error("El título es obligatorio.")
            else:
                with st.spinner("Guardando en Google Sheets..."):
                    ok = save_offer(form_data)
                if ok:
                    st.success("✅ Oferta guardada correctamente.")
                    st.balloons()

    # ── TAB 2: Extracción IA desde imagen ──
    with tab2:
        st.markdown('<div class="section-title">Extraer oferta desde captura de pantalla</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        with c1:
            st.info("📸 Subí una captura de pantalla de una publicación de trabajo (Facebook, WhatsApp, etc.) y la IA extraerá los datos automáticamente.")
        with c2:
            ai_model = st.selectbox(
                "Modelo de IA",
                ["Claude 3.5 Sonnet (Recomendado)", "GPT-4o"],
                key="ai_model_select"
            )

        uploaded_file = st.file_uploader(
            "Seleccionar imagen",
            type=["png", "jpg", "jpeg", "webp"],
            key="img_upload"
        )

        if uploaded_file:
            img_bytes = uploaded_file.read()
            img = Image.open(BytesIO(img_bytes))
            col_img, col_btn = st.columns([2, 1])
            with col_img:
                st.image(img, caption="Imagen cargada", use_container_width=True)
            with col_btn:
                st.markdown("**Imagen cargada ✅**")
                st.caption(f"Tamaño: {img.size[0]}×{img.size[1]}px")
                st.caption(f"Formato: {img.format or 'desconocido'}")
                extraer_btn = st.button("🤖 Extraer con IA", type="primary", key="extract_btn")

            if extraer_btn or st.session_state.get("extracted_data"):
                if extraer_btn:
                    # Determinar mime type
                    mime_map = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
                    mime = mime_map.get(img.format or "", "image/jpeg")
                    with st.spinner(f"🔍 Analizando imagen con {'Claude' if 'Claude' in ai_model else 'GPT-4o'}..."):
                        if "Claude" in ai_model:
                            result = extract_with_claude(img_bytes, mime)
                        else:
                            result = extract_with_openai(img_bytes, mime)
                    if result:
                        st.session_state["extracted_data"] = result
                        st.success("✅ Extracción completada. Revisá y editá los datos antes de guardar.")
                    else:
                        st.error("❌ No se pudo extraer información. Intentá con otra imagen o modelo.")
                        st.session_state.pop("extracted_data", None)

                if st.session_state.get("extracted_data"):
                    extracted = st.session_state["extracted_data"]
                    with st.expander("🔎 Ver JSON extraído (datos crudos)", expanded=False):
                        st.markdown('<div class="extraction-result">', unsafe_allow_html=True)
                        st.markdown('<div class="extraction-title">JSON extraído por la IA</div>', unsafe_allow_html=True)
                        st.json(extracted)
                        st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown('<div class="section-title">Revisar y editar datos extraídos</div>', unsafe_allow_html=True)
                    form_data_ai = offer_form(prefill=extracted, key_prefix="ai")
                    col_save, col_clear = st.columns([1, 1])
                    with col_save:
                        if st.button("💾 Guardar oferta extraída", key="save_ai", type="primary"):
                            if not form_data_ai["Título"]:
                                st.error("El título es obligatorio.")
                            else:
                                with st.spinner("Guardando en Google Sheets..."):
                                    ok = save_offer(form_data_ai)
                                if ok:
                                    st.success("✅ Oferta guardada correctamente.")
                                    st.session_state.pop("extracted_data", None)
                                    st.balloons()
                    with col_clear:
                        if st.button("🗑️ Descartar extracción", key="clear_ai"):
                            st.session_state.pop("extracted_data", None)
                            st.rerun()

    # ── TAB 3: Gestionar ofertas ──
    with tab3:
        st.markdown('<div class="section-title">Listado completo de ofertas</div>', unsafe_allow_html=True)
        df = load_offers()

        if df.empty:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div class="empty-state-text">No hay ofertas cargadas todavía.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Buscador rápido
            q = st.text_input("🔍 Buscar en lista", placeholder="Filtrar por título o empresa...", key="admin_search")
            filtered_admin = df.copy()
            if q:
                mask = (
                    filtered_admin["Título"].str.contains(q, case=False, na=False) |
                    filtered_admin["Empresa"].str.contains(q, case=False, na=False)
                )
                filtered_admin = filtered_admin[mask]

            st.caption(f"Mostrando {len(filtered_admin)} de {len(df)} ofertas")

            for idx, (df_idx, row) in enumerate(filtered_admin.iterrows()):
                with st.expander(
                    f"{'⭐ ' if row.get('Destacada') else ''}**{row.get('Título','Sin título')}** — {row.get('Empresa','')} | {row.get('Fecha_Publicación','')}"
                ):
                    # Vista previa
                    render_job_card(row)
                    st.markdown("---")
                    sub_tabs = st.tabs(["✏️ Editar", "🗑️ Eliminar"])

                    with sub_tabs[0]:
                        edit_data = offer_form(prefill=row.to_dict(), key_prefix=f"edit_{idx}")
                        if st.button("💾 Actualizar", key=f"upd_{idx}"):
                            edit_data["ID"] = str(row["ID"])
                            edit_data["Fecha_Publicación"] = str(row.get("Fecha_Publicación", ""))[:10]
                            with st.spinner("Actualizando..."):
                                # Encontrar posición real en el sheet
                                ws = get_worksheet()
                                if ws:
                                    try:
                                        cell = ws.find(str(row["ID"]), in_column=1)
                                        if cell:
                                            sheet_row = cell.row
                                            row_values = [str(edit_data.get(col, "")) for col in SHEET_COLUMNS]
                                            ws.update(f"A{sheet_row}:{chr(64+len(SHEET_COLUMNS))}{sheet_row}", [row_values])
                                            invalidate_cache()
                                            st.success("✅ Oferta actualizada.")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")

                    with sub_tabs[1]:
                        st.warning(f"⚠️ ¿Eliminar **{row.get('Título','')}**? Esta acción no se puede deshacer.")
                        confirm = st.checkbox("Confirmar eliminación", key=f"confirm_del_{idx}")
                        if confirm:
                            if st.button("🗑️ Eliminar definitivamente", key=f"del_{idx}", type="primary"):
                                with st.spinner("Eliminando..."):
                                    ok = delete_offer(str(row["ID"]))
                                if ok:
                                    st.success("✅ Oferta eliminada.")
                                    st.rerun()
                                else:
                                    st.error("No se pudo eliminar.")


# ─────────────────────────────────────────────
# AUTENTICACIÓN ADMIN
# ─────────────────────────────────────────────
def login_screen():
    st.markdown("""
    <style>
    .login-card {
        max-width: 380px;
        margin: 4rem auto;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 2.5rem 2rem;
        text-align: center;
    }
    .login-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
    .login-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.25rem; font-weight: 700;
        color: #F9FAFB; margin-bottom: 0.25rem;
    }
    .login-sub { font-size: 0.8rem; color: #6B7280; margin-bottom: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-card">
        <div class="login-icon">🔒</div>
        <div class="login-title">Acceso Admin</div>
        <div class="login-sub">Neuquén Labora · Panel de gestión</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        usuario = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        submit = st.form_submit_button("Ingresar", use_container_width=True)

    if submit:
        admin_user = st.secrets.get("admin", {}).get("username", "admin")
        admin_pass = st.secrets.get("admin", {}).get("password", "")
        if usuario == admin_user and password == admin_pass:
            st.session_state["admin_logged"] = True
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos.")


# ─────────────────────────────────────────────
# NAVEGACIÓN PRINCIPAL
# ─────────────────────────────────────────────
def main():
    inject_css()

    # Parámetro de URL para acceder al admin: ?page=admin
    params = st.query_params
    page = params.get("page", "public")

    if page == "admin":
        if not st.session_state.get("admin_logged"):
            login_screen()
        else:
            # Botón de logout en sidebar
            with st.sidebar:
                st.markdown("### ⚙️ Admin")
                if st.button("🚪 Cerrar sesión"):
                    st.session_state["admin_logged"] = False
                    st.rerun()
                if st.button("👁️ Ver sitio público"):
                    st.query_params["page"] = "public"
                    st.rerun()
            page_admin()
    else:
        # Link al admin en sidebar (oculto)
        with st.sidebar:
            st.markdown("### 💼 Neuquén Labora")
            st.caption("Plataforma de empleos para la región del Comahue")
            st.markdown("---")
            if st.button("⚙️ Administración"):
                st.query_params["page"] = "admin"
                st.rerun()
        page_public()


if __name__ == "__main__":
    main()
