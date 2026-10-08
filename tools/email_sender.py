"""AutoApply AI — Email Sender Tool
Sends job application emails via Gmail SMTP using App Password authentication.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from config.settings import EMAIL_SENDER, EMAIL_APP_PASSWORD, SMTP_HOST, SMTP_PORT


class EmailSender:
    """Sends job application emails using Gmail SMTP."""

    def __init__(self):
        self.sender      = EMAIL_SENDER
        self.password    = EMAIL_APP_PASSWORD
        self.smtp_host   = SMTP_HOST
        self.smtp_port   = SMTP_PORT

    # ─── Validation ───────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(self.sender and self.password)

    # ─── Main Send Method ─────────────────────────────────────────────

    def send_application(
        self,
        to_email: str,
        applicant_name: str,
        job_title: str,
        company: str,
        cover_letter: str,
        resume_path: str = None,
    ) -> dict:
        """
        Send a job application email.
        Returns: {"success": bool, "message": str}
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "Email not configured. Add EMAIL_SENDER and EMAIL_APP_PASSWORD in .env"
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Job Application — {job_title} | {applicant_name}"
            msg["From"]    = f"{applicant_name} <{self.sender}>"
            msg["To"]      = to_email

            # Plain text version
            plain_text = f"""
Dear Hiring Team at {company},

{cover_letter}

Best Regards,
{applicant_name}
{self.sender}
            """.strip()

            # HTML version
            html_content = self._build_html_email(
                applicant_name, job_title, company, cover_letter
            )

            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Attach resume if provided
            if resume_path and Path(resume_path).exists():
                msg.attach(self._build_attachment(resume_path))

            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, to_email, msg.as_string())

            return {
                "success": True,
                "message": f"✅ Email sent to {to_email} successfully!"
            }

        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "❌ Authentication failed. Check your Gmail App Password in .env"
            }
        except smtplib.SMTPException as e:
            return {
                "success": False,
                "message": f"❌ SMTP error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Error sending email: {str(e)}"
            }

    # ─── HTML Email Template ──────────────────────────────────────────

    def _build_html_email(
        self, name: str, job_title: str, company: str, cover_letter: str
    ) -> str:
        """Build a premium HTML email template."""
        cl_html = cover_letter.replace("\n\n", "</p><p>").replace("\n", "<br>")

        return f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body        {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7fb; margin: 0; padding: 20px; }}
    .container  {{ max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px;
                   box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden; }}
    .header     {{ background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 100%);
                   padding: 32px 40px; color: white; }}
    .header h1  {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .header p   {{ margin: 6px 0 0; opacity: 0.85; font-size: 14px; }}
    .body       {{ padding: 40px; color: #374151; line-height: 1.7; }}
    .body p     {{ margin: 0 0 16px; }}
    .footer     {{ background: #f9fafb; padding: 20px 40px; border-top: 1px solid #e5e7eb;
                   font-size: 12px; color: #9ca3af; text-align: center; }}
    .badge      {{ display: inline-block; background: #ede9fe; color: #7c3aed;
                   padding: 4px 12px; border-radius: 20px; font-size: 12px;
                   font-weight: 600; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Job Application — {job_title}</h1>
      <p>Applying to <strong>{company}</strong></p>
      <span class="badge">📄 Resume Attached</span>
    </div>
    <div class="body">
      <p>Dear Hiring Team at <strong>{company}</strong>,</p>
      <p>{cl_html}</p>
      <p>Best Regards,<br><strong>{name}</strong></p>
    </div>
    <div class="footer">
      Sent via AutoApply AI &mdash; Intelligent Job Application Automation &bull;
      MCA Minor Project
    </div>
  </div>
</body>
</html>
""".strip()

    # ─── Attachment Builder ───────────────────────────────────────────

    def _build_attachment(self, file_path: str) -> MIMEBase:
        """Create a MIME attachment from a file path."""
        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = Path(file_path).name
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}"
        )
        return part

    # ─── Test Connection ──────────────────────────────────────────────

    def test_connection(self) -> dict:
        """Test SMTP connection without sending email."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
            return {"success": True, "message": "✅ Gmail SMTP connection successful!"}
        except Exception as e:
            return {"success": False, "message": f"❌ Connection failed: {str(e)}"}
