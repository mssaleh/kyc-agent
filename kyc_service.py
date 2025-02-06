import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import aiofiles
import aiohttp
import uvicorn
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field

from email_service import EmailService
from kyc_agent import KYCAgent, KYCReport, ReportHandler, logger

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Initialize KYC agent (assuming environment variables are set)
agent = KYCAgent(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    idcheck_api_key=os.getenv("IDCHECK_API_KEY"),
    watchman_api_key=os.getenv("WATCHMAN_API_KEY"),
    dilisense_api_key=os.getenv("DILISENSE_API_KEY"),
    opensanctions_api_key=os.getenv("OPENSANCTIONS_API_KEY"),
    idcheck_url=os.getenv("ID_CHECK_URL", "https://idcheck.nxu.ae/api/id"),
    watchman_url=os.getenv("WATCHMAN_URL", "https://watchman.nxu.ae/search"),
    dilisense_url=os.getenv(
        "DILISENSE_URL", "https://api.dilisense.com/v1/media/checkIndividual"
    ),
    opensanctions_url=os.getenv(
        "OPENSANCTIONS_URL", "https://api.opensanctions.org/match/default"
    ),
    sanctions_list_path=os.getenv("SANCTIONS_LIST_PATH", "lists/UAE_08012025.pdf"),
)


