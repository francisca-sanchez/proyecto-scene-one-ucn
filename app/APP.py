import streamlit as st
from PIL import Image

# Tu configuración inicial (la mantienes tal cual)

#configuracion del logo de la pestana
img = Image.open("assets/LogoSceneOneRosaTransparente.png")

#Configuración de la página (ancho completo para que quepan las tarjetas)
st.set_page_config(page_title="Scene One", page_icon=img, layout="wide", initial_sidebar_state="collapsed")


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
# ----------------------------------------------------
# 3. BARRA LATERAL (El menú izquierdo)
# ----------------------------------------------------
with st.sidebar:
    st.title("⚙️ Panel Scene One")
    menu = st.radio("Navegación", ["🛒 Punto de Venta", "📦 Inventario", "👥 Clientes", "📈 Finanzas y Totales"])

# ----------------------------------------------------
# 4. PANTALLA PRINCIPAL: PUNTO DE VENTA
# ----------------------------------------------------
if menu == "🛒 Punto de Venta":
    
# El banner oscuro tipo "Shop in style"
    st.markdown("""
    <div style='background-color: #412206; padding: 40px; text-align: center; color: white; border-radius: 10px; margin-bottom: 30px;'>
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
                if st.button("🛒 Seleccionar", key=f"btn_{producto['id']}", use_container_width=True):
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
elif menu == "📦 Inventario":
    st.title("📦 Inventario Actual")
    st.info("Aquí irá la tabla conectada a Supabase para agregar nueva ropa.")
    
elif menu == "👥 Clientes":
    st.title("👥 Base de Clientes")
    st.info("Aquí irá el historial de los clientes frecuentes.")
    
elif menu == "📈 Finanzas y Totales":
    st.title("📈 Resumen de Finanzas")
    st.markdown("---")
    
    # Hacemos 3 columnas para mostrar los totales bien ordenados
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    
    with col_fin1:
        st.metric(label="💰 Total Recaudado Hoy", value="$450.000", delta="+$50.000 (vs ayer)")
        
    with col_fin2:
        st.metric(label="👕 Prendas Vendidas", value="18", delta="3 en la última hora")
        
    with col_fin3:
        st.metric(label="💳 Porcentaje Transferencias", value="85%", delta="-5% efectivo", delta_color="off")
        
    st.markdown("---")
    st.subheader("📊 Próximos Pasos")
    st.info("Aquí después conectaremos los datos reales de Supabase para que los números se actualicen solos con cada venta.")

