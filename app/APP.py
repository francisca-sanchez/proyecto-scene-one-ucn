"""
SCENE ONE - Tienda de reservas + Panel de gestión (Streamlit + Supabase)
Ejecutar con:  streamlit run app.py
"""
import re
import uuid
import html as html_lib
from urllib.parse import quote_plus
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

NOMBRE_TIENDA = "SCENE ONE"
INSTAGRAM = "https://instagram.com/sceneoneclub"
TIKTOK = "https://www.tiktok.com/@scene.one.social"

# Íconos dibujados como SVG (se ven como logos, no como texto)
ICON_IG = ("<svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='#fff' stroke-width='2' "
           "stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='3' width='18' height='18' rx='5'/>"
           "<circle cx='12' cy='12' r='4'/><circle cx='17.5' cy='6.5' r='.6' fill='#fff'/></svg>")
ICON_TT = ("<svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='#fff' stroke-width='2' "
           "stroke-linecap='round' stroke-linejoin='round'><path d='M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5'/></svg>")

# Ícono de la pestaña: assets/LogoOficialSceneOne.png (se busca desde la raíz del proyecto
# y desde la carpeta del archivo; si no lo encuentra usa el ícono por defecto para no romper la app)
RUTA_ICONO = "assets/LogoOficialSceneOne.png"
_candidatos = [Path(RUTA_ICONO), Path(__file__).resolve().parent / RUTA_ICONO,
               Path(__file__).resolve().parent.parent / RUTA_ICONO]
ICONO = next((str(c) for c in _candidatos if c.exists()), None)

st.set_page_config(page_title=NOMBRE_TIENDA, page_icon=ICONO, layout="wide")

# ----------------------------------------------------------------------
# CONFIGURACIÓN POR DEFECTO DEL DISEÑO
# ----------------------------------------------------------------------
DEFAULT_CFG = {
    "color_fondo": "#1c1c1c",
    "color_lateral": "#2a2a2a",
    "color_banner": "#8a4026",
    "color_texto": "#ffffff",
    "color_boton": "#7a3228",
    "fuente": "Inter",
    "titulo": "DROP 01: NIGHTFALL",
    "subtitulo": "La nueva colección exclusiva ya está aquí.",
    "banner_url": "",
    "logo_url": "",
    "nombre_tienda": NOMBRE_TIENDA,
    "texto_catalogo": "",
    "mensaje_reserva": "¡Listo {nombre}! Tu reserva quedó registrada. Te escribiremos por Instagram.",
    "instagram": INSTAGRAM,
    "tiktok": TIKTOK,
    "datos_transferencia": "",
}

# Tipografías disponibles (una formal, una juvenil y tres populares)
FUENTES = {
    "Formal - Playfair Display": ("Playfair Display", "Playfair+Display:wght@400;700"),
    "Juvenil - Poppins": ("Poppins", "Poppins:wght@400;600;800"),
    "Popular - Inter": ("Inter", "Inter:wght@400;600;800"),
    "Popular - Montserrat": ("Montserrat", "Montserrat:wght@400;600;800"),
    "Popular - Roboto": ("Roboto", "Roboto:wght@400;700"),
}
# Valores guardados en versiones anteriores
FUENTES_ANTIGUAS = {"Moderna y limpia (Inter)": "Inter", "Juvenil y redonda (Poppins)": "Poppins",
                    "Urbana y fuerte (Bebas Neue)": "Bebas Neue"}

# Opciones iniciales de los menús. Después se administran desde Inventario > Categorías y tallas.
CATEGORIAS_BASE = ["Polera"]
TALLAS_BASE = ["S", "M", "L", "XL", "XXL"]
ORDEN_TALLAS = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "Única"]

COLUMNAS_PROD = ["id", "nombre", "categoria", "talla", "precio", "stock", "imagen_url", "activo"]


# ----------------------------------------------------------------------
# CONEXIÓN A SUPABASE
# ----------------------------------------------------------------------
@st.cache_resource
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


try:
    db = get_db()
except Exception:
    st.error("No se pudo conectar a Supabase. Revisa el archivo `.streamlit/secrets.toml` "
             "(mira `secrets.toml.example`).")
    st.stop()


# ----------------------------------------------------------------------
# FUNCIONES DE DATOS
# ----------------------------------------------------------------------
def money(n):
    return "$" + f"{int(n):,}".replace(",", ".")


def cargar_config():
    try:
        r = db.table("config").select("*").eq("id", 1).execute().data
        if r:
            return {**DEFAULT_CFG, **{k: v for k, v in r[0].items() if v is not None and k != "id"}}
    except Exception:
        pass
    return DEFAULT_CFG.copy()


def guardar_config(cfg):
    db.table("config").upsert({"id": 1, **cfg}).execute()


def listar_productos(solo_activos=True):
    q = db.table("productos").select("*").order("nombre")
    if solo_activos:
        q = q.eq("activo", True)
    return q.execute().data or []


def a_int(v):
    try:
        return int(v)
    except Exception:
        return 0


def clave_talla(t):
    if t in ORDEN_TALLAS:
        return (0, ORDEN_TALLAS.index(t), "")
    if t.isdigit():
        return (1, int(t), "")
    return (2, 0, t.lower())


def opciones(tipo):
    """Lista de categorías o tallas: las guardadas + las que ya usa algún producto."""
    campo = "categoria" if tipo == "categoria" else "talla"
    try:
        guardadas = [f["valor"] for f in (db.table("opciones").select("valor").eq("tipo", tipo).execute().data or [])]
    except Exception:
        guardadas = []
    try:
        usadas = [p[campo] for p in (db.table("productos").select(campo).execute().data or []) if p.get(campo)]
    except Exception:
        usadas = []
    base = (CATEGORIAS_BASE if tipo == "categoria" else TALLAS_BASE) if not guardadas else []
    vals = set(guardadas) | set(usadas) | set(base)
    if tipo == "categoria":
        return sorted(vals, key=str.lower)
    return sorted(vals, key=clave_talla)


def asegurar_opcion(tipo, valor):
    if valor:
        db.table("opciones").upsert({"tipo": tipo, "valor": valor}, on_conflict="tipo,valor").execute()


def renombrar_opcion(tipo, viejo, nuevo):
    """Cambia el nombre en todos los productos. Si 'nuevo' ya existe, las junta."""
    campo = "categoria" if tipo == "categoria" else "talla"
    db.table("productos").update({campo: nuevo}).eq(campo, viejo).execute()
    db.table("opciones").delete().eq("tipo", tipo).eq("valor", viejo).execute()
    asegurar_opcion(tipo, nuevo)


def subir_imagen(archivo, carpeta="productos"):
    ext = archivo.name.split(".")[-1].lower()
    ruta = f"{carpeta}/{uuid.uuid4().hex}.{ext}"
    db.storage.from_("imagenes").upload(ruta, archivo.getvalue(), {"content-type": archivo.type or "application/octet-stream"})
    return db.storage.from_("imagenes").get_public_url(ruta)


def crear_reserva(cliente, instagram, email, nota, carrito, adelanto="", pagos=None):
    """Descuenta stock (queda 'apartado') y guarda la reserva como pendiente."""
    prods = {p["id"]: p for p in listar_productos(False)}
    for it in carrito.values():
        if prods.get(it["id"], {}).get("stock", 0) < it["cantidad"]:
            return False, f"No hay stock suficiente de {it['nombre']}."
    for it in carrito.values():
        nuevo = prods[it["id"]]["stock"] - it["cantidad"]
        db.table("productos").update({"stock": nuevo}).eq("id", it["id"]).execute()
    items = list(carrito.values())
    total = sum(i["precio"] * i["cantidad"] for i in items)
    db.table("reservas").insert({
        "cliente": cliente, "instagram": instagram or None, "email": email or None, "nota": nota or None,
        "items": items, "total": total, "estado": "pendiente",
        "adelanto": adelanto or None, "pagos": pagos or [],
    }).execute()
    return True, "ok"


