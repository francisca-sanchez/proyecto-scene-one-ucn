"""
SCENE ONE - Tienda de reservas + Panel de gestión (Streamlit + Supabase)
Ejecutar con:  streamlit run app.py
"""
import re
import smtplib
import uuid
from datetime import timedelta
from email.message import EmailMessage
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
    "mensaje_reserva": "¡Listo {nombre}! Tu reserva quedó registrada.",
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


def validar_descuento(codigo):
    """Comprueba un código de descuento. Devuelve (descuento, mensaje_de_error)."""
    cod = re.sub(r"\s+", "", codigo or "").upper()
    if not cod:
        return None, "Escribe un código."
    try:
        r = db.table("descuentos").select("*").eq("codigo", cod).limit(1).execute().data
    except Exception:
        return None, "Los códigos de descuento no están disponibles por ahora."
    if not r:
        return None, "Ese código no existe."
    d = r[0]
    if not d.get("activo", True):
        return None, "Ese código no está activo."
    hoy = pd.Timestamp.now(tz="America/Santiago").date()
    if d.get("vence") and hoy > pd.to_datetime(d["vence"]).date():
        return None, "Ese código ya venció."
    if d.get("cupos_total") is not None and a_int(d.get("usos")) >= a_int(d["cupos_total"]):
        return None, "Ese código ya no tiene cupos disponibles."
    return d, None


def crear_reserva(cliente, instagram, email, nota, carrito, adelanto="", pagos=None, codigo=None):
    """Descuenta stock (queda 'apartado') y guarda la reserva como pendiente."""
    prods = {p["id"]: p for p in listar_productos(False)}
    for it in carrito.values():
        if prods.get(it["id"], {}).get("stock", 0) < it["cantidad"]:
            return False, f"No hay stock suficiente de {it['nombre']}."
    items = list(carrito.values())
    subtotal = sum(i["precio"] * i["cantidad"] for i in items)
    datos = {
        "cliente": cliente, "instagram": instagram or None, "email": email or None, "nota": nota or None,
        "items": items, "estado": "pendiente", "adelanto": adelanto or None, "pagos": pagos or [],
    }
    desc = None
    if codigo:
        desc, err = validar_descuento(codigo)
        if err:
            return False, err
        monto = int(round(subtotal * desc["porcentaje"] / 100))
        datos.update({"subtotal": subtotal, "descuento_codigo": desc["codigo"],
                      "descuento_pct": desc["porcentaje"], "descuento_monto": monto})
        subtotal -= monto
    datos["total"] = subtotal
    # el stock se descuenta solo cuando todo lo anterior salió bien
    for it in carrito.values():
        nuevo = prods[it["id"]]["stock"] - it["cantidad"]
        db.table("productos").update({"stock": nuevo}).eq("id", it["id"]).execute()
    reserva = db.table("reservas").insert(datos).execute().data[0]
    if desc:
        db.table("descuentos").update({"usos": a_int(desc.get("usos")) + 1}).eq("id", desc["id"]).execute()
    return True, reserva


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


def finalizar_compra(items, cliente, instagram, email, nota, pagos, origen, reserva_id=None, descontar_stock=True, descuento=None):
    """Crea la compra con sus pagos y comprobantes, las ventas por prenda y actualiza al cliente.
    Devuelve (compra, mensaje_de_error)."""
    subtotal = sum(a_int(i["precio"]) * a_int(i["cantidad"]) for i in items)
    monto_desc = a_int((descuento or {}).get("monto"))
    total = subtotal - monto_desc
    try:
        actuales = {}
        if descontar_stock:
            for it in items:
                r = db.table("productos").select("stock").eq("id", it["id"]).execute().data
                actuales[it["id"]] = r[0]["stock"] if r else 0
                if actuales[it["id"]] < it["cantidad"]:
                    return None, f"No hay stock suficiente de {it['nombre']}."
        cliente_id = registrar_cliente(cliente, instagram, email, total)
        datos = {
            "cliente_id": cliente_id, "cliente": cliente, "instagram": normalizar_instagram(instagram) or None,
            "email": email or None, "nota": nota or None, "items": items, "total": total,
            "pagos": pagos, "origen": origen, "reserva_id": reserva_id,
        }
        if monto_desc:
            datos.update({"subtotal": subtotal, "descuento_codigo": descuento.get("codigo"),
                          "descuento_pct": a_int(descuento.get("pct")), "descuento_monto": monto_desc})
        compra = db.table("compras").insert(datos).execute().data[0]
        if descontar_stock:
            for it in items:
                db.table("productos").update({"stock": actuales[it["id"]] - it["cantidad"]}).eq("id", it["id"]).execute()
        metodo = metodo_resumen(pagos)
        lineas = [a_int(i["precio"]) * a_int(i["cantidad"]) for i in items]
        if monto_desc and subtotal:                         # reparte el descuento entre las prendas
            lineas = [int(round(x * total / subtotal)) for x in lineas]
            lineas[-1] += total - sum(lineas)
        for it, linea in zip(items, lineas):
            db.table("ventas").insert({
                "producto_id": it["id"], "nombre_producto": it["nombre"], "cantidad": it["cantidad"],
                "total": linea, "metodo_pago": metodo,
                "cliente": cliente, "compra_id": compra["id"],
            }).execute()
        return compra, None
    except Exception as e:
        return None, f"No se pudo registrar la venta. Detalle técnico: {e}"


