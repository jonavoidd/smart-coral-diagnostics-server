import aiosmtplib
import logging

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Template
from typing import Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = settings.MAIL_SERVER
        self.smtp_port = settings.MAIL_PORT
        self.smtp_username = settings.MAIL_USERNAME
        self.smtp_password = settings.MAIL_PASSWORD
        self.from_email = settings.MAIL_FROM
        self.from_name = settings.MAIL_FROM_NAME
        self.use_tls = settings.MAIL_USE_TLS

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        to_name: Optional[str] = None,
    ) -> bool:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = f"{to_name} <{to_email}>" if to_name else to_email

            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                start_tls=self.use_tls,
            )

            logger.info(f"Service: Email send successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Service: Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_password_reset_email(
        self, email: str, name: str, reset_url: str, expires_mins: int
    ) -> bool:
        subject = "Reset Your Password"

        # HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    background-color: #eaf6fb; /* Light blue background */
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .container {
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    border: 1px solid #cce7f0;
                    box-shadow: 0 4px 10px rgba(0, 123, 255, 0.1);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .logo {
                    font-size: 26px;
                    font-weight: bold;
                    color: #0077b6; /* Deep sky blue */
                }
                .content {
                    background-color: #f0faff; /* Very light blue */
                    padding: 25px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                h2 {
                    color: #0077b6;
                }
                .button {
                    display: inline-block;
                    background-color: #00b4d8; /* Light blue */
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                    transition: background-color 0.3s ease;
                }
                .button:hover {
                    background-color: #0096c7;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }
                .warning {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    color: #856404;
                }
                .link-fallback {
                    word-break: break-word;
                    background-color: #e3f2fd;
                    padding: 10px;
                    border-radius: 3px;
                    font-family: monospace;
                    font-size: 12px;
                    color: #0d47a1;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{{ app_name }}</div>
                </div>
                
                <div class="content">
                    <h2>Reset Your Password</h2>
                    
                    <p>Hello {{ name }},</p>
                    
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{{ reset_url }}" class="button">Reset Password</a>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong> This link will expire in {{ expires_minutes }} minutes for security reasons.
                    </div>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <div class="link-fallback">{{ reset_url }}</div>
                    
                    <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                    
                    <p>Best regards,<br>The {{ app_name }} Team</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated email. Please do not reply to this message.</p>
                    <p>&copy; {{ current_year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_template = """
        Reset Your Password - {{ app_name }}
        
        Hello {{ name }},
        
        We received a request to reset your password. Click the link below to create a new password:
        
        {{ reset_url }}
        
        ⚠️ Important: This link will expire in 30 minutes for security reasons.
        
        If you didn't request this password reset, please ignore this email. Your password will remain unchanged.
        
        Best regards,
        The {{ app_name }} Team
        
        ---
        This is an automated email. Please do not reply to this message.
        © {{ current_year }} {{ app_name }}. All rights reserved.
        """

        template_vars = {
            "name": name,
            "reset_url": reset_url,
            "expires_minutes": expires_mins,
            "app_name": settings.APP_NAME,
            "current_year": datetime.now().year,
        }

        html_content = Template(html_template).render(**template_vars)
        text_content = Template(text_template).render(**template_vars)

        return await self.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=name,
        )

    async def send_password_changed_confirmation(self, email: str, name: str) -> bool:
        subject = "Password Changed Successfully!"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Changed</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .container {
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 10px;
                    border: 1px solid #ddd;
                }
                .success {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
                .content {
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <h2>Password Changed Successfully</h2>
                    
                    <div class="success">
                        ✅ Your password has been successfully changed.
                    </div>
                    
                    <p>Hello {{ name }},</p>
                    
                    <p>This is to confirm that your password was successfully changed on {{ current_date }}.</p>
                    
                    <p>If you did not make this change, please contact our support team immediately.</p>
                    
                    <p>Best regards,<br>The {{ app_name }} Team</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated email. Please do not reply to this message.</p>
                    <p>&copy; {{ current_year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template_vars = {
            "name": name,
            "app_name": settings.APP_NAME,
            "current_date": datetime.now(timezone.utc).strftime(
                "%B %d, %Y at %I:%M %p"
            ),
            "current_year": datetime.now().year,
        }

        html_content = Template(html_template).render(**template_vars)

        return await self.send_email(
            to_email=email, subject=subject, html_content=html_content, to_name=name
        )

    async def send_verification_email(
        self, email: str, name: str, verification_url: str, expires_mins: int
    ) -> bool:
        subject = "Email Confirmation"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    background-color: #eaf6fb;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .container {
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    border: 1px solid #cce7f0;
                    box-shadow: 0 4px 10px rgba(0, 123, 255, 0.1);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .logo {
                    font-size: 26px;
                    font-weight: bold;
                    color: #0077b6;
                }
                .content {
                    background-color: #f0faff;
                    padding: 25px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                h2 {
                    color: #0077b6;
                }
                .button {
                    display: inline-block;
                    background-color: #00b4d8;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                    transition: background-color 0.3s ease;
                }
                .button:hover {
                    background-color: #0096c7;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }
                .warning {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    color: #856404;
                }
                .link-fallback {
                    word-break: break-word;
                    background-color: #e3f2fd;
                    padding: 10px;
                    border-radius: 3px;
                    font-family: monospace;
                    font-size: 12px;
                    color: #0d47a1;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{{ app_name }}</div>
                </div>

                <div class="content">
                    <h2>Verify Your Email</h2>

                    <p>Hello {{ name }},</p>

                    <p>Thank you for signing up! Please confirm your email address by clicking the button below:</p>

                    <div style="text-align: center;">
                        <a href="{{ verification_url }}" class="button">Verify Email</a>
                    </div>

                    <div class="warning">
                        <strong>⚠️ Note:</strong> This link will expire in 60 minutes for security reasons.
                    </div>

                    <p>If the button doesn’t work, copy and paste this link into your browser:</p>
                    <div class="link-fallback">{{ verification_url }}</div>

                    <p>Welcome aboard!<br>The {{ app_name }} Team</p>
                </div>

                <div class="footer">
                    <p>This is an automated email. Please do not reply to this message.</p>
                    <p>&copy; {{ current_year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_template = """
        Verify Your Email - {{ app_name }}

        Hello {{ name }},

        Thank you for signing up! Please confirm your email address by clicking the link below:

        {{ verification_url }}

        ⚠️ Note: This link will expire in 24 hours minutes for security reasons.

        Welcome aboard!

        The {{ app_name }} Team

        ---
        This is an automated email. Please do not reply to this message.
        © {{ current_year }} {{ app_name }}. All rights reserved.
        """

        template_vars = {
            "name": name,
            "app_name": settings.APP_NAME,
            "verification_url": verification_url,
            "expires_minutes": expires_mins,
            "current_year": datetime.now().year,
        }

        html_content = Template(html_template).render(**template_vars)
        text_content = Template(text_template).render(**template_vars)

        return await self.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=name,
        )

    async def send_web_update_email_to_admins(
        self, emails: List[str], name: str, title: str, content: str
    ) -> bool:
        subject = "Website Content Updates"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Website Content Updated</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    background-color: #eaf6fb;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .container {
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    border: 1px solid #cce7f0;
                    box-shadow: 0 4px 10px rgba(0, 123, 255, 0.1);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .logo {
                    font-size: 26px;
                    font-weight: bold;
                    color: #0077b6;
                }
                .content {
                    background-color: #f0faff;
                    padding: 25px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                h2 {
                    color: #0077b6;
                }
                .update-title {
                    font-weight: bold;
                    font-size: 18px;
                    margin-bottom: 10px;
                }
                .update-body {
                    background-color: #ffffff;
                    padding: 15px;
                    border-radius: 6px;
                    border: 1px solid #cce7f0;
                    white-space: pre-wrap;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }
                .note {
                    background-color: #e0f7fa;
                    border-left: 5px solid #00acc1;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    color: #006064;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{{ app_name }}</div>
                </div>

                <div class="content">
                    <h2>Website Content Updated</h2>

                    <p>Hello {{ name }},</p>

                    <p>The following update has been made to the {{ app_name }} website:</p>

                    <div class="update-title">{{ update_title }}</div>
                    <div class="update-body">{{ update_content }}</div>

                    <div class="note">
                        <strong>ℹ️ Note:</strong> This update was sent to all admin users to ensure awareness and transparency.
                    </div>

                    <p>Thank you for staying updated.<br>The {{ app_name }} Team</p>
                </div>

                <div class="footer">
                    <p>This is an automated email. Please do not reply to this message.</p>
                    <p>&copy; {{ current_year }} {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_template = """
        Website Content Updated - {{ app_name }}

        Hello {{ name }},

        The following update has been made to the {{ app_name }} website:

        Title: {{ update_title }}

        {{ update_content }}

        ℹ️ Note: This update was sent to all admin users.

        Thank you for staying informed.

        The {{ app_name }} Team

        ---
        This is an automated email. Please do not reply to this message.
        © {{ current_year }} {{ app_name }}. All rights reserved.
        """

        template_vars = {
            "app_name": settings.APP_NAME,
            "name": name,
            "updated_title": title,
            "updated_content": content,
            "time_updated": datetime.now(timezone.utc),
        }

        html_content = Template(html_template).render(**template_vars)
        text_content = Template(text_template).render(**template_vars)

        return await self.send_email(
            to_email=emails,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


email_service = EmailService()


async def send_password_reset_email(
    email: str, name: str, reset_url: str, expires_mins: int = 30
) -> bool:
    return await email_service.send_password_reset_email(
        email, name, reset_url, expires_mins
    )


async def send_password_changed_confirmation(email: str, name: str) -> bool:
    return await email_service.send_password_changed_confirmation(email, name)


async def send_verification_email(
    email: str, name: str, verification_url: str, expires_mins: int
):
    return await email_service.send_verification_email(
        email, name, verification_url, expires_mins
    )


async def send_web_update_email_to_admins(
    emails: List[str], name: str, title: str, content: str
) -> bool:
    return await email_service.send_web_update_email_to_admins(
        emails, name, title, content
    )
