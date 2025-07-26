#!/usr/bin/env python3
"""
Robust logging filter to sanitize sensitive data from logs.
This module provides comprehensive filtering to protect privacy and business information
in logs that may be exposed in public repositories or monitoring systems.
"""

import re
import json
import logging
from typing import Any, Dict, List, Union, Optional
from copy import deepcopy


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to sanitize sensitive information from log records.
    Protects company info, personal data, product details, and business information.
    """
    
    # Sensitive field patterns (case-insensitive)
    SENSITIVE_FIELD_PATTERNS = [
        # Company and personal information
        r'empresa',
        r'company',
        r'nif',
        r'cif',
        r'vat',
        r'tax',
        r'email',
        r'mail',
        r'phone',
        r'telephone',
        r'telefono',
        r'contact',
        r'contacto',
        r'address',
        r'direccion',
        r'name',
        r'nombre',
        r'apellido',
        r'surname',
        
        # Product and business information
        r'modelo',
        r'model',
        r'brand',
        r'marca',
        r'price',
        r'precio',
        r'cost',
        r'coste',
        r'budget',
        r'presupuesto',
        r'problem',
        r'problema',
        r'description',
        r'descripcion',
        r'solution',
        r'solucion',
        r'repair',
        r'reparacion',
        
        # Invoice and financial
        r'invoice',
        r'factura',
        r'bill',
        r'payment',
        r'pago',
        r'amount',
        r'cantidad',
        r'total',
        
        # File and document references
        r'file',
        r'document',
        r'documento',
        r'attachment',
        r'adjunto',
        r'url',
        r'link',
        r'path',
        r'ruta'
    ]
    
    # Email pattern
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    )
    
    # NIF/CIF/VAT pattern (Spanish format)
    NIF_CIF_PATTERN = re.compile(
        r'\b[A-HJ-NP-SUVW]\d{8}|[KLM]\d{7}[A-Z]|[0-9]{8}[A-HJ-NP-TV-Z]|\d{8}[A-Z]\b',
        re.IGNORECASE
    )
    
    # URL pattern
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    )
    
    # Phone number pattern (various formats)
    PHONE_PATTERN = re.compile(
        r'(\+34|0034|34)?[\s\-]?[6789]\d{2}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}',
        re.IGNORECASE
    )
    
    # UUID pattern (for ticket IDs - we keep these but hash them)
    UUID_PATTERN = re.compile(
        r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
        re.IGNORECASE
    )
    
    def __init__(self, mask_char: str = '*', preserve_length: bool = True):
        """
        Initialize the sensitive data filter.
        
        Args:
            mask_char: Character to use for masking sensitive data
            preserve_length: Whether to preserve the original length when masking
        """
        super().__init__()
        self.mask_char = mask_char
        self.preserve_length = preserve_length
        
        # Compile sensitive field patterns
        self.sensitive_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.SENSITIVE_FIELD_PATTERNS
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter the log record, sanitizing sensitive data.
        
        Args:
            record: The log record to filter
            
        Returns:
            True to allow the record through (after sanitization)
        """
        # Sanitize the main message
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._sanitize_text(str(record.msg))
        
        # Sanitize arguments if present
        if hasattr(record, 'args') and record.args:
            record.args = self._sanitize_args(record.args)
        
        return True
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize sensitive data from text.
        
        Args:
            text: The text to sanitize
            
        Returns:
            Sanitized text with sensitive data masked
        """
        if not text:
            return text
        
        # Make a copy to work with
        sanitized = text
        
        # Sanitize emails
        sanitized = self.EMAIL_PATTERN.sub(
            lambda m: self._mask_sensitive_data(m.group(0), 'email'),
            sanitized
        )
        
        # Sanitize NIF/CIF/VAT numbers
        sanitized = self.NIF_CIF_PATTERN.sub(
            lambda m: self._mask_sensitive_data(m.group(0), 'nif'),
            sanitized
        )
        
        # Sanitize URLs
        sanitized = self.URL_PATTERN.sub(
            lambda m: self._mask_sensitive_data(m.group(0), 'url'),
            sanitized
        )
        
        # Sanitize phone numbers
        sanitized = self.PHONE_PATTERN.sub(
            lambda m: self._mask_sensitive_data(m.group(0), 'phone'),
            sanitized
        )
        
        # Sanitize UUIDs (keep first 8 chars for debugging)
        sanitized = self.UUID_PATTERN.sub(
            lambda m: f"{m.group(0)[:8]}-{'*' * 4}-{'*' * 4}-{'*' * 4}-{'*' * 12}",
            sanitized
        )
        
        # Context-aware sanitization for common patterns
        sanitized = self._sanitize_contextual_data(sanitized)
        
        return sanitized
    
    def _sanitize_contextual_data(self, text: str) -> str:
        """
        Sanitize data based on context clues in the text.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Text with contextually sensitive data masked
        """
        if not text:
            return text
        
        # Common company name patterns (ending with S.L., S.A., Ltd., etc.)
        company_pattern = re.compile(
            r'[A-Za-z][A-Za-z\s&.-]*(?:S\.L\.|S\.A\.|Ltd\.?|Inc\.?|LLC|GmbH|B\.V\.)',
            re.IGNORECASE
        )
        text = company_pattern.sub(
            lambda m: self._mask_sensitive_data(m.group(0), 'empresa'),
            text
        )
        
        # Product model patterns (brand + model with numbers/letters)
        product_pattern = re.compile(
            r'\b(?:Conway|Cycplus|Dare|Kogel)\s+[A-Za-z0-9\s.-]+(?:\d+\.?\d*|\d+)\b',
            re.IGNORECASE
        )
        text = product_pattern.sub(
            lambda m: self._mask_sensitive_data(m.group(0), 'modelo'),
            text
        )
        
        # Price patterns (numbers with currency symbols) - simplified
        price_pattern = re.compile(
            r'\d{1,6}(?:[.,]\d{1,2})?\s*[€$£¥]',
            re.IGNORECASE
        )
        text = price_pattern.sub('[PRICE_MASKED]', text)
        
        # Spanish phone patterns
        spanish_phone_pattern = re.compile(
            r'\+34\s*\d{3}\s*\d{3}\s*\d{3}',
            re.IGNORECASE
        )
        text = spanish_phone_pattern.sub('[PHONE_MASKED]', text)
        
        # File paths and folder names
        file_path_pattern = re.compile(
            r'(?:form_submission/tests/|form_submission/src/|/[A-Z_]+/)[A-Za-z0-9_./\\-]+\.(?:json|py|xlsx|pdf|csv|txt)',
            re.IGNORECASE
        )
        text = file_path_pattern.sub('[FILE_PATH_MASKED]', text)
        
        # Dropbox paths and file names
        dropbox_path_pattern = re.compile(
            r'/[A-Z_]+/[A-Za-z0-9_]+\.xlsx',
            re.IGNORECASE
        )
        text = dropbox_path_pattern.sub('[DROPBOX_PATH_MASKED]', text)
        
        # Event IDs (test-brand-numbers pattern)
        event_id_pattern = re.compile(
            r'test-[a-z]+-\d+',
            re.IGNORECASE
        )
        text = event_id_pattern.sub('[EVENT_ID_MASKED]', text)
        
        # Event types (FORM_RESPONSE, etc.) - be more specific
        event_type_pattern = re.compile(
            r'\b(?:FORM_RESPONSE|WEBHOOK_EVENT|API_CALL|USER_ACTION)\b',
            re.IGNORECASE
        )
        text = event_type_pattern.sub('[EVENT_TYPE_MASKED]', text)
        
        return text
    
    def _sanitize_args(self, args: tuple) -> tuple:
        """
        Sanitize arguments that might contain sensitive data.
        
        Args:
            args: Tuple of arguments to sanitize
            
        Returns:
            Sanitized arguments tuple
        """
        sanitized_args = []
        
        for arg in args:
            if isinstance(arg, str):
                sanitized_args.append(self._sanitize_text(arg))
            elif isinstance(arg, dict):
                sanitized_args.append(self._sanitize_dict(arg))
            elif isinstance(arg, list):
                sanitized_args.append(self._sanitize_list(arg))
            else:
                # For other types, convert to string and sanitize
                sanitized_args.append(self._sanitize_text(str(arg)))
        
        return tuple(sanitized_args)
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize dictionary data, masking sensitive fields.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            is_sensitive_key = any(
                pattern.search(key) for pattern in self.sensitive_patterns
            )
            
            if is_sensitive_key:
                # Mask the value
                if isinstance(value, str):
                    sanitized[key] = self._mask_sensitive_data(value, key.lower())
                elif isinstance(value, (int, float)):
                    sanitized[key] = self._mask_numeric_data(value)
                elif isinstance(value, list):
                    sanitized[key] = [self._mask_sensitive_data(str(item), key.lower()) for item in value]
                else:
                    sanitized[key] = '[MASKED]'
            else:
                # Recursively sanitize nested structures
                if isinstance(value, dict):
                    sanitized[key] = self._sanitize_dict(value)
                elif isinstance(value, list):
                    sanitized[key] = self._sanitize_list(value)
                elif isinstance(value, str):
                    sanitized[key] = self._sanitize_text(value)
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _sanitize_list(self, data: List[Any]) -> List[Any]:
        """
        Sanitize list data.
        
        Args:
            data: List to sanitize
            
        Returns:
            Sanitized list
        """
        if not isinstance(data, list):
            return data
        
        sanitized = []
        
        for item in data:
            if isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            elif isinstance(item, str):
                sanitized.append(self._sanitize_text(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    def _mask_sensitive_data(self, data: str, data_type: str = 'generic') -> str:
        """
        Mask sensitive data with appropriate strategy.
        
        Args:
            data: The sensitive data to mask
            data_type: Type of data for context-aware masking
            
        Returns:
            Masked data string
        """
        if not data:
            return data
        
        data_str = str(data).strip()
        
        if not data_str:
            return data_str
        
        # Context-aware masking strategies
        if data_type.lower() in ['email', 'mail']:
            # For emails, show first char + domain
            if '@' in data_str:
                local, domain = data_str.split('@', 1)
                return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"
            
        elif data_type.lower() in ['nif', 'cif', 'vat']:
            # For ID numbers, show first 2 and last 1 characters
            if len(data_str) >= 4:
                return f"{data_str[:2]}{'*' * (len(data_str) - 3)}{data_str[-1]}"
            
        elif data_type.lower() in ['phone', 'telefono']:
            # For phones, show country code and mask the rest
            if len(data_str) >= 6:
                return f"{data_str[:3]}{'*' * (len(data_str) - 3)}"
        
        elif data_type.lower() in ['url', 'link']:
            # For URLs, show domain but mask path
            return '[URL_MASKED]'
        
        elif data_type.lower() in ['empresa', 'company']:
            # For company names, show first few chars
            if len(data_str) >= 3:
                return f"{data_str[:3]}{'*' * (len(data_str) - 3)}"
        
        # Generic masking: preserve length, show first character if long enough
        if len(data_str) <= 2:
            return self.mask_char * len(data_str)
        elif len(data_str) <= 4:
            return f"{data_str[0]}{'*' * (len(data_str) - 1)}"
        else:
            return f"{data_str[0]}{'*' * (len(data_str) - 2)}{data_str[-1]}"
    
    def _mask_numeric_data(self, data: Union[int, float]) -> str:
        """
        Mask numeric sensitive data (prices, amounts, etc.).
        
        Args:
            data: Numeric data to mask
            
        Returns:
            Masked representation
        """
        return '[AMOUNT_MASKED]'
    
    def sanitize_json(self, json_data: Union[str, dict]) -> str:
        """
        Sanitize JSON data for logging.
        
        Args:
            json_data: JSON string or dictionary to sanitize
            
        Returns:
            Sanitized JSON string
        """
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            sanitized_data = self._sanitize_dict(data)
            return json.dumps(sanitized_data, indent=2, ensure_ascii=False)
            
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, treat as regular text
            return self._sanitize_text(str(json_data))


def setup_secure_logging(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with sensitive data filtering.
    
    Args:
        name: Logger name
        level: Logging level
        format_string: Custom format string
        
    Returns:
        Configured logger with sensitive data filter
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def create_log_filter() -> SensitiveDataFilter:
    """
    Create a standalone sensitive data filter instance.
    
    Returns:
        SensitiveDataFilter instance
    """
    return SensitiveDataFilter()


# Example usage and testing
if __name__ == "__main__":
    # Test the filter with sample sensitive data
    test_logger = setup_secure_logging('test_logger', logging.INFO)
    
    # Test various sensitive data scenarios
    test_logger.info("Processing warranty for empresa: Test Company S.L.")
    test_logger.info("Client email: test@example.com")
    test_logger.info("NIF: B12345678")
    test_logger.info("Phone: +34 666 123 456")
    test_logger.info("Problem: Brake issues with Conway Cairon C 2.0")
    test_logger.info("Budget: 150€ for repair")
    test_logger.info("Invoice URL: https://storage.example.com/invoice123.pdf")
    
    # Test JSON sanitization
    filter_instance = create_log_filter()
    sample_json = {
        "empresa": "Test Company S.L.",
        "email": "contact@testcompany.com",
        "nif": "B12345678",
        "modelo": "Conway Cairon C 2.0 500",
        "problema": "Brake system malfunction",
        "precio": 1200.50,
        "safe_field": "This should not be masked"
    }
    
    print("\nOriginal JSON:")
    print(json.dumps(sample_json, indent=2))
    
    print("\nSanitized JSON:")
    print(filter_instance.sanitize_json(sample_json))