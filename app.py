import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from pymongo import MongoClient
from datetime import date

# =========================
# Configuracion inicial
# =========================
st.set_page_config(
    page_title="Panel Cloud de Citas Medicas",
    layout="wide"
)

st.title("Panel Cloud de Citas Medicas")
st.caption(
    "Prototipo academico con datos simulados. "
    "Integra citas y resumen clinico desde Supabase, y notas clinicas desde MongoDB Atlas."
)

# =========================
# Secrets
# =========================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MONGO_URI = st.secrets["MONGO_URI"]

# =========================
# Conexion a servicios cloud
# =========================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["health_cloud"]
notes_collection = mongo_db["clinical_notes"]

# =========================
# Cargar datos desde Supabase
# =========================
try:
    appointments_response = supabase.table("appointments").select("*").execute()
    patients_response = supabase.table("patients").select("*").execute()
    summary_response = supabase.table("clinical_summary").select("*").execute()

    appointments = pd.DataFrame(appointments_response.data)
    patients = pd.DataFrame(patients_response.data)
    clinical_summary = pd.DataFrame(summary_response.data)

except Exception as e:
    st.error("Error al conectar con Supabase.")
    st.exception(e)
    st.stop()

if appointments.empty or patients.empty:
    st.warning("No hay datos suficientes en Supabase.")
    st.stop()

# =========================
# Filtro de citas de hoy
# =========================
st.subheader("Citas programadas")

selected_date = st.date_input(
    "Fecha de citas",
    value=date.today()
)

appointments["appointment_date"] = pd.to_datetime(
    appointments["appointment_date"]
).dt.date

appointments_today = appointments[
    appointments["appointment_date"] == selected_date
].copy()

if appointments_today.empty:
    st.info("No hay citas para la fecha seleccionada. Se mostraran todas las citas registradas para fines de demostracion.")
    appointments_today = appointments.copy()

appointments_today["appointment_label"] = (
    appointments_today["appointment_code"] + " | " +
    appointments_today["appointment_time"].astype(str) + " | " +
    appointments_today["specialty"] + " | " +
    appointments_today["status"]
)

selected_appointment_label = st.selectbox(
    "Selecciona una cita programada",
    appointments_today["appointment_label"].tolist()
)

selected_appointment = appointments_today[
    appointments_today["appointment_label"] == selected_appointment_label
].iloc[0]

patient_code = selected_appointment["patient_code"]

selected_patient_df = patients[
    patients["patient_code"] == patient_code
]

if selected_patient_df.empty:
    st.error("No se encontro el paciente asociado a la cita.")
    st.stop()

selected_patient = selected_patient_df.iloc[0]

# =========================
# Informacion de la cita
# =========================
st.divider()
st.subheader("Informacion de la cita actual")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Codigo de cita", selected_appointment["appointment_code"])

with col2:
    st.metric("Hora", str(selected_appointment["appointment_time"]))

with col3:
    st.metric("Especialidad", selected_appointment["specialty"])

with col4:
    st.metric("Estado", selected_appointment["status"])

st.write("**Motivo de atencion:**", selected_appointment["reason"])

# =========================
# Datos del paciente
# =========================
st.subheader("Paciente asociado a la cita")

patient_view = pd.DataFrame([{
    "Codigo de paciente": selected_patient["patient_code"],
    "Nombre": selected_patient["full_name"],
    "Edad": selected_patient["age"],
    "Genero": selected_patient["gender"],
    "Distrito": selected_patient["district"],
    "Documento simulado": selected_patient["document_number"]
}])

st.dataframe(patient_view, use_container_width=True)

# =========================
# Resumen clinico desde Supabase
# =========================
st.subheader("Resumen clinico estructurado")

patient_summary = clinical_summary[
    clinical_summary["patient_code"] == patient_code
].copy()

if patient_summary.empty:
    st.info("No hay resumen clinico registrado para este paciente.")
else:
    patient_summary = patient_summary[
        ["diagnosis", "allergies", "medication", "last_visit", "risk_level"]
    ]

    patient_summary = patient_summary.rename(columns={
        "diagnosis": "Diagnostico",
        "allergies": "Alergias",
        "medication": "Medicacion",
        "last_visit": "Ultima visita",
        "risk_level": "Nivel de riesgo"
    })

    st.dataframe(patient_summary, use_container_width=True)

# =========================
# Notas clinicas desde MongoDB
# =========================
st.subheader("Notas clinicas externas desde MongoDB Atlas")

try:
    notes = list(notes_collection.find(
        {"patient_code": patient_code},
        {"_id": 0}
    ))

    if notes:
        notes_df = pd.DataFrame(notes)
        notes_df = notes_df.rename(columns={
            "patient_code": "Codigo de paciente",
            "source_platform": "Plataforma origen",
            "note_type": "Tipo de nota",
            "note": "Nota clinica",
            "created_at": "Fecha",
            "doctor_code": "Codigo medico",
            "priority": "Prioridad"
        })
        st.dataframe(notes_df, use_container_width=True)
    else:
        st.info("No hay notas clinicas externas registradas para este paciente.")

except Exception as e:
    st.error("Error al conectar con MongoDB Atlas.")
    st.exception(e)

# =========================
# Dashboard general
# =========================
st.divider()
st.subheader("Dashboard general")

col_a, col_b = st.columns(2)

with col_a:
    fig1 = px.histogram(
        appointments,
        x="specialty",
        title="Citas por especialidad"
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    if not clinical_summary.empty:
        fig2 = px.histogram(
            clinical_summary,
            x="risk_level",
            title="Pacientes por nivel de riesgo"
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No hay datos de resumen clinico para graficar.")

# =========================
# Stack tecnologico
# =========================
st.divider()
st.subheader("Stack tecnologico cloud usado")

st.markdown("""
**Servicios cloud utilizados:**

- **Streamlit Cloud:** despliegue publico de la aplicacion web.
- **Supabase:** almacenamiento de datos estructurados como pacientes, citas y resumen clinico.
- **MongoDB Atlas:** almacenamiento de notas clinicas semiestructuradas provenientes de plataformas externas simuladas.

**Flujo del sistema:**

`Profesional de salud -> Streamlit Cloud -> Cita programada -> Supabase -> Paciente asociado -> MongoDB Atlas -> Notas clinicas externas -> Dashboard`
""")

st.code("""
[Profesional de salud]
        |
        v
[Streamlit Cloud]
App web publica
        |
        v
[Seleccion de cita programada]
        |
        v
[Supabase]
Pacientes | Citas | Resumen clinico
        |
        v
[MongoDB Atlas]
Notas clinicas externas | Observaciones semiestructuradas
        |
        v
[Dashboard de atencion medica]
""")