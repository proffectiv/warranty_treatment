#!/usr/bin/env python3
"""
Email Templates for Status Update Notifications
Spanish email templates for warranty status updates
"""

import sys
import os
from typing import Dict, Any

# Import logging filter from root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

# Set up secure logging
logger = setup_secure_logging('email_templates')

def create_status_update_email(ticket_data: Dict[str, Any], new_status: str) -> tuple:
    """
    Create status update email content based on the new status
    
    Args:
        ticket_data: Dictionary containing ticket information
        new_status: New status value (Tramitada, Aceptada, Denegada)
        
    Returns:
        Tuple of (html_content, subject, client_email)
    """
    
    try:
        ticket_id = ticket_data.get('Ticket ID', 'N/A')
        empresa = ticket_data.get('Empresa', 'N/A')
        email = ticket_data.get('Email', '')
        brand = ticket_data.get('Brand', 'N/A')
        modelo = ticket_data.get('Modelo', 'N/A')
        
        if new_status == 'Tramitada':
            subject = "Actualización de Estado de Garantía - En Trámite"
            html_content = f"""
            <html>
            <body>
                <h2>Actualización de Estado de Garantía</h2>
                
                <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <h3>Su solicitud está siendo tramitada</h3>
                    <p><strong style="font-size: 18px; color: #856404;">Ticket: {ticket_id}</strong></p>
                </div>
                
                <p>Estimado/a cliente de <strong>{empresa}</strong>,</p>
                
                <p>Le informamos que su solicitud de garantía ha sido revisada y actualmente se encuentra <strong>en tramitación</strong>.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>Detalles de la Solicitud</h3>
                    <ul>
                        <li><strong>Ticket ID:</strong> {ticket_id}</li>
                        <li><strong>Marca:</strong> {brand}</li>
                        <li><strong>Modelo:</strong> {modelo}</li>
                        <li><strong>Estado actual:</strong> En tramitación</li>
                    </ul>
                </div>
                
                <p>Nuestro equipo técnico está revisando su caso detalladamente. Le mantendremos informado sobre cualquier actualización adicional.</p>
                
                <p>Si tiene alguna pregunta, no dude en contactarnos a través de nuestro correo electrónico <a href="mailto:info@proffectiv.com">info@proffectiv.com</a> indicando su número de ticket.</p>
                
                <br>
                <p>Saludos cordiales,</p>
                <p>El equipo de PROFFECTIV</p>
                
                <hr>
                <p style="font-size: 12px; color: #666;">Este es un mensaje automático. Por favor, conserve su número de ticket para futuras consultas.</p>
            </body>
            </html>
            """
            
        elif new_status == 'Aceptada':
            subject = "✅ Garantía Aceptada - Siguiente Paso"
            html_content = f"""
            <html>
            <body>
                <h2>Su Garantía Ha Sido Aceptada</h2>
                
                <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                    <h3>✅ Garantía ACEPTADA</h3>
                    <p><strong style="font-size: 18px; color: #155724;">Ticket: {ticket_id}</strong></p>
                </div>
                
                <p>Estimado/a cliente de <strong>{empresa}</strong>,</p>
                
                <p>Nos complace informarle que su solicitud de garantía ha sido <strong>ACEPTADA</strong> tras nuestra revisión técnica.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>Detalles de la Solicitud Aceptada</h3>
                    <ul>
                        <li><strong>Ticket ID:</strong> {ticket_id}</li>
                        <li><strong>Marca:</strong> {brand}</li>
                        <li><strong>Modelo:</strong> {modelo}</li>
                        <li><strong>Estado:</strong> Aceptada</li>
                    </ul>
                </div>
                
                <div style="background-color: #cce5ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Próximos Pasos</h3>
                    <p>En breve, uno de nuestros agentes se pondrá en contacto con usted para coordinar:</p>
                    <ul>
                        <li>El proceso de reparación o reemplazo</li>
                        <li>Instrucciones de envío (si aplica)</li>
                        <li>Tiempos estimados de resolución</li>
                    </ul>
                </div>
                
                <p>Gracias por confiar en PROFFECTIV. Estamos comprometidos con brindarle el mejor servicio.</p>
                
                <p>Si tiene alguna pregunta, no dude en contactarnos a través de nuestro correo electrónico <a href="mailto:info@proffectiv.com">info@proffectiv.com</a> indicando su número de ticket.</p>
                
                <br>
                <p>Saludos cordiales,</p>
                <p>El equipo de PROFFECTIV</p>
                
                <hr>
                <p style="font-size: 12px; color: #666;">Este es un mensaje automático. Por favor, conserve su número de ticket para futuras consultas.</p>
            </body>
            </html>
            """
            
        elif new_status == 'Denegada':
            subject = "❌ Resolución de Garantía - Información Importante"
            html_content = f"""
            <html>
            <body>
                <h2>Resolución de Su Solicitud de Garantía</h2>
                
                <div style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
                    <h3>Solicitud No Aprobada</h3>
                    <p><strong style="font-size: 18px; color: #721c24;">Ticket: {ticket_id}</strong></p>
                </div>
                
                <p>Estimado/a cliente de <strong>{empresa}</strong>,</p>
                
                <p>Después de una revisión exhaustiva, lamentamos informarle que su solicitud de garantía no ha podido ser aprobada según nuestros términos y condiciones de garantía.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>Detalles de la Solicitud</h3>
                    <ul>
                        <li><strong>Ticket ID:</strong> {ticket_id}</li>
                        <li><strong>Marca:</strong> {brand}</li>
                        <li><strong>Modelo:</strong> {modelo}</li>
                        <li><strong>Estado:</strong> No aprobada</li>
                    </ul>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>¿Necesita Más Información?</h3>
                    <p>En breve, uno de nuestros agentes se pondrá en contacto con usted para informale sobre los motivos de la denegación de su solicitud de garantía y como proceder.</p>
                </div>
                
                <p>Agradecemos su comprensión y seguimos a su disposición para cualquier consulta adicional.</p>
                
                <br>
                <p>Saludos cordiales,</p>
                <p>El equipo de PROFFECTIV</p>
                
                <hr>
                <p style="font-size: 12px; color: #666;">Este es un mensaje automático. Por favor, conserve su número de ticket para futuras consultas.</p>
            </body>
            </html>
            """
            
        else:
            logger.warning(f"Unknown status: {new_status}")
            return None, None, None
            
        logger.info(f"Created email template for status: {new_status}")
        return html_content, subject, email
        
    except Exception as e:
        logger.error(f"Error creating email template: {str(e)}")
        return None, None, None

def get_supported_statuses():
    """Return list of supported status values for notifications"""
    return ['Tramitada', 'Aceptada', 'Denegada']

if __name__ == "__main__":
    # Test template creation
    test_data = {
        'Ticket ID': 'TEST-12345',
        'Empresa': 'Test Company S.L.',
        'Email': 'test@example.com',
        'Brand': 'Conway',
        'Modelo': 'Cairon C 2.0 500'
    }
    
    for status in get_supported_statuses():
        html_content, subject, email = create_status_update_email(test_data, status)
        if html_content:
            print(f"✅ Template created for status: {status}")
            print(f"Subject: {subject}")
            print(f"Email: {email}")
            print("---")
        else:
            print(f"❌ Failed to create template for status: {status}")