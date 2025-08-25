import pdfplumber
import pandas as pd
import camelot
import re
import io
from fastapi import UploadFile

def procesar_pdf(file_pdf: UploadFile) -> pd.DataFrame:
    """
    Procesa un PDF bancario subido vía FastAPI y devuelve un DataFrame
    con columnas: FECHA, DESCRIPCION, VALOR.
    Compatible con pdfplumber y Camelot, maneja errores de stream.
    """
    # Leer PDF completo en memoria
    pdf_bytes = file_pdf.file.read()
    pdf_stream = io.BytesIO(pdf_bytes)

    all_rows = []

    # --- Intento con pdfplumber ---
    try:
        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        all_rows.append(row)
    except Exception as e:
        # Si pdfplumber falla, seguimos con Camelot
        print(f"Warning pdfplumber: {e}")

    # --- Intento con Camelot si no hay filas extraídas ---
    if len(all_rows) == 0:
        pdf_stream.seek(0)
        try:
            tablas = camelot.read_pdf(pdf_stream, pages="all", flavor="lattice")
            if tablas:
                all_rows = [row for t in tablas for row in t.df.values.tolist()]
        except Exception as e:
            print(f"Warning Camelot: {e}")
            all_rows = []

    if len(all_rows) == 0:
        # Retornar DataFrame vacío si no se pudo extraer info
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    # Convertir a DataFrame
    df = pd.DataFrame(all_rows)

    # Ajustar columnas si hay al menos 6
    if df.shape[1] >= 6:
        df = df.iloc[:, :6]
        df.columns = ["FECHA", "DESCRIPCION", "SUCURSAL", "DCTO", "VALOR", "SALDO"]

    # Limpiar filas irrelevantes
    df = df[df["FECHA"].notna()]
    df = df[df["FECHA"] != "FECHA"]

    # Expandir celdas con saltos de línea
    filas = []
    for _, row in df.iterrows():
        cols_divididas = [str(row[c]).split("\n") for c in df.columns]
        max_len = max(len(col) for col in cols_divididas)
        for i in range(max_len):
            fila = []
            for col in cols_divididas:
                fila.append(col[i] if i < len(col) else "")
            filas.append(fila)

    df = pd.DataFrame(filas, columns=["FECHA", "DESCRIPCION", "SUCURSAL", "DCTO", "VALOR", "SALDO"])

    # Filtrar fechas válidas
    df = df[df["FECHA"].str.contains(r"\d{1,2}/\d{1,2}", na=False)]

    # Extraer año desde texto completo del PDF
    pdf_stream.seek(0)
    pdf_text = ""
    with pdfplumber.open(pdf_stream) as pdf:
        for page in pdf.pages:
            pdf_text += page.extract_text() or ""
    match = re.search(r"(20\d{2})", pdf_text)
    anio_pdf = match.group(1) if match else "2025"

    # Completar fechas incompletas
    df["FECHA"] = df["FECHA"].astype(str).str.strip()
    mask_fechas = df["FECHA"].str.match(r"^\d{1,2}/\d{1,2}$")
    df.loc[mask_fechas, "FECHA"] = df.loc[mask_fechas, "FECHA"] + "/" + anio_pdf

    # Convertir a formato YYYY-MM-DD
    df["FECHA"] = (
    pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
      .dt.strftime("%d/%m/%Y")
    )

    # Seleccionar y limpiar columnas finales
    df_final = df[["FECHA", "DESCRIPCION", "VALOR"]].copy()
    df_final["VALOR"] = (
        df_final["VALOR"].astype(str).str.replace(",", "", regex=False)
    )
    df_final["VALOR"] = pd.to_numeric(df_final["VALOR"], errors="coerce").round(0)

    return df_final