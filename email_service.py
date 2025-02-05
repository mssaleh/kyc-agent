import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            logger.warning("SendGrid API key not configured")
        self.sg = SendGridAPIClient(api_key)

        self.from_email = os.getenv("SENDGRID_FROM_EMAIL")
        if not self.from_email:
            logger.warning("SendGrid from email not configured")

    async def send_report(
        self, to_email: str, report_id: str, pdf_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Send KYC report via email asynchronously

        Args:
            to_email: Recipient email address
            report_id: Unique identifier for the report
            pdf_path: Path to the PDF report file

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        logger.info(f"Preparing to send report {report_id} to {to_email}")

        try:
            if not pdf_path.exists():
                raise FileNotFoundError(f"Report PDF not found at {pdf_path}")

            # Read PDF file
            with open(pdf_path, "rb") as f:
                file_content = f.read()
                logger.debug(f"Read PDF file of size {len(file_content)} bytes")

            # Create attachment
            attachment = Attachment(
                FileContent(file_content),
                FileName(f"kyc_report_{report_id}.pdf"),
                FileType("application/pdf"),
                Disposition("attachment"),
            )

            # Create email
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=f"KYC Report {report_id}",
                plain_text_content=f"Your KYC report {report_id} is attached.\n\nThis is an automated message.",
            )
            message.attachment = attachment

            # Send email
            logger.debug(f"Sending email for report {report_id}")
            response = self.sg.send(message)

            if response.status_code == 202:
                logger.info(f"Successfully sent report {report_id} to {to_email}")
                return True, None
            else:
                error_msg = f"Unexpected status code: {response.status_code}"
                logger.error(error_msg)
                return False, error_msg

        except FileNotFoundError as e:
            error_msg = f"PDF file error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
