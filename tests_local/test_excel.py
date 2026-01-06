import os
import pandas as pd

if __name__ == "__main__":
    xls_path = os.path.join(os.getcwd(), "Movimiento banco noviembre.xlsx")

    df = pd.read_excel(xls_path)
    print("Columnas:", list(df.columns))
    print(df.head(20))
    print(df.dtypes)
    print("rows:", len(df))