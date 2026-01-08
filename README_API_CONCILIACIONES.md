# API Conciliaciones Bancarias

Una API en FastAPI para:
- Extraer movimientos desde PDFs bancarios.
- Leer contabilidad desde Excel.
- Conciliar ambos y devolver un Excel con resultados.

## Estructura del proyecto

```
.
├─ main.py
├─ procesar_pdf.py
├─ unir_archivos.py
├─ requirements.txt
└─ tests_local/
   ├─ archivos/
   ├─ test_pdf.py
   ├─ test_excel.py
   ├─ test_conciliacion.py
   └─ utils_debug.py
```

## Requisitos y dependencias

Archivo: `requirements.txt`
- fastapi, uvicorn: servidor API.
- pandas: dataframes y transformaciones.
- openpyxl: lectura y escritura de Excel.
- pdfplumber: extracción de texto desde PDF.
- camelot-py: extracción de tablas desde PDF (cuando el PDF tiene tablas).
- python-multipart: soporte de subida de archivos en `multipart/form-data`.

Notas prácticas (sí, la vida es dura):
- `camelot-py` suele requerir dependencias del sistema (Ghostscript). Si falla, tu síntoma típico es que el PDF “sale en blanco”.
- Si tu PDF no trae texto embebido (escaneado como imagen), `pdfplumber` no saca nada. En ese caso este proyecto retorna DataFrame vacío para ese tipo.

## Cómo correr la API

### 1) Crear entorno e instalar
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Levantar servidor
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) Probar en Swagger
- Abre `http://localhost:8000/docs`
- Endpoint principal: `POST /conciliacion-unificada/`

## Endpoint principal

Archivo: `main.py`

### `POST /conciliacion-unificada/`

Entradas (form-data):
- `pdf_file`: PDF del banco.
- `contabilidad_file`: Excel de contabilidad.

Salida:
- Si todo sale bien: un Excel generado en memoria (bytes) con la conciliación.
- Si el PDF no se logra extraer: 400 con JSON `{ "detail": "No se pudo extraer información del PDF." }`
- Si ocurre un error interno: 500 con JSON, incluyendo tipo de error.

Flujo:
1) Lee y procesa el PDF con `procesar_pdf_universal(pdf_file)`.
2) Lee el Excel en memoria con `pandas.read_excel(BytesIO(...))`.
3) Llama `conciliar_movimientos(df_contabilidad, df_extracto)`.
4) Devuelve el resultado como archivo Excel en respuesta HTTP.

Manejo de errores:
- `HTTPException` para errores esperados.
- `try/except Exception` para fallos inesperados.
- Respuesta 500 incluye:
  - `detail`: mensaje resumido.
  - `error_type`: clase de excepción.
  - `traceback`: hoy está condicionado por un chequeo simple; no siempre llega.

CORS:
- Configurado para permitir cualquier origen.
- `allow_credentials=False`.

Estáticos:
- Monta `/static` apuntando a carpeta `static/` (se crea si no existe).

## Extracción de PDF

Archivo: `procesar_pdf.py`

Objetivo:
- Transformar un PDF bancario a un DataFrame con columnas estándar:
  - `FECHA` en formato `dd/mm/YYYY`
  - `DESCRIPCION` en mayúsculas, normalizada
  - `VALOR` como entero (sin separadores, sin símbolos)

Funciones clave:

### `_pdf_text(bio: BytesIO) -> str`
- Usa `pdfplumber` para extraer texto por página.
- Une todo en un solo string.
Errores típicos:
- PDF escaneado. Texto vacío.

### `_detectar_tipo(texto: str) -> TipoPDF`
Clasifica el PDF en:
- `estado_cuenta`
- `movimiento_diario`
- `sin_texto`
- `desconocido`

Cómo decide:
- Señales por palabras clave en el texto.
- Si texto vacío, marca `sin_texto`.

### `_parse_estado_cuenta_por_lineas(pdf_bytes) -> DataFrame`
Estrategia:
- Extrae texto.
- Busca líneas que parezcan movimiento.
- Usa regex para capturar:
  - fecha día/mes y año inferido
  - descripción
  - valor y saldo (se ignora saldo en salida final)
- Normaliza:
  - fecha a `dd/mm/YYYY`
  - descripción en mayúsculas
  - valor a entero

### `_parse_movimiento_diario_con_camelot(tmp_path) -> DataFrame`
Estrategia:
- Usa Camelot para extraer tablas.
- Busca una fila header con FECHA, DESCRIPCION, VALOR.
- Recorta desde el header y limpia filas vacías.
Errores típicos:
- Ghostscript no instalado.
- PDF sin líneas de tabla o con estructura rara.
- Tablas detectadas pero con columnas corridas.

### `_parse_movimiento_diario_por_texto(pdf_bytes) -> DataFrame`
Fallback cuando Camelot no trae nada.
- Regex por líneas con patrón:
  - `dd/mm` + descripción + valor + saldo

### `procesar_pdf_universal(file_pdf) -> DataFrame`
Orquestador:
1) Lee bytes del PDF.
2) Extrae texto y detecta tipo.
3) Si `sin_texto`: retorna DataFrame vacío.
4) Si `estado_cuenta`: parseo por líneas.
5) Si `movimiento_diario`:
   - guarda temporal a disco
   - intenta Camelot
   - si vacío, intenta parseo por texto
   - borra el temporal siempre (finally)
6) Si tipo `desconocido`: intenta primero estado de cuenta, luego movimiento diario.