def corregir_total_venta(k, nuevo_total, montos, motivo, corte=None):
    """Cambia el total de una venta ya registrada y deja todo cuadrado: ventas (Finanzas), pagos, ficha del
    cliente y comprobante. Guarda el registro de la corrección. Devuelve un mensaje de error o None."""
    antes, nuevo = a_int(k["total"]), a_int(nuevo_total)
    try:
        filas = db.table("ventas").select("id,total,creado_en").eq("compra_id", k["id"]).execute().data or []
        if corte and any(pd.to_datetime(f["creado_en"], utc=True, format="ISO8601") <= pd.to_datetime(corte, utc=True, format="ISO8601")
                         for f in filas):
            return "Esa venta pertenece a una tanda ya cerrada. Deshaz el cierre en Finanzas si necesitas corregirla."

        pagos = [dict(pg) for pg in (k.get("pagos") or [])]
        if len(pagos) == 1:
            pagos[0]["monto"] = nuevo
        else:
            for i, m in (montos or {}).items():
                pagos[i]["monto"] = a_int(m)
        subtotal = a_int(k.get("subtotal")) or sum(a_int(i["precio"]) * a_int(i["cantidad"]) for i in k["items"])
        esperado = subtotal - a_int(k.get("descuento_monto"))
        ajuste = nuevo - esperado                                   # 0 si el total vuelve a ser el original

        # 1) primero el registro: si falla (tabla sin crear), no se cambia nada
        db.table("correcciones_venta").insert({
            "compra_id": k["id"], "cliente": k.get("cliente"), "total_anterior": antes,
            "total_nuevo": nuevo, "motivo": motivo}).execute()
        # 2) ventas por prenda (lo que lee Finanzas): se reparte el nuevo total en proporción
        if filas:
            viejos = [a_int(f["total"]) for f in filas]
            suma = sum(viejos)
            nuevos = [int(round(v * nuevo / suma)) for v in viejos] if suma > 0 else [nuevo] + [0] * (len(filas) - 1)
            nuevos[-1] += nuevo - sum(nuevos)
            for f, t in zip(filas, nuevos):
                db.table("ventas").update({"total": t}).eq("id", f["id"]).execute()
        # 3) lo gastado por el cliente
        if k.get("cliente_id"):
            c = db.table("clientes").select("id,total_gastado").eq("id", k["cliente_id"]).limit(1).execute().data
            if c:
                db.table("clientes").update({"total_gastado": max(a_int(c[0].get("total_gastado")) + nuevo - antes, 0)}
                                            ).eq("id", c[0]["id"]).execute()
        # 4) la venta y su comprobante
        db.table("compras").update({"total": nuevo, "pagos": pagos, "ajuste_monto": ajuste}).eq("id", k["id"]).execute()
        return None
    except Exception as e:
        return f"No se pudo corregir la venta. Si dice que falta una tabla o columna, ejecuta actualizacion_correcciones.sql en Supabase. Detalle: {e}"


def concretar_reserva(reserva, pagos):
    """La reserva ya está pagada: se convierte en compra (el stock ya estaba descontado)."""
    compra, err = finalizar_compra(reserva["items"], reserva["cliente"], reserva.get("instagram"), reserva.get("email"),
                                   reserva.get("nota"), pagos, "reserva", reserva["id"], descontar_stock=False,
                                   descuento=({"codigo": reserva.get("descuento_codigo"), "pct": reserva.get("descuento_pct"),
                                               "monto": reserva.get("descuento_monto")} if a_int(reserva.get("descuento_monto")) else None))
    if err:
        return None, err
    db.table("reservas").update({"estado": "vendida", "pagos": pagos}).eq("id", reserva["id"]).execute()
    return compra, None


def correo_valido(v):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (v or "").strip()))


def enviar_correo(destino, asunto, texto, html):
    """Envía un correo por SMTP. Devuelve True si salió; False si no está configurado o falló."""
    try:
        host, usuario, clave = st.secrets.get("SMTP_HOST"), st.secrets.get("SMTP_USER"), st.secrets.get("SMTP_PASSWORD")
        if not (host and usuario and clave):
            print("[correo] SMTP no configurado en secrets.toml: no se envió el correo.")
            return False
        puerto = int(st.secrets.get("SMTP_PORT", 465))
        remitente = st.secrets.get("SMTP_FROM", usuario)
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = asunto, f"{NOMBRE_TIENDA} <{remitente}>", destino
        msg.set_content(texto)
        msg.add_alternative(html, subtype="html")
        if puerto == 465:
            with smtplib.SMTP_SSL(host, puerto, timeout=15) as srv:
                srv.login(usuario, clave)
                srv.send_message(msg)
        else:
            with smtplib.SMTP(host, puerto, timeout=15) as srv:
                srv.starttls()
                srv.login(usuario, clave)
                srv.send_message(msg)
        return True
    except Exception as e:
        print(f"[correo] no se pudo enviar a {destino}: {e}")
        return False


def money_signado(n):
    return ("-" if n < 0 else "+") + money(abs(n))


def filas_descuento(x):
    """Filas de subtotal, descuento y ajuste manual para boletas y comprobantes (vacío si no hay nada de eso)."""
    desc, ajuste = a_int(x.get("descuento_monto")), a_int(x.get("ajuste_monto"))
    if not desc and not ajuste:
        return ""
    subtotal = a_int(x.get("subtotal")) or sum(a_int(i.get("precio")) * a_int(i.get("cantidad")) for i in (x.get("items") or []))
    filas = f"<tr><td colspan='2'>Subtotal</td><td style='text-align:right'>{money(subtotal)}</td></tr>"
    if desc:
        filas += (f"<tr><td colspan='2'>Descuento {html_lib.escape(str(x.get('descuento_codigo') or ''))} "
                  f"({a_int(x.get('descuento_pct'))}%)</td><td style='text-align:right'>-{money(desc)}</td></tr>")
    if ajuste:
        filas += f"<tr><td colspan='2'>Ajuste manual</td><td style='text-align:right'>{money_signado(ajuste)}</td></tr>"
    return filas


