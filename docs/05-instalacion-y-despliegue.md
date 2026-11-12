# 5. Instalación y despliegue


### (Falta publicacion o traspaso a aplicacion)


## 5.1 Requisitos

- Python **3.12** y `pip`
- Git
- Una cuenta gratuita en [Supabase](https://supabase.com)
- (Opcional) Una cuenta de Gmail para enviar la boleta de reserva por correo

## 5.2 Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>

# 2. Crear y activar un entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt
```

## 5.3 Configurar Supabase

1. En Supabase crea un **proyecto nuevo** y espera a que termine de iniciarse.
2. Abre **SQL Editor**, pega el contenido de [`database/schema.sql`](../database/schema.sql) y presiona **Run**. Crea todas las
   tablas, los índices, las categorías y tallas iniciales y el bucket de imágenes.
3. (Opcional) Para probar con datos de ejemplo, ejecuta después [`database/datos_demo.sql`](../database/datos_demo.sql) **una sola vez**.
4. En **Table Editor** comprueba que aparezcan las tablas. En **Storage** debe existir el bucket `imagenes`.
5. En **Project Settings > API** copia la **URL** del proyecto y la clave **`service_role`**.

> Si ya tienes una base de una versión anterior, no uses `schema.sql`: aplica en orden los archivos de
> [`database/migraciones/`](../database/migraciones/).

## 5.4 Configurar los secretos

Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completa los datos:

```toml
SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
SUPABASE_KEY = "TU_SERVICE_ROLE_KEY"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "correo.de.la.tienda@gmail.com"
SMTP_PASSWORD = "contraseña-de-aplicacion"

[admin]
email = "admin@tu-dominio.cl"
password = "una-contraseña-larga-y-propia"
```

- Las claves sueltas (`SUPABASE_*`, `SMTP_*`) deben ir **antes** de la sección `[admin]`; en TOML todo lo que sigue a un
  `[título]` pertenece a esa sección.
- **`secrets.toml` no se sube a GitHub** (está en `.gitignore`). Nunca compartas la clave `service_role`.
- Si no configuras el correo, la aplicación funciona igual, pero la boleta no se envía por mail; el cliente la descarga en pantalla.

**Correo con Gmail:** activa la verificación en dos pasos en la cuenta y crea una *contraseña de aplicación* desde la configuración
de seguridad de Google. Usa esa contraseña en `SMTP_PASSWORD`, no la contraseña normal de la cuenta.

## 5.5 Ejecutar

```bash
streamlit run app/app.py
```

Se abre en `http://localhost:8501`. Si el archivo principal se llama distinto (por ejemplo `APP.py`), usa ese nombre.

## 5.6 Despliegue en Streamlit Community Cloud

1. Sube el repositorio a GitHub (sin `secrets.toml`).
2. En [share.streamlit.io](https://share.streamlit.io) elige **New app**, selecciona el repositorio y la rama, y en *Main file path* escribe `app/app.py`.
3. En **Advanced settings > Secrets** pega el contenido de tu `secrets.toml`.
4. Presiona **Deploy**. Cada `git push` a esa rama actualiza la aplicación.

## 5.7 Problemas frecuentes

| Mensaje o síntoma | Causa y solución |
|---|---|
| `Could not find the table 'public.productos'` | No se ejecutó `schema.sql`, o se ejecutó en otro proyecto de Supabase. Revisa que la URL de los secretos sea la del proyecto correcto. Si ya existen las tablas, ejecuta `notify pgrst, 'reload schema';`. |
| `Could not find the 'xxx' column of ...` | Falta una migración. Aplica los archivos de `database/migraciones/` que no hayas ejecutado. |
| Error de conexión o *Invalid API key* | La URL o la clave de `secrets.toml` están mal copiadas, o están después de la sección `[admin]`. |
| No llega la boleta por correo | Revisa los datos `SMTP_*`. En Gmail hace falta una contraseña de aplicación. El motivo exacto se imprime en la terminal donde corre Streamlit. |
| Las fotos no se suben | Falta el bucket `imagenes` o no es público. Revisa **Storage** en Supabase. |
| El archivo principal no se encuentra | Linux distingue mayúsculas: `APP.py` y `app.py` son archivos distintos. Usa el nombre exacto en el comando y en el despliegue. |