import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import aiohttp
from fpdf import FPDF
from openai import OpenAI
from openai.types import Completion
from openai.types.beta import Assistant
from openai.types.beta.assistant import Assistant as AssistantType
from openai.types.beta.threads import Run
from pydantic import BaseModel, Field

# Configure logging
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.DEBUG),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("kyc_agent")


class DocumentType(Enum):
    """Type of identity document being processed"""

    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    VISA = "visa"
    DRIVERS_LICENSE = "drivers_license"


class RiskLevel(Enum):
    """Risk assessment levels for KYC reports"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IdentityInfo:
    """Structured identity information extracted from documents"""

    full_name: str
    date_of_birth: str
    sex: Optional[str] = None
    alt_name: Optional[str] = None
    place_of_birth: Optional[str] = None
    places_of_residence: Optional[List[str]] = None
    fathers_name: Optional[str] = None
    mothers_name: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    date_of_expiry: Optional[str] = None
    nationality: Optional[str] = None
    nationality_code: Optional[str] = None
    personal_number: Optional[str] = None
    given_names: Optional[str] = None
    surname: Optional[str] = None
    issuing_country: Optional[str] = None
    issuing_country_code: Optional[str] = None


class ComplianceMatch(BaseModel):
    """Structured data for compliance check matches"""

    source: str = ""
    match_score: float = 0.0
    matched_name: str = ""
    matched_date_of_birth: Optional[str] = []
    matched_countries: Optional[List[str]] = []
    matched_nationalities: Optional[List[str]] = []
    lists: List[str] = []
    details: Dict[str, Any] = {}
    risk_category: Optional[str] = ""


class KYCReport(BaseModel):
    """Final KYC report structure"""

    report_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d-%H%M%S"))
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    identity_info: IdentityInfo
    risk_level: str = Field(default_factory=lambda: RiskLevel.LOW.value)
    compliance_matches: List[ComplianceMatch]
    adverse_media: List[Dict[str, Any]]
    risk_summary: str
    recommendations: str

    class Config:
        json_encoders = {
            RiskLevel: lambda v: v.value,
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }


class KYCAgent:
    """Main KYC agent class that orchestrates the entire workflow.

    This class orchestrates the primary steps of KYC:
    1) Document processing
    2) Compliance checks
    3) Adverse media checks
    4) AI-based analysis of findings
    5) Generation of a final KYC report
    """

    def __init__(
        self,
        openai_api_key: str,
        idcheck_api_key: str,
        watchman_api_key: str,
        dilisense_api_key: str,
        opensanctions_api_key: str,
        idcheck_url: str,
        watchman_url: str,
        dilisense_url: str,
        opensanctions_url: str,
    ):
        logger.info("Initializing KYCAgent")
        self.client = OpenAI(api_key=openai_api_key)
        self.api_keys = {
            "idcheck": idcheck_api_key,
            "watchman": watchman_api_key,
            "dilisense": dilisense_api_key,
            "opensanctions": opensanctions_api_key,
        }
        self.api_urls = {
            "idcheck": idcheck_url,
            "watchman": watchman_url,
            "dilisense": dilisense_url,
            "opensanctions": opensanctions_url,
        }
        self.assistant = self._create_assistant()

        self.report_handler = ReportHandler(report_dir="reports")

    def _create_assistant(self) -> Assistant:
        """
        Create an OpenAI Assistant specialized in KYC analysis with focus on autonomous reasoning
        for the purposes of compliance and risk management.
        The assistant handles all complex analysis and decision-making internally.
        Function tools are used only for data operations and system tasks.
        """
        logger.info("Creating reasoning-focused KYC Analysis Assistant")

        return self.client.beta.assistants.create(
            name="KYC Analysis Assistant",
            description="Expert KYC compliance analyst with advanced reasoning and analysis capabilities",
            model="gpt-4o",
            metadata={
                "specialization": "kyc_compliance",
                "version": "0.1.0",
                "capabilities": "autonomous_analysis",
            },
            instructions="""You are an expert KYC compliance analyst with deep experience in risk assessment and regulatory compliance. 