def normalizar_instagram(v):
    """'@Mi.Usuario', 'instagram.com/mi.usuario/' o 'mi.usuario' -> 'mi.usuario'."""
    v = re.sub(r"\s+", "", v or "")
    v = re.sub(r"^https?://(www\.)?instagram\.com/", "", v, flags=re.I)
    return v.split("?")[0].strip("/").lstrip("@").split("/")[0].lower()


def ver_instagram(v):
    return f"@{v}" if v else "—"


def clave_cliente(instagram, nombre):
    """Identifica a un cliente repetido por su usuario de Instagram (o por el nombre si no lo tiene)."""
    ig = normalizar_instagram(instagram)
    return ig if ig else "n:" + (nombre or "").strip().lower()


def ahora():
    return pd.Timestamp.now(tz="UTC").isoformat()


def registrar_cliente(nombre, instagram, email, total, fecha=None):
    """Crea o actualiza al cliente (acumula compras y total gastado). Devuelve su id."""
    ig = normalizar_instagram(instagram)
    clave = clave_cliente(ig, nombre)
    fecha = fecha or ahora()
    existente = db.table("clientes").select("*").eq("clave", clave).limit(1).execute().data
    if existente:
        c = existente[0]
        db.table("clientes").update({
            "nombre": c.get("nombre") or nombre or "Sin nombre",
            "instagram": c.get("instagram") or ig or None,
            "email": c.get("email") or email or None,
            "compras": a_int(c.get("compras")) + 1,
            "total_gastado": a_int(c.get("total_gastado")) + a_int(total),
            "ultima_compra": fecha,
        }).eq("id", c["id"]).execute()
        return c["id"]
    nuevo = db.table("clientes").insert({
        "nombre": nombre or "Sin nombre", "instagram": ig or None, "clave": clave,
        "email": email or None, "compras": 1, "total_gastado": a_int(total),
        "primera_compra": fecha, "ultima_compra": fecha,
    }).execute().data
    return nuevo[0]["id"]


def metodo_resumen(pagos):
    metodos = {p["metodo"] for p in (pagos or [])}
    if not metodos:
        return None
    return metodos.pop() if len(metodos) == 1 else "Mixto"


def finalizar_compra(items, cliente, instagram, email, nota, pagos, origen, reserva_id=None, descontar_stock=True):
    """Crea la compra con sus pagos y comprobantes, las ventas por prenda y actualiza al cliente.
    Devuelve (compra, mensaje_de_error)."""
    total = sum(a_int(i["precio"]) * a_int(i["cantidad"]) for i in items)
    try:
        actuales = {}
        if descontar_stock:
            for it in items:
                r = db.table("productos").select("stock").eq("id", it["id"]).execute().data
                actuales[it["id"]] = r[0]["stock"] if r else 0
                if actuales[it["id"]] < it["cantidad"]:
                    return None, f"No hay stock suficiente de {it['nombre']}."
        cliente_id = registrar_cliente(cliente, instagram, email, total)
        compra = db.table("compras").insert({
            "cliente_id": cliente_id, "cliente": cliente, "instagram": normalizar_instagram(instagram) or None,
            "email": email or None, "nota": nota or None, "items": items, "total": total,
            "pagos": pagos, "origen": origen, "reserva_id": reserva_id,
        }).execute().data[0]
        if descontar_stock:
            for it in items:
                db.table("productos").update({"stock": actuales[it["id"]] - it["cantidad"]}).eq("id", it["id"]).execute()
        metodo = metodo_resumen(pagos)
        for it in items:
            db.table("ventas").insert({
                "producto_id": it["id"], "nombre_producto": it["nombre"], "cantidad": it["cantidad"],
                "total": a_int(it["precio"]) * a_int(it["cantidad"]), "metodo_pago": metodo,
                "cliente": cliente, "compra_id": compra["id"],
            }).execute()
        return compra, None
    except Exception as e:
        return None, f"No se pudo registrar la venta. Detalle técnico: {e}"


def concretar_reserva(reserva, pagos):
    """La reserva ya está pagada: se convierte en compra (el stock ya estaba descontado)."""
    compra, err = finalizar_compra(reserva["items"], reserva["cliente"], reserva.get("instagram"), reserva.get("email"),
                                   reserva.get("nota"), pagos, "reserva", reserva["id"], descontar_stock=False)
    if err:
        return None, err
    db.table("reservas").update({"estado": "vendida", "pagos": pagos}).eq("id", reserva["id"]).execute()
    return compra, None


def comprobante_html(c):
    """Comprobante de compra (HTML): se puede imprimir o guardar como PDF desde el navegador."""
    esc = html_lib.escape
    fecha = pd.to_datetime(c["creado_en"], utc=True).tz_convert("America/Santiago").strftime("%d-%m-%Y %H:%M")
    filas = "".join(
        f"<tr><td>{esc(str(it['nombre']))} (talla {esc(str(it.get('talla') or 'única'))})</td>"
        f"<td style='text-align:center'>{it['cantidad']}</td>"
        f"<td style='text-align:right'>{money(it['precio'] * it['cantidad'])}</td></tr>" for it in c["items"])
    pagos = "".join(
        f"<tr><td>{esc(str(p['metodo']))}</td><td style='text-align:right'>{money(a_int(p.get('monto')))}</td></tr>"
        for p in (c.get("pagos") or []))
    capturas = "".join(
        f"<p style='margin:8px 0'><b>Comprobante de transferencia</b><br>"
        f"<img src='{esc(p['url'], quote=True)}' style='max-width:100%;max-height:340px'></p>"
        for p in (c.get("pagos") or []) if p.get("url"))
    datos = f"<b>Cliente:</b> {esc(c.get('cliente') or '')}<br>"
    if c.get("instagram"):
        datos += f"<b>Instagram:</b> @{esc(c['instagram'])}<br>"
    if c.get("email"):
        datos += f"<b>Correo:</b> {esc(c['email'])}<br>"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Comprobante N° {c['id']:06d}</title></head>"
        "<body style=\"font-family:Arial,sans-serif;max-width:520px;margin:24px auto;padding:0 16px;color:#111;background:#fff;\">"
        f"<h2 style='margin:0'>{esc(NOMBRE_TIENDA)}</h2>"
        f"<p style='margin:4px 0 16px;color:#555'>Comprobante de compra N° {c['id']:06d}<br>{fecha}</p>"
        f"<p>{datos}</p>"
        "<table style='width:100%;border-collapse:collapse' cellpadding='6'>"
        "<tr style='border-bottom:1px solid #999'><th style='text-align:left'>Detalle</th><th>Cant.</th>"
        "<th style='text-align:right'>Subtotal</th></tr>"
        f"{filas}"
        f"<tr style='border-top:2px solid #111'><td colspan='2'><b>TOTAL</b></td>"
        f"<td style='text-align:right'><b>{money(c['total'])}</b></td></tr></table>"
        "<h4 style='margin:18px 0 4px'>Pagos</h4>"
        f"<table style='width:100%' cellpadding='4'>{pagos}</table>"
        f"{capturas}"
        "<p style='margin-top:24px;color:#555;font-size:12px'>Gracias por tu compra.</p>"
        "</body></html>")


