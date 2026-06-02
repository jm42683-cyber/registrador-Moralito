import streamlit as st
import datetime
import pandas as pd
import pytz

# Configuración de página
st.set_page_config(page_title="Registrador Moralito", page_icon="🎙️", layout="wide")

# Zona horaria de Salta
tz = pytz.timezone('America/Argentina/Salta')

st.title("🎙️ Registrador Moralito por Voz")
st.write("Sistema inteligente de registro histórico y cálculo automático de tiempos muertos.")

if 'historial' not in st.session_state:
    st.session_state.historial = []

# --- SECCIÓN 1: INGRESO DE DATOS ---
st.subheader("📝 1. Dictá o escribí la novedad")
entrada = st.text_input("Presioná el micrófono de tu teclado para dictar:", placeholder="Ej: Bomba 3410 01 paro por cambio de sello")

col1, col2, col3 = st.columns(3)
with col1: btn_guardar = st.button("💾 Registrar Evento")
with col2: btn_deshacer = st.button("↩️ Borrar Último")
with col3: btn_limpiar = st.button("🗑️ Vaciar Historial Completo")

if btn_limpiar:
    st.session_state.historial = []
    st.rerun()

if btn_deshacer and st.session_state.historial:
    st.session_state.historial.pop()
    st.rerun()

if btn_guardar and entrada:
    ahora = datetime.datetime.now(tz)
    texto_min = entrada.lower().replace("ó", "o").replace("á", "a").replace("í", "i").replace("é", "e")
    
    evento = "REPARACION / OTRO"
    if any(p in texto_min for p in ["paro", "detuvo", "parada", "corte"]): evento = "PARADA"
    elif any(a in texto_min for a in ["arranco", "inicio", "marcha", "arranque"]): evento = "ARRANQUE"
        
    palabras = entrada.split()
    equipo_detected = "General"
    palabras_min = texto_min.split()
    indice_corte = len(palabras)
    for i, p in enumerate(palabras_min):
        if p in ["paro", "detuvo", "parada", "arranco", "inicio", "marcha", "en", "por"]:
            indice_corte = i; break
            
    equipo_detected = " ".join(palabras[:indice_corte]).strip(",. ") if indice_corte > 0 else palabras[0]

    st.session_state.historial.append({
        "Fecha": ahora.strftime("%d/%m/%Y"),
        "Hora": ahora.strftime("%H:%M:%S"),
        "Objeto_Tiempo": ahora,
        "Equipo": equipo_detected.upper(),
        "Acción": evento,
        "Detalle": entrada
    })
    st.success(f"¡Registrado '{equipo_detected.upper()}'!")

# --- SECCIÓN 2: BUSCADOR Y EDITOR ---
if st.session_state.historial:
    df = pd.DataFrame(st.session_state.historial)
    st.write("---")
    st.subheader("🔍 2. Buscador y Editor de Histórico")
    
    filtro = st.text_input("Filtrar por nombre de equipo:")
    
    # Filtrar
    df_mostrar = df[df['Equipo'].str.contains(filtro, case=False, na=False)] if filtro else df
    
    # Editor interactivo
    df_editado = st.data_editor(
        df_mostrar.sort_values("Objeto_Tiempo", ascending=False),
        column_config={"Acción": st.column_config.SelectboxColumn("Acción", options=["ARRANQUE", "PARADA", "REPARACION / OTRO"])},
        use_container_width=True
    )

    # --- SECCIÓN 3: TIEMPOS MUERTOS ---
    st.write("---")
    st.subheader("⏳ 3. Tiempos Muertos Automatizados")
    for eq in df['Equipo'].unique():
        if eq == "GENERAL": continue
        df_eq = df[df['Equipo'] == eq].sort_values(by="Objeto_Tiempo")
        parada_detectada = None
        for idx, row in df_eq.iterrows():
            if row['Acción'] == "PARADA": parada_detectada = row['Objeto_Tiempo']
            elif row['Acción'] == "ARRANQUE" and parada_detectada:
                diff = row['Objeto_Tiempo'] - parada_detectada
                st.error(f"🔴 **{eq}** parado el {parada_detectada.strftime('%d/%m')} de {parada_detectada.strftime('%H:%M')} a {row['Objeto_Tiempo'].strftime('%H:%M')} (Total: {int(diff.total_seconds()/60)} min.)")
                parada_detectada = None
