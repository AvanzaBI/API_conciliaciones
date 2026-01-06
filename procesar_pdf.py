import io
import re
from typing import Optional

import camelot
import pandas as pd
import pdfplumber
from fastapi import UploadFile


def _norm_col(s: str) -> str:
    s = (s or "").strip().upper()
    s = (
        s.replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ü", "U")
    )
    s = re.sub(r"\s+", " ", s)
    return s


def _extract_year_from_pdf_text(pdf_text: str, default_year: str = "2025") -> str:
    m = re.search(r"(20\d{2})", pdf_text or "")
    return m.group(1) if m else default_year


def _clean_valor_series(s: pd.Series) -> pd.Series:
    out = s.astype(str)
    out = out.str.replace("$", "", regex=False)
    out = out.str.replace(" ", "", regex=False)
    out = out.str.replace(",", "", regex=False)
    out = out.str.replace("(", "-", regex=False).str.replace(")", "", regex=False)
    return pd.to_numeric(out, errors="coerce").round(0)


def _pick_col(cols_norm: list[str], contains: list[str]) -> Optional[int]:
    for i, c in enumerate(cols_norm):
        if any(k in c for k in contains):
            return i
    return None


def _build_df_from_rows(all_rows: list[list[object]]) -> Optional[pd.DataFrame]:
    if not all_rows:
        return None

    df_raw = pd.DataFrame(all_rows)

    # quitar columnas totalmente vacías
    df_raw = df_raw.dropna(axis=1, how="all")
    if df_raw.empty:
        return None

    # detectar header real
    header_idx = None
    for i in range(min(10, len(df_raw))):
        row = [str(x or "").strip() for x in df_raw.iloc[i].tolist()]
        joined = " ".join(row).upper()
        if "FECHA" in joined and ("DESCRIP" in joined or "DESCRIPC" in joined):
            header_idx = i
            break

    if header_idx is None:
        return df_raw

    header = [str(x or "").strip() for x in df_raw.iloc[header_idx].tolist()]
    df = df_raw.iloc[header_idx + 1 :].copy()
    df.columns = header

    # quitar filas vacías
    df = df.dropna(how="all")
    return df


def _extract_from_text(pdf_text: str) -> pd.DataFrame:
    """Fallback cuando no se logra tabla.

    Soporta:
    - Movimiento diario: 2025/11/30 ... 96.32
    - Estado de cuenta: 1/05 ... 8.85 6,551,997.94
    """

    lines = [ln.strip() for ln in (pdf_text or "").splitlines() if ln.strip()]

    date_pat = re.compile(r"^(\d{4}/\d{2}/\d{2}|\d{1,2}/\d{2})\b")
    money_pat = re.compile(r"-?\d{1,3}(?:,\d{3})*(?:\.\d{2})|-?\d+(?:\.\d{2})")

    rows = []
    cur_date = None
    cur_chunk = ""

    def flush():
        nonlocal cur_date, cur_chunk
        if not cur_date:
            return
        nums = money_pat.findall(cur_chunk)
        if not nums:
            return

        # si hay 2 o mas numeros, asumimos VALOR y SALDO al final
        valor = nums[-2] if len(nums) >= 2 else nums[-1]

        # quitar date y numeros finales del texto
        desc = cur_chunk
        desc = desc.replace(valor, "")
        if len(nums) >= 2:
            desc = desc.replace(nums[-1], "")

        desc = re.sub(r"\s+", " ", desc).strip()

        rows.append([cur_date, desc, valor])
        cur_date = None
        cur_chunk = ""

    for ln in lines:
        m = date_pat.match(ln)
        if m:
            flush()
            cur_date = m.group(1)
            cur_chunk = ln[len(cur_date) :].strip()
        else:
            if cur_date:
                cur_chunk = (cur_chunk + " " + ln).strip()

    flush()

    if not rows:
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    return pd.DataFrame(rows, columns=["FECHA", "DESCRIPCION", "VALOR"])


