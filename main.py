from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from procesar_pdf import procesar_pdf_universal
from unir_archivos import conciliar_movimientos
import pandas as pd
from io import BytesIO
import os

app = FastAPI()

# --- CORS: permitir todos los orígenes, sin credenciales ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/conciliacion-unificada/")
async def conciliacion_unificada(
    pdf_file: UploadFile = File(...),
    contabilidad_file: UploadFile = File(...)
):
    try:
        # --- Procesar PDF ---
        df_extracto = procesar_pdf_universal(pdf_file)

        if df_extracto.empty:
            return JSONResponse(
                status_code=400,
                content={"detail": "No se pudo extraer información del PDF."}
            )

        # --- Leer Excel contabilidad directamente en memoria ---
        contabilidad_bytes = await contabilidad_file.read()
        df_contabilidad = pd.read_excel(BytesIO(contabilidad_bytes))
        # FIX CRÍTICO: Resetear índice del DataFrame leído para evitar problemas de alineación
        df_contabilidad = df_contabilidad.reset_index(drop=True)

        # --- Conciliación ---
        excel_bytes = conciliar_movimientos(df_contabilidad, df_extracto)

        # --- Retornar Excel como streaming ---
        return StreamingResponse(
            BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Conciliacion_bancaria.xlsx"}
        ) 

    except Exception as e:
        # Captura cualquier error y devuelve detalle con traceback para debugging
        import traceback
        error_detail = str(e)
        error_traceback = traceback.format_exc()
        
        # Log del error completo para debugging
        print(f"\n{'='*60}")
        print("ERROR EN CONCILIACIÓN:")
        print(f"{'='*60}")
        print(error_traceback)
        print(f"{'='*60}\n")
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Error en proceso unificado: {error_detail}",
                "error_type": type(e).__name__,
                "traceback": error_traceback if "traceback" in str(e).lower() else None
            }
        )

# --- Carpeta estática ---
os.makedirs("static", exist_ok=True)
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")