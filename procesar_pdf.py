import io
import os
import re
import tempfile
from typing import Literal, Optional

import pandas as pd
import pdfplumber
import camelot
from fastapi import UploadFile


TipoPDF = Literal["estado_cuenta", "movimiento_diario", "sin_texto", "desconocido"]


def _norm_text(s: str) -> str:
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


def _clean_valor(v: str) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None

    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()

    s = s.replace("$", "").replace(" ", "")
    s = s.replace(",", "")

    if re.fullmatch(r"-?\.\d+", s):
        s = "0" + s

    try:
        num = float(s)
    except Exception:
        return None

    num = int(round(num, 0))
    if neg:
        num = -abs(num)
    return num


def _pdf_text(pdf_stream: io.BytesIO) -> str:
    pdf_stream.seek(0)
    out = []
    with pdfplumber.open(pdf_stream) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
    return "\n".join(out)


def _detectar_tipo(texto: str) -> TipoPDF:
    t = _norm_text(texto)

    if not t.strip():
        return "sin_texto"

    if "ESTADO DE CUENTA" in t and "SALDO" in t and "VALOR" in t:
        return "estado_cuenta"

    if "SUCURSAL/CANAL" in t and "REFERENCIA" in t and re.search(r"\b20\d{2}/\d{2}/\d{2}\b", t):
        return "movimiento_diario"

    return "desconocido"


def _extraer_anio_desde_texto(texto: str, default_year: str = "2025") -> str:
    t = _norm_text(texto)
    m = re.search(r"DESDE:\s*(20\d{2})/", t)
    if m:
        return m.group(1)
    m = re.search(r"(20\d{2})", t)
    return m.group(1) if m else default_year


def _parse_estado_cuenta_por_lineas(pdf_bytes: bytes) -> pd.DataFrame:
    bio = io.BytesIO(pdf_bytes)
    texto = _pdf_text(bio)
    if not (texto or "").strip():
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    anio = _extraer_anio_desde_texto(texto, default_year="2025")

    lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]

    # Ejemplos detectados:
    # 2/05 IMPTO ... -19,865.88 7,329,926.63
    # 3/05 ABONO ... 6.46 2,363,461.09
    mov_re = re.compile(
        r"^(?P<dm>\d{1,2}/\d{2})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<valor>-?[\d,]+\.\d{2})\s+"
        r"(?P<saldo>[\d,]+\.\d{2})$"
    )

    data = []
    for ln in lineas:
        mm = mov_re.match(ln)
        if not mm:
            continue
        fecha = f"{mm.group('dm')}/{anio}"
        data.append((fecha, mm.group("desc"), mm.group("valor")))

    df = pd.DataFrame(data, columns=["FECHA", "DESCRIPCION", "VALOR"])
    if df.empty:
        return df

    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce").dt.strftime("%d/%m/%Y")
    df["DESCRIPCION"] = df["DESCRIPCION"].map(_norm_text)
    df["VALOR"] = df["VALOR"].map(_clean_valor)
    df = df.dropna(subset=["FECHA", "VALOR"]).reset_index(drop=True)
    return df


def _parse_movimiento_diario_con_camelot(tmp_path: str) -> pd.DataFrame:
    tablas = camelot.read_pdf(tmp_path, pages="all", flavor="lattice")
    if not tablas or len(tablas) == 0:
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    frames = []
    for t in tablas:
        df = t.df.copy()
        if df.shape[1] < 3:
            continue

        # Buscar header con FECHA y DESCRIPCION y VALOR
        header_idx = None
        for i in range(min(12, len(df))):
            row = " ".join(df.iloc[i].astype(str).tolist()).upper()
            if "FECHA" in row and "DESCRIP" in row and "VALOR" in row:
                header_idx = i
                break

        if header_idx is None:
            continue

        df2 = df.iloc[header_idx + 1 :].copy()
        df2 = df2[df2.iloc[:, 0].astype(str).str.match(r"^20\d{2}/\d{2}/\d{2}$", na=False)]
        if df2.empty:
            continue

        # Normalmente:
        # 0 FECHA, 1 DESCRIPCION, última columna VALOR
        df2 = df2.rename(columns={0: "FECHA", 1: "DESCRIPCION", df2.columns[-1]: "VALOR"})
        frames.append(df2[["FECHA", "DESCRIPCION", "VALOR"]])

    if not frames:
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    out = pd.concat(frames, ignore_index=True)
    out["FECHA"] = pd.to_datetime(out["FECHA"], format="%Y/%m/%d", errors="coerce").dt.strftime("%d/%m/%Y")
    out["DESCRIPCION"] = out["DESCRIPCION"].astype(str).map(_norm_text)
    out["VALOR"] = out["VALOR"].map(_clean_valor)
    out = out.dropna(subset=["FECHA", "VALOR"]).reset_index(drop=True)
    return out


def _parse_movimiento_diario_por_texto(pdf_bytes: bytes) -> pd.DataFrame:
    bio = io.BytesIO(pdf_bytes)
    texto = _pdf_text(bio)
    if not (texto or "").strip():
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    data = []

    # FECHA al inicio: 2025/05/08
    date_re = re.compile(r"^(20\d{2}/\d{2}/\d{2})\s+")

    for ln in lineas:
        if not date_re.search(ln):
            continue

        fecha = ln.split()[0]
        m = re.search(r"(-?[\d.,]+)\s*$", ln)
        if not m:
            continue
        valor_raw = m.group(1)

        mid = ln[len(fecha) :].strip()
        if valor_raw in mid:
            mid = mid[: mid.rfind(valor_raw)].strip()
        desc = mid

        data.append((fecha, desc, valor_raw))

    df = pd.DataFrame(data, columns=["FECHA", "DESCRIPCION", "VALOR"])
    if df.empty:
        return df

    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%Y/%m/%d", errors="coerce").dt.strftime("%d/%m/%Y")
    df["DESCRIPCION"] = df["DESCRIPCION"].map(_norm_text)
    df["VALOR"] = df["VALOR"].map(_clean_valor)
    df = df.dropna(subset=["FECHA", "VALOR"]).reset_index(drop=True)
    return df


def procesar_pdf_universal(file_pdf: UploadFile) -> pd.DataFrame:
    """
    Retorna DataFrame con:
    FECHA (dd/mm/YYYY), DESCRIPCION (UPPER), VALOR (int)

    Tipos:
    - Estado de cuenta: parseo por líneas
    - Movimiento diario: Camelot, fallback por texto
    - Sin texto: retorna vacío
    """
    pdf_bytes = file_pdf.file.read()
    bio = io.BytesIO(pdf_bytes)

    texto = _pdf_text(bio)
    tipo = _detectar_tipo(texto)

    if tipo == "sin_texto":
        return pd.DataFrame(columns=["FECHA", "DESCRIPCION", "VALOR"])

    if tipo == "estado_cuenta":
        return _parse_estado_cuenta_por_lineas(pdf_bytes)

    if tipo == "movimiento_diario":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            df = _parse_movimiento_diario_con_camelot(tmp_path)
            if df.empty:
                df = _parse_movimiento_diario_por_texto(pdf_bytes)
            return df
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # fallback: intentar ambos
    df1 = _parse_estado_cuenta_por_lineas(pdf_bytes)
    if not df1.empty:
        return df1

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        df2 = _parse_movimiento_diario_con_camelot(tmp_path)
        if df2.empty:
            df2 = _parse_movimiento_diario_por_texto(pdf_bytes)
        return df2
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
