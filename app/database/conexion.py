import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. abre base de datos
# ==========================================
# Aquí Python va a leer tu archivo secrets.toml sin mostrárselo a nadie
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

# ==========================================
# 2. crea conexion
# ==========================================
# Conectamos tu app de Streamlit con el servidor de Supabase
supabase: Client = create_client(url, key)

# ==========================================
# 3. funciones para la app
# ==========================================
def obtener_inventario():
    """Esta función va a Supabase, entra a la tabla 'inventario' y trae todo"""
    try:
        # El .select("*") significa "tráeme todas las columnas"
        respuesta = supabase.table("inventario").select("*").execute()
        return respuesta.data
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return []

    