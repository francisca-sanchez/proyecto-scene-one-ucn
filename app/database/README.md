# Base de datos

PostgreSQL en [Supabase](https://supabase.com). Modelo y diccionario en [`docs/03-modelo-de-datos.md`](../docs/03-modelo-de-datos.md).

## ¿Qué archivo uso?

| Situación | Qué ejecutar |
|---|---|
| Proyecto de Supabase **nuevo** | [`schema.sql`](schema.sql) |
| Quiero datos de ejemplo para probar o presentar | [`datos_demo.sql`](datos_demo.sql), **una sola vez**, después de `schema.sql` |
| Ya tengo una base de una versión anterior | Los archivos de [`migraciones/`](migraciones/) que aún no hayas aplicado, **en orden** |

Todo se ejecuta pegando el contenido en **Supabase > SQL Editor > Run**.

## Migraciones

Son los cambios incrementales, en el orden en que se aplicaron durante el desarrollo. Cada una puede ejecutarse más de una vez sin
problema (`if not exists`).

| Archivo | Qué agrega |
|---|---|
| `001_categorias_y_tallas.sql` | Tabla `opciones` con las categorías y tallas de los menús |
| `002_diseno_textos_y_redes.sql` | Columnas del diseño: nombre, textos, Instagram y TikTok |
| `003_clientes.sql` | Tabla `clientes` |
| `004_instagram.sql` | Columna `instagram` en reservas y clientes, y la clave que identifica al cliente |
| `005_compras_pagos_comprobantes.sql` | Tabla `compras` y las columnas de pagos |
| `006_codigos_de_descuento.sql` | Tabla `descuentos` y las columnas de descuento |
| `007_tandas_de_finanzas.sql` | Tabla `tandas_finanzas` (historial de cierres) |
| `008_correcciones_de_ventas.sql` | Tabla `correcciones_venta` y la columna de ajuste |

> `schema.sql` ya incluye el resultado de todas las migraciones, sin las columnas que quedaron en desuso (como el teléfono del cliente).

## Si aparece "could not find the table"

La API de Supabase guarda el esquema en caché. Ejecuta `notify pgrst, 'reload schema';` y vuelve a cargar la aplicación.
