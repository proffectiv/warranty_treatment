#!/usr/bin/env python3
"""
WarrantyFormData Class
Centralized webhook data parsing and normalization for warranty form processing
"""

import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import logging filter from root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

# Set up secure logging
logger = setup_secure_logging('warranty_form_data')

@dataclass
class FileInfo:
    """Represents a file attachment"""
    id: str
    name: str
    url: str
    mime_type: str = ""
    size: int = 0

class WarrantyFormData:
    """
    Centralized class for parsing and normalizing warranty form webhook data.
    Handles multiple webhook formats (old structure, new unified structure, GitHub Actions format).
    """
    
    def __init__(self, webhook_data: Dict[str, Any], ticket_id: str = ""):
        """
        Initialize with webhook data and parse all fields
        
        Args:
            webhook_data: Raw webhook data from Tally
            ticket_id: Optional ticket ID to assign
        """
        self.raw_data = webhook_data
        self.ticket_id = ticket_id
        self._fields = {}
        self._parse_webhook_data()
        
    def _parse_webhook_data(self):
        """Parse webhook data and extract fields based on format"""
        try:
            # Determine webhook format and extract fields
            if 'fields' in self.raw_data and 'fieldsById' in self.raw_data:
                # New GitHub action webhook structure (direct client_payload)
                self._fields = self.raw_data['fields']
                logger.info("Detected new GitHub action webhook structure")
                
            elif 'client_payload' in self.raw_data:
                # GitHub webhook structure with client_payload
                if 'fields' in self.raw_data['client_payload']:
                    self._fields = self.raw_data['client_payload']['fields']
                    logger.info("Detected GitHub webhook structure with client_payload")
                else:
                    # Old structure within client_payload
                    self._parse_old_structure(self.raw_data['client_payload'])
                    
            elif 'data' in self.raw_data and 'fields' in self.raw_data['data']:
                # Old webhook structure with data.fields
                self._parse_old_structure(self.raw_data['data'])
                
            else:
                # Try parsing as direct old structure
                self._parse_old_structure(self.raw_data)
                
        except Exception as e:
            logger.error(f"Error parsing webhook data: {str(e)}")
            self._fields = {}
    
    def _parse_old_structure(self, data: Dict[str, Any]):
        """Parse old webhook structure with field arrays"""
        try:
            fields_array = data.get('fields', [])
            self._fields = {}
            
            for field in fields_array:
                label = field.get('label', '')
                value = field.get('value')
                
                # Handle dropdown options - convert IDs to text values
                if isinstance(value, list) and field.get('options'):
                    converted_values = []
                    for val in value:
                        if isinstance(val, str):
                            # Find matching option text
                            for option in field.get('options', []):
                                if option.get('id') == val or option.get('text') == val:
                                    converted_values.append(option.get('text', val))
                                    break
                            else:
                                converted_values.append(val)
                    self._fields[label] = converted_values
                else:
                    self._fields[label] = value
                    
            logger.info("Parsed old webhook structure")
            
        except Exception as e:
            logger.error(f"Error parsing old structure: {str(e)}")
            self._fields = {}
    
    def _get_field_value(self, field_name: str, fallback_names: List[str] = None) -> str:
        """
        Get field value with fallback support for backward compatibility
        
        Args:
            field_name: Primary field name to look for
            fallback_names: List of fallback field names for backward compatibility
            
        Returns:
            Field value as string or 'No especificado' if not found
        """
        # Try primary field name first
        value = self._fields.get(field_name)
        
        # Try fallback names if primary not found
        if value is None and fallback_names:
            for fallback in fallback_names:
                value = self._fields.get(fallback)
                if value is not None:
                    break
        
        if value is None:
            return 'No especificado'
        
        # Handle different value types
        if isinstance(value, list):
            if len(value) > 0:
                if isinstance(value[0], dict):
                    # File upload - return file info
                    return f"Archivo adjunto: {value[0].get('name', 'archivo')}"
                else:
                    # Dropdown selection - return the selected value
                    return str(value[0])
            else:
                return 'No especificado'
        elif isinstance(value, str):
            return value if value.strip() else 'No especificado'
        else:
            return str(value) if value else 'No especificado'
    
    def _get_file_list(self, field_name: str, fallback_names: List[str] = None) -> List[FileInfo]:
        """
        Get list of files from a field
        
        Args:
            field_name: Primary field name to look for
            fallback_names: List of fallback field names
            
        Returns:
            List of FileInfo objects
        """
        # Try primary field name first
        value = self._fields.get(field_name)
        
        # Try fallback names if primary not found
        if value is None and fallback_names:
            for fallback in fallback_names:
                value = self._fields.get(fallback)
                if value is not None:
                    break
        
        if not isinstance(value, list):
            return []
        
        files = []
        for item in value:
            if isinstance(item, dict) and 'url' in item:
                file_info = FileInfo(
                    id=item.get('id', ''),
                    name=item.get('name', 'file'),
                    url=item['url'],
                    mime_type=item.get('mimeType', ''),
                    size=item.get('size', 0)
                )
                files.append(file_info)
        
        return files
    
    # Company Information Properties
    @property
    def empresa(self) -> str:
        """Company name"""
        return self._get_field_value('Empresa')
    
    @property
    def nif_cif(self) -> str:
        """Company tax ID"""
        return self._get_field_value('NIF/CIF/VAT')
    
    @property
    def email(self) -> str:
        """Company email"""
        return self._get_field_value('Email')
    
    # Product Information Properties
    @property
    def brand(self) -> str:
        """Product brand"""
        return self._get_field_value('Marca del Producto')
    
    @property
    def modelo(self) -> str:
        """Product model - handles both unified and brand-specific fields"""
        if self.is_conway():
            # Conway uses text input for model
            return self._get_field_value(
                'Conway - Modelo',
                ['Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)']
            )
        elif self.is_cycplus():
            # Cycplus uses unified dropdown or brand-specific
            return self._get_field_value('Modelo', ['Cycplus - Modelo'])
        elif self.is_dare():
            # Dare uses unified dropdown or brand-specific
            return self._get_field_value('Modelo', ['Dare - Modelo'])
        elif self.is_kogel():
            return self._get_field_value('Kogel - Modelo', ['Modelo'])
        else:
            return self._get_field_value('Modelo')
    
    @property
    def talla(self) -> str:
        """Product size - only for Conway and Dare"""
        if self.is_conway():
            return self._get_field_value('Talla', ['Conway - Talla'])
        elif self.is_dare():
            return self._get_field_value('Talla', ['Dare - Talla'])
        else:
            return 'No aplicable'
    
    @property
    def año(self) -> str:
        """Manufacturing year"""
        if self.is_conway():
            return self._get_field_value('Año de fabricación', ['Conway - Año de fabricación'])
        elif self.is_dare():
            return self._get_field_value('Año de fabricación', ['Dare - Año de fabricación'])
        else:
            return self._get_field_value('Año de fabricación')
    
    @property
    def estado(self) -> str:
        """Product condition"""
        if self.is_conway():
            return self._get_field_value('Estado del producto', ['Conway - Estado de la bicicleta'])
        elif self.is_cycplus():
            return self._get_field_value('Estado del producto', ['Cycplus - Estado del Producto'])
        elif self.is_dare():
            return self._get_field_value('Estado del producto', ['Dare - Estado de la bicicleta'])
        else:
            return self._get_field_value('Estado del producto')
    
    # Problem Information Properties
    @property
    def problema(self) -> str:
        """Problem description"""
        return self._get_field_value(
            'Descripción del problema',
            [
                'Conway - Descripción del problema',
                'Cycplus - Descripción del problema', 
                'Dare - Descripción del problema'
            ]
        )
    
    @property
    def solucion(self) -> str:
        """Proposed solution - only for Conway and Dare"""
        if self.is_conway():
            return self._get_field_value(
                'Solución o reparación propuesta y presupuesto',
                ['Solución o reparación propuesta y presupuesto aproximado', 'Conway - Solución o reparación propuesta y presupuesto aproximado']
            )
        elif self.is_dare():
            return self._get_field_value(
                'Solución o reparación propuesta y presupuesto',
                ['Solución o reparación propuesta y presupuesto aproximado', 'Dare - Solución o reparación propuesta y presupuesto aproximado']
            )
        else:
            return 'No aplicable'
    
    # File Attachment Properties
    @property
    def factura_compra(self) -> List[FileInfo]:
        """Purchase invoice files"""
        if self.is_conway():
            return self._get_file_list(
                'Factura de compra',
                ['Conway - Adjunta la factura de compra a Hartje']
            )
        elif self.is_cycplus():
            return self._get_file_list(
                'Factura de compra',
                ['Adjunta la factura de compra']
            )
        elif self.is_dare():
            return self._get_file_list(
                'Factura de compra',
                ['Dare - Adjunta la factura de compra']
            )
        else:
            return self._get_file_list('Factura de compra')
    
    @property
    def factura_venta(self) -> List[FileInfo]:
        """Sales invoice files"""
        if self.is_conway():
            return self._get_file_list(
                'Factura de venta',
                ['Conway - Adjunta la factura de venta']
            )
        elif self.is_cycplus():
            return self._get_file_list(
                'Factura de venta',
                ['Cycplus - Adjunta la factura de venta']
            )
        elif self.is_dare():
            return self._get_file_list(
                'Factura de venta',
                ['Dare - Adjunta la factura de venta']
            )
        else:
            return self._get_file_list('Factura de venta')
    
    @property
    def fotos_problema(self) -> List[FileInfo]:
        """Problem photos"""
        return self._get_file_list('Fotos del problema (requerido)')
    
    @property
    def videos_problema(self) -> List[FileInfo]:
        """Problem videos"""
        return self._get_file_list('Videos del problema (opcional)', ['Vídeos del problema (opcional)'])
    
    # Brand Detection Methods
    def is_conway(self) -> bool:
        """Check if this is a Conway warranty request"""
        return self.brand.lower() == 'conway'
    
    def is_cycplus(self) -> bool:
        """Check if this is a Cycplus warranty request"""
        return self.brand.lower() == 'cycplus'
    
    def is_dare(self) -> bool:
        """Check if this is a Dare warranty request"""
        return self.brand.lower() == 'dare'
    
    def is_kogel(self) -> bool:
        """Check if this is a Kogel warranty request"""
        return self.brand.lower() == 'kogel'
    
    # Utility Methods
    def get_all_files(self) -> List[FileInfo]:
        """Get all file attachments"""
        all_files = []
        all_files.extend(self.factura_compra)
        all_files.extend(self.factura_venta)
        all_files.extend(self.fotos_problema)
        all_files.extend(self.videos_problema)
        return all_files
    
    def has_invoices(self) -> bool:
        """Check if any invoice files are attached"""
        return len(self.factura_compra) > 0 or len(self.factura_venta) > 0
    
    def to_excel_row(self, brand: str) -> Dict[str, Any]:
        """
        Generate Excel row data for the specified brand sheet
        
        Args:
            brand: Brand name for sheet-specific formatting
            
        Returns:
            Dictionary with Excel column names and values
        """
        fecha_creacion = datetime.now().strftime('%d/%m/%Y')
        
        if brand == 'Conway':
            return {
                'Ticket ID': self.ticket_id,
                'Estado': 'Recibida',
                'Fecha de creación': fecha_creacion,
                'Empresa': self.empresa,
                'NIF/CIF/VAT': self.nif_cif,
                'Email': self.email,
                'Modelo': self.modelo,
                'Talla': self.talla,
                'Año de fabricación': self.año,
                'Estado de la bicicleta': self.estado,
                'Descripción del problema': self.problema,
                'Solución y/o reparación propuesta y presupuesto': self.solucion,
                'Factura de compra': {'type': 'hyperlink', 'url': self.factura_compra[0].url, 'text': self.factura_compra[0].name} if self.factura_compra else '',
                'Factura de venta': {'type': 'hyperlink', 'url': self.factura_venta[0].url, 'text': self.factura_venta[0].name} if self.factura_venta else '',
                'Imágenes': {'type': 'hyperlink', 'url': self.fotos_problema[0].url, 'text': self.fotos_problema[0].name} if self.fotos_problema else '',
                'Vídeos': {'type': 'hyperlink', 'url': self.videos_problema[0].url, 'text': self.videos_problema[0].name} if self.videos_problema else ''
            }
        elif brand == 'Cycplus':
            return {
                'Ticket ID': self.ticket_id,
                'Estado': 'Recibida',
                'Fecha de creación': fecha_creacion,
                'Empresa': self.empresa,
                'NIF/CIF/VAT': self.nif_cif,
                'Email': self.email,
                'Modelo': self.modelo,
                'Estado del producto': self.estado,
                'Descripción del problema': self.problema,
                'Solución y/o reparación propuesta y presupuesto': 'No aplicable',
                'Factura de compra': {'type': 'hyperlink', 'url': self.factura_compra[0].url, 'text': self.factura_compra[0].name} if self.factura_compra else '',
                'Factura de venta': {'type': 'hyperlink', 'url': self.factura_venta[0].url, 'text': self.factura_venta[0].name} if self.factura_venta else '',
                'Imágenes': {'type': 'hyperlink', 'url': self.fotos_problema[0].url, 'text': self.fotos_problema[0].name} if self.fotos_problema else '',
                'Vídeos': {'type': 'hyperlink', 'url': self.videos_problema[0].url, 'text': self.videos_problema[0].name} if self.videos_problema else ''
            }
        elif brand == 'Dare':
            return {
                'Ticket ID': self.ticket_id,
                'Estado': 'Recibida',
                'Fecha de creación': fecha_creacion,
                'Empresa': self.empresa,
                'NIF/CIF/VAT': self.nif_cif,
                'Email': self.email,
                'Modelo': self.modelo,
                'Talla': self.talla,
                'Estado de la bicicleta': self.estado,
                'Descripción del problema': self.problema,
                'Solución y/o reparación propuesta y presupuesto': self.solucion,
                'Factura de compra': {'type': 'hyperlink', 'url': self.factura_compra[0].url, 'text': self.factura_compra[0].name} if self.factura_compra else '',
                'Factura de venta': {'type': 'hyperlink', 'url': self.factura_venta[0].url, 'text': self.factura_venta[0].name} if self.factura_venta else '',
                'Imágenes': {'type': 'hyperlink', 'url': self.fotos_problema[0].url, 'text': self.fotos_problema[0].name} if self.fotos_problema else '',
                'Vídeos': {'type': 'hyperlink', 'url': self.videos_problema[0].url, 'text': self.videos_problema[0].name} if self.videos_problema else ''
            }
        elif brand == 'Kogel':
            return {
                'Ticket ID': self.ticket_id,
                'Estado': 'Recibida',
                'Fecha de creación': fecha_creacion,
                'Empresa': self.empresa,
                'NIF/CIF/VAT': self.nif_cif,
                'Email': self.email,
                'Modelo': self.modelo,
                'Estado del producto': self.estado,
                'Descripción del problema': self.problema,
                'Solución y/o reparación propuesta y presupuesto': 'No aplicable',
                'Factura de compra': {'type': 'hyperlink', 'url': self.factura_compra[0].url, 'text': self.factura_compra[0].name} if self.factura_compra else '',
                'Factura de venta': {'type': 'hyperlink', 'url': self.factura_venta[0].url, 'text': self.factura_venta[0].name} if self.factura_venta else '',
                'Imágenes': {'type': 'hyperlink', 'url': self.fotos_problema[0].url, 'text': self.fotos_problema[0].name} if self.fotos_problema else '',
                'Vídeos': {'type': 'hyperlink', 'url': self.videos_problema[0].url, 'text': self.videos_problema[0].name} if self.videos_problema else ''
            }
        else:
            # Generic format
            return {
                'Ticket ID': self.ticket_id,
                'Estado': 'Recibida',
                'Fecha de creación': fecha_creacion,
                'Empresa': self.empresa,
                'NIF/CIF/VAT': self.nif_cif,
                'Email': self.email,
                'Modelo': self.modelo,
                'Descripción del problema': self.problema
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for template usage
        
        Returns:
            Dictionary with all form data
        """
        return {
            'empresa': self.empresa,
            'nif_cif': self.nif_cif,
            'email': self.email,
            'ticket_id': self.ticket_id,
            'brand': self.brand,
            'modelo': self.modelo,
            'talla': self.talla,
            'año': self.año,
            'estado': self.estado,
            'problema': self.problema,
            'solucion': self.solucion,
            'factura_compra_count': len(self.factura_compra),
            'factura_venta_count': len(self.factura_venta),
            'fotos_count': len(self.fotos_problema),
            'videos_count': len(self.videos_problema),
            'fecha_creacion': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return f"WarrantyFormData(brand={self.brand}, empresa={self.empresa}, ticket_id={self.ticket_id})"