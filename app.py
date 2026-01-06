"""
Aplicación web Streamlit para carga controlada de archivos Excel a Azure Data Lake Storage Gen2.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os
from config import Config
from validators import ExcelValidator
from storage_client import AzureStorageClient


# Configuración de la página
st.set_page_config(
    page_title="Excel Uploader - Carga Controlada",
    page_icon="📊",
    layout="wide"
)


def construir_ruta_storage(standard: dict, empresa: str, fecha_carga: datetime.date) -> str:
    """
    Construye la ruta completa de almacenamiento según el formato del estándar.
    
    Args:
        standard: Diccionario con el estándar del informe
        empresa: Nombre de la empresa
        fecha_carga: Fecha seleccionada por el usuario
    
    Returns:
        Ruta completa de almacenamiento
    """
    storage_path = standard.get('storage_path', '')
    if not storage_path:
        storage_path = standard.get('report_type', '').lower().replace(' ', '_')
    
    # Verificar si usa formato especial (año/mes con nombre)
    path_format = standard.get('storage_path_format', 'default')
    
    if path_format == 'year_month_name':
        # Formato para POS 3: {AÑO}/{MM}. {NombreMes}
        año = fecha_carga.strftime('%Y')
        mes_num = fecha_carga.strftime('%m')
        # Nombres de mes en español
        meses_es = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        mes_nombre = meses_es.get(mes_num, mes_num)
        fecha_str = f"{año}/{mes_num}. {mes_nombre}"
    else:
        # Formato por defecto: {año}/{mes}/{día}
        fecha_str = fecha_carga.strftime('%Y/%m/%d')
    
    return f"{Config.BASE_PATH_BUSINT}/{empresa}/{storage_path}/{fecha_str}"

# Título principal
st.title("📊 Excel Uploader - Carga Controlada")
st.markdown("---")
st.markdown(
    """
    Esta aplicación permite cargar archivos Excel de forma guiada y segura, 
    garantizando que únicamente archivos que cumplen con los estándares definidos 
    lleguen a Azure Storage.
    """
)

# Inicializar sesión
if 'validator' not in st.session_state:
    st.session_state.validator = ExcelValidator(Config.STANDARDS_DIR)

if 'storage_client' not in st.session_state:
    # Validar configuración
    is_valid, errors = Config.validate()
    if not is_valid:
        st.error("⚠️ **Error de Configuración**")
        st.error("Por favor, configura las siguientes variables de entorno:")
        for error in errors:
            st.error(f"- {error}")
        st.stop()
    
    # Inicializar cliente de Azure Storage
    try:
        st.session_state.storage_client = AzureStorageClient(
            account_name=Config.AZURE_STORAGE_ACCOUNT_NAME,
            account_key=Config.AZURE_STORAGE_ACCOUNT_KEY,
            container_name=Config.AZURE_STORAGE_CONTAINER_NAME
        )
    except Exception as e:
        st.error(f"⚠️ **Error al conectar con Azure Storage**: {str(e)}")
        st.stop()

# Obtener tipos de informe disponibles
report_types = st.session_state.validator.get_available_report_types()

if not report_types:
    st.warning("⚠️ No se encontraron estándares de informe. Por favor, agrega archivos JSON en el directorio 'standards'.")
    st.stop()

# Formulario de carga
with st.form("upload_form", clear_on_submit=False):
    st.subheader("📝 Información de Carga")
    
    # Campo 1: Empresa
    empresa = st.selectbox(
        "Empresa",
        options=Config.EMPRESAS_DISPONIBLES,
        help="Selecciona la empresa para la cual vas a cargar el informe"
    )
    
    # Campo 2: Tipo de informe
    tipo_informe = st.selectbox(
        "Tipo de Informe",
        options=report_types,
        help="Selecciona el tipo de informe que vas a cargar"
    )
    
    # Mostrar guía de origen del informe (source_hint)
    standard = st.session_state.validator.load_standard(tipo_informe)
    if standard and standard.get('source_hint'):
        st.info(f"📋 **Guía de origen:**\n\nLa ruta para sacar el informe es la siguiente:\n\n{standard.get('source_hint')}")
    
    # Campo 3: Fecha de carga
    fecha_carga = st.date_input(
        "Fecha de Carga",
        value=datetime.now().date(),
        help="Selecciona la fecha asociada a esta carga"
    )
    
    # Mostrar información detallada del estándar
    if standard:
        with st.expander("ℹ️ Ver estándar del informe seleccionado"):
            # Construir ruta completa de ejemplo usando la función helper
            ruta_completa = construir_ruta_storage(standard, empresa, fecha_carga)
            
            st.write(f"**Ruta base del informe:** `{standard.get('storage_path', 'N/A')}`")
            st.write(f"**Ruta completa en Azure Storage:** `{ruta_completa}`")
            st.write(f"**Número de columnas requeridas:** {len(standard.get('columns', []))}")
            st.write("**Columnas requeridas:**")
            st.code(", ".join(standard.get('columns', [])))
    
    # Campo 4: Archivo Excel
    archivo_excel = st.file_uploader(
        "Archivo Excel (.xlsx)",
        type=['xlsx'],
        help="Selecciona el archivo Excel que deseas cargar"
    )
    
    # Botón de envío
    submitted = st.form_submit_button("🚀 Validar y Cargar", use_container_width=True)

# Procesar formulario
if submitted:
    if not archivo_excel:
        st.error("❌ Por favor, selecciona un archivo Excel para cargar.")
    else:
        # Mostrar información del archivo
        st.info(f"📄 **Archivo seleccionado:** {archivo_excel.name}")
        
        # Validar estructura
        with st.spinner("🔍 Validando estructura del archivo..."):
            es_valido, mensaje, detalles = st.session_state.validator.validate_excel_structure(
                archivo_excel,
                tipo_informe
            )
        
        if not es_valido:
            # Mostrar error detallado
            st.error(f"❌ **Validación Fallida**")
            st.error(mensaje)
            
            # Mostrar detalles
            with st.expander("📋 Detalles de la validación"):
                st.write(f"**Columnas esperadas:** {detalles.get('total_esperadas', 0)}")
                st.write(f"**Columnas encontradas:** {detalles.get('total_encontradas', 0)}")
                
                if detalles.get('columnas_faltantes'):
                    st.error(f"**Columnas faltantes ({len(detalles['columnas_faltantes'])}):**")
                    for col in detalles['columnas_faltantes']:
                        st.write(f"- ❌ {col}")
                
                if detalles.get('columnas_sobrantes'):
                    st.warning(f"**Columnas no esperadas ({len(detalles['columnas_sobrantes'])}):**")
                    for col in detalles['columnas_sobrantes']:
                        st.write(f"- ⚠️ {col}")
                
                st.write("**Columnas esperadas:**")
                st.code(", ".join(detalles.get('columnas_esperadas', [])))
                
                st.write("**Columnas encontradas en el archivo:**")
                st.code(", ".join(detalles.get('columnas_encontradas', [])))
            
            st.warning("⚠️ El archivo **NO** se ha subido a Azure Storage.")
        
        else:
            # Validación exitosa - Subir a Azure Storage
            st.success(f"✅ {mensaje}")
            
            # Cargar estándar para obtener la ruta de destino
            standard = st.session_state.validator.load_standard(tipo_informe)
            
            if not standard:
                st.error("❌ Error: No se pudo cargar el estándar del informe")
                st.stop()
            
            # Construir ruta completa usando la función helper
            full_storage_path = construir_ruta_storage(standard, empresa, fecha_carga)
            
            # Subir archivo
            with st.spinner(f"📤 Subiendo archivo a Azure Storage..."):
                # Resetear el archivo al inicio para leerlo
                archivo_excel.seek(0)
                
                exito, mensaje_upload = st.session_state.storage_client.upload_file(
                    file_path_or_content=archivo_excel,
                    destination_path=full_storage_path,
                    file_name=archivo_excel.name
                )
            
            if exito:
                st.success(f"✅ **Carga Exitosa**")
                st.success(mensaje_upload)
                st.info(f"📍 **Ubicación:** `{full_storage_path}/{archivo_excel.name}`")
                
                # Mostrar resumen
                st.balloons()
            else:
                st.error(f"❌ **Error al subir archivo**")
                st.error(mensaje_upload)

# Información adicional
st.markdown("---")
with st.expander("ℹ️ Información sobre la aplicación"):
    st.markdown("""
    ### ¿Cómo funciona?
    
    1. **Selecciona la empresa** para la cual vas a cargar el informe.
    2. **Elige el tipo de informe** que vas a cargar.
    3. **Selecciona la fecha** asociada a la carga de datos.
    4. **Sube el archivo Excel** (.xlsx).
    5. La aplicación **valida automáticamente** que el archivo cumpla con el estándar.
    6. Si la validación es exitosa, el archivo se sube a Azure Storage Gen2 en la ruta: `raw/busint/{empresa}/{tipo_informe}/{fecha}`.
    
    ### Validaciones realizadas
    
    - ✅ Verificación de encabezados de columna
    - ✅ Coincidencia exacta de columnas con el estándar
    - ✅ Detección de columnas faltantes
    - ✅ Detección de columnas adicionales
    
    ### Estándares de informe
    
    Los estándares se definen en archivos JSON dentro del directorio `standards/`.
    Cada estándar define:
    - Las columnas requeridas
    - La ruta de destino en Azure Storage
    """)

