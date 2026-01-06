import os
from pathlib import Path

import pandas as pd

from procesar_pdf import procesar_pdf
from unir_archivos import conciliar_movimientos
from tests_local.utils_debug import make_run_dir, dump_csv, dump_excel

class FakeUploadFile:
    def __init__(self, path: str):
        self.filename = Path(path).name
        self.file = open(path, "rb")

if __name__ == "__main__":
    run_dir = make_run_dir()

    pdf_path = os.path.join(os.getcwd(), "Formato movimiento diario bancolombia.pdf")
    xls_path = os.path.join(os.getcwd(), "Movimiento banco noviembre.xlsx")

    df_excel = pd.read_excel(xls_path)
    dump_csv(df_excel, run_dir, "01_excel_raw")

    up = FakeUploadFile(pdf_path)
    df_pdf = procesar_pdf(up)
    dump_csv(df_pdf, run_dir, "02_pdf_df")

    # Si conciliar_movimientos lee el excel desde archivo, usa el path directo.
    # Si conciliar_movimientos recibe DataFrames, pásalos.
    # Ajusta esta llamada a tu firma real.
    resultado = conciliar_movimientos(df_excel, df_pdf)

    # 1) Si devuelve bytes, guárdalo como .xlsx
    if isinstance(resultado, (bytes, bytearray)):
        out_path = os.path.join(run_dir, "Conciliacion_bancaria_debug.xlsx")
        with open(out_path, "wb") as f:
            f.write(resultado)
        print("Excel generado:", out_path)
    
    # 2) Si devuelve dict de DataFrames
    elif isinstance(resultado, dict):
        for k, v in resultado.items():
            dump_csv(v, run_dir, f"out_{k}")
        dump_excel(resultado, run_dir, "conciliacion_debug")
    
    # 3) Si devuelve DataFrame
    else:
        dump_csv(resultado, run_dir, "out_merged")
        dump_excel({"merged": resultado}, run_dir, "conciliacion_debug")