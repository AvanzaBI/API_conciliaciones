"""
Módulo de validación de archivos Excel.
Valida que la estructura del Excel coincida con los estándares definidos.
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import os


class ExcelValidator:
    """Validador de estructura de archivos Excel."""
    
    def __init__(self, standards_dir: str):
        """
        Inicializa el validador.
        
        Args:
            standards_dir: Directorio donde se encuentran los archivos JSON de estándares.
        """
        self.standards_dir = standards_dir
        self._standards_cache: Dict[str, Dict] = {}
    
    def load_standard(self, report_type: str) -> Optional[Dict]:
        """
        Carga el estándar de un tipo de informe desde un archivo JSON.
        
        Args:
            report_type: Nombre del tipo de informe (nombre del archivo sin extensión).
        
        Returns:
            Diccionario con el estándar o None si no existe.
        """
        if report_type in self._standards_cache:
            return self._standards_cache[report_type]
        
        json_path = os.path.join(self.standards_dir, f"{report_type}.json")
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                standard = json.load(f)
                self._standards_cache[report_type] = standard
                return standard
        except Exception as e:
            print(f"Error al cargar estándar {report_type}: {e}")
            return None
    
    def get_available_report_types(self) -> List[str]:
        """
        Obtiene la lista de tipos de informe disponibles.
        
        Returns:
            Lista de nombres de tipos de informe.
        """
        if not os.path.exists(self.standards_dir):
            return []
        
        report_types = []
        for filename in os.listdir(self.standards_dir):
            if filename.endswith('.json'):
                report_type = filename[:-5]  # Remover .json
                report_types.append(report_type)
        
        return sorted(report_types)
    
    def validate_excel_structure(
        self, 
        excel_file, 
        report_type: str
    ) -> Tuple[bool, str, Dict]:
        """
        Valida que la estructura del Excel coincida con el estándar.
        
        Args:
            excel_file: Archivo Excel cargado (objeto de Streamlit UploadedFile o path).
            report_type: Tipo de informe a validar.
        
        Returns:
            Tupla (es_válido, mensaje, detalles)
            - es_válido: True si la validación es exitosa
            - mensaje: Mensaje descriptivo del resultado
            - detalles: Diccionario con información detallada (columnas_faltantes, columnas_sobrantes, etc.)
        """
        # Cargar estándar
        standard = self.load_standard(report_type)
        if not standard:
            return False, f"No se encontró el estándar para el tipo de informe '{report_type}'", {}
        
        expected_columns = standard.get("columns", [])
        if not expected_columns:
            return False, f"El estándar '{report_type}' no define columnas", {}
        
        # Leer Excel
        try:
            df = pd.read_excel(excel_file, nrows=0)  # Solo leer encabezados
        except Exception as e:
            return False, f"Error al leer el archivo Excel: {str(e)}", {}
        
        # Validar que tenga encabezados
        if df.empty or len(df.columns) == 0:
            return False, "El archivo Excel no tiene encabezados de columna", {}
        
        # Obtener columnas del Excel (normalizadas: sin espacios extras, en mayúsculas)
        excel_columns = [str(col).strip() for col in df.columns]
        expected_columns_normalized = [str(col).strip() for col in expected_columns]
        
        # Encontrar diferencias
        excel_set = set(excel_columns)
        expected_set = set(expected_columns_normalized)
        
        missing_columns = sorted(list(expected_set - excel_set))
        extra_columns = sorted(list(excel_set - expected_set))
        
        detalles = {
            "columnas_esperadas": expected_columns_normalized,
            "columnas_encontradas": excel_columns,
            "columnas_faltantes": missing_columns,
            "columnas_sobrantes": extra_columns,
            "total_esperadas": len(expected_columns_normalized),
            "total_encontradas": len(excel_columns)
        }
        
        # Validación estricta: debe coincidir exactamente
        if missing_columns or extra_columns:
            mensaje = self._generate_error_message(missing_columns, extra_columns)
            return False, mensaje, detalles
        
        return True, f"✓ Validación exitosa: El archivo cumple con el estándar '{report_type}'", detalles
    
    def _generate_error_message(
        self, 
        missing_columns: List[str], 
        extra_columns: List[str]
    ) -> str:
        """
        Genera un mensaje de error claro y entendible.
        
        Args:
            missing_columns: Lista de columnas faltantes.
            extra_columns: Lista de columnas sobrantes.
        
        Returns:
            Mensaje de error formateado.
        """
        mensajes = []
        
        if missing_columns:
            if len(missing_columns) == 1:
                mensajes.append(f"Falta la columna: {missing_columns[0]}")
            else:
                mensajes.append(f"Faltan {len(missing_columns)} columnas: {', '.join(missing_columns)}")
        
        if extra_columns:
            if len(extra_columns) == 1:
                mensajes.append(f"Columna no esperada: {extra_columns[0]}")
            else:
                mensajes.append(f"{len(extra_columns)} columnas no esperadas: {', '.join(extra_columns)}")
        
        return " | ".join(mensajes)


