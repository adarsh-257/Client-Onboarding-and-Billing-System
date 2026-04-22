"""Notification service — email and webhook notifications."""
import logging
import json
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def send_email(to_email, subject, body_html, body_text=None, sender=None):
    """
    Send an email via AWS SES.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (optional)
        sender: Sender email (defaults to config)

    Returns:
        Message ID or None on failure
    """
    from flask import current_app

    if sender is None:
        sender = current_app.config.get('SES_SENDER_EMAIL', 'noreply@example.com')

    try:
        ses = boto3.client(
            'ses',
            region_name=current_app.config.get('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=current_app.config.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
        )

        body = {'Html': {'Data': body_html, 'Charset': 'UTF-8'}}
        if body_text:
            body['Text'] = {'Data': body_text, 'Charset': 'UTF-8'}

        response = ses.send_email(
            Source=sender,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': body,
            },
        )

        message_id = response.get('MessageId')
        logger.info(f"Email sent to {to_email}: {subject} (MessageId: {message_id})")
        return message_id

    except ClientError as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return None
    except Exception as e:
        logger.error(f"Email service error: {e}")
        return None


def send_invoice_notification(client, invoice):
    """Send invoice notification email to client."""
    subject = f"Invoice {invoice.invoice_number} — ${invoice.total:.2f} Due"

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">Invoice Notification</h2>
            <p>Dear {client.contact_name},</p>
            <p>A new invoice has been generated for your account:</p>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <table style="width: 100%;">
                    <tr><td><strong>Invoice #:</strong></td><td>{invoice.invoice_number}</td></tr>
                    <tr><td><strong>Amount:</strong></td><td>${invoice.total:.2f} {invoice.currency}</td></tr>
                    <tr><td><strong>Due Date:</strong></td><td>{invoice.due_date.strftime('%B %d, %Y')}</td></tr>
                    <tr><td><strong>Status:</strong></td><td>{invoice.status.value.capitalize()}</td></tr>
                </table>
            </div>
            <p>Please process payment before the due date to avoid any service interruptions.</p>
            <p>Thank you,<br>Client Onboarding Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(client.email, subject, body_html)


def send_welcome_email(client):
    """Send welcome email to newly onboarded client."""
    subject = f"Welcome to Our Platform, {client.company_name}!"

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">Welcome Aboard! 🎉</h2>
            <p>Dear {client.contact_name},</p>
            <p>We're thrilled to have <strong>{client.company_name}</strong> join our platform.</p>
            <p>Your account has been set up and you're ready to get started. Here's what to do next:</p>
            <ol>
                <li>Review your subscription plan</li>
                <li>Upload required documents</li>
                <li>Configure your team settings</li>
            </ol>
            <p>If you have any questions, our support team is here to help.</p>
            <p>Best regards,<br>Client Onboarding Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(client.email, subject, body_html)