def boleta_reserva_texto(r):
    """Texto de la boleta de reserva: sirve para el correo y para copiar y pegar en un mensaje de Instagram."""
    lineas = [f"{NOMBRE_TIENDA} - Boleta de reserva N° {r['id']:06d}", f"Cliente: {r['cliente']}", ""]
    for it in r["items"]:
        lineas.append(f"- {it['cantidad']} x {it['nombre']} (talla {it.get('talla') or 'única'}): {money(it['precio'] * it['cantidad'])}")
    lineas.append("")
    if a_int(r.get("descuento_monto")):
        lineas += [f"Subtotal: {money(r['subtotal'])}",
                   f"Descuento {r.get('descuento_codigo')} ({a_int(r.get('descuento_pct'))}%): -{money(r['descuento_monto'])}"]
    lineas += [f"Total: {money(r['total'])}", "Coordinaremos contigo la entrega y el pago.",
               "Guarda esta boleta como respaldo de tu reserva."]
    return "\n".join(lineas)


def boleta_reserva_html(r):
    esc = html_lib.escape
    fecha = pd.to_datetime(r["creado_en"], utc=True, format="ISO8601").tz_convert("America/Santiago").strftime("%d-%m-%Y %H:%M")
    filas = "".join(
        f"<tr><td>{esc(str(it['nombre']))} (talla {esc(str(it.get('talla') or 'única'))})</td>"
        f"<td style='text-align:center'>{it['cantidad']}</td>"
        f"<td style='text-align:right'>{money(it['precio'] * it['cantidad'])}</td></tr>" for it in r["items"])
    datos = f"<b>Cliente:</b> {esc(r.get('cliente') or '')}<br>"
    if r.get("instagram"):
        datos += f"<b>Instagram:</b> @{esc(r['instagram'])}<br>"
    if r.get("email"):
        datos += f"<b>Correo:</b> {esc(r['email'])}<br>"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Boleta de reserva N° {r['id']:06d}</title></head>"
        "<body style=\"font-family:Arial,sans-serif;max-width:520px;margin:24px auto;padding:0 16px;color:#111;background:#fff;\">"
        f"<h2 style='margin:0'>{esc(NOMBRE_TIENDA)}</h2>"
        f"<p style='margin:4px 0 16px;color:#555'>Boleta de reserva N° {r['id']:06d}<br>{fecha}</p>"
        f"<p>{datos}</p>"
        "<table style='width:100%;border-collapse:collapse' cellpadding='6'>"
        "<tr style='border-bottom:1px solid #999'><th style='text-align:left'>Detalle</th><th>Cant.</th>"
        "<th style='text-align:right'>Subtotal</th></tr>"
        f"{filas}{filas_descuento(r)}"
        f"<tr style='border-top:2px solid #111'><td colspan='2'><b>TOTAL</b></td>"
        f"<td style='text-align:right'><b>{money(r['total'])}</b></td></tr></table>"
        "<p style='margin-top:18px'>Coordinaremos contigo la entrega y el pago.</p>"
        "<p style='color:#555;font-size:13px'>Guarda esta boleta como respaldo de tu reserva.</p>"
        "</body></html>")


def enviar_boleta_reserva(r):
    return enviar_correo(r["email"], f"Tu reserva N° {r['id']:06d} - {NOMBRE_TIENDA}",
                         boleta_reserva_texto(r), boleta_reserva_html(r))


def mostrar_boleta_reserva():
    """Boleta de la reserva que acaba de hacer el cliente (con descarga)."""
    r = st.session_state.get("ultima_reserva")
    if not r:
        return
    with st.container(border=True):
        st.markdown(f"**Boleta de reserva N° {r['id']:06d}** · Total {money(r['total'])}")
        b1, b2 = st.columns(2)
        b1.download_button("Descargar boleta", data=boleta_reserva_html(r), file_name=f"boleta_reserva_{r['id']:06d}.html",
                           mime="text/html", key="dl_boleta_res", use_container_width=True)
        if b2.button("Cerrar", key="cerrar_boleta_res", use_container_width=True):
            st.session_state.pop("ultima_reserva", None)
            st.rerun()
        with st.expander("Ver boleta"):
            components.html(boleta_reserva_html(r), height=420, scrolling=True)


def comprobante_html(c):
    """Comprobante de compra (HTML): se puede imprimir o guardar como PDF desde el navegador."""
    esc = html_lib.escape
    fecha = pd.to_datetime(c["creado_en"], utc=True, format="ISO8601").tz_convert("America/Santiago").strftime("%d-%m-%Y %H:%M")
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
        f"{filas}{filas_descuento(c)}"
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
    if reserva.get("descuento_codigo"):                      # el cupo del código vuelve a estar disponible
        try:
            d = db.table("descuentos").select("id,usos").eq("codigo", reserva["descuento_codigo"]).limit(1).execute().data
            if d:
                db.table("descuentos").update({"usos": max(a_int(d[0].get("usos")) - 1, 0)}).eq("id", d[0]["id"]).execute()
        except Exception:
            pass


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
.cart-total-label {{ font-size: .85rem; opacity: .7; letter-spacing: .12em; text-transform: uppercase; margin-top: 6px; }}
.cart-total {{ font-size: 2.6rem; font-weight: 800; line-height: 1.1; margin-bottom: 8px; }}
.sin-foto-mini {{ background:#e9ecef; color:#6c757d; width:80px; height:100px; border-radius:8px;
                  display:flex; align-items:center; justify-content:center; font-size:.7rem; font-weight:700; }}
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
                ya = carrito.get(p["id"], {}).get("cantidad", 0)
                disponible = a_int(p["stock"]) - ya           # el cliente no ve el stock, solo no puede pasarse de él
                if disponible <= 0:
                    st.caption("Ya tienes en tu reserva todas las unidades disponibles de esta talla.")
                else:
                    cantidad = st.number_input("Cantidad", min_value=1, max_value=disponible, value=1, step=1,
                                               key=f"cant_{p['id']}_{disponible}")
                    if st.button("Agregar a mi reserva", key=f"add_{p['id']}", use_container_width=True):
                        carrito[p["id"]] = {"id": p["id"], "nombre": p["nombre"], "talla": p.get("talla"),
                                            "precio": p["precio"], "cantidad": ya + int(cantidad),
                                            "imagen_url": p.get("imagen_url") or foto}
                        st.toast(f"{int(cantidad)} × {p['nombre']} (talla {talla}) agregado")
                        st.rerun()


