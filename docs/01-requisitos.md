# 1. Levantamiento de requisitos

**Proyecto:** Scene One Club · Sistema de reservas, punto de venta y gestión

**Versión del documento:** 1.0 · Noviembre de 2026

## 1.1 Propósito y alcance

Scene One Club es una pyme de venta de ropa ubicada en Antofagasta, Chile. Hasta ahora llevaba el inventario, las ventas y los
clientes en planillas de Excel, lo que dificultaba saber el stock real, el dinero recaudado y quién compra más.

El sistema busca **centralizar esa gestión en una aplicación web** con dos caras:

- una **tienda de reservas** para los clientes (no es una tienda con pago online), y
- un **panel de administración** que funciona además como **punto de venta** (POS) e inventario.

### Fuera del alcance (por ahora)

- Pago online con pasarela (por ejemplo Webpay/Transbank) o confirmación automática de transferencias.
- Emisión de boleta o factura electrónica ante el SII. Los comprobantes del sistema son documentos internos de respaldo.
- Despacho o seguimiento de envíos.
- Varias sucursales y usuarios con distintos permisos.

## 1.2 Definiciones

| Término | Significado |
|---|---|
| **Reserva** | Pedido que hace un cliente desde la tienda. Aparta el stock, pero no implica pago online. |
| **Compra** | Venta completa y cerrada, hecha desde el punto de venta o al confirmar una reserva. |
| **Venta** | Línea de detalle por prenda de una compra. Es lo que usa Finanzas para sumar. |
| **Comprobante** | Documento de respaldo de una compra (total, cliente, pagos y captura de la transferencia). |
| **Boleta de reserva** | Documento que recibe el cliente al reservar, por correo y descargable. |
| **Tanda** | Período de ventas que la tienda cierra y guarda aparte (por ejemplo, un *drop*). |
| **Cupo** | Cantidad de veces que se puede usar un código de descuento. |

## 1.3 Actores

| Actor | Descripción |
|---|---|
| **Cliente** | Persona que entra a la tienda, arma su carrito y reserva. No necesita cuenta. |
| **Administrador** | Personal de la tienda. Inicia sesión y gestiona reservas, ventas, inventario, clientes, finanzas y diseño. |

## 1.4 Requisitos funcionales

Prioridad: **A** = alta, **M** = media. Estado: **✔** implementado.

### Tienda (cliente)

| ID | Requisito | Prior. | Estado |
|---|---|:-:|:-:|
| RF-01 | Mostrar el catálogo de prendas visibles con stock disponible, agrupando por nombre en una sola tarjeta. | A | ✔ |
| RF-02 | Permitir elegir talla y cantidad de cada prenda, sin mostrar al cliente el stock exacto. | A | ✔ |
| RF-03 | Filtrar el catálogo por categoría. | M | ✔ |
| RF-04 | Actualizar el catálogo automáticamente cada pocos segundos, sin recargar la página. | M | ✔ |
| RF-05 | Mostrar un carrito de reserva con foto, talla, precio, cantidad editable, opción de quitar y total. | A | ✔ |
| RF-06 | Aplicar un código de descuento válido (existente, activo, vigente y con cupos) sobre el subtotal. | M | ✔ |
| RF-07 | Registrar la reserva con nombre y correo obligatorios e Instagram opcional. | A | ✔ |
| RF-08 | Al reservar, descontar el stock (queda apartado) y dejar la reserva en estado *pendiente*. | A | ✔ |
| RF-09 | Enviar la boleta de reserva al correo del cliente y permitir descargarla. | A | ✔ |

### Administración

