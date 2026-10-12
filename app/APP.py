import streamlit as st
from PIL import Image
import json  
import os    


#configuracion del logo de la pestana
img = Image.open("assets/LogoOficialSceneOne.png")


#Configuración de la página (ancho completo para que quepan las tarjetas)
st.set_page_config(page_title="Scene One", page_icon=img, layout="wide", initial_sidebar_state="collapsed")


#base de datos temporal de productos (simulando lo que vendría de Supabase)
productos_bd = [
    {"id": 1, "nombre": "Polera Drop Negro", "precio": 25000, "tallas": ["S", "M", "L", "XL"]},
    {"id": 2, "nombre": "Polerón Classic", "precio": 35000, "tallas": ["M", "L"]},
    {"id": 3, "nombre": "Jockey Scene One", "precio": 15000, "tallas": ["Única"]},
    {"id": 4, "nombre": "Tote Bag Logo", "precio": 12000, "tallas": ["Única"]},
    {"id": 5, "nombre": "Polera Oversize Blanca", "precio": 25000, "tallas": ["S", "M", "L"]},
    {"id": 6, "nombre": "Calcetines Urban", "precio": 8000, "tallas": ["Única"]}
]


# Inicializar la "memoria" para saber si seleccionaron un producto
if "producto_seleccionado" not in st.session_state:
    st.session_state.producto_seleccionado = None


if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False


# Memoria de datos colores/font 
ARCHIVO_COLORES = "colores_drop.json"


# Colores por defecto si es la primera vez que abren la app
colores_default = {
    "color_fondo": "#121212",
    "color_lateral": "#1E1E1E",
    "color_banner": "#412206",
    "color_texto": "#FFFFFF",
    "fuente_texto": "sans-serif",
    "color_botones": "#8B4513"
}


# Intentamos leer el archivo guardado
if os.path.exists(ARCHIVO_COLORES):
    with open(ARCHIVO_COLORES, "r") as archivo:
        colores_guardados = json.load(archivo)
else:
    colores_guardados = colores_default


# 2. Le pasamos esos colores a la memoria de la página
for llave, valor in colores_guardados.items():
    if llave not in st.session_state:
        st.session_state[llave] = valor


# Inicializa los colores y la tipografía a toda la app
st.markdown(f"""
    <style>
    /* 1. Fondo principal de la pantalla derecha */
    .stApp {{
        background-color: {st.session_state.color_fondo};
    }}
    
    /* 2. Color y TIPO DE LETRA (sin romper el ojito de la clave) */
    h1, h2, h3, p, label {{
        color: {st.session_state.color_texto} !important;
        font-family: {st.session_state.fuente_texto} !important;
    }}
    
    /* 3. Fondo de la barra lateral izquierda */
    [data-testid="stSidebar"] {{
        background-color: {st.session_state.color_lateral} !important;
    }}
    
    /* 4. NUEVO: Color permanente de los botones */
    .stButton > button {{
        background-color: {st.session_state.color_botones} !important;
        border-color: {st.session_state.color_botones} !important;
        color: #FFFFFF !important; /* Letra blanca para que siempre se lea bien */
    }}
    </style>
""", unsafe_allow_html=True)