def vista_tienda(cfg):
    hero(cfg)
    if "carrito" not in st.session_state:
        st.session_state.carrito = {}
    carrito = st.session_state.carrito

    if st.session_state.get("reserva_ok"):
        st.success(st.session_state.pop("reserva_ok"))
    mostrar_boleta_reserva()
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
            stock_actual = {p["id"]: a_int(p["stock"]) for p in listar_productos(False)}
            subtotal = sum(i["precio"] * i["cantidad"] for i in carrito.values())

            # Código de descuento aplicado: se vuelve a comprobar cada vez (fecha, cupos, si sigue activo)
            descuento, monto_desc = None, 0
            if st.session_state.get("codigo_descuento"):
                descuento, err = validar_descuento(st.session_state["codigo_descuento"])
                if err:
                    st.session_state.pop("codigo_descuento", None)
                    st.warning(f"Se quitó el código de descuento: {err}")
                    descuento = None
                else:
                    monto_desc = int(round(subtotal * descuento["porcentaje"] / 100))
            total = subtotal - monto_desc

            izq, der = st.columns([2, 1], gap="large")
            n = st.session_state.setdefault("res_n", 0)        # cambia al reservar, para limpiar el formulario
            with izq:
                st.markdown("### Tu carrito")
                for pid, it in list(carrito.items()):
                    with st.container(border=True):
                        c_foto, c_info, c_cant, c_quitar = st.columns([1, 3, 2, 1])
                        if it.get("imagen_url"):
                            c_foto.image(it["imagen_url"], width=80)
                        else:
                            c_foto.markdown("<div class='sin-foto-mini'>FOTO</div>", unsafe_allow_html=True)
                        c_info.markdown(f"**{it['nombre']}**")
                        c_info.caption(f"Talla {it.get('talla') or 'única'}")
                        c_info.markdown(f"<span class='precio'>{money(it['precio'])}</span>", unsafe_allow_html=True)
                        tope = max(stock_actual.get(pid, 0), 1)       # el cliente nunca ve el stock
                        nueva = c_cant.number_input("Cantidad", min_value=1, max_value=tope, value=min(it["cantidad"], tope),
                                                    step=1, key=f"cq_{pid}_{it['cantidad']}", label_visibility="collapsed")
                        if int(nueva) != it["cantidad"]:
                            it["cantidad"] = int(nueva)
                            st.rerun()
                        if c_quitar.button("Quitar", key=f"del_{pid}"):
                            del carrito[pid]
                            st.rerun()

                st.markdown("### Tus datos")
                nombre = st.text_input("Nombre y apellido *", key=f"res_nombre_{n}")
                mail = st.text_input("Correo *", placeholder="tucorreo@ejemplo.com", key=f"res_mail_{n}",
                                     help="Te enviaremos la boleta de tu reserva a este correo")
                ig = st.text_input("Tu usuario de Instagram (opcional)", placeholder="@tuusuario", key=f"res_ig_{n}")
                nota = st.text_area("Comentario (opcional)", placeholder="Ej: puedo retirar el sábado en la tarde",
                                    key=f"res_nota_{n}")

            with der:
                with st.container(border=True):
                    st.markdown("#### Resumen de la reserva")
                    f1, f2 = st.columns([3, 2])
                    f1.write(f"Subtotal ({sum(i['cantidad'] for i in carrito.values())} prendas)")
                    f2.markdown(f"<div style='text-align:right'>{money(subtotal)}</div>", unsafe_allow_html=True)
                    if descuento:
                        g1, g2 = st.columns([3, 2])
                        g1.write(f"Descuento {descuento['codigo']} ({descuento['porcentaje']}%)")
                        g2.markdown(f"<div style='text-align:right'>-{money(monto_desc)}</div>", unsafe_allow_html=True)
                    st.divider()
                    st.markdown("<div class='cart-total-label'>Total</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='cart-total'>{money(total)}</div>", unsafe_allow_html=True)
                    if descuento:
                        st.caption(f"Código aplicado: {descuento['codigo']}")
                        if st.button("Quitar código", key="quitar_cod", use_container_width=True):
                            st.session_state.pop("codigo_descuento", None)
                            st.rerun()
                    else:
                        cod = st.text_input("Código de descuento", placeholder="Ej: DESCUENTO123", key=f"cod_in_{n}")
                        if st.button("Aplicar código", key=f"aplicar_cod_{n}", use_container_width=True):
                            d, err = validar_descuento(cod)
                            if err:
                                st.warning(err)
                            else:
                                st.session_state.codigo_descuento = d["codigo"]
                                st.rerun()
                    st.divider()
                    enviar = st.button("CONFIRMAR RESERVA", use_container_width=True, key=f"res_enviar_{n}")
                    st.caption("Reservas ahora y coordinamos para la entrega")

            if enviar:
                if not nombre.strip():
                    st.warning("Falta tu nombre y apellido.")
                elif not correo_valido(mail):
                    st.warning("Escribe un correo válido: ahí te enviaremos la boleta de tu reserva.")
                else:
                    try:
                        ok, res = crear_reserva(nombre.strip(), normalizar_instagram(ig), mail.strip(), nota.strip(), carrito,
                                                codigo=descuento["codigo"] if descuento else None)
                    except Exception as e:
                        ok, res = False, f"No se pudo registrar la reserva. Detalle técnico: {e}"
                    if ok:
                        texto = (cfg.get("mensaje_reserva") or "Reserva registrada.").replace("{nombre}", nombre.strip().split()[0])
                        if enviar_boleta_reserva(res):
                            texto += f" Te enviamos la boleta a {mail.strip()}."
                        else:
                            texto += " No pudimos enviar el correo, pero puedes descargar tu boleta aquí abajo."
                        if normalizar_instagram(ig):
                            texto += " También te escribiremos por Instagram."
                        st.session_state.reserva_ok = texto
                        st.session_state.ultima_reserva = res
                        st.session_state.carrito = {}
                        st.session_state.pop("codigo_descuento", None)
                        st.session_state.res_n = n + 1
                        st.rerun()
                    else:
                        st.error(res)


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
            st.download_button("Descargar boleta de reserva", data=boleta_reserva_html(r),
                               file_name=f"boleta_reserva_{r['id']:06d}.html", mime="text/html", key=f"bol_{r['id']}")

            st.markdown(f"### Total: {money(total)}")
            if r.get("descuento_codigo"):
                st.caption(f"Incluye el código {r['descuento_codigo']} ({a_int(r.get('descuento_pct'))}% de descuento)")

            if estado != "pendiente":
                mostrar_pagos(pagos)
                continue

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
                nk = st.session_state.setdefault(f"pago_n_{r['id']}", 0)     # cambia al registrar, para limpiar los campos
                metodo_p = st.radio("Método de pago", ["Efectivo", "Transferencia"], horizontal=True, key=f"pm_{r['id']}_{nk}")
                monto_p = st.number_input("Monto recibido (CLP)", min_value=0, step=500, value=int(falta),
                                          key=f"pmo_{r['id']}_{nk}_{falta}")
                comp = None
                if metodo_p == "Transferencia":
                    st.caption("Revisa en la cuenta de la tienda que el depósito llegó y sube aquí la captura.")
                    comp = st.file_uploader("Comprobante de la transferencia (foto o captura)",
                                            type=["png", "jpg", "jpeg", "webp"], key=f"pc_{r['id']}_{nk}")
                if st.button("Registrar pago", key=f"pg_{r['id']}_{nk}", use_container_width=True):
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
                            st.session_state[f"pago_n_{r['id']}"] = nk + 1
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
    n = st.session_state.setdefault("pos_n", 0)        # cambia al registrar, para limpiar el formulario
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
        subtotal = sum(i["precio"] * i["cantidad"] for i in items)

        # Código de descuento: se vuelve a comprobar cada vez (fecha, cupos y si sigue activo)
        descuento, monto_desc, codigo_perdido = None, 0, False
        if items and st.session_state.get("pos_codigo"):
            descuento, err = validar_descuento(st.session_state["pos_codigo"])
            if err:
                st.session_state.pop("pos_codigo", None)
                st.warning(f"Se quitó el código de descuento: {err}")
                descuento, codigo_perdido = None, True
            else:
                monto_desc = int(round(subtotal * descuento["porcentaje"] / 100))
        total = subtotal - monto_desc

        if items:
            if descuento:
                st.write(f"Subtotal: {money(subtotal)}")
                st.write(f"Descuento {descuento['codigo']} ({descuento['porcentaje']}%): -{money(monto_desc)}")
                if st.button("Quitar código de descuento", key=f"pos_quitar_cod_{n}"):
                    st.session_state.pop("pos_codigo", None)
                    st.rerun()
            else:
                cod_in = st.text_input("Código de descuento (opcional)", placeholder="Ej: DESCUENTO123", key=f"pos_cod_in_{n}")
                if st.button("Aplicar código", key=f"pos_aplicar_cod_{n}"):
                    d_ok, err = validar_descuento(cod_in)
                    if err:
                        st.warning(err)
                    else:
                        st.session_state.pos_codigo = d_ok["codigo"]
                        st.rerun()
        st.markdown(f"### Total a cobrar: {money(total)}")

    if not items:
        return
    st.divider()
    st.subheader("Datos del cliente y pago")
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
        elif codigo_perdido:                               # el código dejó de valer: no se cobra sin avisar
            st.error("El código de descuento dejó de valer. Revisa el nuevo total y vuelve a presionar el botón.")
        else:
            if descuento:                                  # se comprueba otra vez justo antes de cobrar
                descuento, err_desc = validar_descuento(descuento["codigo"])
                if err_desc:
                    st.session_state.pop("pos_codigo", None)
                    st.error(f"El código de descuento ya no es válido: {err_desc}")
                    return
                monto_desc = int(round(subtotal * descuento["porcentaje"] / 100))
                total = subtotal - monto_desc
            try:
                url = subir_imagen(comp, "comprobantes") if metodo == "Transferencia" else None
            except Exception as e:
                st.error(f"No se pudo subir el comprobante. Detalle técnico: {e}")
                return
            pagos = [{"metodo": metodo, "monto": total, "url": url, "fecha": ahora(), "verificado": True, "origen": "admin"}]
            compra, err = finalizar_compra(items, nombre.strip(), ig, mail.strip(), None, pagos, "punto_de_venta",
                                           descuento={"codigo": descuento["codigo"], "pct": descuento["porcentaje"],
                                                      "monto": monto_desc} if descuento else None)
            if err:
                st.error(err)
            else:
                if descuento:                              # cada venta con código gasta un cupo
                    try:
                        db.table("descuentos").update({"usos": a_int(descuento.get("usos")) + 1}).eq("id", descuento["id"]).execute()
                    except Exception:
                        pass
                st.session_state.pop("pos_codigo", None)
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
            ok = st.form_submit_button("AGREGAR AL INVENTARIO", use_container_width=True)
        if ok:
            def norm(x):
                return (x or "").strip().lower()
            nombre_final = nombre.strip() or elegido or "Sin nombre"
            base = next((p for p in todos if norm(p["nombre"]) == norm(nombre_final)), None)
            categoria = categoria_sel or ((base.get("categoria") if base else "") or "")
            talla = talla_sel
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
        "Última compra": pd.to_datetime(df["ultima_compra"], utc=True, format="ISO8601").dt.tz_convert("America/Santiago").dt.strftime("%d-%m-%Y"),
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
            fecha = pd.to_datetime(k["creado_en"], utc=True, format="ISO8601").tz_convert("America/Santiago").strftime("%d-%m-%Y")
            with st.expander(f"Compra N° {k['id']:06d} · {fecha} · {money(k['total'])}"):
                for it in k["items"]:
                    st.write(f"- {it['cantidad']} × {it['nombre']} (talla {it.get('talla') or 'única'})")
                mostrar_pagos([{**pg, "verificado": True} for pg in (k.get("pagos") or [])])
                st.download_button("Descargar comprobante", data=comprobante_html(k),
                                   file_name=f"comprobante_{k['id']:06d}.html", mime="text/html", key=f"dl_{k['id']}")


