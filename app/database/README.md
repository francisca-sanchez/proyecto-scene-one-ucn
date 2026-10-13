# Backend y Base de Datos - Scene One

Esta carpeta contiene toda la lógica de conexión y gestión de datos entre la aplicación web y nuestro servidor en **Supabase**.

## Propósito de la Carpeta
Aquí se alojan los scripts, diagramas y modelos encargados de:
* Establecer un puente seguro con la base de datos en la nube.
* Realizar consultas en tiempo real (lectura de inventario, registro de ventas, etc.).
* Guardar los modelos relacionales y diagramas de arquitectura del proyecto.

## Archivos Principales
* `conexion.py`: Contiene la configuración del cliente de Supabase y las funciones puente (ej: `obtener_inventario()`).
* *(Aquí guardaremos las fotos de los diagramas de base de datos)*.

## Estructura de Tablas (Supabase)
El proyecto se conecta con las siguientes entidades principales en la nube:
1. **Inventario:** Control de stock, precios y tallas (`nombre`, `precio`, `stock`, `tallas`).
2. **Clientes** *(Próximamente)*: Registro de compradores y sus redes sociales (Instagram).
3. **Ventas** *(Próximamente)*: Historial de transacciones, carrito de compras y comprobantes de pago.

> **AVISO DE SEGURIDAD IMPORTANTE:** 
> Por motivos de ciberseguridad, las credenciales de acceso (`SUPABASE_URL` y `SUPABASE_KEY`) **NUNCA** deben escribirse en los archivos de esta carpeta ni subirse a GitHub. Toda llave secreta se maneja exclusivamente de forma local a través del archivo `.streamlit/secrets.toml`.
