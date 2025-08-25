import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font 
from openpyxl.utils import get_column_letter
from io import BytesIO
from openpyxl.styles import numbers

def conciliar_movimientos(contabilidad_path: str, df_extracto: pd.DataFrame) -> str:    
    

    df1 = contabilidad_path.copy()
    df2 = df_extracto.copy()   

    # --- Preparación del df1 ---
    df1['FECHA'] = pd.to_datetime(df1['FECHA']).dt.strftime('%Y-%m-%d')
    df1['VALOR'] = df1['VALOR'].astype(int)
    df1['clave_unica'] = df1['FECHA'] + '_' + df1['VALOR'].astype(str)

    # --- Preparación del df2 ---
    df2['VALOR'] = df2['VALOR'].astype(int)
    df2['FECHA'] = pd.to_datetime(df2['FECHA']).dt.strftime('%Y-%m-%d')
    df2['clave_unica'] = df2['FECHA'] + '_' + df2['VALOR'].astype(str) 



    merged_df = pd.merge(df1, df2, on='clave_unica', how='outer', suffixes=('_Contabilidad', '_Extracto'))
    consolidado = merged_df.copy()

    # Caso 1: Entradas en contabilidad y no en extracto
    caso_1 = merged_df[(merged_df['VALOR_Contabilidad'] > 0) & (merged_df['VALOR_Extracto'].isna())]
    caso_1 = caso_1.drop(['FECHA_Extracto', 'VALOR_Extracto','clave_unica','DESCRIPCION'], axis=1)
    # Caso 2: Entradas en extracto y no en contabilidad
    caso_2 = merged_df[(merged_df['VALOR_Extracto'] > 0) & (merged_df['VALOR_Contabilidad'].isna())]
    caso_2 = caso_2.drop(['FECHA_Contabilidad', 'VALOR_Contabilidad','Concepto Contabilidad','clave_unica'], axis=1)
    # Caso 3: Salidas en contabilidad y no en extracto
    caso_3 = merged_df[(merged_df['VALOR_Contabilidad'] < 0) & (merged_df['VALOR_Extracto'].isna())]
    caso_3 = caso_3.drop(['FECHA_Extracto', 'VALOR_Extracto','DESCRIPCION','clave_unica'], axis=1)
    # Caso 4: Salidas en extracto y no en contabilidad
    caso_4 = merged_df[(merged_df['VALOR_Extracto'] < 0) & (merged_df['VALOR_Contabilidad'].isna())]
    caso_4 = caso_4.drop(['FECHA_Contabilidad', 'VALOR_Contabilidad','Concepto Contabilidad','clave_unica'], axis=1)
    # Eliminar la columna de clave temporal
    consolidado.drop('clave_unica', axis=1, inplace=True)

    consolidado = consolidado[['FECHA_Contabilidad', 'VALOR_Contabilidad', 'FECHA_Extracto', 'VALOR_Extracto']]
    # Hoja gastos bancarios
    ingresos =["ABONO INTERESES AHORROS","AJUSTE INTERES AHORROS DB"]
    df_ingresos = df2[df2['DESCRIPCION'].isin(ingresos)]
    df_ingresos['VALOR'] = df_ingresos['VALOR'].abs()
    df_ingresos=df_ingresos.groupby('DESCRIPCION').agg({'VALOR':'sum'}).reset_index()

    gastos_bancarios=["IMPTO GOBIERNO 4X1000","CUOTA MANEJO SUC VIRT EMPRESA","COMISION PAGO A PROVEEDORES","COMISION PAGO A NOMINA"]
    df_gastos_bancarios = df2[df2['DESCRIPCION'].isin(gastos_bancarios)]
    df_gastos_bancarios['VALOR'] = df_gastos_bancarios['VALOR'].abs()
    df_gastos_bancarios=df_gastos_bancarios.groupby('DESCRIPCION').agg({'VALOR':'sum'}).reset_index()

    impuestos =["IVA CUOTA MANEJO SUC VIRT EMP","COBRO IVA PAGOS AUTOMATICOS"]
    df_impuestos = df2[df2['DESCRIPCION'].isin(impuestos)]
    df_impuestos['VALOR'] = df_impuestos['VALOR'].abs()
    df_impuestos=df_impuestos.groupby('DESCRIPCION').agg({'VALOR':'sum'}).reset_index()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:

            # 🔹 Hoja 1: Resultado del join con formato
            # Escribimos el título primero
            merged_df.drop(columns=['clave_unica'], inplace=True)
            merged_df.to_excel(writer, sheet_name='Conciliacion', index=False, startrow=2)
            worksheet = writer.sheets['Conciliacion']
            worksheet.cell(row=1, column=1, value="Resultado de la Conciliación Bancaria").font = Font(bold=True, size=14)

            # Ajustar el ancho de las columnas y formatear fechas (usando openpyxl)
            for col_idx, col in enumerate(worksheet.columns, 1):
                max_length = 0
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

            

            # 🔹 Hoja 2: Ejemplo de encabezados y tablas
            # Creamos un DataFrame de ejemplo
            caso_1.to_excel(writer, sheet_name='Casos', index=False, startrow=4)
            caso_2.to_excel(writer, sheet_name='Casos', index=False, startrow=4+len(caso_1)+3)
            caso_3.to_excel(writer, sheet_name='Casos', index=False, startrow=4+len(caso_1) + len(caso_2) + 6)
            caso_4.to_excel(writer, sheet_name='Casos', index=False, startrow=4+len(caso_1) + len(caso_2) + len(caso_3) + 9)

            # Accedemos a la hoja 'Ejemplo' para añadir los textos y encabezados
            worksheet_ejemplo = writer.sheets['Casos']
            worksheet_ejemplo.cell(row=1, column=1, value="Formato de Conciliación Bancaria").font = Font(bold=True, size=14)
            worksheet_ejemplo.cell(row=3, column=1, value="Caso 1: Entradas en Contabilidad no en Extracto").font = Font(bold=True)
            worksheet_ejemplo.cell(row=4+len(caso_1)+3, column=1, value="Caso 2: Entradas en Extracto y no en Contabilidad").font = Font(bold=True)
            worksheet_ejemplo.cell(row=4+len(caso_1) + len(caso_2) + 6, column=1, value="Caso 3: Salidas en Contabilidad no en Extracto").font = Font(bold=True)
            worksheet_ejemplo.cell(row=4+len(caso_1) + len(caso_2) + len(caso_3) + 9, column=1, value="Caso 4: Salidas en Extracto y no en Contabilidad").font = Font(bold=True)

            # Ajustar el ancho de las columnas y formatear fechas (usando openpyxl)
            for col_idx, col in enumerate(worksheet_ejemplo.columns, 1):
                max_length = 0
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet_ejemplo.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

            # Buscar encabezados y aplicar formato en columnas de valores
            for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row):
                for cell in row:
                    if cell.value and "VALOR" in str(cell.value).upper():
                        col_idx = cell.col_idx  # número de columna de este encabezado
            
                        # Aplicar formato desde la fila siguiente hasta el final
                        for data_row in range(cell.row + 1, worksheet.max_row + 1):
                            valor_cell = worksheet.cell(data_row, col_idx)
                            if isinstance(valor_cell.value, (int, float)):
                                valor_cell.number_format = '"$"#,##0'  # COP sin decimales


            # Formatear columnas de VALOR como moneda en todas las hojas# Recorremos todas las filas
            for row_idx, row in enumerate(worksheet_ejemplo.iter_rows(min_row=1, max_row=worksheet_ejemplo.max_row), start=1):
                first_cell = str(row[0].value).strip() if row[0].value else ""

                # Detectamos inicio de tabla
                if first_cell.startswith("Caso"):
                    # La fila 2 después del encabezado de caso suele ser encabezados de tabla
                    header_row = row_idx + 1

                    # Recorremos desde header_row+1 hasta encontrar fila vacía
                    data_row = header_row + 1
                    while data_row <= worksheet_ejemplo.max_row and worksheet_ejemplo.cell(data_row, 1).value:
                        cell = worksheet_ejemplo.cell(data_row, 3)  # Columna C (VALOR)
                        if isinstance(cell.value, (int, float)):
                            cell.number_format = numbers.FORMAT_CURRENCY_USD_SIMPLE
                        data_row += 1

            # Hoja 3: Gastos Bancarios
            df_ingresos.to_excel(writer, sheet_name='Gastos Bancarios', index=False, startrow=2)
            df_gastos_bancarios.to_excel(writer, sheet_name='Gastos Bancarios', index=False, startrow=2+len(df_ingresos)+4)
            df_impuestos.to_excel(writer, sheet_name='Gastos Bancarios', index=False, startrow=2+len(df_ingresos)+4+len(df_gastos_bancarios)+4)

            # Textos y encabezados
            worksheet_gastos = writer.sheets['Gastos Bancarios']
            worksheet_gastos.cell(row=1, column=1, value="Gastos Bancarios").font = Font(bold=True, size=14)
            worksheet_gastos.cell(row=2, column=1, value="Ingresos").font = Font(bold=True)
            worksheet_gastos.cell(row=2+len(df_ingresos)+4, column=1, value="Gastos Bancarios").font = Font(bold=True)
            worksheet_gastos.cell(row=2+len(df_ingresos)+4+len(df_gastos_bancarios)+4, column=1, value="Impuestos").font = Font(bold=True)

            # Ajustar el ancho de las columnas y formatear fechas (usando openpyxl)
            for col_idx, col in enumerate(worksheet_gastos.columns, 1):
                max_length = 0
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet_gastos.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

            # Recorremos filas para encontrar encabezados de tabla
            for row_idx, row in enumerate(worksheet_gastos.iter_rows(min_row=1, max_row=worksheet_gastos.max_row), start=1):
                # Detectar encabezados de tabla (cuando la segunda celda dice "VALOR")
                if row[1].value and str(row[1].value).strip().upper() == "VALOR":
                    # Empezar a leer los datos desde la siguiente fila
                    data_row = row_idx + 1

                    # Recorremos hasta encontrar una fila vacía (fin de la tabla)
                    while data_row <= worksheet_gastos.max_row and worksheet_gastos.cell(data_row, 1).value:
                        cell = worksheet_gastos.cell(data_row, 2)  # Columna B (VALOR)
                        if isinstance(cell.value, (int, float)):
                            # Formato pesos colombianos sin decimales
                            cell.number_format = '"$"#,##0'
                        data_row += 1


    # Guardar el archivo Excel en memoria
    output.seek(0)
    return output.read()  # Retornamos los bytes del archivo Excel
