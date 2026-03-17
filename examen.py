import streamlit as st
import random
import pandas as pd
import PyPDF2
import google.generativeai as genai
import re
from io import BytesIO
from datetime import datetime, timedelta
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIGURACIÓN DE IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró la configuración de la API Key en los secretos.")
model = genai.GenerativeModel('gemini-3-flash-preview')

st.set_page_config(page_title="NeuralExam Pro v3.1", page_icon="🧠", layout="wide")

# --- 2. BÚNKER DE MEMORIA ---
if 'auth_docente' not in st.session_state:
    st.session_state.update({
        'auth_docente': False, 
        'examen_activo': False, 
        'preguntas_seleccionadas': [],
        'lista_results': [], 
        'correos_usados': [], 
        'examen_cerrado_global': False, 
        'revelar_notas': False,
        'pool_ia': [], 
        'pool_manual': [], 
        'lista_blanca': {}, 
        'modo_acceso': "Abierto (Cualquiera)",
        'feedbacks_privados': {},
        'alumno_actual_correo': "",
        'hora_inicio': None,
        'duracion_minutos': 30,
        'usar_tiempo': False
    })

# --- 3. BANCO COMPLETO ---
BANCO = {
    "Español": [
        "¿Qué es un ensayo y cuál es su estructura principal?", "Define qué es una ficha de trabajo y para qué sirve.",
        "Explica la diferencia entre lenguaje formal e informal.", "¿Qué es una antología y para qué se realiza?",
        "Define qué es un poema y menciona tres de sus elementos.", "¿Qué es una biografía y en qué se diferencia de una autobiografía?",
        "Explica la función de las oraciones principales y secundarias en un párrafo.", "¿Para qué sirven las comillas en un texto?",
        "Qué es un reporte de encuesta y qué partes lo integran?", "Define qué es un programa de radio y cuál es la función del guion.",
        "¿Qué es el Renacimiento y cómo influyó en la literatura?", "Explica qué es un caligrama.",
        "¿Qué es una mesa redonda y quiénes participan en ella?", "Define qué es el modo imperativo y da un ejemplo.",
        "¿Qué es la publicidad y cuál es su objetivo principal?"
    ],
    "Ciencias (Química)": [
        "¿Qué es la tabla periódica y cómo se organizan los elementos?", "Explica qué es una mezcla homogénea y da un ejemplo.",
        "¿Qué sucede con las moléculas de agua cuando pasan de líquido a gas?", "¿Qué es un enlace químico y cuáles son los tipos principales?",
        "Define qué es la masa y qué es el volumen.", "¿Qué es una reacción química y cómo se representa?",
        "Explica la Ley de Conservación de la Materia de Lavoisier.", "¿Qué es un átomo y cuáles son sus partículas subatómicas?",
        "¿Cuál es la diferencia entre un elemento y un compuesto?", "¿Qué es el pH y qué mide la escala?",
        "Explica qué es un catalizador.", "¿Qué es la energía cinética?",
        "Define qué es un modelo atómico y menciona uno (ej. Bohr).", "¿Cómo se diferencia un ácido de una base?",
        "¿Qué es la oxidación? Da un ejemplo de la vida cotidiana."
    ],
    "Matemáticas": [
        "Resuelve 3x - 5 = 10. Explica paso a paso cómo despejaste la X.", "¿Cómo se calcula el área de un círculo? Escribe la fórmula y un ejemplo.",
        "Un coche recorre 120km en 2 horas, ¿cuál es su velocidad media?", "¿Qué es el Teorema de Pitágoras y para qué sirve?",
        "Si un pantalón cuesta $500 y tiene el 20% de descuento, ¿cuánto pagaré?", "Resuelve la operación: (5 + 3) * 2 - 4. Explica el orden.",
        "¿Qué es una sucesión numérica y cómo se encuentra el siguiente término?", "Define qué es un ángulo agudo, recto y obtuso.",
        "¿Cómo se calcula el volumen de un cubo de 4cm de lado?", "Si tengo 3 canicas rojas y 2 azules, ¿cual es la probabilidad de sacar roja?",
        "¿Qué es una gráfica de barras y para qué se utiliza?", "Resuelve: 2x + 8 = 20. Describe los pasos.",
        "¿Qué es el máximo común divisor (MCD)?", "Explica cómo se suman dos fracciones con diferente denominador.",
        "¿Qué es el perímetro y cómo se calcula en un rectángulo?"
    ],
    "Geografía": [
        "¿Qué son las coordenadas geográficas (latitud y longitud)?", "Explica qué es el ciclo del agua y su importancia.",
        "Menciona las capas internas de la Tierra y describe una.", "¿Qué es el relieve y menciona dos tipos de formaciones?",
        "Explica la diferencia entre clima y estado del tiempo.", "¿Qué es la migración y cuáles son sus causas principales?",
        "Define qué es la biodiversidad.", "¿Qué son los recursos naturales renovables y no renovables?",
        "Explica qué es el efecto invernadero.", "¿Qué es la globalización y cómo afecta a la cultura?",
        "Menciona los tres tipos de límites de las placas tectónicas.", "¿Qué es una cuenca hídrica?",
        "¿Cuál es la función de los mapas y qué elementos deben tener?", "Explica qué es la densidad de población.",
        "¿Qué son las actividades económicas primarias? Da ejemplos."
    ]
}

