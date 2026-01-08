import os
from pathlib import Path

from procesar_pdf import procesar_pdf

class FakeUploadFile:
    def __init__(self, path: str):
        self.filename = Path(path).name
        self.file = open(path, "rb")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent          # .../tests_local
    ARCHIVOS_DIR = BASE_DIR / "archivos"
    
    pdf_path = str(ARCHIVOS_DIR / "EXTRACTO AGOSTO 2025.pdf")
    up = FakeUploadFile(pdf_path)
    df = procesar_pdf(up)

    print(df.head(20))
    print(df.dtypes)
    print("rows:", len(df))