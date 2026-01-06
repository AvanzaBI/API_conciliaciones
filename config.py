"""
Configuración de la aplicación Excel Uploader.
Define las variables de entorno y configuraciones necesarias.
"""
import os
from typing import Optional, Tuple, List


class Config:
    """Configuración de la aplicación."""
    
    # Azure Storage Gen2
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    AZURE_STORAGE_CONTAINER_NAME: Optional[str] = os.getenv(
        "AZURE_STORAGE_CONTAINER_NAME", 
        "raw"
    )
    
    # Rutas
    STANDARDS_DIR: str = os.path.join(os.path.dirname(__file__), "standards")
    
    # Empresas disponibles
    # Estas empresas corresponden a carpetas de primer nivel bajo raw/busint en Azure Storage Gen2
    EMPRESAS_DISPONIBLES: List[str] = [
        "indualpes",
        "shape_concept",
        "yanko",
        "safetti",
        "zultex"
    ]
    
    # Ruta base para archivos de negocio
    BASE_PATH_BUSINT: str = "busint"
    
    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """
        Valida que las configuraciones requeridas estén presentes.
        
        Returns:
            tuple: (es_válido, lista_de_errores)
        """
        errores = []
        
        if not cls.AZURE_STORAGE_ACCOUNT_NAME:
            errores.append("AZURE_STORAGE_ACCOUNT_NAME no está configurado")
        
        if not cls.AZURE_STORAGE_ACCOUNT_KEY:
            errores.append("AZURE_STORAGE_ACCOUNT_KEY no está configurado")
        
        if not os.path.exists(cls.STANDARDS_DIR):
            errores.append(f"El directorio de estándares no existe: {cls.STANDARDS_DIR}")
        
        return len(errores) == 0, errores