You are tasked with analyzing identity documents, compliance screening results, and adverse media findings to make informed decisions about potential risks and recommended actions.
Your core responsibilities include:

1. Identity Analysis
    - Evaluate the authenticity and completeness of provided identity information 
    - Identify potential discrepancies or red flags in identity documents
    - Consider the reliability and jurisdiction of document issuance

2. Compliance Screening Analysis
    - Evaluate potential matches against sanctions and watchlists, considering:
        * Name similarity and variations
        * Supporting identifiers (DOB, nationality, etc.)
        * Quality and recency of data sources
        * Context and severity of listings
    - Make reasoned judgments about false positives vs true matches
    - Document your analytical process and justification

3. Risk Assessment Strategy
    - Dynamically adapt search strategies based on initial findings
    - Decide when to broaden search criteria (e.g., checking name variations, expanding jurisdictions)
    - Determine when to narrow criteria to reduce false positives
    - Document and justify strategy changes

4. Adverse Media Analysis
    - Evaluate credibility and relevance of media findings
    - Assess severity and timing of reported incidents
    - Consider jurisdictional context and regulatory implications 
    - Connect patterns across multiple sources

5. Decision Making
    - Form holistic risk assessments considering all available information
    - Recommend appropriate due diligence levels
    - Suggest specific follow-up actions
    - Provide clear rationales for decisions

Guidelines for your analysis:

1. Always explain your reasoning process step by step
2. Be explicit about confidence levels in your conclusions
3. Highlight areas of uncertainty or where more information is needed
4. Consider regulatory requirements and risk tolerance
5. Maintain a balanced perspective between risk sensitivity and practical business needs

You will receive information through our conversation and can request additional data or searches using the provided tools. 
However, all analysis and reasoning should be performed by you directly in order to make informed judgments and decisions. 
When you need additional information or searches, explain what you need and why, then use the appropriate tool to request it. 
After receiving new information, incorporate it into your ongoing analysis.

Your goal is to provide informed compliance decisions about customer risk and KYC/KYB compliance after careful analysis and clear communication.