def mostrar_ultimo_comprobante():
    """Muestra el comprobante de la última venta registrada (con descarga)."""
    cid = st.session_state.get("ultimo_comprobante")
    if not cid:
        return
    try:
        k = db.table("compras").select("*").eq("id", cid).limit(1).execute().data[0]
    except Exception:
        return
    with st.container(border=True):
        st.markdown(f"**Venta registrada. Comprobante N° {k['id']:06d} por {money(k['total'])}**")
        b1, b2 = st.columns(2)
        b1.download_button("Descargar comprobante", data=comprobante_html(k), file_name=f"comprobante_{k['id']:06d}.html",
                           mime="text/html", key="dl_ultimo", use_container_width=True)
        if b2.button("Cerrar", key="cerrar_comprobante", use_container_width=True):
            st.session_state.pop("ultimo_comprobante", None)
            st.rerun()
        with st.expander("Ver comprobante"):
            components.html(comprobante_html(k), height=520, scrolling=True)


def cancelar_reserva(reserva):
    """Devuelve el stock apartado y marca la reserva como cancelada."""
    for it in reserva["items"]:
        r = db.table("productos").select("stock").eq("id", it["id"]).execute().data
        if r:
            db.table("productos").update({"stock": r[0]["stock"] + it["cantidad"]}).eq("id", it["id"]).execute()
    db.table("reservas").update({"estado": "cancelada"}).eq("id", reserva["id"]).execute()


# ----------------------------------------------------------------------
# ESTILOS
# ----------------------------------------------------------------------
def hex_rgb(h):
    try:
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 255, 255)


def nombre_fuente(v):
    v = (v or "").strip()
    if v in FUENTES:
        return FUENTES[v][0]
    return FUENTES_ANTIGUAS.get(v, v)


def fuentes_css(cfg):
    """Devuelve (css para cargar la fuente, familia de textos, familia de títulos)."""
    nombre = re.sub(r"[^\w\s\-]", "", nombre_fuente(cfg.get("fuente"))).strip() or "Inter"
    gf = next((v[1] for v in FUENTES.values() if v[0] == nombre), quote_plus(nombre))
    familia = f"'{nombre}', sans-serif"
    return f"@import url('https://fonts.googleapis.com/css2?family={gf}&display=swap');", familia, familia


def txt_html(t):
    """Texto libre del administrador: se muestra tal cual (con saltos de línea) sin romper la página."""
    return html_lib.escape(t or "").replace("\n", "<br>")


