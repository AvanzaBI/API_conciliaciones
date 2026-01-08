#!/usr/bin/env python3
"""
Script de diagnóstico para identificar errores con archivos de diciembre.
Compara archivos de prueba vs archivos reales y muestra errores detallados.
"""
import sys
import traceback
import pandas as pd
from pathlib import Path
from procesar_pdf import procesar_pdf
from unir_archivos import conciliar_movimientos
import logging

# Configurar logging detallado
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

class FakeUploadFile:
    def __init__(self, path: str):
        self.filename = Path(path).name
        self.file = open(path, 'rb')

def diagnosticar_pdf(pdf_path: str):
    """Diagnostica problemas con el PDF."""
    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO PDF: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    try:
        up = FakeUploadFile(pdf_path)
        df = procesar_pdf(up)
        up.file.close()
        
        print(f"✅ PDF procesado exitosamente")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {list(df.columns)}")
        
        if df.empty:
            print("❌ ERROR: DataFrame vacío después de procesar PDF")
            return None
        
        # Verificar columnas requeridas
        required_cols = ['FECHA', 'DESCRIPCION', 'VALOR']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            print(f"❌ ERROR: Faltan columnas: {missing_cols}")
            return None
        
        # Verificar tipos de datos
        print(f"\n📊 Análisis de datos:")
        print(f"   FECHAs válidas: {df['FECHA'].notna().sum()}/{len(df)}")
        print(f"   VALORs válidos: {df['VALOR'].notna().sum()}/{len(df)}")
        print(f"   VALORs numéricos: {pd.to_numeric(df['VALOR'], errors='coerce').notna().sum()}/{len(df)}")
        
        # Mostrar primeras filas
        print(f"\n📋 Primeras 5 filas:")
        print(df.head().to_string())
        
        return df
        
    except Exception as e:
        print(f"❌ ERROR al procesar PDF: {str(e)}")
        print(f"\n🔍 Traceback completo:")
        traceback.print_exc()
        return None

def diagnosticar_excel(excel_path: str):
    """Diagnostica problemas con el Excel."""
    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO EXCEL: {Path(excel_path).name}")
    print(f"{'='*60}")
    
    try:
        df = pd.read_excel(excel_path)
        
        print(f"✅ Excel leído exitosamente")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {list(df.columns)}")
        
        if df.empty:
            print("❌ ERROR: DataFrame vacío")
            return None
        
        # Mostrar primeras filas
        print(f"\n📋 Primeras 5 filas:")
        print(df.head().to_string())
        
        # Verificar tipos de datos
        print(f"\n📊 Tipos de datos:")
        print(df.dtypes.to_string())
        
        return df
        
    except Exception as e:
        print(f"❌ ERROR al leer Excel: {str(e)}")
        print(f"\n🔍 Traceback completo:")
        traceback.print_exc()
        return None

