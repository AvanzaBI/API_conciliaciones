"""
Cliente para interactuar con Azure Data Lake Storage Gen2.
Maneja la carga de archivos Excel a contenedores específicos.
"""
from azure.storage.filedatalake import DataLakeServiceClient
from azure.core.exceptions import AzureError
from typing import Optional, Tuple
import os
from config import Config


class AzureStorageClient:
    """Cliente para Azure Data Lake Storage Gen2."""
    
    def __init__(
        self, 
        account_name: str, 
        account_key: str, 
        container_name: str = "raw"
    ):
        """
        Inicializa el cliente de Azure Storage.
        
        Args:
            account_name: Nombre de la cuenta de Azure Storage.
            account_key: Clave de acceso de la cuenta.
            container_name: Nombre del contenedor (filesystem) en ADLS Gen2.
        """
        self.account_name = account_name
        self.account_key = account_key
        self.container_name = container_name
        self.service_client = None
        self._connect()
    
    def _connect(self):
        """Establece la conexión con Azure Storage."""
        try:
            account_url = f"https://{self.account_name}.dfs.core.windows.net"
            self.service_client = DataLakeServiceClient(
                account_url=account_url,
                credential=self.account_key
            )
        except Exception as e:
            raise ConnectionError(f"Error al conectar con Azure Storage: {str(e)}")
    
    def upload_file(
        self, 
        file_path_or_content, 
        destination_path: str, 
        file_name: str
    ) -> Tuple[bool, str]:
        """
        Sube un archivo a Azure Data Lake Storage Gen2.
        
        Args:
            file_path_or_content: Ruta del archivo local o contenido del archivo (bytes).
            destination_path: Ruta de destino en el contenedor (sin el nombre del archivo).
            file_name: Nombre del archivo a subir.
        
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # Obtener el sistema de archivos (contenedor)
            file_system_client = self.service_client.get_file_system_client(
                file_system=self.container_name
            )
            
            # Crear el sistema de archivos si no existe
            try:
                file_system_client.create_file_system()
            except Exception:
                # Ya existe, continuar
                pass
            
            # Construir la ruta completa
            full_path = f"{destination_path.rstrip('/')}/{file_name}" if destination_path else file_name
            
            # Obtener el cliente del archivo
            file_client = file_system_client.get_file_client(full_path)
            
            # Leer el contenido del archivo
            if isinstance(file_path_or_content, str) and os.path.exists(file_path_or_content):
                # Es una ruta de archivo
                with open(file_path_or_content, 'rb') as f:
                    file_content = f.read()
            elif hasattr(file_path_or_content, 'read'):
                # Es un objeto file-like (como UploadedFile de Streamlit)
                file_path_or_content.seek(0)  # Asegurar que estamos al inicio
                file_content = file_path_or_content.read()
            else:
                # Asumir que es bytes
                file_content = file_path_or_content
            
            # Subir el archivo
            file_client.upload_data(
                file_content,
                overwrite=True
            )
            
            return True, f"Archivo '{file_name}' subido exitosamente a {full_path}"
            
        except AzureError as e:
            return False, f"Error de Azure Storage: {str(e)}"
        except Exception as e:
            return False, f"Error al subir archivo: {str(e)}"
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Prueba la conexión con Azure Storage.
        
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            file_system_client = self.service_client.get_file_system_client(
                file_system=self.container_name
            )
            # Intentar listar (operación simple para verificar conexión)
            file_system_client.get_file_system_properties()
            return True, "Conexión exitosa con Azure Storage"
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"