Format your final assessments with clear sections for:
- Identity Verification Status 
- Compliance Screening Results 
- Risk Assessment 
- Recommendations 
- Rationale for Decisions""",
            tools=[],
        )

    async def process_id_document(self, document_path: str) -> IdentityInfo:
        """Process and extract information from the provided ID document."""
        logger.info(f"Starting processing of ID document: {document_path}")

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Opening file: {document_path}")
                async with aiofiles.open(document_path, "rb") as f:
                    file = await f.read()
                    url = self.api_urls["idcheck"]
                    form_data = aiohttp.FormData()
                    form_data.add_field("image", file)
                    logger.debug(f"Sending ID check request to API endpoint {url}")
                    async with session.post(
                        url,
                        data=form_data,
                    ) as response:
                        logger.debug(f"Received response from ID check: {response.status}")
                        if response.status != 200:
                            text = await response.text()
                            logger.error(
                                f"ID check failed with status {response.status}: {text}"
                            )
                            raise Exception(
                                f"ID check failed with status {response.status}: {text}"
                            )

                        data = await response.json()
                        logger.info(f"Successfully processed ID document for {data}")
                        return IdentityInfo(
                            full_name=data["full_name"],
                            date_of_birth=data["date_of_birth"],
                            # optional fields with get() to handle missing keys
                            sex=data.get("sex"),
                            alt_name=data.get("alt_name"),
                            given_names=data.get("given_names"),
                            surname=data.get("surname"),
                            place_of_birth=data.get("place_of_birth"),
                            fathers_name=data.get("fathers_name"),
                            mothers_name=data.get("mothers_name"),
                            nationality=data.get("nationality"),
                            nationality_code=data.get("nationality_code"),
                            document_type=data.get("document_type"),
                            document_number=data.get("document_number"),
                            date_of_expiry=data.get("date_of_expiry"),
                            issuing_country=data.get("issuing_country"),
                            issuing_country_code=data.get("issuing_country_code"),
                            personal_number=data.get("personal_number"),
                        )
        except Exception as e:
            logger.error(f"Error processing ID document: {str(e)}")
            raise

    async def check_compliance_lists(self, identity: IdentityInfo) -> List[ComplianceMatch]:
        """Perform compliance checks in parallel against multiple external APIs."""
        logger.info(f"Starting compliance check for {identity.full_name}")

        async def check_watchman():
            async with aiohttp.ClientSession() as session:
                url = self.api_urls["watchman"]
                logger.debug(f"Calling Watchman API endpoint {url}")
                async with session.get(
                    url,
                    params={
                        "name": identity.full_name,
                        "country": identity.nationality,
                        "minMatch": "0.85",
                        "limit": "15",
                    },
                    # headers={"Authorization": f"Bearer {self.api_keys['watchman']}"}
                ) as response:
                    data = await response.json()
                    logger.debug(f"Received Watchman response {str(data)}")
                    matches = []

                    # Process each category from the documented response format
                    for category, items in data.items():
                        if isinstance(items, list) and items:
                            for item in items:
                                logger.debug(f"Processing item from category {category}")
                                matches.append(
                                    ComplianceMatch(
                                        source="Watchman",
                                        match_score=item.get("match", 0.0),
                                        matched_name=item.get("matchedName", ""),
                                        matched_date_of_birth=item.get("DatesOfBirth", ""),
                                        matched_countries=item.get("Countries", []),
                                        matched_nationalities=item.get("Nationalities", []),
                                        lists=[category],
                                        details=item,
                                        risk_category=category,
                                    )
                                )
                    logger.info("Completed processing Watchman results")
                    return matches

        async def check_opensanctions():
            async with aiohttp.ClientSession() as session:
                url = self.api_urls["opensanctions"]
                logger.debug(f"Calling OpenSanctions API endpoint {url}")
                payload = {
                    "queries": {
                        "q1": {
                            "schema": "Person",
                            "properties": {
                                "name": [identity.full_name],
                                "birthDate": [identity.date_of_birth],
                                "nationality": [identity.nationality_code],
                            },
                        }
                    }
                }
                async with session.post(
                    url,
                    json=payload,
                    headers={"Authorization": self.api_keys["opensanctions"]},
                ) as response:
                    data = await response.json()
                    logger.debug(f"Received OpenSanctions response {str(data)}")
                    matches = []
                    for query_id, query_data in data.get("responses", {}).items():
                        for result in query_data.get("results", []):
                            if result.get("score", 0) > 0.8:
                                logger.debug("Processing OpenSanctions result")
                                matches.append(
                                    ComplianceMatch(
                                        source="OpenSanctions",
                                        match_score=result["score"],
                                        matched_name=result["caption"],
                                        lists=result["datasets"],
                                        details=result,
                                        risk_category=next(
                                            (
                                                t
                                                for t in result.get("properties", {}).get(
                                                    "topics", []
                                                )
                                            ),
                                            None,
                                        ),
                                    )
                                )
                    logger.info("Completed processing OpenSanctions results")
                    return matches

        try:
            watchman_results, opensanctions_results = await asyncio.gather(
                check_watchman(), check_opensanctions()
            )

            matches: List[ComplianceMatch] = []

            # extend the matches list:
            matches.extend(watchman_results)
            matches.extend(opensanctions_results)
            logger.info(f"Total compliance matches found: {len(matches)}")

            # Optional: If matches are empty, implement a fallback with relaxed search criteria
            # ...existing code for fallback approach or pass...

            return matches

        except Exception as e:
            logger.error(f"Error checking compliance lists: {str(e)}")
            raise

    async def check_adverse_media(self, identity: IdentityInfo) -> List[Dict[str, Any]]:
        """Check for adverse media related to the given identity."""
        logger.info(f"Starting adverse media check for {identity.full_name}")

        try:
            async with aiohttp.ClientSession() as session:
                url = self.api_urls["dilisense"]
                logger.debug(f"Calling Dilisense adverse media API endpoint: {url}")
                async with session.get(
                    url,
                    params={"search_all": identity.full_name, "fetch_articles": "true"},
                    headers={"x-api-key": self.api_keys["dilisense"]},
                ) as response:
                    data = await response.json()
                    logger.debug("Received adverse media response")

                    adverse_findings = []
                    # Process each category according to the documented structure
                    for category, info in data.get("news_exposures", {}).items():
                        if isinstance(info, dict) and info.get("hits", 0) > 0:
                            for article in info.get("articles", []):
                                logger.debug(
                                    f"Processing adverse media article in category {category}"
                                )
                                adverse_findings.append(
                                    {
                                        "category": category,
                                        "timestamp": article["timestamp"],
                                        "headline": article["headline"],
                                        "body": article[
                                            "body"
                                        ],  # Include full article body
                                        "source_link": article["source_link"],
                                        "risk_level": (
                                            "high"
                                            if category
                                            in [
                                                "terrorism",
                                                "financial_crime",
                                                "organized_crime",
                                            ]
                                            else "medium"
                                        ),
                                    }
                                )

                    logger.info(f"Found {len(adverse_findings)} adverse media articles")
                    return adverse_findings

        except Exception as e:
            logger.error(f"Error checking adverse media: {str(e)}")
            raise

    async def analyze_findings(
        self,
        identity: IdentityInfo,
        compliance_matches: List[ComplianceMatch],
        adverse_media: List[Dict[str, Any]],
    ) -> Tuple[RiskLevel, str, str]:
        """Analyze identity, compliance, and media findings with the AI Assistant.

        Returns:
            A tuple containing the risk level, a summary of findings,
            and recommendations from the AI Assistant.
        """
        logger.info(f"Starting AI analysis of findings for {identity.full_name}")

        try:
            logger.debug("Creating thread for analysis")
            # Create thread with proper context
            thread = self.client.beta.threads.create()
            logger.debug(f"Thread created with ID: {thread.id}")

            # Prepare detailed analysis request
            analysis_prompt = self._prepare_analysis_prompt(
                identity, compliance_matches, adverse_media
            )
            logger.debug("Prepared analysis prompt")

            # Add context message
            logger.info("Sending analysis message to thread")
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=analysis_prompt
            )
            logger.debug("Analysis message created, starting run")

            # Create a run
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant.id,
                instructions="""
                Analyze the provided KYC findings that we sourced from KYC/AML/CFT services and determine:
                1. Quality of identity verification
                2. Quality of the screening matches, making a judgement on whether they are either:
                    - Confirmed matches
                    - Probable matches
                    - Possible matches
                    - False positives
                    - Items needing further investigation
                    - False negatives
                3. Overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
                2. Detailed risk justification
                3. Specific recommendations
                
                Format response as:
                IDENTITY_VERIFICATION: [quality]

                MATCH_QUALITY: [quality]

                RISK_LEVEL: [level]
                
                SUMMARY: [Detailed analysis of key findings]
                
                RECOMMENDATIONS: [Specific action items] """,
            )
            logger.debug(f"Run created with ID: {run.id}")

            # Monitor run with new method
            run = await self._monitor_analysis_run(thread.id, run.id)
            logger.info("Run completed successfully")

            # Process response with new method
            risk_level, summary, recommendations, structured_findings = (
                await self._process_analysis_response(thread.id, run.id)
            )
            logger.info(f"Analysis processed: risk level {risk_level}")

            return risk_level, summary, recommendations, structured_findings

        except TimeoutError as e:
            logger.error("Analysis run timed out", exc_info=True)
            raise TimeoutError("Analysis exceeded time limit") from e

        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}", exc_info=True)
            raise

    async def _monitor_analysis_run(
        self, thread_id: str, run_id: str, timeout: int = 600
    ) -> Run:
        """Monitor the AI analysis run, handle status changes, and manage overall flow."""
        logger.info(f"Starting monitoring of run {run_id}")
        start_time = datetime.now()
        last_status = None

        while (datetime.now() - start_time).seconds < timeout:
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id, run_id=run_id
                )

                # Log status changes
                if run.status != last_status:
                    logger.info(
                        f"Run {run_id} status changed: {last_status} -> {run.status}"
                    )
                    last_status = run.status

                # Handle each possible run status
                if run.status == "completed":
                    logger.info(f"Run {run_id} completed successfully")
                    return run

                elif run.status == "requires_action":
                    logger.info(f"Run {run_id} requires action - handling tool calls")
                    run = await self._handle_required_actions(thread_id, run)
                    # Don't sleep after handling actions
                    continue

                elif run.status == "failed":
                    error_msg = f"Run {run_id} failed: {run.last_error}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                elif run.status == "expired":
                    error_msg = f"Run {run_id} expired"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                elif run.status == "cancelled":
                    error_msg = f"Run {run_id} was cancelled"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                elif run.status in ["queued", "in_progress"]:
                    # Normal processing states, continue monitoring
                    pass
                else:
                    logger.warning(f"Unexpected run status: {run.status}")

                # Sleep before next poll, but only for non-action states
                await asyncio.sleep(2)

            except Exception as e:
                if "Rate limit" in str(e):
                    logger.warning("Rate limited, increasing polling interval")
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Error monitoring run: {str(e)}")
                raise

        # Handle timeout
        logger.error(f"Run {run_id} timed out after {timeout} seconds")
        try:
            self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)
        except Exception as e:
            logger.error(f"Error cancelling timed out run: {str(e)}")
        raise TimeoutError(f"Run {run_id} exceeded timeout of {timeout} seconds")

    async def _process_analysis_response(
        self, thread_id: str, run_id: str
    ) -> Tuple[RiskLevel, str, List[Dict[str, Any]]]:
        """Parse the AI Assistant's final analysis to extract risk details and recommendations."""
        logger.info(f"Processing analysis response for run {run_id}")

        try:
            # Retrieve all messages from the thread
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id, order="desc", limit=10  # Get recent context
            )

            # Extract assistant's analysis
            analysis_content = ""
            findings = []

            for message in messages.data:
                if message.role == "assistant":
                    # Process each content item
                    for content in message.content:
                        if content.type == "text":
                            analysis_content = content.text.value

                        # Handle function call results
                        if getattr(content, "function_call", None):
                            findings.append(json.loads(content.function_call.arguments))

            # Parse the structured analysis response
            risk_section = re.search(r"RISK_LEVEL:\s*(\w+)", analysis_content)
            if not risk_section:
                raise ValueError("Missing risk assessment in analysis")

            risk_level = RiskLevel[risk_section.group(1).upper()]
            logger.debug(f"Extracted risk level: {risk_level}")

            # Extract key sections using regex
            summary_section = re.search(
                r"SUMMARY:(.*?)(?=RECOMMENDATIONS:|$)", analysis_content, re.DOTALL
            )
            recommendations_section = re.search(
                r"RECOMMENDATIONS:(.*?)(?=$)", analysis_content, re.DOTALL
            )

            if not summary_section or not recommendations_section:
                raise ValueError("Missing required analysis sections")

            summary = summary_section.group(1).strip()
            logger.debug(f"Extracted summary: {summary}")
            recommendations = recommendations_section.group(1).strip()
            logger.debug(f"Extracted recommendations: {recommendations}")

            # Process any function-generated findings
            structured_findings = []
            for finding in findings:
                if "analysis_results" in finding:
                    structured_findings.extend(finding["analysis_results"])
            logger.debug(f"Extracted structured findings: {structured_findings}")

            logger.info(f"Processed analysis with risk level: {risk_level}")
            logger.info(f"Found {len(structured_findings)} structured findings")

            return risk_level, summary, recommendations, structured_findings

        except Exception as e:
            logger.error(f"Error processing analysis: {str(e)}", exc_info=True)
            raise RuntimeError(f"Analysis processing failed: {str(e)}")

    async def generate_report(self, identity: IdentityInfo) -> KYCReport:
        """
        Generate a comprehensive KYC report by combining identity, compliance, and media findings.

        Runs all checks concurrently and handles potential errors appropriately.
        """
        logger.info(f"Generating KYC report for {identity.full_name}")
        try:
            # Run all checks in parallel with timeout
            async with asyncio.TaskGroup() as group:
                compliance_task = group.create_task(self.check_compliance_lists(identity))
                media_task = group.create_task(self.check_adverse_media(identity))

            compliance_matches = compliance_task.result()
            adverse_media = media_task.result()

            # Analyze findings
            risk_level, risk_summary, recommendations, structured_findings = (
                await self.analyze_findings(identity, compliance_matches, adverse_media)
            )

            # Create report
            report = KYCReport(
                identity_info=identity,
                risk_level=risk_level,
                compliance_matches=compliance_matches,
                adverse_media=adverse_media,
                risk_summary=risk_summary,
                recommendations=recommendations,
            )

            logger.info(f"KYC report generated with risk level: {risk_level}")
            logger.debug(f"Report details: {report.model_dump()}")

            # Save report files using ReportHandler
            json_path, pdf_path = await self.report_handler.save_report(report)
            logger.info(f"Saved report files: JSON at {json_path} and PDF at {pdf_path}")

            return report

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}", exc_info=True)
            raise

    def _prepare_analysis_prompt(
        self,
        identity: IdentityInfo,
        compliance_matches: List[ComplianceMatch],
        adverse_media: List[Dict[str, Any]],
    ) -> str:
        """
        Prepare a structured prompt for AI analysis including identity, compliance and media details.

        Returns:
            A formatted string prompt.
        """
        return f"""Please analyze the following KYC findings:

Subject Information:
- Name: {identity.full_name}
- Date of Birth: {identity.date_of_birth}
- Nationality: {identity.nationality}
- Document Type: {identity.document_type}

Compliance Matches: {json.dumps([m.model_dump() for m in compliance_matches if isinstance(m, ComplianceMatch)], indent=2)}

Adverse Media Findings: {json.dumps(adverse_media, indent=2)}

Please provide:
1. Overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
2. Detailed analysis of key findings
3. Specific recommendations for further action

Format your response according to the instructions provided."""