def ventas_desde(corte=None):
    """Todas las ventas posteriores al último cierre (de a 1000, que es lo máximo que entrega Supabase por consulta)."""
    filas, ini = [], 0
    while True:
        q = db.table("ventas").select("*").order("creado_en", desc=True)
        if corte:
            q = q.gt("creado_en", corte)
        lote = q.range(ini, ini + 999).execute().data or []
        filas += lote
        if len(lote) < 1000:
            return filas
        ini += 1000


def resumen_ventas(df):
    """Totales de un conjunto de ventas: recaudado, prendas, ventas, efectivo y transferencia."""
    total = int(df["total"].sum())
    transf = int(df.loc[df["metodo_pago"] == "Transferencia", "total"].sum())
    if "compra_id" in df:
        mixtos = [int(x) for x in df.loc[df["metodo_pago"] == "Mixto", "compra_id"].dropna().unique()]
        if mixtos:
            for k in db.table("compras").select("pagos").in_("id", mixtos).execute().data or []:
                transf += sum(a_int(pg.get("monto")) for pg in (k.get("pagos") or []) if pg.get("metodo") == "Transferencia")
        ventas = int(df["compra_id"].dropna().nunique() + df["compra_id"].isna().sum())
    else:
        ventas = len(df)
    transf = min(transf, total)
    fechas = pd.to_datetime(df["creado_en"], utc=True, format="ISO8601")
    return {"total": total, "prendas": int(df["cantidad"].sum()), "ventas": ventas,
            "transferencia": transf, "efectivo": total - transf,
            "desde": fechas.min().isoformat(), "hasta": fechas.max().isoformat()}


