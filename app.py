import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
import urllib.parse
from streamlit_gsheets import GSheetsConnection

# Librerías para armar el PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuración de zona horaria de Salta/Argentina
argentina_tz = pytz.timezone('America/Argentina/Salta')

st.set_page_config(page_title="Registrador Moralito", layout="wide")
st.title("📊 Registrador Moralito - Gestión de Planta")

# Conectar con Google Sheets (Base de datos general permanente)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_global = conn.read(ttl="0m")
except:
    df_global = pd.DataFrame(columns=['Fecha', 'Hora', 'Objeto_Tiempo', 'Equipo', 'Acción', 'Detalle'])

# --- CONTROL DE TURNO LOCAL (Para los muchachos) ---
if 'turno_data' not in st.session_state:
    st.session_state.turno_data = pd.DataFrame(columns=['Fecha', 'Hora', 'Objeto_Tiempo', 'Equipo', 'Acción', 'Detalle'])

# --- 1. REGISTRO DE EVENTOS ---
st.header("🎙️ 1. Registrar Evento del Turno (Voz o Texto)")
entrada = st.text_input("Dictá o escribí lo que pasó en este turno:")

if st.button("Guardar Registro") and entrada:
    ahora = datetime.now(argentina_tz)
    fecha_str = ahora.strftime('%d/%m/%Y')
    hora_str = ahora.strftime('%H:%M:%S')
    timestamp = ahora.isoformat()
    
    entrada_minuscula = entrada.lower()
    
    # Identificación Inteligente y Ultra-Flexible de Equipo
    if "clarif" in entrada_minuscula:
        equipo = "CLARIFICADOR"
    elif any(p in entrada_minuscula for p in ['bomb', 'bonb', '3410', 'bomba']):
        equipo = "BOMBA 3410 01"
    else:
        equipo = "GENERAL"
        
    # Identificación Inteligente de Acción (Fijate que ahora lee march, marcha, arranque, par, deteni, etc)
    if any(p in entrada_minuscula for p in ['par', 'deten', 'detuv', 'falla', 'corte', 'stop', 'romp', 'parada']):
        accion = 'PARADA'
    elif any(p in entrada_minuscula for p in ['arranc', 'march', 'inic', 'ok', 'run', 'gcha', 'vuelv', 'alta', 'arranque']):
        accion = 'ARRANQUE'
    else:
        accion = 'REPARACION / OTRO'
            
    nueva_fila = pd.DataFrame([{
        'Fecha': fecha_str,
        'Hora': hora_str,
        'Objeto_Tiempo': timestamp,
        'Equipo': equipo,
        'Acción': accion,
        'Detalle': entrada.upper()
    }])
    
    # Guardar local y en la nube
    st.session_state.turno_data = pd.concat([nueva_fila, st.session_state.turno_data], ignore_index=True)
    df_total_sheets = pd.concat([df_global, nueva_fila], ignore_index=True)
    try:
        conn.update(data=df_total_sheets)
        st.success(f"✅ Guardado: {equipo} -> {accion}")
    except:
        st.warning(f"⚠️ Guardado en el turno. Revisar configuración de Secrets.")

# --- 2. HISTORIAL VISIBLE DEL TURNO ---
st.header("🔍 2. Historial del Turno Actual")
st.info("💡 Muchachos: Acá ven y editan SOLO lo que cargaron en este turno.")

st.session_state.turno_data = st.data_editor(st.session_state.turno_data, num_rows="dynamic", use_container_width=True)

# --- 3. CIERRE DE TURNO: REPORTE PDF Y WHATSAPP ---
st.write("---")
st.header("📋 3. Cierre de Turno e Informe PDF")

if not st.session_state.turno_data.empty:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1E3A8A'), spaceAfter=10)
    texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=10, leading=14)
    
    fecha_hoy = datetime.now(argentina_tz).strftime('%d/%m/%Y')
    story.append(Paragraph(f"<b>REPORTE DE NOVEDADES DE PLANTA - REGISTRADOR MORALITO</b>", titulo_style))
    story.append(Paragraph(f"<b>Fecha de Emisión:</b> {fecha_hoy} | <b>Generado al cierre del turno</b>", texto_style))
    story.append(Spacer(1, 15))
    
    tabla_datos = [["Fecha", "Hora", "Equipo", "Acción", "Detalle"]]
    for _, fila in st.session_state.turno_data.sort_values(by='Hora').iterrows():
        tabla_datos.append([
            fila['Fecha'],
            fila['Hora'],
            fila['Equipo'],
            fila['Acción'],
            Paragraph(str(fila['Detalle']), texto_style)
        ])
    
    t = Table(tabla_datos, colWidths=[60, 50, 100, 80, 260])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)
    doc.build(story)
    pdf_data = buffer.getvalue()
    
    st.download_button(
        label="📥 1º DESCARGAR REPORTE PDF",
        data=pdf_data,
        file_name=f"Reporte_Turno_{datetime.now(argentina_tz).strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf"
    )
    
    texto_whatsapp = f"Hola Jorge, acá te mando el Reporte en PDF del cierre de turno de hoy ({fecha_hoy}). Ya lo descargué a mi teléfono."
    texto_codificado = urllib.parse.quote(texto_whatsapp)
    url_wa = f"https://wa.me/5493875043818?text={texto_codificado}"
    
    st.markdown(f'<a href="{url_wa}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;font-weight:bold;margin-top:10px;">📲 2º ENVIAR REPORTE POR WHATSAPP</button></a>', unsafe_allow_index=True)
else:
    st.info("No hay datos cargados en este turno para generar reportes.")

# --- 4. SECCIÓN EXCLUSIVA JORGE (ADMINISTRADOR) ---
st.write("---")
st.sidebar.header("🔑 Zona de Control (Jorge)")
clave = st.sidebar.text_input("Contraseña de Supervisor:", type="password")

if clave == "4268":
    st.header("👑 4. Panel de Control General (Historial Acumulado Completo)")
    st.success("Acceso Supervisor concedido.")
    
    df_editado_global = st.data_editor(df_global, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios Globales en Google Sheets"):
        conn.update(data=df_editado_global)
        st.success("¡Base de datos global actualizada en la nube!")
