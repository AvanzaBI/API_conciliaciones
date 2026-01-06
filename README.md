# Excel Uploader - Carga Controlada

Aplicación web para la carga controlada de archivos Excel hacia Azure Data Lake Storage Gen2, con validación estricta de estructura antes de la carga.

## 🎯 Objetivo

Permitir que usuarios carguen archivos Excel de forma guiada y segura, garantizando que únicamente archivos que cumplen con estándares definidos lleguen a Azure Storage (raw).

## ✨ Características

- ✅ Validación estricta de estructura de archivos Excel
- ✅ Soporte para múltiples tipos de informe con estándares personalizados
- ✅ Interfaz web intuitiva con Streamlit
- ✅ Carga automática a Azure Data Lake Storage Gen2
- ✅ Mensajes de error claros y detallados
- ✅ Validación de columnas faltantes y sobrantes

## 📋 Requisitos Previos

- Python 3.8 o superior
- Cuenta de Azure Storage con Data Lake Storage Gen2 habilitado
- Credenciales de acceso a Azure Storage (nombre de cuenta y clave)

## 🚀 Instalación

1. **Clonar o descargar el proyecto:**
   ```bash
   cd excel-uploader-app
   ```

2. **Crear un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   
   Crea un archivo `.env` o exporta las siguientes variables:
   ```bash
   export AZURE_STORAGE_ACCOUNT_NAME="tu_cuenta_storage"
   export AZURE_STORAGE_ACCOUNT_KEY="tu_clave_acceso"
   export AZURE_STORAGE_CONTAINER_NAME="raw"  # Opcional, por defecto es "raw"
   ```

   O en Windows:
   ```cmd
   set AZURE_STORAGE_ACCOUNT_NAME=tu_cuenta_storage
   set AZURE_STORAGE_ACCOUNT_KEY=tu_clave_acceso
   set AZURE_STORAGE_CONTAINER_NAME=raw
   ```

## 🏃 Ejecución

Ejecuta la aplicación con:

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`.

## 📁 Estructura del Proyecto

```
excel-uploader-app/
├── app.py                 # Aplicación principal Streamlit
├── config.py              # Configuración y variables de entorno
├── validators.py          # Módulo de validación de Excel
├── storage_client.py      # Cliente de Azure Storage Gen2
├── standards/             # Directorio de estándares JSON
│   └── pedidos_pendientes.json
├── requirements.txt       # Dependencias Python
└── README.md             # Este archivo
```

## 📝 Definición de Estándares

Los estándares se definen en archivos JSON dentro del directorio `standards/`. Cada archivo debe seguir este formato:

```json
{
  "report_type": "nombre_tipo_informe",
  "display_name": "Nombre para Mostrar",
  "description": "Descripción del informe",
  "storage_path": "ruta/en/azure/storage",
  "columns": [
    "Columna1",
    "Columna2",
    "Columna3"
  ]
}
```

### Ejemplo: `standards/pedidos_pendientes.json`

```json
{
  "report_type": "pedidos_pendientes",
  "display_name": "Pedidos Pendientes",
  "description": "Informe de pedidos pendientes de procesamiento",
  "storage_path": "pedidos_pendientes",
  "columns": [
    "ID_Pedido",
    "Fecha_Pedido",
    "Cliente",
    "Producto",
    "Cantidad",
    "Precio_Unitario",
    "Total",
    "Estado",
    "Fecha_Entrega_Estimada",
    "Comentarios"
  ]
}
```

### Agregar Nuevos Estándares

1. Crea un nuevo archivo JSON en el directorio `standards/`
2. El nombre del archivo (sin extensión) será el identificador del tipo de informe
3. Define las columnas requeridas en el array `columns`
4. Define la ruta de destino en `storage_path`
5. La aplicación detectará automáticamente el nuevo estándar

## 🔍 Validaciones Realizadas

La aplicación valida:

1. **Presencia de encabezados:** El archivo Excel debe tener encabezados de columna
2. **Coincidencia exacta:** Las columnas del Excel deben coincidir EXACTAMENTE con el estándar
3. **Columnas faltantes:** Detecta y reporta columnas requeridas que no están presentes
4. **Columnas sobrantes:** Detecta y reporta columnas adicionales no esperadas

## 📤 Estructura de Carga en Azure Storage

Los archivos se cargan en la siguiente estructura:

```
{storage_path}/{año}/{mes}/{día}/{nombre_archivo_original.xlsx}
```

Por ejemplo:
```
pedidos_pendientes/2024/01/15/pedidos_enero.xlsx
```

## ⚙️ Configuración

### Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Nombre de la cuenta de Azure Storage | Sí |
| `AZURE_STORAGE_ACCOUNT_KEY` | Clave de acceso de la cuenta | Sí |
| `AZURE_STORAGE_CONTAINER_NAME` | Nombre del contenedor (filesystem) | No (default: "raw") |

## 🛠️ Desarrollo

### Agregar Nuevas Funcionalidades

- **Nuevos tipos de validación:** Modifica `validators.py`
- **Cambios en la UI:** Modifica `app.py`
- **Configuración adicional:** Modifica `config.py`
- **Cambios en Azure Storage:** Modifica `storage_client.py`

## 📄 Licencia

Este proyecto es independiente y no está acoplado a ningún sistema ETL existente.

## ⚠️ Notas Importantes

- Esta aplicación **NO** interactúa con bases de datos SQL
- Esta aplicación **NO** ejecuta procesos ETL
- Esta aplicación **SOLO** valida estructura y sube archivos a Azure Storage
- Los archivos se suben con el nombre original
- La validación es **estricta**: debe haber coincidencia exacta de columnas

## 🐛 Solución de Problemas

### Error: "No se encontraron estándares de informe"
- Verifica que exista el directorio `standards/`
- Verifica que haya archivos JSON en ese directorio
- Verifica que los archivos JSON tengan formato válido

### Error: "Error al conectar con Azure Storage"
- Verifica las variables de entorno `AZURE_STORAGE_ACCOUNT_NAME` y `AZURE_STORAGE_ACCOUNT_KEY`
- Verifica que la cuenta de Azure Storage tenga Data Lake Storage Gen2 habilitado
- Verifica que las credenciales sean correctas

### Error: "Error al leer el archivo Excel"
- Verifica que el archivo sea un Excel válido (.xlsx)
- Verifica que el archivo no esté corrupto
- Verifica que el archivo tenga encabezados de columna

## 📞 Soporte

Para problemas o preguntas, revisa la documentación de:
- [Streamlit](https://docs.streamlit.io/)
- [Azure Data Lake Storage Gen2](https://docs.microsoft.com/azure/storage/blobs/data-lake-storage-introduction)
- [pandas](https://pandas.pydata.org/docs/)