def fecha_corta(v):
    return pd.to_datetime(v, utc=True, format="ISO8601").tz_convert("America/Santiago").strftime("%d-%m-%Y")


def admin_correcciones(corte):
    st.subheader("Corregir el total de una venta")
    try:
        q = db.table("compras").select("*").order("creado_en", desc=True).limit(300)
        if corte:
            q = q.gt("creado_en", corte)
        compras = q.execute().data or []
    except Exception as e:
        st.error(f"No se pudieron leer las ventas. Ejecuta actualizacion_pagos.sql en Supabase. Detalle: {e}")
        return

    if not compras:
        st.info("No hay ventas con comprobante en esta tanda.")
    else:
        def etiqueta(c):
            f = pd.to_datetime(c["creado_en"], utc=True, format="ISO8601").tz_convert("America/Santiago").strftime("%d-%m %H:%M")
            return f"N° {c['id']:06d} · {f} · {c.get('cliente') or 'Sin nombre'} · {money(c['total'])}" + (
                " (corregida)" if a_int(c.get("ajuste_monto")) else "")
        k = st.selectbox("Venta", compras, format_func=etiqueta)
        for it in k["items"]:
            st.write(f"- {it['cantidad']} × {it['nombre']} (talla {it.get('talla') or 'única'})")
        pagos = k.get("pagos") or []
        for pg in pagos:
            st.write(f"Pago en {pg['metodo'].lower()}: {money(a_int(pg.get('monto')))}")
        st.markdown(f"**Total actual: {money(k['total'])}**")

        with st.form(f"form_corr_{k['id']}", clear_on_submit=True):
            nuevo_total = st.number_input("Nuevo total (CLP)", min_value=0, step=500, value=int(a_int(k["total"])))
            montos = {}
            if len(pagos) > 1:
                st.caption("Esta venta tiene varios pagos: indica cuánto corresponde a cada uno (deben sumar el nuevo total).")
                for i, pg in enumerate(pagos):
                    montos[i] = st.number_input(f"Monto en {pg['metodo'].lower()}", min_value=0, step=500,
                                                value=int(a_int(pg.get("monto"))), key=f"corr_pago_{k['id']}_{i}")
            motivo = st.text_input("Motivo de la corrección *", placeholder="Ej: se cobró de más")
            ok = st.form_submit_button("Guardar corrección", use_container_width=True)
        if ok:
            if not motivo.strip():
                st.warning("Escribe el motivo de la corrección.")
            elif a_int(nuevo_total) == a_int(k["total"]):
                st.info("El nuevo total es igual al actual: no hay nada que cambiar.")
            elif len(pagos) > 1 and sum(a_int(m) for m in montos.values()) != a_int(nuevo_total):
                st.error(f"Los pagos deben sumar el nuevo total. Ahora suman {money(sum(a_int(m) for m in montos.values()))}.")
            else:
                err = corregir_total_venta(k, nuevo_total, montos, motivo.strip(), corte)
                if err:
                    st.error(err)
                else:
                    st.session_state.flash = f"Total de la venta N° {k['id']:06d} corregido"
                    st.rerun()

    st.markdown("**Historial de correcciones**")
    try:
        hist = db.table("correcciones_venta").select("*").order("creado_en", desc=True).limit(100).execute().data or []
    except Exception:
        st.caption("Para registrar correcciones, ejecuta actualizacion_correcciones.sql en Supabase.")
        return
    if not hist:
        st.caption("Todavía no se ha corregido ninguna venta.")
        return
    st.dataframe(pd.DataFrame({
        "Fecha": [pd.to_datetime(h["creado_en"], utc=True, format="ISO8601").tz_convert("America/Santiago").strftime("%d-%m-%Y %H:%M") for h in hist],
        "Venta": [f"N° {h['compra_id']:06d}" for h in hist],
        "Cliente": [h.get("cliente") or "" for h in hist],
        "Total anterior": [money(h["total_anterior"]) for h in hist],
        "Total nuevo": [money(h["total_nuevo"]) for h in hist],
        "Diferencia": [money_signado(a_int(h["total_nuevo"]) - a_int(h["total_anterior"])) for h in hist],
        "Motivo": [h.get("motivo") or "" for h in hist],
    }), hide_index=True, use_container_width=True)


