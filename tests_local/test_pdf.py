import os
from pathlib import Path

from procesar_pdf import procesar_pdf

class FakeUploadFile:
    def __init__(self, path: str):
        self.filename = Path(path).name
        self.file = open(path, "rb")

if __name__ == "__main__":
    pdf_path = os.path.join(os.getcwd(), "Formato movimiento diario bancolombia.pdf")
    up = FakeUploadFile(pdf_path)
    df = procesar_pdf(up)

    print(df.head(20))
    print(df.dtypes)
    print("rows:", len(df))