def main():
    # --- 1. LOGO Y ESTILOS DE ANIMACIÓN ---
    izq, centro, der = st.columns([2, 1, 2])
    with centro:
        st.markdown("""
            <div style="text-align: center; margin-bottom: -15px;">
                <div class="logo-neural">🧠</div>
            </div>
            <style>
                .logo-neural {
                    font-size: 80px;
                    filter: drop-shadow(0 0 15px #58a6ff);
                    animation: pulse 2.5s infinite ease-in-out;
                }
                @keyframes pulse {
                    0% { transform: scale(1); filter: drop-shadow(0 0 10px #58a6ff); }
                    50% { transform: scale(1.1); filter: drop-shadow(0 0 25px #bc8cff); }
                    100% { transform: scale(1); filter: drop-shadow(0 0 10px #58a6ff); }
                }
            </style>
        """, unsafe_allow_html=True)

    # --- 2. DISEÑO CYBERPUNK CON SCANLINES Y BARRA DE ESTADO ---
    st.markdown("""
        <style>
        /* FONDO CON TEXTURA DE MONITOR CRT */
        .stApp {
            background-color: #030303 !important;
            background-image: 
                linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03)),
                radial-gradient(circle at center, #001a33 0%, #030303 100%) !important;
            background-size: 100% 3px, 2px 100%, 100% 100% !important;
            background-attachment: fixed !important;
        }

        /* BARRA DE ESTADO */
        .status-bar {
            display: flex;
            justify-content: space-around;
            background: rgba(88, 166, 255, 0.05);
            border: 1px solid rgba(88, 166, 255, 0.2);
            border-radius: 4px;
            padding: 4px;
            margin: 10px auto 25px auto;
            max-width: 850px;
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            color: #58a6ff;
        }
        .online-dot {
            height: 7px; width: 7px; background-color: #00ff41;
            border-radius: 50%; display: inline-block;
            margin-right: 5px; animation: blink 1.2s infinite;
        }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }

        .titulo-cyber {
            background: linear-gradient(90deg, #58a6ff, #bc8cff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 3.5rem; font-weight: 800; text-align: center;
            text-shadow: 0 0 20px rgba(88, 166, 255, 0.4);
            margin-bottom: 0px;
        }
        
        /* Efecto Glitch al pasar el mouse por botones */
        div.stButton > button:hover {
            box-shadow: 0 0 20px #58a6ff !important;
            transform: skewX(-3deg);
            transition: 0.1s;
        }

        [data-testid="stSidebar"] { display: none !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 20px; justify-content: center; }
        .stTabs [data-baseweb="tab"] { background-color: #161b22 !important; color: white !important; border-radius: 8px 8px 0 0 !important; }
        .stTabs [aria-selected="true"] { background-color: #58a6ff !important; color: #030303 !important; }
        header {visibility: hidden;} footer {visibility: hidden;}
        </style>

        <h1 class="titulo-cyber">NEURAL EXAM PRO</h1>
        
        <div class="status-bar">
            <span><span class="online-dot"></span> 📡 NODE-IA: ONLINE</span>
            <span>🕒 SYS-TIME: """ + datetime.now().strftime("%H:%M") + """</span>
            <span>🔋 PWR: 98% [AC-CONN]</span>
            <span>🌐 LATENCY: 14ms</span>
        </div>

        <p style="text-align:center; color:#8b949e; margin-bottom:40px; font-family:monospace; font-size: 0.9rem;">
            > ACCESO_AUTORIZADO: VERSIÓN_2026.4.1<br>
            > USER_ID: DOCENTE_ROOT
        </p>
    """, unsafe_allow_html=True)

    # --- 5. INTERFAZ POR PESTAÑAS (TABS) ---
    tab_alumno, tab_docente = st.tabs(["🎓 PORTAL ALUMNO", "🛡️ PANEL DOCENTE"])

    with tab_alumno:
        # --- TÍTULO ESTILO TERMINAL ---
        st.markdown('<h2 style="color: #58a6ff; font-family: monospace; letter-spacing: 2px;">⚡ TERMINAL_ESTUDIANTE</h2>', unsafe_allow_html=True)
        
        tiempo_agotado = False
        if st.session_state.examen_activo and st.session_state.hora_inicio and st.session_state.usar_tiempo:
            limite = st.session_state.hora_inicio + timedelta(minutes=st.session_state.duracion_minutos)
            restante = limite - datetime.now()
            
            if restante.total_seconds() <= 0: 
                tiempo_agotado = True
            else: 
                # --- CRONÓMETRO CON ESTILO NEÓN ---
                st.markdown(f"""
                    <div style="background: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; padding: 10px; border-radius: 5px; text-align: center; font-family: monospace; color: #ff4b4b; text-shadow: 0 0 10px #ff4b4b;">
                        ⚠️ TIEMPO_RESTANTE: {int(restante.total_seconds()//60):02d}:{int(restante.total_seconds()%60):02d}
                    </div>
                    <br>
                """, unsafe_allow_html=True)

        if st.session_state.examen_cerrado_global or tiempo_agotado:
            st.error("🔒 El examen ha concluido.")
        elif st.session_state.examen_activo:
            c_in = st.text_input("Tu Correo:", key="input_correo").lower().strip()
            n_in = st.text_input("Tu Nombre Completo:", key="input_nombre")
            
            if c_in in st.session_state.correos_usados:
                st.info("Tu examen ya ha sido enviado.")
                if st.session_state.revelar_notas: st.markdown(st.session_state.feedbacks_privados.get(c_in, ""))
            else:
                acceso = False
                if st.session_state.modo_acceso == "Abierto (Cualquiera)":
                    if c_in and n_in: acceso = True
                elif c_in in st.session_state.lista_blanca:
                    nom_reg = str(st.session_state.lista_blanca[c_in]).lower().strip()
                    if n_in.lower().strip() == nom_reg: acceso = True
                    elif n_in: st.error("El nombre no coincide con el registro.")
                
                if acceso:
                    respuestas = []
                    for i, p in enumerate(st.session_state.preguntas_seleccionadas):
                        # --- IMPLEMENTACIÓN DE MICRO + TEXTO ---
                        st.markdown(f"**{i+1}. {p}**")
                        col_txt, col_mic = st.columns([0.85, 0.15])
                        transcription = ""
                        
                        with col_mic:
                            audio_data = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key=f"mic_{i}")
                            if audio_data:
                                try:
                                    r = sr.Recognizer()
                                    with BytesIO(audio_data['bytes']) as f:
                                        with sr.AudioFile(f) as source:
                                            audio_captured = r.record(source)
                                            transcription = r.recognize_google(audio_captured, language="es-MX")
                                except:
                                    st.error("Error de audio.")

                        with col_txt:
                            r_text = st.text_area(f"Respuesta {i+1}:", value=transcription, key=f"ans_{c_in}_{i}", label_visibility="collapsed")
                        respuestas.append(r_text)

                    if st.button("🚀 ENVIAR RESPUESTAS"):
                        if all(r.strip() != "" for r in respuestas):
                            with st.spinner("IA Analizando respuestas..."):
                                raw = "\n".join([f"P: {p} | R: {r}" for p, r in zip(st.session_state.preguntas_seleccionadas, respuestas)])
                                calif = model.generate_content(f"Nota 0-100. Termina con NOTA_NUMERICA: X\n{raw}").text
                                nota = re.search(r"NOTA_NUMERICA:\s*(\d+)", calif)
                                reg = {"Nombre": n_in.title(), "Correo": c_in, "Calificación": nota.group(1) if nota else "0"}
                                for idx, r in enumerate(respuestas): reg[f"Pregunta {idx+1}"] = r
                                st.session_state.lista_results.append(reg)
                                st.session_state.correos_usados.append(c_in)
                                st.session_state.feedbacks_privados[c_in] = calif
                                st.success("¡Enviado con éxito!"); st.rerun()
                        else: st.error("Por favor responde todas las preguntas.")
        else:
            st.warning("📡 No hay ningún examen activo en este momento.")

    with tab_docente:
        st.header("👨‍🏫 Panel de Gestión Docente")
        if not st.session_state.auth_docente:
            if st.text_input("Llave Maestra:", type="password", key="llave_docente") == "profe2026": 
                st.session_state.auth_docente = True; st.rerun()
        
        if st.session_state.auth_docente:
            st.subheader("👥 Control de Alumnos")
            st.session_state.modo_acceso = st.radio("Configuración de Acceso:", ["Abierto (Cualquiera)", "Lista Blanca (Excel/Manual)"])
            
            if st.session_state.modo_acceso == "Lista Blanca (Excel/Manual)":
                c1, c2 = st.columns(2)
                with c1:
                    n_m = st.text_input("Nombre:")
                    c_m = st.text_input("Correo:").lower().strip()
                    if st.button("➕ Registrar Alumno"): 
                        st.session_state.lista_blanca[c_m] = n_m.strip()
                        st.success("Registrado.")
                with c2:
                    f_a = st.file_uploader("Cargar Alumnos (.xlsx):", type=["xlsx"])
                    if f_a:
                        df_a = pd.read_excel(f_a)
                        for _, f in df_a.iterrows(): 
                            st.session_state.lista_blanca[str(f['Correo']).lower().strip()] = str(f['Nombre']).strip()
                        st.success("Lista cargada.")

            st.divider()
            st.subheader("🕒 Tiempo y Resultados")
            st.session_state.usar_tiempo = st.toggle("Habilitar Cronómetro", value=st.session_state.usar_tiempo)
            if st.session_state.usar_tiempo:
                st.session_state.duracion_minutos = st.select_slider("Duración (Min):", options=[30, 45, 60], value=st.session_state.duracion_minutos)
            
            if st.session_state.examen_activo:
                if st.button("🛑 CERRAR EXAMEN AHORA"):
                    st.session_state.examen_cerrado_global = True
                    st.session_state.examen_activo = False; st.rerun()

            st.session_state.revelar_notas = st.toggle("🔓 Revelar Calificaciones a Alumnos", value=st.session_state.revelar_notas)
            
            st.divider()
            st.subheader("📝 Creación de Examen")
            modo = st.radio("Origen de preguntas:", ["Banco de 60 Preguntas", "Texto Manual", "Generar desde PDF"])
            pool_final = []

            if modo == "Banco de 60 Preguntas":
                mats = st.multiselect("Materias (Español, Química, Mates, Geografía):", list(BANCO.keys()))
                for m in mats: pool_final.extend(BANCO[m])
            elif modo == "Texto Manual":
                t_area = st.text_area("Escribe una pregunta por línea:", height=150)
                if st.button("💾 Guardar Manuales"):
                    st.session_state.pool_manual = [p.strip() for p in t_area.split('\n') if len(p.strip()) > 3]
                pool_final = st.session_state.pool_manual
            elif modo == "Generar desde PDF":
                arc = st.file_uploader("Subir PDF:", type=["pdf"])
                if arc and st.button("🤖 IA: Generar"):
                    reader = PyPDF2.PdfReader(arc)
                    texto = "".join([p.extract_text() for p in reader.pages])
                    res = model.generate_content(f"Genera 10 preguntas sobre: {texto[:4000]}. Una por línea.").text
                    
                    # --- LIMPIEZA DE NÚMEROS REPETIDOS ---
                    lineas = [p.strip() for p in res.split('\n') if len(p.strip()) > 10]
                    # Esta línea quita cualquier número o símbolo al inicio de la pregunta (ej: "1.- ", "2. ")
                    st.session_state.pool_ia = [re.sub(r'^[\d\s\.\-\)\(]+', '', p) for p in lineas]
                    
                pool_final = st.session_state.pool_ia

            if st.button("🚀 LANZAR EXAMEN A LOS ALUMNOS"):
                if pool_final:
                    st.session_state.preguntas_seleccionadas = random.sample(pool_final, min(len(pool_final), 10))
                    st.session_state.examen_activo, st.session_state.examen_cerrado_global = True, False
                    st.session_state.hora_inicio = datetime.now(); st.balloons()
                else: st.warning("El pool de preguntas está vacío.")

            if st.session_state.lista_results:
                st.subheader("📊 Reporte de Resultados")
                df = pd.DataFrame(st.session_state.lista_results)
                st.dataframe(df)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
                st.download_button("📥 Descargar Excel", data=output.getvalue(), file_name="Resultados_Examen.xlsx")
            
            if st.button("⚠️ REINICIAR TODO EL SISTEMA"):
                st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()