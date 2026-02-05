# Sistema de Gestión de Impresiones 3D Modular
Sistema integral de gestión para servicios de impresión 3D, diseñado con una arquitectura modular escalable. Permite gestionar desde la captación de clientes en la landing page hasta el control financiero y de inventario de materiales.

---

## 🛠️ Guía de Instalación y Configuración

Sigue estos pasos detalladamente para ejecutar el proyecto en tu entorno local:

### 1. Clonar el repositorio
Primero, descarga el código en tu máquina local:
```
git clone [https://github.com/TU_USUARIO/TU_REPOSIORIO.git](https://github.com/TU_USUARIO/TU_REPOSIORIO.git)
cd Nombre_del_Proyecto
```

### 2. Configurar el Entorno Virtual
Es necesario para aislar las librerías del proyecto:

En Windows:
```
python -m venv .venv
.venv\Scripts\activate
```
En macOS/Linux:
```
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias
Instala todas las librerías necesarias (Django, Tailwind, Pillow, etc.):
```
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
El proyecto utiliza variables de entorno para mayor seguridad.

1-Crea un archivo llamado .env en la raíz del proyecto.

2-Copia el contenido de .env.example en tu nuevo archivo .env.

3-Abre la terminal y genera una SECRET_KEY con este comando:
```
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```
4- Pégalo en el archivo .env siguiendo este formato:
```
SECRET_KEY=pega_aqui_el_resultado_del_paso_3
DEBUG=True
```

### 5. Preparar la Base de Datos
Ejecuta las migraciones para crear las tablas en SQLite:
```
python manage.py makemigrations
python manage.py migrate
```

### 6. Configuración inicial del Administrador (Setup automático)

⚠️ **Importante**

Este sistema cuenta con un **proceso de configuración inicial automático**.

- Si la base de datos **no tiene ningún usuario registrado**,  
  la **primera cuenta creada desde la página de registro** será configurada automáticamente como:
  - Administrador del sistema
  - Cuenta verificada
  - Acceso completo al panel de gestión

- Una vez creada esta primera cuenta:
  - El registro vuelve a funcionar solo para clientes
  - Ya no es posible crear más administradores desde el formulario

👉 Esto elimina la necesidad obligatoria de usar `createsuperuser` en la primera ejecución.


### 7. Iniciar el Servidor
Finalmente, levanta el proyecto:
```
python manage.py runserver
```

## 🔐 Autenticación y Seguridad

El sistema utiliza un modelo de usuario personalizado con las siguientes características:

- El **correo electrónico** es el identificador principal para iniciar sesión
- El campo **username es opcional**
- Todos los usuarios deben **verificar su correo electrónico** antes de iniciar sesión
- El sistema envía un enlace de verificación con un botón
- Existe un control de reenvío para evitar spam (rate limit)

🛡️ Los administradores creados durante el setup inicial no requieren verificación por correo.


🌐 Direcciones de Acceso
Una vez el servidor esté corriendo, puedes entrar a:

- **Página de Inicio (Pública):** `http://127.0.0.1:8000/`
- **Panel del Cliente:** `http://127.0.0.1:8000/dashboard/`
- **Panel Administrativo (ERP):** `http://127.0.0.1:8000/administrador/dashboard/`
- **Django Admin (DB):** `http://127.0.0.1:8000/admin/`

📂 Arquitectura Modular (apps/)
El proyecto se ha dividido en micro-aplicaciones para facilitar el mantenimiento:

- **apps/core**: Dashboard principal, calculadora de costos y lógica central del sistema.
- **apps/usuarios**: Gestión de perfiles, roles (Admin/Cliente) y autenticación personalizada.
- **apps/productos**: Catálogo, categorías y gestión de modelos 3D.
- **apps/materiales**: Control de inventario de filamentos, resinas y trazabilidad de stock.
- **apps/pedidos**: Flujo de trabajo, desde la cotización inicial hasta el estado de impresión.
- **apps/finanzas**: Registro de gastos, ingresos y reportes de rentabilidad.
- **apps/clientes**: Interfaz pública, landing page y proceso de pedidos para el usuario final.
- **apps/reportes**: Generación de métricas y estadísticas del negocio.

📝 Notas Adicionales
Archivos Media: Las imágenes y archivos subidos se guardarán en la carpeta media/.

Estilos: El proyecto utiliza Tailwind CSS vía CDN para el diseño de la interfaz oscura.

Usuarios:
- El primer usuario registrado se convierte automáticamente en Administrador
- Los usuarios posteriores se registran como Clientes
- El acceso está protegido por verificación de correo electrónico
- **Modularidad:** Cada funcionalidad vive en su propia app dentro de la carpeta `apps/`. Para crear una nueva funcionalidad, usa: `python manage.py startapp nombre_app apps/nombre_app`.
- **Diseño:** Interfaz Dark Mode consistente en todas las aplicaciones usando Tailwind CSS.