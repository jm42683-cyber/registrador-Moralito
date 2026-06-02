import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# Configuración de zona horaria de Salta/Argentina
argentina_tz = pytz.timezone('America/Argentina/Salta')

st.set_page_config(page_title="Registrador Moralito", layout="wide")

st.title("📊 Registrador Moralito - Planta")

# Inicializar base de datos en la sesión
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Fecha', 'Hora', 'Objeto_Tiempo', 'Equipo', 'Acción', 'Detalle'])

# --- 1. REGISTRO DE EVENTOS ---
st.header("🎙️ 1. Registrar Evento (Voz o Texto)")
entrada = st.text_input("Dictá o escribí lo que pasó (Ej: clarificador detuvo por falla, bomba 3410 arranco):")

if st.button("Guardar Registro") and entrada:
    ahora = datetime.now(argentina_tz)
    fecha_str = ahora.strftime('%d/%m/%Y')
    hora_str = ahora.strftime('%H:%M:%S')
    timestamp = ahora.isoformat()
    
    entrada_minuscula = entrada.lower()
    
    # Lógica inteligente de detección de Acción
    if any(palabra in entrada_minuscula for palabra in ['par', 'deten', 'detuv', 'falla', 'corte', 'stop']):
        accion = 'PARADA'
    elif any(palabra in entrada_minuscula for palabra in ['arranc', 'march', 'inic', 'ok', 'run', 'gcha']):
        accion = 'ARRANQUE'
    else:
        accion = 'REPARACION / OTRO'
        
    # Limpieza inteligente del nombre del Equipo
    equipo = "GENERAL"
    if "clarif" in entrada_minuscula:
        equipo = "CLARIFICADOR"
    elif "bomba" in entrada_minuscula:
        if "3410" in entrada_minuscula:
            equipo = "BOMBA 3410"
        else:
            equipo = "BOMBA GENERAL"
            
    # Agregar a la tabla al principio (más nuevo primero)
    nueva_fila = pd.DataFrame([{
        'Fecha': fecha_str,
        'Hora': hora_str,
        'Objeto_Tiempo': timestamp,
        'Equipo': equipo,
        'Acción': accion,
        'Detalle': entrada.upper()
    }])
    
    st.session_state.data = pd.concat([nueva_fila, st.session_state.data], ignore_index=True)
    st.success(f"Entendido: guardado como {accion} para el equipo {equipo}")

# --- 2. EDITOR EN VIVO Y BORRADO ---
st.header("🔍 2. Buscador y Editor de Histórico")
st.info("💡 Cómo borrar una fila: Hacé clic en la casilla de la izquierda de la fila (el índice) para seleccionarla y presioná la tecla 'Supr' (Delete) en tu teclado.")

# El editor ahora permite borrar filas dinámicamente
st.session_state.data = st.data_editor(
    st.session_state.data, 
    num_rows="dynamic",
    use_container_width=True
)

# --- 3. TIEMPOS MUERTOS AUTOMÁTICOS ---
st.header("⏳ 3. Tiempos Muertos Automatizados")

df_tiempos = st.session_state.data.copy()
if not df_tiempos.empty and len(df_tiempos) > 1:
    # Ordenar cronológicamente para procesar correctamente las diferencias
    df_tiempos = df_tiempos.sort_values(by='Objeto_Tiempo', ascending=True)
    
    reporte_tiempos = []
    
    # Procesar por cada equipo por separado
    for equipo_nom, grupo in df_tiempos.groupby('Equipo'):
        ultima_parada = None
        
        for idx, fila in grupo.iterrows():
            if fila['Acción'] == 'PARADA':
                ultima_parada = fila['Objeto_Tiempo']
            elif fila['Acción'] == 'ARRANQUE' and ultima_parada is not None:
                # Calcular la diferencia real
                t_parada = datetime.fromisoformat(ultima_parada)
                t_arranque = datetime.fromisoformat(fila['Objeto_Tiempo'])
                
                duracion = t_arranque - t_parada
                minutos_muertos = round(duracion.total_seconds() / 60, 2)
                
                if minutos_muertos >= 0:
                    reporte_tiempos.append({
                        'Equipo': equipo_nom,
                        'Desde (Parada)': t_parada.strftime('%H:%M:%S'),
                        'Hasta (Arranque)': t_arranque.strftime('%H:%M:%S'),
                        'Duración (Minutos)': minutos_muertos
                    })
                ultima_parada = None # Resetear ciclo para la siguiente parada
                
    if reporte_tiempos:
        st.dataframe(pd.DataFrame(reporte_tiempos), use_container_width=True)
    else:
        st.info("No hay ciclos completos de 'PARADA' y 'ARRANQUE' válidos para el mismo equipo.")
else:
    st.info("Esperando registros suficientes para calcular tiempos muertos.")
