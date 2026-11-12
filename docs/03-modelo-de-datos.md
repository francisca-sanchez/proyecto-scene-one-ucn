# 3. Modelo de datos

Base de datos PostgreSQL alojada en Supabase. El script completo está en database/schema.sql

## 3.1 Diagrama entidad-relación

Las relaciones son **lógicas**: las tablas se conectan por el id de la otra tabla, pero no se declararon llaves foráneas
(ver [limitaciones](07-limitaciones-y-roadmap.md)).

```mermaid
erDiagram
    CLIENTES ||--o{ COMPRAS : "realiza"
    RESERVAS ||--o| COMPRAS : "se convierte en"
    COMPRAS ||--|{ VENTAS : "se desglosa en"
    PRODUCTOS ||--o{ VENTAS : "se vende en"
    COMPRAS ||--o{ CORRECCIONES_VENTA : "puede tener"
    DESCUENTOS ||--o{ RESERVAS : "se aplica en"

    PRODUCTOS {
        bigint id PK
        text nombre
        text categoria
        text talla
        integer precio
        integer stock
        text imagen_url
        boolean activo
    }
    OPCIONES {
        bigint id PK
        text tipo
        text valor
    }
    CLIENTES {
        bigint id PK
        text nombre
        text instagram
        text email
        text clave
        integer compras
        integer total_gastado
        timestamptz ultima_compra
    }
    RESERVAS {
        bigint id PK
        text cliente
        text instagram
        text email
        jsonb items
        integer total
        text estado
        text descuento_codigo
        integer descuento_monto
    }
    COMPRAS {
        bigint id PK
        bigint cliente_id FK
        bigint reserva_id FK
        jsonb items
        jsonb pagos
        integer total
        text origen
        integer descuento_monto
        integer ajuste_monto
    }
    VENTAS {
        bigint id PK
        bigint compra_id FK
        bigint producto_id FK
        integer cantidad
        integer total
        text metodo_pago
        timestamptz creado_en
    }
    DESCUENTOS {
        bigint id PK
        text codigo
        integer porcentaje
        date vence
        integer cupos_total
        integer usos
        boolean activo
    }
    TANDAS_FINANZAS {
        bigint id PK
        text nombre
        timestamptz desde
        timestamptz hasta
        integer total
        integer efectivo
        integer transferencia
    }
    CORRECCIONES_VENTA {
        bigint id PK
        bigint compra_id FK
        integer total_anterior
        integer total_nuevo
        text motivo
    }
    CONFIG {
        integer id PK
        text color_fondo
        text fuente
        text titulo
        text logo_url
    }
```

## 3.2 Diccionario de tablas

| Tabla | Para qué sirve |
|---|---|
| `productos` | Catálogo. Cada fila es **una prenda en una talla** (por ejemplo, "Polera Nightfall" talla M). La tienda agrupa las filas con el mismo nombre. |
| `opciones` | Listas de categorías y tallas que aparecen en los menús desplegables del inventario. |
| `clientes` | Un registro por cliente, con número de compras y total gastado acumulados. |
| `reservas` | Pedidos hechos desde la tienda. Estado: `pendiente`, `vendida` o `cancelada`. |
| `compras` | Venta completa y cerrada: prendas, pagos (con capturas), cliente, descuento y ajustes. Es la base del comprobante. |
| `ventas` | Una fila por prenda vendida. Es lo que lee el módulo de Finanzas. |
| `descuentos` | Códigos de descuento con porcentaje, fecha de término, cupos y usos. |
| `tandas_finanzas` | Historial de cierres: período, totales, efectivo y transferencia. |
| `correcciones_venta` | Registro de cada corrección de total: valor anterior, valor nuevo y motivo. |
| `config` | Diseño de la aplicación (una sola fila, `id = 1`). |




