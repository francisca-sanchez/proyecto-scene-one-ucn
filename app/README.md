# Frontend e Interfaz Visual - Scene One

Esta subcarpeta contiene todo el código responsable de la interfaz de usuario (UI) y la experiencia de usuario (UX) de nuestra aplicación web, desarrollada íntegramente con **Streamlit**.

## Propósito de la Carpeta
Aquí se gestiona toda la "cara visible" del proyecto. Los scripts de esta sección se encargan de:
* Renderizar el Punto de Venta (POS) y las tarjetas de productos.
* Gestionar el sistema de inicio de sesión oculto.
* Mantener el diseño corporativo de Scene One mediante inyección de código CSS.
* Capturar las interacciones del usuario (clics, selección de tallas, métodos de pago) para enviarlas al backend.

## Archivos Principales
* `APP.py`: Es el motor visual del proyecto. Contiene la estructura de la página, el menú de navegación y la lógica para mostrar los datos que vienen de Supabase.
* `colores_drop.json`: Archivo de configuración local que guarda de forma persistente la paleta de colores dinámica elegida para la marca.
* `assets/` *(Carpeta)*: Directorio destinado a almacenar recursos estáticos como el logo oficial y otras imágenes corporativas.

## Características Técnicas Destacadas
* **Diseño Personalizado:** Uso avanzado de Streamlit con HTML/CSS inyectado para superar las limitaciones visuales por defecto.
* **Reactividad:** Interfaz que responde en tiempo real a las consultas de inventario de la base de datos.