| ID | Requisito | Prior. | Estado |
|---|---|:-:|:-:|
| RF-10 | Acceso del administrador mediante correo y contraseña. | A | ✔ |
| RF-11 | Listar reservas por estado (pendiente, vendida, cancelada) con datos del cliente, prendas, total y código usado. | A | ✔ |
| RF-12 | Registrar los pagos de una reserva (efectivo o transferencia con captura) y confirmar la venta cuando el pago está completo. | A | ✔ |
| RF-13 | Cancelar una reserva devolviendo el stock y el cupo del código de descuento. | A | ✔ |
| RF-14 | Armar una venta en el punto de venta con una o varias prendas. | A | ✔ |
| RF-15 | Pedir los datos del cliente en cada venta: nombre obligatorio; Instagram y correo opcionales. | A | ✔ |
| RF-16 | Pago en efectivo: generar y guardar un comprobante. Pago por transferencia: exigir la captura del comprobante. | A | ✔ |
| RF-17 | Descontar el stock al vender y no permitir vender más unidades que las disponibles. | A | ✔ |
| RF-18 | Ver y editar el inventario en una tabla (nombre, categoría, talla, precio, stock, foto, visibilidad). | A | ✔ |
| RF-19 | Agregar productos con foto, pudiendo partir desde una prenda existente; si la talla ya existe, sumar el stock. | A | ✔ |
| RF-20 | Administrar categorías y tallas (agregar, renombrar y eliminar si no están en uso). | M | ✔ |
| RF-21 | Cambiar la foto de un producto y eliminarlo. | M | ✔ |
| RF-22 | Crear o actualizar al cliente en cada venta, acumulando su número de compras y total gastado. | A | ✔ |
| RF-23 | Consultar por cliente su historial de compras y comprobantes; buscar, ordenar por mayor comprador y editar sus datos. | A | ✔ |
| RF-24 | Mostrar indicadores de la tanda actual (total, prendas, ventas, efectivo, transferencia, % de transferencias, hoy y reservas pendientes) y ventas por día. | A | ✔ |
| RF-25 | Cerrar la tanda guardando un historial (período, totales y método de pago) y dejar las finanzas en cero. | A | ✔ |
| RF-26 | Deshacer el último cierre de tanda. | M | ✔ |
| RF-27 | Corregir el total de una venta de la tanda actual con motivo obligatorio, manteniendo coherentes finanzas, cliente y comprobante, y dejando un registro. | M | ✔ |
| RF-28 | Personalizar colores, tipografía (5 opciones), textos del banner, mensaje de reserva, logo, foto de banner y enlaces de redes, sin tocar el código. | M | ✔ |
| RF-29 | Administrar códigos de descuento: nombre, porcentaje, fecha de término, cupos y activación. | M | ✔ |

## 1.5 Requisitos no funcionales

| ID | Categoría | Requisito |
|---|---|---|
| RNF-01 | Usabilidad | Interfaz en español, simple de usar para personal sin conocimientos técnicos. |
| RNF-02 | Disponibilidad | Aplicación web accesible desde navegador; base de datos y archivos alojados en la nube. |
| RNF-03 | Persistencia | Los datos se guardan en PostgreSQL (Supabase) y las imágenes en Supabase Storage. |
| RNF-04 | Seguridad | Las credenciales y claves no se almacenan en el repositorio; el panel exige inicio de sesión. |
| RNF-05 | Trazabilidad | Los cierres de tanda y las correcciones de ventas quedan registrados con fecha y motivo. |
| RNF-06 | Integridad | Los totales de Finanzas, la ficha del cliente y los comprobantes deben coincidir, incluso con descuentos y correcciones. |
| RNF-07 | Mantenibilidad | El esquema de la base de datos está versionado en `database/` y el diseño se cambia sin editar el código. |
| RNF-08 | Rendimiento | Las consultas de ventas se leen por páginas de 1000 filas; el catálogo se refresca cada 15 segundos. |
| RNF-09 | Compatibilidad | Python 3.12 y Streamlit 1.40 o superior. |

## 1.6 Reglas de negocio

| ID | Regla |
|---|---|
| RN-01 | Al reservar se descuenta el stock; al cancelar la reserva se devuelve. |
| RN-02 | El pago y la entrega de una reserva se coordinan con la tienda; el sistema no cobra online. |
| RN-03 | Un código de descuento se valida en cada reserva: debe existir, estar activo, no haber vencido (vale hasta el final del día indicado) y tener cupos. |
| RN-04 | Cada reserva con código consume un cupo; si se cancela, el cupo vuelve a estar disponible. |
| RN-05 | Una reserva solo se confirma como venta cuando el pago verificado cubre el total. |
| RN-06 | Un cliente se reconoce por su usuario de Instagram; si no lo entrega, por su nombre. |
| RN-07 | Una tanda cuenta las ventas posteriores al último cierre. Cerrar una tanda **no borra** ventas, clientes ni productos. |
| RN-08 | Las ventas de una tanda cerrada no se corrigen, salvo que primero se deshaga el cierre. |
| RN-09 | Al corregir el total de una venta, la diferencia se reparte proporcionalmente entre sus prendas. |
| RN-10 | El cliente nunca ve el stock exacto: solo se le impide pedir más de lo disponible. |