class JobStatus(BaseModel):
    """
    Status information for a KYC analysis job with comprehensive tracking.

    This model tracks the complete lifecycle of a KYC analysis job, including
    timing information, processing status, results, and any errors that occurred.
    It integrates with the KYCReport model for completed analyses.
    """

    # Core identifiers and timing
    job_id: str = Field(description="Unique identifier for the job")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when the job was created"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when the job finished (success or failure)"
    )

    # Processing status
    status: str = Field(
        description="Current job status",
        # Valid status transitions: submitted -> processing -> (completed|failed)
        pattern="^(submitted|processing|completed|failed)$",
    )

    # Results and error tracking
    report: Optional[KYCReport] = Field(
        default=None, description="Generated KYC report for completed jobs"
    )
    error: Optional[str] = Field(default=None, description="Error message if job failed")

    # Optional callback configuration
    callback_url: Optional[str] = Field(
        default=None, description="URL to notify when job completes"
    )
    email_notification: Optional[str] = Field(
        default=None, description="Email address to notify when job completes"
    )
    email_status: Optional[Dict[str, Any]] = Field(
        default=None, description="Status of email notification delivery"
    )

    # Metadata tracking
    document_path: Optional[Path] = Field(
        default=None, description="Path to uploaded document being analyzed"
    )
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about processing steps"
    )

    class Config:
        """Pydantic model configuration"""

        json_encoders = {datetime: lambda v: v.isoformat(), Path: str}

    def duration(self) -> Optional[float]:
        """
        Calculate job duration in seconds if completed

        Returns:
            Float duration in seconds or None if job not completed
        """
        if self.completed_at and self.created_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None

    def update_status(self, new_status: str, error: Optional[str] = None) -> None:
        """
        Update job status with validation of state transitions

        Args:
            new_status: New status to set
            error: Optional error message for failed status

        Raises:
            ValueError: If status transition is invalid
        """
        valid_transitions = {
            "submitted": ["processing"],
            "processing": ["completed", "failed"],
            "completed": [],  # Terminal state
            "failed": [],  # Terminal state
        }

        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(f"Invalid status transition: {self.status} -> {new_status}")

        self.status = new_status
        if new_status in ["completed", "failed"]:
            self.completed_at = datetime.now()

        if error:
            if new_status != "failed":
                raise ValueError("Error message only valid for failed status")
            self.error = error

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add processing metadata with timestamp

        Args:
            key: Metadata key
            value: Metadata value to store
        """
        self.processing_metadata[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }

    def set_email_status(self, success: bool, error: Optional[str] = None) -> None:
        """Update email notification status"""
        self.email_status = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "error": error,
        }

    def to_response_dict(self) -> Dict[str, Any]:
        """
        Convert to API response format

        Returns:
            Dict with formatted status information
        """
        response = {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "duration": self.duration(),
        }

        if self.completed_at:
            response["completed_at"] = self.completed_at.isoformat()

        if self.error:
            response["error"] = self.error

        if self.report:
            response["report"] = self.report.model_dump()

        if self.email_notification:
            response["email_notification"] = {
                "address": self.email_notification,
                "status": self.email_status,
            }

        return response


class KYCService:
    """FastAPI service for KYC processing"""

    def __init__(self):
        self.app = FastAPI(
            title="KYC Analysis Service",
            description="Automated KYC processing with document analysis and risk assessment",
            version="0.1.0",
        )
        self.setup_routes()
        self.report_handler = ReportHandler()
        self.jobs: Dict[str, JobStatus] = {}
        self.email_service = EmailService()

    def setup_routes(self):
        """Configure API routes"""
        # Mount static files for web interface
        self.app.mount("/static", StaticFiles(directory="static"), name="static")

        # API endpoints
        self.app.post("/api/v1/kyc/analyze")(self.analyze_document)
        self.app.get("/api/v1/kyc/status/{job_id}")(self.get_job_status)
        self.app.get("/api/v1/kyc/report/{job_id}")(self.get_report)

        # Serve index and status pages:
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            return templates.TemplateResponse("index.html", {"request": request})

        @self.app.get("/status/{job_id}", response_class=HTMLResponse)
        async def status_page(request: Request, job_id: str):
            if job_id not in self.jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            return templates.TemplateResponse(
                "status.html", {"request": request, "job": self.jobs[job_id]}
            )

        # Health check
        self.app.get("/health")(self.health_check)

    async def analyze_document(
        self,
        background_tasks: BackgroundTasks,
        document: UploadFile = File(...),
        callback_url: Optional[str] = Form(None),
        email_notification: Optional[EmailStr] = Form(None),
    ) -> JobStatus:
        """
        Submit document for KYC analysis.
        Uses asynchronous file writing for better performance.
        """
        try:
            job_id = str(uuid4())
            # Save uploaded file
            file_location = Path("uploads") / f"{job_id}_{document.filename}"

            # Validate email if provided
            if email_notification:
                logger.info(f"Email notification requested for {email_notification}")

            # Save uploaded file
            async with aiofiles.open(file_location, "wb") as f:
                await f.write(await document.read())

            # Create job status with email notification
            self.jobs[job_id] = JobStatus(
                job_id=job_id,
                status="submitted",
                document_path=file_location,
                callback_url=callback_url,
                email_notification=email_notification,
            )

            # Start processing in background
            background_tasks.add_task(self.process_document, job_id, file_location)

            return self.jobs[job_id]

        except Exception as e:
            logger.error(f"Error submitting document: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error submitting document: {str(e)}"
            )

    async def get_job_status(self, job_id: str) -> JobStatus:
        """
        Get status of KYC analysis job
        """
        if job_id not in self.jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        return self.jobs[job_id]

    async def get_report(
        self, job_id: str, format: str = Query("json", regex="^(json|pdf)$")
    ) -> FileResponse:
        """
        Get full KYC report in requested format.
        Returns either the complete JSON object of the report or the PDF file.
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            raise HTTPException(status_code=404, detail="Job not found")

        job = self.jobs[job_id]
        if job.status != "completed" or not job.report:
            error_msg = f"Report not ready. Current status: {job.status}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        try:
            if format == "json":
                logger.info(f"Returning JSON report for job {job_id}")
                return JSONResponse(content=job.report.model_dump())
            elif format == "pdf":
                pdf_path = self.report_handler._get_report_path(job.report.report_id, "pdf")
                if not pdf_path.exists():
                    error_msg = "PDF report file not found"
                    logger.error(error_msg)
                    raise HTTPException(status_code=404, detail=error_msg)
                logger.info(f"Returning PDF report for job {job_id}")
                return FileResponse(
                    path=str(pdf_path), media_type="application/pdf", filename=pdf_path.name
                )
        except Exception as e:
            logger.error(f"Error retrieving report for job {job_id}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving report: {str(e)}"
            )

    async def health_check(self):
        """Health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    async def process_document(self, job_id: str, document_path: Path):
        """
        Process document in background task
        """
        try:
            # Update job status
            self.jobs[job_id].status = "processing"

            # Process document using KYC agent
            identity = await agent.process_id_document(str(document_path))
            report = await agent.generate_report(identity)

            # Save report files
            await self.report_handler.save_report(report)

            # Update job status
            self.jobs[job_id].status = "completed"
            self.jobs[job_id].completed_at = datetime.now()
            self.jobs[job_id].report = report

            # Send email if configured
            if self.jobs[job_id].email_notification:
                try:
                    pdf_path = self.report_handler._get_report_path(report.report_id, "pdf")
                    await self.email_service.send_report(
                        self.jobs[job_id].email_notification, job_id, pdf_path
                    )
                    self.jobs[job_id].add_metadata("email_sent", True)
                except Exception as e:
                    logger.error(f"Failed to send email notification: {str(e)}")
                    self.jobs[job_id].add_metadata("email_error", str(e))

            # Send callback if configured
            if self.jobs[job_id].callback_url:
                await self._send_callback(job_id)

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            self.jobs[job_id].status = "failed"
            self.jobs[job_id].error = str(e)
            self.jobs[job_id].completed_at = datetime.now()

    async def _send_callback(self, job_id: str):
        """
        Send a callback notification for the given job if callback_url is set.
        """
        job = self.jobs[job_id]
        if not job.callback_url:
            return
        payload = {
            "job_id": job_id,
            "status": job.status,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(job.callback_url, json=payload)
            logger.info(f"Callback sent successfully for job {job_id}")
        except Exception as e:
            logger.error(f"Error sending callback for job {job_id}: {str(e)}")


# Expose the FastAPI app instance as a global variable
app = KYCService().app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