def aplicar_estilos(cfg):
    r, g, b = hex_rgb(cfg["color_texto"])
    carga_fuentes, fam_texto, fam_titulos = fuentes_css(cfg)
    st.markdown(f"""
<style>
/* fuentes */ {carga_fuentes}
html, body, .stApp, .stApp button, .stApp input, .stApp textarea {{ font-family: {fam_texto}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp [data-testid="stHeading"] {{ font-family: {fam_titulos} !important; }}
.stApp {{ background: {cfg['color_fondo']}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp li,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stMetricValue"],
.stApp [data-testid="stMetricLabel"] {{ color: {cfg['color_texto']}; }}
[data-testid="stSidebar"] {{ background: {cfg['color_lateral']}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.stButton > button, .stFormSubmitButton > button {{
    background: {cfg['color_boton']}; color: #fff; border: none;
    border-radius: 10px; font-weight: 700; padding: .55rem 1rem;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{ filter: brightness(1.2); color: #fff; }}
/* Avisos (info, success, warning, error) y toasts en tono neutro: se adaptan al color de texto elegido */
[data-testid="stAlert"], [data-testid="stAlertContainer"] {{
    background: rgba({r},{g},{b},.10) !important; border-radius: 12px; }}
[data-testid="stAlertContainer"] {{ border: 1px solid rgba({r},{g},{b},.25); }}
[data-testid="stAlert"] *, [data-testid="stToast"] * {{ color: {cfg['color_texto']} !important; }}
[data-testid="stAlert"] svg, [data-testid="stToast"] svg {{ fill: {cfg['color_texto']} !important; }}
[data-testid="stToast"] {{ background: {cfg['color_lateral']} !important; border: 1px solid rgba({r},{g},{b},.25); }}
.precio {{ font-size: 1.25rem; font-weight: 800; }}
.sin-foto {{ background:#e9ecef; color:#6c757d; height:260px; border-radius:12px;
             display:flex; align-items:center; justify-content:center; font-weight:700; }}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# VISTA PÚBLICA: TIENDA DE RESERVAS
# ----------------------------------------------------------------------
def hero(cfg):
    _, _, fam_titulos = fuentes_css(cfg)
    if cfg.get("banner_url"):
        fondo = f"linear-gradient(rgba(0,0,0,.45),rgba(0,0,0,.65)), url('{cfg['banner_url']}') center/cover"
    else:
        fondo = cfg["color_banner"]
    links = ""
    for url, nombre_red, icono in ((cfg.get("instagram"), "Instagram", ICON_IG), (cfg.get("tiktok"), "TikTok", ICON_TT)):
        if url:
            links += f"<a href='{html_lib.escape(url, quote=True)}' target='_blank' title='{nombre_red}'>{icono}</a>"
    # OJO: el HTML va sin sangría ni líneas en blanco; si no, Streamlit lo muestra como código.
    html = f"<div style=\"background:{fondo};border-radius:18px;padding:70px 24px;text-align:center;margin-bottom:24px;color:#fff;\">"
    if cfg.get("nombre_tienda"):
        html += f"<div style='font-size:.9rem;letter-spacing:.4em;opacity:.85;'>{txt_html(cfg['nombre_tienda'])}</div>"
    if cfg.get("titulo"):
        html += (f"<h1 style=\"font-size:3.2rem;margin:.2em 0;font-weight:800;color:#fff;font-family:{fam_titulos};"
                 f"text-shadow:2px 2px 4px #000;\">{txt_html(cfg['titulo'])}</h1>")
    if cfg.get("subtitulo"):
        html += f"<p style='font-size:1.15rem;color:#fff;text-shadow:1px 1px 3px #000;'>{txt_html(cfg['subtitulo'])}</p>"
    if links:
        html += f"<div style='margin-top:18px;display:flex;gap:22px;justify-content:center;'>{links}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


@st.fragment(run_every="15s")
def catalogo(cfg):
    """Catálogo: se vuelve a leer de la base de datos cada 15 segundos, así lo que se cambia
    en Inventario (productos nuevos, precios, stock, fotos) aparece solo, sin recargar la página."""
    carrito = st.session_state.carrito
    if cfg.get("texto_catalogo"):
        st.markdown(cfg["texto_catalogo"])
    todos = listar_productos(False)
    prods = [p for p in todos if p.get("activo", True) and p["stock"] > 0]
    if st.session_state.get("admin") and len(todos) > len(prods):
        st.caption(f"Vista de administrador: {len(todos) - len(prods)} producto(s) no se muestran a los clientes "
                   "(sin stock o con 'Visible en tienda' desactivado).")
    if not prods:
        st.info("Pronto subiremos nuevas prendas. ¡Vuelve en un rato!")
    cats = sorted({p["categoria"] for p in prods if p.get("categoria")})
    opciones_filtro = ["Todas"] + cats
    if st.session_state.get("filtro_cat") not in (None, *opciones_filtro):
        del st.session_state["filtro_cat"]       # la categoría elegida ya no existe
    filtro = st.pills("Categoría", opciones_filtro, default="Todas", key="filtro_cat") if cats else "Todas"
    if filtro and filtro != "Todas":
        prods = [p for p in prods if p.get("categoria") == filtro]

    # Una sola tarjeta por prenda (mismo nombre): el cliente elige la talla
    grupos = {}
    for p in prods:
        grupos.setdefault((p["nombre"] or "").strip().lower(), []).append(p)

    cols = st.columns(4)
    for i, (_, variantes) in enumerate(sorted(grupos.items())):
        por_talla = {}
        for v in variantes:
            por_talla.setdefault(v.get("talla") or "Única", v)     # una opción por talla
        tallas = sorted(por_talla, key=clave_talla)
        foto = next((v["imagen_url"] for v in variantes if v.get("imagen_url")), None)
        with cols[i % 4]:
            with st.container(border=True):
                if foto:
                    st.image(foto, use_container_width=True)
                else:
                    st.markdown("<div class='sin-foto'>FOTO PRODUCTO</div>", unsafe_allow_html=True)
                st.markdown(f"**{variantes[0]['nombre']}**")
                k = f"talla_{min(v['id'] for v in variantes)}"
                if st.session_state.get(k) not in (None, *tallas):
                    del st.session_state[k]               # esa talla ya no está disponible
                talla = st.selectbox("Talla", tallas, key=k)
                p = por_talla[talla]
                st.markdown(f"<div class='precio'>{money(p['precio'])}</div>", unsafe_allow_html=True)
                if st.button("Agregar a mi reserva", key=f"add_{p['id']}", use_container_width=True):
                    ya = carrito.get(p["id"], {}).get("cantidad", 0)
                    if ya + 1 > p["stock"]:
                        st.toast("No quedan más unidades de esa talla")
                    else:
                        carrito[p["id"]] = {"id": p["id"], "nombre": p["nombre"], "talla": p.get("talla"),
                                            "precio": p["precio"], "cantidad": ya + 1}
                        st.toast(f"{p['nombre']} (talla {talla}) agregado")
                        st.rerun()


def vista_tienda(cfg):
    hero(cfg)
    if "carrito" not in st.session_state:
        st.session_state.carrito = {}
    carrito = st.session_state.carrito

    if st.session_state.get("reserva_ok"):
        st.success(st.session_state.pop("reserva_ok"))
    n_prendas = sum(i["cantidad"] for i in carrito.values())
    if n_prendas:
        st.caption(f"Prendas en tu reserva: {n_prendas}. Revísala en la pestaña 'Mi reserva'.")
    tab_cat, tab_res = st.tabs(["Catálogo", "Mi reserva"])

    with tab_cat:
        catalogo(cfg)

    with tab_res:
        if not carrito:
            st.info("Tu reserva está vacía. Agrega prendas desde el catálogo.")
        else:
            for pid, it in list(carrito.items()):
                c1, c2, c3 = st.columns([5, 2, 1])
                c1.markdown(f"**{it['nombre']}** · talla {it.get('talla') or 'única'}")
                c2.markdown(f"{it['cantidad']} × {money(it['precio'])}")
                if c3.button("Quitar", key=f"del_{pid}"):
                    del carrito[pid]
                    st.rerun()
            total = sum(i["precio"] * i["cantidad"] for i in carrito.values())
            st.markdown(f"### Total: {money(total)}")

            n = st.session_state.setdefault("res_n", 0)        # cambia al reservar, para limpiar el formulario
            nombre = st.text_input("Nombre y apellido *", key=f"res_nombre_{n}")
            ig = st.text_input("Tu usuario de Instagram (opcional)", placeholder="@tuusuario", key=f"res_ig_{n}")
            mail = st.text_input("Correo (opcional)", key=f"res_mail_{n}")
            nota = st.text_area("Comentario (opcional)", placeholder="Ej: retiro el sábado en la tarde", key=f"res_nota_{n}")
            pago = st.radio("¿Cómo quieres pagar?", ["Pago al retirar", "Pagar por adelantado"], key=f"res_pago_{n}")
            adelanto, comp, monto = "", None, total
            if pago == "Pagar por adelantado":
                adelanto = st.radio("Método de pago adelantado", ["Transferencia", "Efectivo"], horizontal=True, key=f"res_met_{n}")
                if adelanto == "Transferencia":
                    if cfg.get("datos_transferencia"):
                        st.info(cfg["datos_transferencia"].replace("\n", "  \n"))
                    monto = st.number_input("Monto que transferiste (CLP)", min_value=0, step=500, value=int(total),
                                            key=f"res_monto_{n}_{total}")
                    comp = st.file_uploader("Comprobante de la transferencia (foto o captura)",
                                            type=["png", "jpg", "jpeg", "webp"], key=f"res_comp_{n}")
                else:
                    st.caption("Pagarás en efectivo antes de retirar; el equipo registrará tu pago.")
            else:
                st.caption("Reservas ahora y pagas al retirar (efectivo o transferencia).")

            if st.button("CONFIRMAR RESERVA", use_container_width=True, key=f"res_enviar_{n}"):
                if not nombre.strip():
                    st.warning("Falta tu nombre y apellido.")
                elif adelanto == "Transferencia" and not comp:
                    st.warning("Sube la captura del comprobante de tu transferencia, o elige pagar al retirar.")
                else:
                    try:
                        pagos = []
                        if adelanto == "Transferencia":
                            pagos.append({"metodo": "Transferencia", "monto": a_int(monto),
                                          "url": subir_imagen(comp, "comprobantes"), "fecha": ahora(),
                                          "verificado": False, "origen": "cliente"})
                        ok, msg = crear_reserva(nombre.strip(), normalizar_instagram(ig), mail.strip(), nota.strip(),
                                                carrito, adelanto, pagos)
                    except Exception as e:
                        ok, msg = False, f"No se pudo registrar la reserva. Detalle técnico: {e}"
                    if ok:
                        texto = (cfg.get("mensaje_reserva") or "Reserva registrada.").replace("{nombre}", nombre.strip().split()[0])
                        if adelanto == "Transferencia":
                            texto += " Revisaremos tu comprobante."
                        st.session_state.reserva_ok = texto
                        st.session_state.carrito = {}
                        st.session_state.res_n = n + 1
                        st.rerun()
                    else:
                        st.error(msg)


# ----------------------------------------------------------------------
# PANEL ADMIN
# ----------------------------------------------------------------------
def guardar_pagos(reserva_id, pagos):
    db.table("reservas").update({"pagos": pagos}).eq("id", reserva_id).execute()


def mostrar_pagos(pagos):
    for pg in pagos:
        estado = "verificado" if pg.get("verificado") else "por verificar"
        st.write(f"{pg['metodo']} - {money(a_int(pg.get('monto')))} ({estado})")
        if pg.get("url"):
            st.image(pg["url"], width=260)


def admin_reservas():
    st.title("Reservas")
    mostrar_ultimo_comprobante()
    estado = st.radio("Mostrar", ["pendiente", "vendida", "cancelada"], horizontal=True)
    res = db.table("reservas").select("*").eq("estado", estado).order("creado_en", desc=True).execute().data or []
    if not res:
        st.info(f"No hay reservas {estado}s.")
    for r in res:
        pagos = list(r.get("pagos") or [])
        total = a_int(r["total"])
        verificado = sum(a_int(p.get("monto")) for p in pagos if p.get("verificado"))
        falta = max(total - verificado, 0)
        sin_verificar = [p for p in pagos if not p.get("verificado")]
        with st.expander(f"{r['cliente']} · {money(total)} · {r['creado_en'][:10]}"):
            contacto = ver_instagram(r["instagram"]) if r.get("instagram") else (r.get("telefono") or "—")
            st.write(f"Instagram: {contacto}  ·  Correo: {r.get('email') or '—'}")
            if r.get("nota"):
                st.write(f"Nota: {r['nota']}")
            for it in r["items"]:
                st.write(f"- {it['cantidad']} × {it['nombre']} (talla {it.get('talla') or 'única'}) — {money(it['precio'] * it['cantidad'])}")
            if r.get("adelanto"):
                st.write(f"Forma de pago elegida: adelantado por {r['adelanto'].lower()}")
            else:
                st.write("Forma de pago elegida: paga al retirar")

            if estado != "pendiente":
                mostrar_pagos(pagos)
                continue

            st.markdown(f"**Total de la reserva: {money(total)}**  ·  Pago verificado: {money(verificado)}  ·  Falta: {money(falta)}")
            for i, pg in enumerate(pagos):
                with st.container(border=True):
                    mostrar_pagos([pg])
                    if not pg.get("verificado"):
                        st.caption(f"Compara el monto del comprobante con el total de la reserva ({money(total)}).")
                        monto_v = st.number_input("Monto que aparece en el comprobante", min_value=0, step=500,
                                                  value=a_int(pg.get("monto")), key=f"mv_{r['id']}_{i}")
                        b1, b2 = st.columns(2)
                        if b1.button("Verificar pago", key=f"vp_{r['id']}_{i}", use_container_width=True):
                            pagos[i] = {**pg, "monto": a_int(monto_v), "verificado": True}
                            guardar_pagos(r["id"], pagos)
                            st.session_state.flash = "Pago verificado"
                            st.rerun()
                        if b2.button("Descartar comprobante", key=f"dp_{r['id']}_{i}", use_container_width=True):
                            del pagos[i]
                            guardar_pagos(r["id"], pagos)
                            st.session_state.flash = "Comprobante descartado"
                            st.rerun()

            if sin_verificar:
                st.caption("Verifica o descarta los comprobantes de arriba antes de registrar otro pago o confirmar la venta.")
            elif falta > 0:
                st.info(f"Falta {money(falta)}. Si el depósito fue menor, pide al cliente que deposite el resto, "
                        "o registra aquí el pago apenas lo recibas.")
                with st.form(f"pago_{r['id']}", clear_on_submit=True):
                    metodo_p = st.radio("Método de pago", ["Efectivo", "Transferencia"], horizontal=True, key=f"pm_{r['id']}")
                    monto_p = st.number_input("Monto recibido (CLP)", min_value=0, step=500, value=int(falta), key=f"pmo_{r['id']}")
                    comp = st.file_uploader("Comprobante de la transferencia (foto o captura)",
                                            type=["png", "jpg", "jpeg", "webp"], key=f"pc_{r['id']}")
                    ok_p = st.form_submit_button("Registrar pago", use_container_width=True)
                if ok_p:
                    if a_int(monto_p) <= 0:
                        st.warning("El monto debe ser mayor a 0.")
                    elif metodo_p == "Transferencia" and not comp:
                        st.warning("Sube la captura del comprobante de la transferencia.")
                    else:
                        try:
                            url = subir_imagen(comp, "comprobantes") if metodo_p == "Transferencia" else None
                            pagos.append({"metodo": metodo_p, "monto": a_int(monto_p), "url": url, "fecha": ahora(),
                                          "verificado": True, "origen": "admin"})
                            guardar_pagos(r["id"], pagos)
                            st.session_state.flash = "Pago registrado"
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo registrar el pago. Detalle técnico: {e}")

            c1, c2 = st.columns(2)
            if not sin_verificar and falta == 0:
                if c1.button("Confirmar venta", key=f"v_{r['id']}", use_container_width=True):
                    compra, err = concretar_reserva(r, pagos)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.ultimo_comprobante = compra["id"]
                        st.session_state.flash = "Venta confirmada: comprobante y cliente guardados"
                        st.rerun()
            if c2.button("Cancelar (devuelve stock)", key=f"c_{r['id']}", use_container_width=True):
                cancelar_reserva(r)
                st.session_state.flash = "Reserva cancelada, stock devuelto"
                st.rerun()
            if verificado > 0:
                st.caption("Esta reserva tiene pagos registrados: si la cancelas, recuerda devolver el dinero.")


def admin_pos():
    st.title("Punto de Venta")
    mostrar_ultimo_comprobante()
    items = st.session_state.setdefault("pos_items", [])
    prods = [p for p in listar_productos() if p["stock"] > 0]
    if not prods:
        st.warning("No hay productos con stock. Agrega inventario primero.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Agregar prenda")
        p = st.selectbox("Prenda", prods, format_func=lambda x: f"{x['nombre']} · talla {x.get('talla') or 'única'} · stock {x['stock']}")
        ya = sum(i["cantidad"] for i in items if i["id"] == p["id"])
        disponible = int(p["stock"]) - ya
        if p.get("imagen_url"):
            st.image(p["imagen_url"], width=160)
        if disponible <= 0:
            st.caption("Ya agregaste todo el stock de esta prenda a la venta.")
        else:
            cant = st.number_input("Cantidad", 1, disponible, 1)
            if st.button("Agregar a la venta", use_container_width=True):
                for i in items:
                    if i["id"] == p["id"]:
                        i["cantidad"] += int(cant)
                        break
                else:
                    items.append({"id": p["id"], "nombre": p["nombre"], "talla": p.get("talla"),
                                  "precio": p["precio"], "cantidad": int(cant)})
                st.rerun()
    with col2:
        st.subheader("Venta actual")
        if not items:
            st.caption("Aún no agregas prendas.")
        for idx, it in enumerate(items):
            a, b = st.columns([5, 1])
            a.write(f"{it['cantidad']} × {it['nombre']} (talla {it.get('talla') or 'única'}) — {money(it['precio'] * it['cantidad'])}")
            if b.button("Quitar", key=f"pos_del_{idx}"):
                del items[idx]
                st.rerun()
        total = sum(i["precio"] * i["cantidad"] for i in items)
        st.markdown(f"### Total a cobrar: {money(total)}")

    if not items:
        return
    st.divider()
    st.subheader("Datos del cliente y pago")
    n = st.session_state.setdefault("pos_n", 0)        # cambia al registrar, para limpiar el formulario
    d1, d2, d3 = st.columns(3)
    nombre = d1.text_input("Nombre y apellido *", key=f"pos_nombre_{n}")
    ig = d2.text_input("Usuario de Instagram (opcional)", placeholder="@usuario", key=f"pos_ig_{n}")
    mail = d3.text_input("Correo (opcional)", key=f"pos_mail_{n}")
    metodo = st.radio("Método de pago", ["Efectivo", "Transferencia"], horizontal=True, key=f"pos_metodo_{n}")
    comp = None
    if metodo == "Transferencia":
        comp = st.file_uploader("Comprobante de la transferencia (foto o captura)",
                                type=["png", "jpg", "jpeg", "webp"], key=f"pos_comp_{n}")
    else:
        st.caption("Al registrar la venta se crea y guarda el comprobante con el total y los datos del cliente.")

    if st.button("REGISTRAR VENTA Y DESCONTAR STOCK", use_container_width=True, key=f"pos_ok_{n}"):
        if not nombre.strip():
            st.warning("Falta el nombre del cliente.")
        elif metodo == "Transferencia" and not comp:
            st.warning("Sube la captura del comprobante de la transferencia.")
        else:
            try:
                url = subir_imagen(comp, "comprobantes") if metodo == "Transferencia" else None
            except Exception as e:
                st.error(f"No se pudo subir el comprobante. Detalle técnico: {e}")
                return
            pagos = [{"metodo": metodo, "monto": total, "url": url, "fecha": ahora(), "verificado": True, "origen": "admin"}]
            compra, err = finalizar_compra(items, nombre.strip(), ig, mail.strip(), None, pagos, "punto_de_venta")
            if err:
                st.error(err)
            else:
                st.session_state.pos_items = []
                st.session_state.pos_n = n + 1
                st.session_state.ultimo_comprobante = compra["id"]
                st.session_state.flash = "Venta registrada con éxito"
                st.rerun()


def gestor_opciones(tipo, titulo):
    campo = "categoria" if tipo == "categoria" else "talla"
    st.subheader(titulo)
    usos = {}
    for p in (db.table("productos").select(campo).execute().data or []):
        if p.get(campo):
            usos[p[campo]] = usos.get(p[campo], 0) + 1
    vals = opciones(tipo)
    st.dataframe(pd.DataFrame({"Nombre": vals, "Productos que la usan": [usos.get(v, 0) for v in vals]}),
                 hide_index=True, use_container_width=True)

    with st.form(f"form_add_{tipo}", clear_on_submit=True):
        nueva = st.text_input("Agregar nueva")
        ok_add = st.form_submit_button("Agregar", use_container_width=True)
    with st.form(f"form_edit_{tipo}", clear_on_submit=True):
        elegido = st.selectbox("Elegir una para corregir o eliminar", vals)
        nuevo_nombre = st.text_input("Nuevo nombre")
        c1, c2 = st.columns(2)
        ok_ren = c1.form_submit_button("Renombrar", use_container_width=True)
        ok_del = c2.form_submit_button("Eliminar", use_container_width=True)

    try:
        if ok_add:
            if not nueva.strip():
                st.warning("Escribe un nombre.")
            else:
                asegurar_opcion(tipo, nueva.strip())
                st.session_state.flash = "Agregada"
                st.rerun()
        if ok_ren:
            if not nuevo_nombre.strip():
                st.warning("Escribe el nuevo nombre.")
            elif nuevo_nombre.strip() == elegido:
                st.warning("El nombre nuevo es igual al actual.")
            else:
                renombrar_opcion(tipo, elegido, nuevo_nombre.strip())
                st.session_state.flash = f"'{elegido}' ahora se llama '{nuevo_nombre.strip()}'"
                st.rerun()
        if ok_del:
            if usos.get(elegido, 0) > 0:
                st.error(f"{usos[elegido]} producto(s) usan '{elegido}'. Renómbrala o cámbialos antes de eliminarla.")
            else:
                db.table("opciones").delete().eq("tipo", tipo).eq("valor", elegido).execute()
                st.session_state.flash = "Eliminada"
                st.rerun()
    except Exception as e:
        st.error(f"No se pudo guardar. Revisa que exista la tabla 'opciones' (archivo actualizacion_opciones.sql). Detalle: {e}")


def admin_inventario():
    st.title("Panel de Gestión de Inventario")
    tab1, tab2, tab3 = st.tabs(["Ver y editar stock", "Agregar nuevo producto", "Categorías y tallas"])

    with tab1:
        st.info("Doble clic en una celda para editar. Después presiona **Guardar cambios**.")
        prods = listar_productos(False)
        if not prods:
            st.write("Aún no hay productos.")
        else:
            df = pd.DataFrame(prods)[COLUMNAS_PROD]
            df["imagen_url"] = df["imagen_url"].fillna("")
            df["categoria"] = df["categoria"].fillna("")
            df["talla"] = df["talla"].fillna("")
            # incluye valores antiguos que no estén en la lista, para no perderlos
            opc_cat = opciones("categoria")
            opc_talla = opciones("talla")
            if "" in set(df["categoria"]):
                opc_cat = [""] + opc_cat
            if "" in set(df["talla"]):
                opc_talla = [""] + opc_talla
            editado = st.data_editor(
                df, hide_index=True, use_container_width=True, disabled=["id"],
                column_config={
                    "categoria": st.column_config.SelectboxColumn("Categoría", options=opc_cat),
                    "talla": st.column_config.SelectboxColumn("Talla", options=opc_talla),
                    "precio": st.column_config.NumberColumn("Precio", step=500, format="$%d"),
                    "stock": st.column_config.NumberColumn("Stock", step=1),
                    "activo": st.column_config.CheckboxColumn("Visible en tienda"),
                    "imagen_url": st.column_config.TextColumn("URL de foto"),
                },
            )
            if st.button("Guardar cambios"):
                n = 0
                for i in df.index:
                    if df.loc[i].to_dict() != editado.loc[i].to_dict():
                        r = editado.loc[i]
                        db.table("productos").update({
                            "nombre": r["nombre"] or "", "categoria": r["categoria"] or "", "talla": r["talla"] or "",
                            "precio": a_int(r["precio"]), "stock": a_int(r["stock"]),
                            "imagen_url": r["imagen_url"] or None, "activo": bool(r["activo"]),
                        }).eq("id", int(r["id"])).execute()
                        n += 1
                st.session_state.flash = f"{n} producto(s) actualizado(s)"
                st.rerun()

            st.divider()
            st.subheader("Cambiar la foto de un producto")
            with st.form("form_foto", clear_on_submit=True):
                prod_f = st.selectbox("Producto", prods, key="foto_sel",
                                      format_func=lambda x: f"{x['nombre']} - talla {x.get('talla') or '-'}")
                nueva_foto = st.file_uploader("Nueva foto o archivo")
                ok_foto = st.form_submit_button("Guardar foto", use_container_width=True)
            if ok_foto:
                if not nueva_foto:
                    st.warning("Elige un archivo.")
                else:
                    try:
                        url = subir_imagen(nueva_foto)
                        db.table("productos").update({"imagen_url": url}).eq("id", prod_f["id"]).execute()
                        st.session_state.flash = "Foto actualizada"
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo subir la foto. Detalle técnico: {e}")

            st.subheader("Eliminar un producto")
            with st.form("form_borrar", clear_on_submit=True):
                prod_b = st.selectbox("Producto a eliminar", prods, key="borrar_sel",
                                      format_func=lambda x: f"{x['nombre']} - talla {x.get('talla') or '-'}")
                seguro = st.checkbox("Estoy seguro, eliminar definitivamente")
                ok_borrar = st.form_submit_button("Eliminar producto", use_container_width=True)
            if ok_borrar:
                if not seguro:
                    st.warning("Marca la casilla para confirmar.")
                else:
                    db.table("productos").delete().eq("id", prod_b["id"]).execute()
                    st.session_state.flash = "Producto eliminado"
                    st.rerun()

    with tab3:
        st.info("Aquí puedes corregir errores de escritura. Al renombrar, el cambio se aplica a todos los productos que la usan.")
        g1, g2 = st.columns(2)
        with g1:
            gestor_opciones("categoria", "Categorías")
        with g2:
            gestor_opciones("talla", "Tallas")

    with tab2:
        st.subheader("Ingresar nueva mercadería")
        st.caption("Para agregar otra talla de una prenda que ya existe, elígela en la primera lista: se copian su categoría, "
                   "precio y foto (puedes cambiarlos). Si esa talla ya existía, el stock se suma al que ya está.")
        todos = listar_productos(False)
        existentes = sorted({p["nombre"] for p in todos if p.get("nombre")}, key=str.lower)
        with st.form("nuevo_producto", clear_on_submit=True):
            elegido = st.selectbox("Prenda que ya existe (opcional)", [""] + existentes,
                                   format_func=lambda v: v or "(escribir un nombre nuevo)")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre de la prenda nueva", help="Déjalo vacío si elegiste una prenda de la lista")
            categoria_sel = c2.selectbox("Categoría", [""] + opciones("categoria"), format_func=lambda v: v or "(sin definir)")
            talla_sel = c1.selectbox("Talla", [""] + opciones("talla"), format_func=lambda v: v or "(sin definir)")
            precio = c2.number_input("Precio (CLP)", step=500, value=0,
                                     help="Si eliges una prenda que ya existe y lo dejas en 0, se usa su precio")
            stock = c1.number_input("Stock inicial", step=1, value=1)
            foto = c2.file_uploader("Foto o archivo")
            otra_cat = c1.text_input("¿Otra categoría? (opcional)", placeholder="Solo si no está en la lista")
            otra_talla = c2.text_input("¿Otra talla? (opcional)", placeholder="Solo si no está en la lista")
            ok = st.form_submit_button("AGREGAR AL INVENTARIO", use_container_width=True)
        if ok:
            def norm(x):
                return (x or "").strip().lower()
            nombre_final = nombre.strip() or elegido or "Sin nombre"
            base = next((p for p in todos if norm(p["nombre"]) == norm(nombre_final)), None)
            categoria = otra_cat.strip() or categoria_sel or ((base.get("categoria") if base else "") or "")
            talla = otra_talla.strip() or talla_sel
            precio_final = a_int(precio) or (a_int(base["precio"]) if base else 0)
            url = None
            try:
                if foto:
                    url = subir_imagen(foto)
            except Exception as e:
                st.warning(f"No se pudo subir la foto ({e}). Se usará la foto de la prenda existente, si hay.")
            if not url and base:
                url = base.get("imagen_url")
            dup = next((p for p in todos if norm(p["nombre"]) == norm(nombre_final) and (p.get("talla") or "") == talla), None)
            try:
                if dup:
                    db.table("productos").update({"stock": a_int(dup["stock"]) + a_int(stock)}).eq("id", dup["id"]).execute()
                    mensaje = "Esa talla ya existía: se sumó el stock"
                else:
                    db.table("productos").insert({
                        "nombre": nombre_final, "categoria": categoria, "talla": talla,
                        "precio": precio_final, "stock": a_int(stock), "imagen_url": url, "activo": True,
                    }).execute()
                    mensaje = "Producto agregado"
            except Exception as e:
                st.error(f"No se pudo guardar el producto. Detalle técnico: {e}")
            else:
                try:
                    asegurar_opcion("categoria", categoria)
                    asegurar_opcion("talla", talla)
                except Exception:
                    pass
                st.session_state.flash = mensaje
                st.rerun()


def admin_clientes():
    st.title("Clientes")
    st.caption("Aquí se guardan los clientes con todas sus compras y comprobantes.")
    try:
        clientes = db.table("clientes").select("*").execute().data or []
    except Exception as e:
        st.error(f"No se pudo leer la tabla de clientes. Ejecuta actualizacion_clientes.sql en Supabase. Detalle: {e}")
        return

    if not clientes:
        st.info("Todavía no hay clientes. Aparecerán cuando se registre una venta (punto de venta o reserva confirmada).")
        antiguas = db.table("reservas").select("id", count="exact").eq("estado", "vendida").execute().count or 0
        if antiguas and st.button(f"Importar clientes de {antiguas} reserva(s) ya vendida(s)"):
            for r in (db.table("reservas").select("*").eq("estado", "vendida").order("creado_en").execute().data or []):
                registrar_cliente(r["cliente"], r.get("instagram"), r.get("email"), r["total"], fecha=r["creado_en"])
            st.session_state.flash = "Clientes importados"
            st.rerun()
        return

    f1, f2 = st.columns([2, 1])
    buscar = f1.text_input("Buscar por nombre, Instagram o correo")
    orden = f2.selectbox("Ordenar por", ["Mayor total gastado", "Más compras", "Compra más reciente"])
    claves = {
        "Mayor total gastado": lambda c: a_int(c.get("total_gastado")),
        "Más compras": lambda c: (a_int(c.get("compras")), a_int(c.get("total_gastado"))),
        "Compra más reciente": lambda c: c.get("ultima_compra") or "",
    }
    clientes = sorted(clientes, key=claves[orden], reverse=True)
    if buscar.strip():
        q = buscar.strip().lower()
        clientes = [c for c in clientes if q in " ".join(str(c.get(k) or "") for k in ("nombre", "instagram", "email")).lower()]
        if not clientes:
            st.info("No se encontró ningún cliente con esa búsqueda.")
            return

    df = pd.DataFrame(clientes)
    if "instagram" not in df:
        df["instagram"] = None
    m1, m2, m3 = st.columns(3)
    m1.metric("Clientes", len(df))
    m2.metric("Han comprado más de una vez", int((df["compras"] > 1).sum()))
    m3.metric("Total vendido", money(df["total_gastado"].sum()))
    tabla = pd.DataFrame({
        "N°": range(1, len(df) + 1),
        "Nombre": df["nombre"],
        "Instagram": df["instagram"].fillna("").map(lambda v: f"@{v}" if v else ""),
        "Correo": df["email"].fillna(""),
        "Compras": df["compras"],
        "Total gastado": df["total_gastado"].map(money),
        "Última compra": pd.to_datetime(df["ultima_compra"], utc=True).dt.tz_convert("America/Santiago").dt.strftime("%d-%m-%Y"),
    })
    st.dataframe(tabla, hide_index=True, use_container_width=True)

    st.divider()
    c = st.selectbox("Ver el detalle de un cliente", clientes,
                     format_func=lambda x: f"{x['nombre']} - {ver_instagram(x.get('instagram')) if x.get('instagram') else 'sin Instagram'}")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Datos")
        with st.form(f"form_cliente_{c['id']}"):
            n = st.text_input("Nombre", c.get("nombre") or "")
            t = st.text_input("Instagram", c.get("instagram") or "")
            e = st.text_input("Correo", c.get("email") or "")
            ok = st.form_submit_button("Guardar datos", use_container_width=True)
        if ok:
            try:
                db.table("clientes").update({
                    "nombre": n.strip() or "Sin nombre", "instagram": normalizar_instagram(t) or None,
                    "clave": clave_cliente(t, n), "email": e.strip() or None,
                }).eq("id", c["id"]).execute()
                st.session_state.flash = "Datos del cliente actualizados"
                st.rerun()
            except Exception as ex:
                st.error(f"No se pudo guardar. Detalle técnico: {ex}")
        st.write(f"Compras: {a_int(c.get('compras'))}  ·  Total gastado: {money(a_int(c.get('total_gastado')))}")
    with col_b:
        st.subheader("Compras y comprobantes")
        try:
            compras = db.table("compras").select("*").eq("cliente_id", c["id"]).order("creado_en", desc=True).execute().data or []
        except Exception as ex:
            st.error(f"No se pudieron leer las compras. Ejecuta actualizacion_pagos.sql en Supabase. Detalle: {ex}")
            compras = []
        if not compras:
            st.write("Sin compras con comprobante todavía.")
        for k in compras:
            fecha = pd.to_datetime(k["creado_en"], utc=True).tz_convert("America/Santiago").strftime("%d-%m-%Y")
            with st.expander(f"Compra N° {k['id']:06d} · {fecha} · {money(k['total'])}"):
                for it in k["items"]:
                    st.write(f"- {it['cantidad']} × {it['nombre']} (talla {it.get('talla') or 'única'})")
                mostrar_pagos([{**pg, "verificado": True} for pg in (k.get("pagos") or [])])
                st.download_button("Descargar comprobante", data=comprobante_html(k),
                                   file_name=f"comprobante_{k['id']:06d}.html", mime="text/html", key=f"dl_{k['id']}")


def admin_finanzas():
    st.title("Resumen de Finanzas")
    ventas = db.table("ventas").select("*").order("creado_en", desc=True).limit(2000).execute().data or []
    pend = db.table("reservas").select("id", count="exact").eq("estado", "pendiente").execute().count or 0
    if not ventas:
        st.info("Todavía no hay ventas registradas.")
        st.metric("Reservas pendientes", pend)
        return
    df = pd.DataFrame(ventas)
    df["fecha"] = pd.to_datetime(df["creado_en"], utc=True).dt.tz_convert("America/Santiago")
    hoy = pd.Timestamp.now(tz="America/Santiago").date()
    h = df[df["fecha"].dt.date == hoy]
    total_hoy = int(h["total"].sum())
    prendas = int(h["cantidad"].sum())
    transf = h.loc[h["metodo_pago"] == "Transferencia", "total"].sum()
    if "compra_id" in h:
        mixtos = [int(x) for x in h.loc[h["metodo_pago"] == "Mixto", "compra_id"].dropna().unique()]
        if mixtos:
            for k in db.table("compras").select("pagos").in_("id", mixtos).execute().data or []:
                transf += sum(a_int(pg.get("monto")) for pg in (k.get("pagos") or []) if pg.get("metodo") == "Transferencia")
    pct = (transf / total_hoy * 100) if total_hoy else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total recaudado hoy", money(total_hoy))
    c2.metric("Prendas vendidas hoy", prendas)
    c3.metric("% en transferencias", f"{pct:.0f}%")
    c4.metric("Reservas pendientes", pend)

    st.divider()
    st.subheader("Ventas por día (últimos 14 días)")
    por_dia = df.groupby(df["fecha"].dt.date)["total"].sum().sort_index().tail(14)
    st.bar_chart(por_dia)

    st.subheader("Últimas ventas")
    tabla = df[["fecha", "nombre_producto", "cantidad", "total", "metodo_pago", "cliente"]].head(30).copy()
    tabla["fecha"] = tabla["fecha"].dt.strftime("%d-%m %H:%M")
    st.dataframe(tabla, hide_index=True, use_container_width=True)


def admin_diseno(cfg):
    st.title("Diseño de la App")
    st.info("Cambia solo lo que quieras: lo que no toques se queda como está. Presiona 'Guardar diseño' al final.")
    nuevo = dict(cfg)

    st.subheader("Colores")
    c1, c2 = st.columns(2)
    nuevo["color_fondo"] = c1.color_picker("Fondo principal", cfg["color_fondo"])
    nuevo["color_banner"] = c2.color_picker("Color del banner", cfg["color_banner"])
    nuevo["color_lateral"] = c1.color_picker("Fondo barra lateral", cfg["color_lateral"])
    nuevo["color_texto"] = c2.color_picker("Color de textos", cfg["color_texto"])
    nuevo["color_boton"] = c1.color_picker("Color de botones", cfg["color_boton"])

    st.divider()
    st.subheader("Textos")
    st.caption("Si dejas un texto vacío, simplemente no se muestra.")
    nuevo["titulo"] = st.text_area("Título del banner", cfg["titulo"], height=80)
    nuevo["subtitulo"] = st.text_area("Subtítulo del banner", cfg["subtitulo"], height=80)
    nuevo["texto_catalogo"] = st.text_area("Texto sobre el catálogo (opcional, acepta **negrita**, enlaces y saltos de línea)",
                                           cfg["texto_catalogo"], height=100)
    nuevo["mensaje_reserva"] = st.text_area("Mensaje al confirmar una reserva (usa {nombre} para el nombre del cliente)",
                                            cfg["mensaje_reserva"], height=80)
    nuevo["datos_transferencia"] = st.text_area("Datos para transferir (se muestran al cliente que elige pagar por adelantado con transferencia)",
                                                cfg["datos_transferencia"], height=100,
                                                placeholder="Banco, tipo de cuenta, número, nombre, RUT y correo")
    nuevo["instagram"] = st.text_input("Link de Instagram (vacío = no mostrar el ícono)", cfg["instagram"])
    nuevo["tiktok"] = st.text_input("Link de TikTok (vacío = no mostrar el ícono)", cfg["tiktok"])

    st.divider()
    st.subheader("Tipografía")
    actual = nombre_fuente(cfg["fuente"])
    familias = {etiqueta: v[0] for etiqueta, v in FUENTES.items()}
    if actual not in familias.values():          # una fuente guardada antes que no está en la lista
        familias = {f"Actual - {actual}": actual, **familias}
    etiquetas = list(familias)
    elegida = st.selectbox("Estilo de letra", etiquetas,
                           index=next(i for i, e in enumerate(etiquetas) if familias[e] == actual))
    if familias[elegida] != actual:
        nuevo["fuente"] = familias[elegida]

    st.divider()
    st.subheader("Imágenes")
    logo = st.file_uploader("Logo de la tienda (aparece arriba a la izquierda, siempre)", type=["png", "jpg", "jpeg", "webp"])
    foto = st.file_uploader("Foto de fondo del banner (opcional)", type=["png", "jpg", "jpeg", "webp"])
    if cfg.get("banner_url") and st.checkbox("Quitar foto actual del banner"):
        nuevo["banner_url"] = ""

    if st.button("GUARDAR DISEÑO DEL DROP", use_container_width=True):
        try:
            if logo:
                nuevo["logo_url"] = subir_imagen(logo, "logos")
            if foto:
                nuevo["banner_url"] = subir_imagen(foto, "banners")
            # Se guarda SOLO lo que cambió; el resto queda intacto
            cambios = {k: v for k, v in nuevo.items() if v != cfg.get(k)}
            if not cambios:
                st.info("No hay cambios que guardar.")
            else:
                guardar_config(cambios)
                st.session_state.flash = "Diseño guardado"
                st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar. Si dice que falta una columna, ejecuta actualizacion_diseno.sql en Supabase. Detalle: {e}")


# ----------------------------------------------------------------------
# FLUJO PRINCIPAL
# ----------------------------------------------------------------------
cfg = cargar_config()
aplicar_estilos(cfg)
if cfg.get("logo_url"):
    st.logo(cfg["logo_url"], size="large")  # logo fijo arriba a la izquierda, independiente del banner

if "admin" not in st.session_state:
    st.session_state.admin = False
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

with st.sidebar:
    st.markdown(f"## {'Panel ' if st.session_state.admin else ''}{cfg['nombre_tienda']}")
    if not st.session_state.admin:
        st.caption("Reserva tus prendas y retíralas en tienda.")
        with st.expander("Acceso administrador"):
            with st.form("login"):
                correo = st.text_input("Correo")
                clave = st.text_input("Contraseña", type="password")
                entrar = st.form_submit_button("Entrar", use_container_width=True)
            if entrar:
                adm = st.secrets.get("admin", {})
                if correo.strip() == adm.get("email", "admin@sceneone.cl") and clave == adm.get("password", "scene1234"):
                    st.session_state.admin = True
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos")
        menu = "Tienda"
    else:
        menu = st.radio("Navegación", ["Tienda", "Reservas", "Punto de Venta",
                                       "Inventario", "Clientes", "Finanzas y Totales", "Diseño de la App"])
        st.divider()
        st.success("Sesión iniciada como Admin")
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.admin = False
            st.rerun()

if menu.startswith("Tienda"):
    vista_tienda(cfg)
elif menu == "Reservas":
    admin_reservas()
elif menu == "Punto de Venta":
    admin_pos()
elif menu == "Inventario":
    admin_inventario()
elif menu == "Clientes":
    admin_clientes()
elif menu == "Finanzas y Totales":
    admin_finanzas()
elif menu == "Diseño de la App":
    admin_diseno(cfg)

    