def diagnosticar_conciliacion(df_contabilidad, df_extracto):
    """Diagnostica problemas en la conciliación."""
    print(f"\n{'='*60}")
    print("DIAGNÓSTICO CONCILIACIÓN")
    print(f"{'='*60}")
    
    try:
        print(f"📊 DataFrames de entrada:")
        print(f"   Contabilidad: {len(df_contabilidad)} filas × {len(df_contabilidad.columns)} columnas")
        print(f"   Extracto: {len(df_extracto)} filas × {len(df_extracto.columns)} columnas")
        
        # Verificar preparación de claves únicas
        print(f"\n🔑 Preparando claves únicas...")
        
        # Preparar df1 (contabilidad)
        df1 = df_contabilidad.copy()
        df1['FECHA'] = pd.to_datetime(df1['FECHA'], dayfirst=True, errors="coerce").dt.strftime("%d/%m/%Y")
        df1['VALOR'] = pd.to_numeric(df1['VALOR'], errors="coerce").fillna(0).astype(int)
        df1['clave_unica'] = df1['FECHA'] + '_' + df1['VALOR'].astype(str)
        
        print(f"   Contabilidad - FECHAs válidas: {df1['FECHA'].notna().sum()}/{len(df1)}")
        print(f"   Contabilidad - VALORs válidos: {df1['VALOR'].notna().sum()}/{len(df1)}")
        print(f"   Contabilidad - Claves únicas: {df1['clave_unica'].nunique()}/{len(df1)}")
        
        # Preparar df2 (extracto)
        df2 = df_extracto.copy()
        df2['FECHA'] = pd.to_datetime(df2['FECHA'], dayfirst=True, errors="coerce").dt.strftime("%d/%m/%Y")
        df2['VALOR'] = pd.to_numeric(df2['VALOR'], errors="coerce").fillna(0).astype(int)
        df2['clave_unica'] = df2['FECHA'] + '_' + df2['VALOR'].astype(str)
        
        print(f"   Extracto - FECHAs válidas: {df2['FECHA'].notna().sum()}/{len(df2)}")
        print(f"   Extracto - VALORs válidos: {df2['VALOR'].notna().sum()}/{len(df2)}")
        print(f"   Extracto - Claves únicas: {df2['clave_unica'].nunique()}/{len(df2)}")
        
        # Merge
        print(f"\n🔀 Ejecutando merge...")
        merged_df = pd.merge(df1, df2, on='clave_unica', how='outer', suffixes=('_Contabilidad', '_Extracto'))
        merged_df = merged_df.reset_index(drop=True)
        
        print(f"   Resultado merge: {len(merged_df)} filas")
        print(f"   Columnas: {list(merged_df.columns)}")
        
        # Verificar tipos numéricos
        merged_df['VALOR_Contabilidad'] = pd.to_numeric(merged_df['VALOR_Contabilidad'], errors="coerce")
        merged_df['VALOR_Extracto'] = pd.to_numeric(merged_df['VALOR_Extracto'], errors="coerce")
        
        print(f"\n✅ Merge exitoso, ejecutando conciliación completa...")
        excel_bytes = conciliar_movimientos(df_contabilidad, df_extracto)
        
        print(f"✅ Conciliación exitosa")
        print(f"   Tamaño Excel generado: {len(excel_bytes)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR en conciliación: {str(e)}")
        print(f"\n🔍 Traceback completo:")
        traceback.print_exc()
        return False

def main():
    """Función principal de diagnóstico."""
    print("="*60)
    print("DIAGNÓSTICO DE ERRORES - CONCILIACIÓN BANCARIA")
    print("="*60)
    
    # Archivos de prueba (que funcionan)
    pdf_prueba = "Formato movimiento diario bancolombia.pdf"
    excel_prueba = "Movimiento banco noviembre.xlsx"
    
    print("\n📁 Archivos de prueba (que funcionan):")
    print(f"   PDF: {pdf_prueba}")
    print(f"   Excel: {excel_prueba}")
    
    # Solicitar archivos de diciembre
    print("\n" + "="*60)
    print("ARCHIVOS DE DICIEMBRE (que fallan)")
    print("="*60)
    
    pdf_diciembre = input("\n📄 Ruta del PDF de diciembre (o Enter para usar archivos de prueba): ").strip()
    excel_diciembre = input("📊 Ruta del Excel de diciembre (o Enter para usar archivos de prueba): ").strip()
    
    if not pdf_diciembre:
        pdf_diciembre = pdf_prueba
    if not excel_diciembre:
        excel_diciembre = excel_prueba
    
    # Verificar que los archivos existan
    if not Path(pdf_diciembre).exists():
        print(f"❌ ERROR: No se encuentra el PDF: {pdf_diciembre}")
        return 1
    
    if not Path(excel_diciembre).exists():
        print(f"❌ ERROR: No se encuentra el Excel: {excel_diciembre}")
        return 1
    
    # Diagnosticar archivos de diciembre
    df_extracto = diagnosticar_pdf(pdf_diciembre)
    if df_extracto is None:
        return 1
    
    df_contabilidad = diagnosticar_excel(excel_diciembre)
    if df_contabilidad is None:
        return 1
    
    # Diagnosticar conciliación
    success = diagnosticar_conciliacion(df_contabilidad, df_extracto)
    
    if success:
        print("\n" + "="*60)
        print("✅ DIAGNÓSTICO COMPLETADO - TODO FUNCIONA")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ DIAGNÓSTICO COMPLETADO - SE ENCONTRARON ERRORES")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())