# 3. BARRA LATERAL
with st.sidebar:
    st.title("Panel Scene One")
    
    # si hay perfil se muestra app completa
    if st.session_state.usuario_autenticado:
        opciones_menu = ["Punto de Venta", "Inventario", "Clientes", "Finanzas y Totales", "Diseño de la App"]
    else:
        # sino se muestra solo venta
        opciones_menu = ["Punto de Venta"]
        
    menu = st.radio("Navegación", opciones_menu)

    
    #inicio de secion
    st.markdown("---") # Línea divisoria para separar la navegación
    
    if not st.session_state.usuario_autenticado:

        # Si NO han entrado, mostramos las cajitas de usuario y clave
        st.subheader("Acceso Administrador")
        correo = st.text_input("Correo electrónico", placeholder="ejemplo@correo.com")
        
        # type="password" hace que la clave se vea con puntitos negros
        contrasena = st.text_input("Contraseña", type="password") 
        
        if st.button("Ingresar", use_container_width=True):

            # Aquí verificamos si los datos son exactamente los que pidieron
            if correo == "1" and contrasena == "1":
                st.session_state.usuario_autenticado = True
                st.toast("¡Bienvenido al panel de control!", icon="🔓")
                st.rerun() # Recarga la página solita para mostrar los nuevos menús
            else:
                st.error("Correo o contraseña incorrectos")
    
    else:
        # Si YA entraron, mostramos un botón para cerrar el turno
        st.success("Sesión iniciada como Admin")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_autenticado = False
            st.rerun()


# 4. PANTALLA PRINCIPAL: PUNTO DE VENTA
if menu == "Punto de Venta":
    
    # El banner ahora usa el color guardado en la memoria
    st.markdown(f"""
    <div style='background-color: {st.session_state.color_banner}; padding: 40px; text-align: center; color: white; border-radius: 10px; margin-bottom: 30px;'>
        <h1 style='color: white; margin-bottom: 0px;'>Drops Scene One</h1>
        <p style='color: #e2d1c3; font-size: 18px;'>Punto de Venta Presencial Rápido</p>
    </div>
    """, unsafe_allow_html=True)

    # Crear una cuadrícula de 4 columnas (igual a tu plantilla)
    columnas = st.columns(4)
    
    # Recorremos nuestra lista de productos para armar las tarjetas
    for index, producto in enumerate(productos_bd):
        # El módulo para que se repartan en las 4 columnas (0, 1, 2, 3, 0, 1...)
        columna_actual = columnas[index % 4]
        
        with columna_actual:
            # st.container(border=True) crea la cajita de la tarjeta
            with st.container(border=True):
                # Cajita gris simulando la foto 450x300
                st.markdown("<div style='background-color: #e9ecef; height: 150px; border-radius: 5px; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; color: #6c757d; font-weight: bold;'>FOTO PRODUCTO</div>", unsafe_allow_html=True)
                
                st.subheader(producto["nombre"])
                st.write(f"**Precio:** ${producto['precio']}")
                
                # El botón de la tarjeta
                if st.button("Seleccionar", key=f"btn_{producto['id']}", use_container_width=True):
                    # Si hacen clic, guardamos este producto en la memoria
                    st.session_state.producto_seleccionado = producto
                    st.rerun() # Recarga la página para mostrar el cuadro de abajo

    # ----------------------------------------------------
    # 5. ZONA DE COBRO (Aparece SOLO si se seleccionó un producto)
    # ----------------------------------------------------
    if st.session_state.producto_seleccionado is not None:
        st.markdown("---") # Línea divisoria
        st.header("💳 Completar Venta")
        
        prod_actual = st.session_state.producto_seleccionado
        
        # Dos columnas para el formulario de pago
        col_pago1, col_pago2 = st.columns(2)
        
        with col_pago1:
            st.info(f"**Producto:** {prod_actual['nombre']}")
            # Mostrar desplegable con las tallas de ese producto específico
            talla_elegida = st.selectbox("Talla a vender:", prod_actual["tallas"])
            metodo = st.selectbox("Método de pago:", ["Transferencia", "Efectivo"])
            
        with col_pago2:
            st.success(f"**Total a cobrar: ${prod_actual['precio']}**")
            st.text_input("RUT o Nombre del cliente (opcional):")
            
            # Botón final gigante
            if st.button("✅ REGISTRAR VENTA Y DESCONTAR STOCK", type="primary", use_container_width=True):
                st.toast("¡Venta registrada con éxito!")
                # Limpiar la selección para atender al siguiente cliente
                st.session_state.producto_seleccionado = None
                st.rerun()

