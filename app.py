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
entrada = st.text_input("Dictá o escribí lo que pasó:")

if st.button("Guardar Registro") and entrada:
    ahora = datetime.now(argentina_tz)
    fecha_str = ahora.strftime('%d/%m/%Y')
    hora_str = ahora.strftime('%H:%M:%S')
    timestamp = ahora.isoformat()
    
    entrada_minuscula = entrada.lower()
    
    # 1. Identificación flexible del EQUIPO (Cubre errores como 'bonba')
    if "clarif" in entrada_minuscula:
        equipo = "CLARIFICADOR"
    elif "bomb" in entrada_minuscula or "bonb" in entrada_minuscula or "3410" in entrada_minuscula:
        equipo = "BOMBA 3410 01"
    else:
        equipo = "GENERAL"
        
    # 2. Identificación ultra flexible de la ACCIÓN
    if any(p in entrada_minuscula for p in ['par', 'deten', 'detuv', 'falla', 'corte', 'stop', 'romp']):
        accion = 'PARADA'
    elif any(p in entrada_minuscula for p in ['arranc', 'march', 'inic', 'ok', 'run', 'gcha', 'vuelv', 'alta']):
        accion = 'ARRANQUE'
    else:
        accion = 'REPARACION / OTRO'
            
    # Agregar a la tabla al principio
    nueva_fila = pd.DataFrame([{
        'Fecha': fecha_str,
        'Hora': hora_str,
        'Objeto_Tiempo': timestamp,
        'Equipo': equipo,
        'Acción': accion,
        'Detalle': entrada.upper()
    }])
    
    st.session_state.data = pd.concat([nueva_fila, st.session_state.data], ignore_index=True)
    st.success(f"Registrado: {equipo} -> {accion}")

# --- 2. EDITOR EN VIVO ---
st.header("🔍 2. Buscador y Editor de Histórico")
st.info("💡 Para borrar filas viejas que traban el cálculo: Selecciona el número de la fila a la izquierda y presiona 'Supr' o 'Delete' en tu teclado.")
st.session_state.data = st.data_editor(st.session_state.data, num_rows="dynamic", use_container_width=True)

# --- 3. TIEMPOS MUERTOS AUTOMÁTICOS ---
st.header("⏳ 3. Tiempos Muertos Automatizados")

df_tiempos = st.session_state.data.copy()
if not df_tiempos.empty and len(df_tiempos) > 1:
    # Ordenar cronológicamente para calcular la diferencia de tiempos
    df_tiempos = df_tiempos.sort_values(by='Objeto_Tiempo', ascending=True)
    
    reporte_tiempos = []
    
    # Agrupar por equipo para no mezclar peras con manzanas
    for equipo_nom, grupo in df_tiempos.groupby('Equipo'):
        if equipo_nom == "GENERAL":
            continue
            
        ultima_parada = None
        for idx, fila in grupo.iterrows():
            # Si encontramos una parada, guardamos el momento
            if fila['Acción'] == 'PARADA':
                ultima_parada = fila['Objeto_Tiempo']
            # Si encontramos un arranque y teníamos una parada previa, calculamos el tiempo muerto
            elif (fila['Acción'] == 'ARRANQUE' or fila['Acción'] == 'MARCHA') and ultima_parada is not None:
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
                ultima_parada = None # Limpiamos para el próximo ciclo
                
    if reporte_tiempos:
        st.dataframe(pd.DataFrame(reporte_tiempos), use_container_width=True)
    else:
        st.info("Esperando un ciclo completo de PARADA y ARRANQUE para el mismo equipo.")
else:
    st.info("Sin datos suficientes.")