def admin_finanzas():
    st.title("Resumen de Finanzas")
    tandas_ok = True
    try:
        cierres = db.table("tandas_finanzas").select("*").order("cerrada_en", desc=True).execute().data or []
    except Exception as e:
        cierres, tandas_ok = [], False
        st.error(f"Falta crear la tabla del historial: ejecuta actualizacion_tandas.sql en Supabase. Detalle: {e}")
    corte = cierres[0]["hasta"] if cierres else None          # la tanda actual cuenta desde el último cierre

    ventas = ventas_desde(corte)
    pend = db.table("reservas").select("id", count="exact").eq("estado", "pendiente").execute().count or 0
    hay_ventas = bool(ventas)

    if not hay_ventas:
        st.info("Todavía no hay ventas en esta tanda." if corte else "Todavía no hay ventas registradas.")
        st.metric("Reservas pendientes", pend)
    else:
        df = pd.DataFrame(ventas)
        df["fecha"] = pd.to_datetime(df["creado_en"], utc=True, format="ISO8601").dt.tz_convert("America/Santiago")
        r = resumen_ventas(df)
        hoy = pd.Timestamp.now(tz="America/Santiago").date()
        total_hoy = int(df.loc[df["fecha"].dt.date == hoy, "total"].sum())
        pct = (r["transferencia"] / r["total"] * 100) if r["total"] else 0

        st.caption(f"Tanda actual: desde el {fecha_corta(r['desde'])}"
                   + (f" (después del cierre del {fecha_corta(cierres[0]['cerrada_en'])})" if cierres else ""))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total recaudado", money(r["total"]))
        c2.metric("Prendas vendidas", r["prendas"])
        c3.metric("Ventas realizadas", r["ventas"])
        c4.metric("% en transferencias", f"{pct:.0f}%")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Recaudado hoy", money(total_hoy))
        c6.metric("En efectivo", money(r["efectivo"]))
        c7.metric("En transferencia", money(r["transferencia"]))
        c8.metric("Reservas pendientes", pend)

        st.divider()
        st.subheader("Ventas por día")
        por_dia = df.groupby(df["fecha"].dt.date)["total"].sum().sort_index().tail(30)
        st.bar_chart(por_dia)

        st.subheader("Últimas ventas")
        tabla = df[["fecha", "nombre_producto", "cantidad", "total", "metodo_pago", "cliente"]].head(30).copy()
        tabla["fecha"] = tabla["fecha"].dt.strftime("%d-%m %H:%M")
        st.dataframe(tabla, hide_index=True, use_container_width=True)

        st.divider()
        admin_correcciones(corte)

    st.divider()
    st.subheader("Cerrar tanda")
    tn = st.session_state.setdefault("tanda_n", 0)             # cambia al cerrar, para limpiar los campos
    nombre_tanda = st.text_input("Nombre de la tanda (opcional)", placeholder="Ej: Drop 01", key=f"tanda_nombre_{tn}")
    confirmar = st.checkbox("Confirmo que quiero resetear las finanzas y guardar esta tanda en el historial", key=f"tanda_ok_{tn}")
    if hay_ventas:
        st.caption(f"Se guardará: {money(r['total'])} · {r['prendas']} prendas · {r['ventas']} ventas "
                   f"· del {fecha_corta(r['desde'])} al {fecha_corta(r['hasta'])}")
    if st.button("RESETEAR FINANZAS Y GUARDAR HISTORIAL", use_container_width=True, key=f"tanda_btn_{tn}",
                 disabled=not (confirmar and hay_ventas and tandas_ok)):
        try:
            db.table("tandas_finanzas").insert({
                "nombre": nombre_tanda.strip() or None, "desde": r["desde"], "hasta": r["hasta"],
                "total": r["total"], "prendas": r["prendas"], "ventas": r["ventas"],
                "efectivo": r["efectivo"], "transferencia": r["transferencia"],
            }).execute()
            st.session_state.tanda_n = tn + 1
            st.session_state.flash = "Tanda cerrada y guardada en el historial"
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar la tanda. Detalle técnico: {e}")

    st.divider()
    st.subheader("Historial de tandas")
    if not cierres:
        st.info("Todavía no hay tandas cerradas.")
        return
    h1, h2 = st.columns(2)
    h1.metric("Tandas cerradas", len(cierres))
    h2.metric("Total de todas las tandas", money(sum(a_int(c["total"]) for c in cierres)))
    tabla = pd.DataFrame({
        "Tanda": [c.get("nombre") or f"Tanda {len(cierres) - i}" for i, c in enumerate(cierres)],
        "Desde": [fecha_corta(c["desde"]) for c in cierres],
        "Hasta": [fecha_corta(c["hasta"]) for c in cierres],
        "Total recaudado": [money(c["total"]) for c in cierres],
        "Prendas": [a_int(c["prendas"]) for c in cierres],
        "Ventas": [a_int(c["ventas"]) for c in cierres],
        "Efectivo": [money(c["efectivo"]) for c in cierres],
        "Transferencia": [money(c["transferencia"]) for c in cierres],
        "% transf.": [f"{(a_int(c['transferencia']) / a_int(c['total']) * 100) if a_int(c['total']) else 0:.0f}%" for c in cierres],
        "Cerrada el": [fecha_corta(c["cerrada_en"]) for c in cierres],
    })
    st.dataframe(tabla, hide_index=True, use_container_width=True)

    deshacer = st.checkbox("Quiero deshacer el último cierre (sus ventas vuelven a contarse en la tanda actual)", key=f"tanda_undo_{tn}")
    if st.button("Deshacer último cierre", disabled=not deshacer, key=f"tanda_undo_btn_{tn}"):
        db.table("tandas_finanzas").delete().eq("id", cierres[0]["id"]).execute()
        st.session_state.tanda_n = tn + 1
        st.session_state.flash = "Último cierre deshecho"
        st.rerun()