def procesar_pdf(file_pdf: UploadFile) -> pd.DataFrame:
    """Procesa un PDF bancario y devuelve FECHA, DESCRIPCION, VALOR.

    Soporta:
    - "Extracto PDF.pdf" (estado de cuenta con columnas VALOR y SALDO)
    - "Formato movimiento diario bancolombia.pdf" (movimiento diario con SUCURSAL/CANAL, REFERENCIAS, DOCUMENTO, VALOR)
    """

    pdf_bytes = file_pdf.file.read()
    pdf_stream = io.BytesIO(pdf_bytes)

    all_rows: list[list[object]] = []

    # 1) pdfplumber tables
    try:
        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    for row in table:
                        all_rows.append(row)
    except Exception as e:
        print(f"Warning pdfplumber: {e}")

    # 2) Camelot si no salió nada
    if not all_rows:
        pdf_stream.seek(0)
        try:
            tablas = camelot.read_pdf(pdf_stream, pages="all", flavor="lattice")
            if tablas:
                all_rows = [r for t in tablas for r in t.df.values.tolist()]
        except Exception as e:
            print(f"Warning Camelot: {e}")
            all_rows = []

    # texto completo para año y fallback
    pdf_stream.seek(0)
    pdf_text = ""
    try:
        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                pdf_text += page.extract_text() or ""
    except Exception:
        pdf_text = ""

    anio_pdf = _extract_year_from_pdf_text(pdf_text, default_year="2025")

    df = _build_df_from_rows(all_rows) if all_rows else None

    # fallback por texto
    if df is None or df.empty:
        df = _extract_from_text(pdf_text)

    # normalizar nombres de columnas
    cols_norm = [_norm_col(c) for c in df.columns]

    # detectar columnas clave
    idx_fecha = _pick_col(cols_norm, ["FECHA"])
    idx_desc = _pick_col(cols_norm, ["DESCRIP"])
    idx_valor = _pick_col(cols_norm, ["VALOR"])

    # si no hay nombres claros, usar posición
    if idx_fecha is None:
        idx_fecha = 0
    if idx_desc is None:
        idx_desc = 1 if df.shape[1] > 1 else 0
    if idx_valor is None:
        idx_valor = df.shape[1] - 1

    df_work = df.iloc[:, [idx_fecha, idx_desc, idx_valor]].copy()
    df_work.columns = ["FECHA", "DESCRIPCION", "VALOR"]

    # limpiar filas basura
    df_work = df_work[df_work["FECHA"].notna()]
    df_work["FECHA"] = df_work["FECHA"].astype(str).str.strip()
    df_work = df_work[~df_work["FECHA"].str.upper().eq("FECHA")]

    # completar año cuando venga dd/mm sin año
    mask_sin_anio = df_work["FECHA"].str.match(r"^\d{1,2}/\d{2}$", na=False)
    df_work.loc[mask_sin_anio, "FECHA"] = df_work.loc[mask_sin_anio, "FECHA"] + "/" + anio_pdf

    # parse fechas
    mask_yyyy = df_work["FECHA"].str.match(r"^\d{4}/\d{2}/\d{2}$", na=False)

    fechas = pd.Series([pd.NaT] * len(df_work))
    fechas.loc[mask_yyyy] = pd.to_datetime(df_work.loc[mask_yyyy, "FECHA"], format="%Y/%m/%d", errors="coerce")
    fechas.loc[~mask_yyyy] = pd.to_datetime(df_work.loc[~mask_yyyy, "FECHA"], dayfirst=True, errors="coerce")

    df_work["FECHA"] = fechas.dt.strftime("%d/%m/%Y")

    # limpiar descripción
    df_work["DESCRIPCION"] = df_work["DESCRIPCION"].astype(str)
    df_work["DESCRIPCION"] = df_work["DESCRIPCION"].str.replace("\n", " ", regex=False)
    df_work["DESCRIPCION"] = df_work["DESCRIPCION"].apply(lambda x: re.sub(r"\s+", " ", x).strip())

    # limpiar valor
    df_work["VALOR"] = _clean_valor_series(df_work["VALOR"])

    # quitar filas sin fecha o sin valor
    df_work = df_work[df_work["FECHA"].notna()]
    df_work = df_work[df_work["VALOR"].notna()]

    df_work["VALOR"] = df_work["VALOR"].astype(int)

    return df_work.reset_index(drop=True)