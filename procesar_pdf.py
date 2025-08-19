import pdfplumber
import pandas as pd
import camelot
import re
from fastapi import UploadFile

def procesar_pdf(file_pdf: UploadFile) -> pd.DataFrame:
    # Leer el PDF desde el UploadFile en memoria
    pdf_bytes = file_pdf.file.read()
    
    # Abrir pdfplumber con archivo en memoria usando io.BytesIO
    import io
    pdf_stream = io.BytesIO(pdf_bytes)
    
    all_rows = []
    with pdfplumber.open(pdf_stream) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    all_rows.append(row)
    
    if len(all_rows) > 0:
        df = pd.DataFrame(all_rows)
    else:
        tablas = camelot.read_pdf(pdf_stream, pages="all", flavor="lattice")
        df = pd.concat([t.df for t in tablas], ignore_index=True)
    
    if df.shape[1] >= 6:
        df = df.iloc[:, :6]
        df.columns = ["FECHA", "DESCRIPCION", "SUCURSAL", "DCTO", "VALOR", "SALDO"]
    
    df = df[df["FECHA"].notna()]
    df = df[df["FECHA"] != "FECHA"]
    
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
    df = df[df["FECHA"].str.contains(r"\d{1,2}/\d{2}", na=False)]
    
    pdf_text = ""
    with pdfplumber.open(pdf_stream) as pdf:
        for page in pdf.pages:
            pdf_text += page.extract_text() or ""
    
    match = re.search(r"(20\d{2})", pdf_text)
    anio_pdf = match.group(1) if match else "2025"
    
    df["FECHA"] = df["FECHA"].astype(str).str.strip()
    mask_fechas = df["FECHA"].str.match(r"^\d{1,2}/\d{1,2}$")
    df.loc[mask_fechas, "FECHA"] = df.loc[mask_fechas, "FECHA"] + "/" + anio_pdf
    
    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["FECHA"])
    
    df_final = df[["FECHA", "DESCRIPCION", "VALOR"]].copy()
    df_final["VALOR"] = (
        df_final["VALOR"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .astype(float).round(0)
    )
    df_final["VALOR"] = pd.to_numeric(df_final["VALOR"], errors="coerce")
    
    return df_final