def admin_descuentos():
    st.subheader("Códigos de descuento")
    st.caption("Los clientes los escriben en su carrito. Cada código funciona de forma independiente del botón 'Guardar diseño'.")
    try:
        codigos = db.table("descuentos").select("*").order("creado_en", desc=True).execute().data or []
    except Exception as e:
        st.error(f"No se pudieron leer los códigos. Ejecuta actualizacion_descuentos.sql en Supabase. Detalle: {e}")
        return

    if codigos:
        def nz(v):
            return None if pd.isna(v) else v
        df = pd.DataFrame({
            "id": [c["id"] for c in codigos],
            "Código": [c["codigo"] for c in codigos],
            "Descuento %": [c["porcentaje"] for c in codigos],
            "Vence (vacío = sin fecha)": [pd.to_datetime(c["vence"]).date() if c.get("vence") else None for c in codigos],
            "Cupos (vacío = ilimitados)": pd.array([c.get("cupos_total") for c in codigos], dtype="Int64"),
            "Usos": [a_int(c.get("usos")) for c in codigos],
            "Activo": [bool(c.get("activo", True)) for c in codigos],
        })
        editado = st.data_editor(
            df, hide_index=True, use_container_width=True, disabled=["id", "Usos"], key="ed_descuentos",
            column_config={
                "id": None,
                "Descuento %": st.column_config.NumberColumn(min_value=1, max_value=100, step=1),
                "Vence (vacío = sin fecha)": st.column_config.DateColumn(format="DD-MM-YYYY"),
                "Cupos (vacío = ilimitados)": st.column_config.NumberColumn(min_value=1, step=1),
            })
        if st.button("Guardar cambios de los códigos"):
            try:
                n = 0
                for i in df.index:
                    if any(nz(df.loc[i, c]) != nz(editado.loc[i, c]) for c in df.columns):
                        r = editado.loc[i]
                        vence = nz(r["Vence (vacío = sin fecha)"])
                        cupos = nz(r["Cupos (vacío = ilimitados)"])
                        db.table("descuentos").update({
                            "codigo": re.sub(r"\s+", "", str(r["Código"])).upper(),
                            "porcentaje": min(max(a_int(r["Descuento %"]), 1), 100),
                            "vence": pd.to_datetime(vence).date().isoformat() if vence is not None else None,
                            "cupos_total": a_int(cupos) if cupos is not None else None,
                            "activo": bool(r["Activo"]),
                        }).eq("id", int(r["id"])).execute()
                        n += 1
                st.session_state.flash = f"{n} código(s) actualizado(s)"
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar. Detalle técnico: {e}")
        with st.form("form_borrar_descuento", clear_on_submit=True):
            elegido = st.selectbox("Eliminar un código", codigos, format_func=lambda c: f"{c['codigo']} ({c['porcentaje']}%)")
            ok_del = st.form_submit_button("Eliminar código")
        if ok_del:
            db.table("descuentos").delete().eq("id", elegido["id"]).execute()
            st.session_state.flash = "Código eliminado"
            st.rerun()
    else:
        st.info("Todavía no hay códigos de descuento.")

    st.markdown("**Crear un código nuevo**")
    nd = st.session_state.setdefault("desc_n", 0)          # cambia al crear, para limpiar los campos
    hoy = pd.Timestamp.now(tz="America/Santiago").date()
    d1, d2 = st.columns(2)
    codigo = d1.text_input("Nombre del código", placeholder="DESCUENTO123", key=f"dc_{nd}")
    pct = d2.number_input("Porcentaje de descuento (%)", min_value=1, max_value=100, value=10, step=1, key=f"dp_{nd}")
    duracion = st.radio("Duración", ["Sin fecha de término", "Hasta una fecha"], horizontal=True, key=f"dd_{nd}")
    vence = None
    if duracion == "Hasta una fecha":
        vence = st.date_input("Válido hasta (inclusive)", value=hoy + timedelta(days=30), min_value=hoy, key=f"dv_{nd}")
    usos = st.radio("Usos", ["Ilimitados", "Con cupos"], horizontal=True, key=f"du_{nd}")
    cupos = None
    if usos == "Con cupos":
        cupos = st.number_input("Cantidad de usos disponibles", min_value=1, value=10, step=1, key=f"dcu_{nd}")
    if st.button("Crear código", key=f"crear_desc_{nd}"):
        limpio = re.sub(r"\s+", "", codigo).upper()
        if not limpio:
            st.warning("Escribe el nombre del código.")
        else:
            try:
                db.table("descuentos").insert({
                    "codigo": limpio, "porcentaje": int(pct),
                    "vence": vence.isoformat() if vence else None,
                    "cupos_total": int(cupos) if cupos else None, "activo": True,
                }).execute()
                st.session_state.desc_n = nd + 1
                st.session_state.flash = f"Código {limpio} creado"
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo crear el código (¿ya existe uno con ese nombre?). Detalle técnico: {e}")


def admin_diseno(cfg):
    st.title("Diseño de la App")
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
    nuevo["mensaje_reserva"] = st.text_area("Mensaje al confirmar una reserva (usa {nombre} para el nombre del cliente)",
                                            cfg["mensaje_reserva"], height=80)
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

    st.divider()
    admin_descuentos()


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
        st.caption("Reserva tus prendas")
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

    