# ----------------------------------------------------
# PANTALLAS DE RELLENO PARA EL MENÚ
# ----------------------------------------------------
elif menu == "Inventario":
    st.title("Inventario Actual")
    st.info("Aquí irá la tabla conectada a Supabase para agregar nueva ropa.")
    
elif menu == "Clientes":
    st.title("Base de Clientes")
    st.info("Aquí irá el historial de los clientes frecuentes.")
    
elif menu == "Finanzas y Totales":
    st.title("Resumen de Finanzas")
    st.markdown("---")
    
    # Hacemos 3 columnas para mostrar los totales bien ordenados
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    
    with col_fin1:
        st.metric(label="Total Recaudado Hoy", value="$450.000", delta="+$50.000 (vs ayer)")
        
    with col_fin2:
        st.metric(label="Prendas Vendidas", value="18", delta="3 en la última hora")
        
    with col_fin3:
        st.metric(label="Porcentaje Transferencias", value="85%", delta="-5% efectivo", delta_color="off")
        
    st.markdown("---")
    st.subheader("Próximos Pasos")
    st.info("Aquí después conectaremos los datos reales de Supabase para que los números se actualicen solos con cada venta.")

elif menu == "Diseño de la App":
    st.title("Diseño de la App")
    st.info("Elige los colores y la letra del nuevo drop. Recuerda presionar 'Guardar Diseño' al final.")
    
    # 1. Los goteros de color (¡Ahora son 5!)
    col1, col2 = st.columns(2)
    with col1:
        nuevo_fondo = st.color_picker("Fondo Principal", st.session_state.color_fondo)
        nuevo_lateral = st.color_picker("Fondo Barra Lateral", st.session_state.color_lateral)
        nuevo_boton = st.color_picker("Color de Botones", st.session_state.color_botones) # NUEVO GOTERO
        
    with col2:
        nuevo_banner = st.color_picker("Color del Banner", st.session_state.color_banner)
        nuevo_texto = st.color_picker("Color de Textos", st.session_state.color_texto)
        
    st.markdown("---")
    
    # 2. El menú de Letras
    opciones_letras = {
        "Moderna y Limpia (Sans Serif)": "sans-serif",
        "Clásica (Serif)": "serif",
        "Estilo Hacker / Tech (Monospace)": "monospace",
        "Urbana y Gruesa (Impact)": "Impact, sans-serif"
    }
    nombre_fuente_actual = list(opciones_letras.keys())[list(opciones_letras.values()).index(st.session_state.fuente_texto)]
    eleccion_letra = st.selectbox("Estilo de Tipografía", list(opciones_letras.keys()), index=list(opciones_letras.keys()).index(nombre_fuente_actual))
    nueva_fuente = opciones_letras[eleccion_letra] 
    
    st.markdown("---")
    
    # 3. El Botón Mágico Permanente ACTUALIZADO
    if st.button("GUARDAR DISEÑO DEL DROP", type="primary", use_container_width=True):
        # Actualizamos la memoria
        st.session_state.color_fondo = nuevo_fondo
        st.session_state.color_lateral = nuevo_lateral
        st.session_state.color_banner = nuevo_banner
        st.session_state.color_texto = nuevo_texto
        st.session_state.fuente_texto = nueva_fuente
        st.session_state.color_botones = nuevo_boton # Metemos el botón a la memoria
        
        # Guardamos TODO en el archivo JSON
        colores_a_guardar = {
            "color_fondo": nuevo_fondo,
            "color_lateral": nuevo_lateral,
            "color_banner": nuevo_banner,
            "color_texto": nuevo_texto,
            "fuente_texto": nueva_fuente,
            "color_botones": nuevo_boton 
        }
        with open(ARCHIVO_COLORES, "w") as archivo:
            json.dump(colores_a_guardar, archivo) 
            
        st.toast("¡Diseño guardado!")
        st.rerun()