class ReportHandler:
    """Handles storage and formatting for generated KYC reports."""

    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)

    def _get_report_path(self, report_id: str, format: str) -> Path:
        """Get full file path for a report in the given format."""
        return self.report_dir / f"kyc_{report_id}.{format}"

    async def save_report(self, report: KYCReport) -> Tuple[Path, Path]:
        """Save the KYC report to both JSON and PDF formats."""
        json_path = self._get_report_path(report.report_id, "json")
        pdf_path = self._get_report_path(report.report_id, "pdf")

        # Save JSON asynchronously
        async with aiofiles.open(json_path, "w") as f:
            await f.write(report.model_dump_json(indent=2))

        # Generate and save PDF
        await self.generate_pdf_report(report, pdf_path)

        return json_path, pdf_path

    async def generate_pdf_report(self, report: KYCReport, output_path: Path) -> None:
        """Generate a nicely formatted PDF version of the KYC report."""
        pdf = FPDF()
        pdf.add_page()

        # Add custom fonts with unicode support
        pdf.add_font("FiraSans-Book", "", "fonts/FiraSans-Book.ttf", uni=True)
        pdf.add_font("FiraSans-Medium", "", "fonts/FiraSans-Medium.ttf", uni=True)
        pdf.add_font("FiraSans-Regular", "", "fonts/FiraSans-Regular.ttf", uni=True)

        # Configure page layout
        pdf.set_margins(15, 15, 15)
        pdf.set_auto_page_break(auto=True, margin=15)

        # Add report header
        pdf.set_font("FiraSans-Medium", "", 16)
        pdf.cell(0, 10, "KYC Report", 0, 1, "C")
        pdf.ln(5)

        pdf.set_font("FiraSans-Book", "", 12)

        def row(label, value):
            pdf.cell(50, 10, str(label), border=1)
            pdf.cell(130, 10, str(value), border=1, ln=1)

        # Add report metadata and identity info
        row("Report ID", report.report_id)
        row("Created At", report.created_at)
        row("Full Name", report.identity_info.full_name)
        row("Date of Birth", report.identity_info.date_of_birth)
        row("Nationality", report.identity_info.nationality)
        row("Sex", report.identity_info.sex)
        row("Document Type", report.identity_info.document_type)
        row("Document Number", report.identity_info.document_number)
        row("Risk Level", report.risk_level)
        pdf.ln(5)

        # Add compliance matches section
        pdf.set_font("FiraSans-Regular", "", 14)
        pdf.cell(0, 10, "Compliance Matches", 0, 1, "L")
        pdf.set_font("FiraSans-Book", "", 12)

        for match in report.compliance_matches:
            row("Source", match.source)
            row("Score", match.match_score)
            row("Matched Name", match.matched_name)
            if match.matched_date_of_birth:
                row("Date of Birth", match.matched_date_of_birth)
            if match.matched_nationalities:
                row("Nationalities", ", ".join(match.matched_nationalities or []))
            pdf.ln(2)
        pdf.ln(5)

        # Add adverse media section
        pdf.set_font("FiraSans-Regular", "", 14)
        pdf.cell(0, 10, "Adverse Media", 0, 1, "L")
        pdf.set_font("FiraSans-Book", "", 12)

        for media in report.adverse_media:
            row("Headline", media.get("headline"))
            row("Risk Level", media.get("risk_level"))
            pdf.ln(2)
        pdf.ln(5)

        # Add risk assessment
        pdf.set_font("FiraSans-Regular", "", 14)
        pdf.cell(0, 10, "Risk Assessment", 0, 1, "L")
        pdf.set_font("FiraSans-Book", "", 12)
        pdf.multi_cell(0, 10, report.risk_summary, border=1)
        pdf.ln(5)

        # Add recommendations
        pdf.set_font("FiraSans-Regular", "", 14)
        pdf.cell(0, 10, "Recommendations", 0, 1, "L")
        pdf.set_font("FiraSans-Book", "", 12)
        pdf.multi_cell(0, 10, report.recommendations, border=1)

        # Save PDF
        pdf.output(str(output_path))


async def main(document_path: str) -> None:
    """Main entry point for running the KYC process."""
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
    )

    try:
        # Process ID document
        identity = await agent.process_id_document(document_path)

        # Generate report
        report = await agent.generate_report(identity)

    except Exception as e:
        logger.error(f"KYC process failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Get allowed extensions from env or use default image extensions
    ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png").split(","))

    if len(sys.argv) != 2:
        print("Usage: python kyc_agent.py <path_to_id_document>")
        sys.exit(1)

    file_path = sys.argv[1]
    extension = Path(file_path).suffix.lower().lstrip(".")

    if extension not in ALLOWED_EXTENSIONS:
        print(f"Error: File must be one of these types: {', '.join(ALLOWED_EXTENSIONS)}")
        sys.exit(1)

    asyncio.run(main(file_path))
