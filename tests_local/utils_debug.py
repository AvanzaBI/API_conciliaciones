import os
from datetime import datetime

def make_run_dir(base_dir: str = "debug_runs") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(base_dir, ts)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir

def dump_csv(df, run_dir: str, name: str):
    path = os.path.join(run_dir, f"{name}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path

def dump_excel(dfs: dict, run_dir: str, name: str):
    import pandas as pd
    path = os.path.join(run_dir, f"{name}.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet[:31], index=False)
    return path