Manejo de errores:
- Limpieza de archivo temporal en `finally` con `try/except` para que no reviente por permisos.

## Conciliación y generación de Excel

Archivo: `unir_archivos.py`

Salida:
- Devuelve `bytes` de un Excel construido con `openpyxl`.

### `_norm(s: str) -> str`
Normaliza nombres:
- trim
- upper
- quita tildes
- colapsa espacios

Se usa para:
- mapear columnas “raras” como `Asiento `, `ASIENTO`, etc.

### `_safe_drop_columns(df, cols) -> df`
- Elimina columnas sin fallar si no existen.
- Evita `KeyError` cuando una columna no está presente.

### `conciliar_movimientos(df_contabilidad, df_extracto) -> bytes`

Entrada esperada:
- Contabilidad (Excel):
  - Caso A: columnas `Fecha` y `Movimiento` y opcional `Asiento`
  - Caso B: columnas ya normalizadas
- Extracto (PDF procesado):
  - `FECHA`, `DESCRIPCION`, `VALOR`

Pasos principales:
1) Copia dataframes para no mutar input.
2) Detecta columnas reales de contabilidad con `colmap` y renombra a:
   - `FECHA`, `VALOR`, `CONCEPTO` (si existe asiento)
3) Limpieza:
   - fechas a datetime y luego a string estándar
   - valores a numérico
4) Crea clave de conciliación:
   - combina fecha y valor (y en algunos casos concepto)
   - objetivo: tener un “join” estable entre contabilidad y extracto
5) Merge:
   - `outer join` para ver coincidencias y faltantes
6) Casos que genera:
   - Caso 1: entradas que están en ambos.
   - Caso 2: entradas en extracto y no en contabilidad.
   - Caso 3: salidas en contabilidad y no en extracto.
   - Caso 4: salidas en extracto y no en contabilidad.
   - Consolidado: resumen con columnas clave.

Secciones adicionales:
- “Ingresos” y “Gastos bancarios”:
  - Filtra `df_extracto` por listas de descripciones.
  - Agrupa por descripción y suma.
  - Convierte a valor absoluto cuando corresponde.

Manejo de errores aplicado (cosas que salvan el día):
- Reseteo de índice antes de usar máscaras `.isin()` para evitar el clásico error de máscara booleana con índices desalineados.
- Verificación de columnas antes de seleccionar (`FIX CRÍTICO` en el código).
- `_safe_drop_columns` para que el Excel no se caiga por columnas inexistentes.

Generación de Excel:
- Usa `openpyxl` y `dataframe_to_rows`.
- Crea varias hojas:
  - conciliación por casos
  - consolidado
  - gastos e ingresos
- Aplica formato:
  - negrilla en títulos
  - anchos de columna ajustados por contenido
  - formato moneda COP sin decimales en columnas VALOR

## Scripts de pruebas locales

Carpeta: `tests_local/`

### `tests_local/utils_debug.py`
Herramientas:
- `make_run_dir()`: crea carpeta `debug_runs/YYYYMMDD_HHMMSS`.
- `dump_csv(df, run_dir, name)`: exporta CSV para inspección.
- `dump_excel(dfs, run_dir, name)`: exporta Excel con varias hojas.

### `tests_local/test_conciliacion.py`
Intención:
- Ejecutar el flujo completo fuera de la API.
- Guardar el Excel final o dumps intermedios.

Detalle importante:
- En el archivo hay una línea con `...` en el bloque principal.
- Eso es una expresión válida en Python, pero es un “placeholder”. Si lo dejas, el script corre, pero queda un hueco lógico.
- Recomendación: reemplazar esa sección por rutas reales a:
  - PDF en `tests_local/archivos/`
  - Excel en `tests_local/archivos/Movimiento Banco Contabilidad.xlsx`

### `tests_local/test_pdf.py`
- Está desactualizado.
- Importa `procesar_pdf`, pero el módulo expone `procesar_pdf_universal`.
Arreglo rápido:
- Cambia `from procesar_pdf import procesar_pdf` por `from procesar_pdf import procesar_pdf_universal`
- Cambia la llamada `procesar_pdf(up)` por `procesar_pdf_universal(up)`

### `tests_local/test_excel.py`
- Valida lectura del Excel y sus tipos.
- Útil para confirmar nombres de columnas y formatos.

## Ejemplos de uso con curl

Subida de archivos:
```bash
curl -X POST "http://localhost:8000/conciliacion-unificada/" \
  -F "pdf_file=@tests_local/archivos/Extracto PDF.pdf" \
  -F "contabilidad_file=@tests_local/archivos/Movimiento Banco Contabilidad.xlsx" \
  -o Conciliacion.xlsx
```

## Guía de troubleshooting

### 1) Respuesta 400: “No se pudo extraer información del PDF”
Causas comunes:
- PDF escaneado (sin texto).
- PDF con estructura distinta a los 2 modelos soportados.
Acciones:
- Prueba primero `procesar_pdf_universal` con `tests_local/test_conciliacion.py` y exporta CSV.

### 2) Camelot retorna vacío
Causas:
- Dependencias del sistema ausentes.
- Tablas sin bordes claros.
Acciones:
- Verifica instalación de Ghostscript.
- Prueba el fallback por texto, ya está integrado.

### 3) Error de máscara booleana
Ya está mitigado en `unir_archivos.py`:
- `reset_index(drop=True)` antes de filtrar con `.isin().values`.

### 4) Valores con signo y formato moneda
- `procesar_pdf.py` limpia símbolos y separadores.
- `unir_archivos.py` aplica formato COP en Excel.
