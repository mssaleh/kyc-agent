import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
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
    age: Optional[str] = None
    sex: Optional[str] = None
    alt_name: Optional[str] = None
    place_of_birth: Optional[str] = None
    places_of_residence: Optional[List[str]] = field(default_factory=list)
    fathers_name: Optional[str] = None
    mothers_name: Optional[str] = None
    document_type: Optional[str] = None
    document_class: Optional[str] = None
    document_number: Optional[str] = None
    document_series: Optional[str] = None
    date_of_issue: Optional[str] = None
    date_of_expiry: Optional[str] = None
    document_expired: Optional[bool] = None
    nationality: Optional[str] = None
    nationality_code: Optional[str] = None
    personal_number: Optional[str] = None
    given_names: Optional[str] = None
    surname: Optional[str] = None
    issuing_country: Optional[str] = None
    issuing_country_code: Optional[str] = None
    mrz: Optional[dict] = None
    status: Optional[str] = None
    mrz_conflict: Optional[bool] = None


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
    risk_level: str = Field(default_factory=lambda: RiskLevel.LOW.value)
    identity_info: IdentityInfo
    identity_verification: str = ""
    match_quality: str = ""
    screening_summary: str = ""
    risk_summary: str
    kyc_summary: str = ""
    compliance_matches: List[ComplianceMatch]
    adverse_media: List[Dict[str, Any]]
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

1. Identity Analysis and Quality of identity verification
    - Evaluate the authenticity and completeness of provided identity information 
    - Identify potential discrepancies or red flags in identity documents
    - Consider the reliability and jurisdiction of document issuance
    - Assess whether the ID document meets regulatory requirements. 
      For example, the field "Status" indicates the Success of Failure of document recognition, while the field "mrz_conflict" indicates a conflict between MRZ data and printed data, potentially a sign of tampering or fake ID.

2. Compliance Screening Analysis
    A. Evaluate potential matches against sanctions and watchlists, considering:
        - Quality of the screening matches, making a judgement on whether they are either:
            - Confirmed matches
            - Probable matches
            - Possible matches
            - False positives
            - Items needing further investigation
            - False negatives
        - Name popularity, similarity and variations
        - Supporting identifiers (DOB, nationality, etc.)
        - Context and severity of listings
    B. Document your analytical process and justification

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
                            age=data.get("age"),
                            sex=data.get("sex"),
                            alt_name=data.get("alt_name"),
                            place_of_birth=data.get("place_of_birth"),
                            places_of_residence=data.get("places_of_residence", []),
                            fathers_name=data.get("fathers_name"),
                            mothers_name=data.get("mothers_name"),
                            document_type=data.get("document_type"),
                            document_class=data.get("document_class"),
                            document_number=data.get("document_number"),
                            document_series=data.get("document_series"),
                            date_of_issue=data.get("date_of_issue"),
                            date_of_expiry=data.get("date_of_expiry"),
                            document_expired=data.get("document_expired"),
                            nationality=data.get("nationality"),
                            nationality_code=data.get("nationality_code"),
                            personal_number=data.get("personal_number"),
                            given_names=data.get("given_names"),
                            surname=data.get("surname"),
                            issuing_country=data.get("issuing_country"),
                            issuing_country_code=data.get("issuing_country_code"),
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
    ) -> Tuple[RiskLevel, str, str, str, str, str, str]:
        """Analyze identity, compliance, and media findings with the AI Assistant.

        Returns:
            A tuple containing:
            - risk_level (RiskLevel)
            - identity_verification (str)
            - match_quality (str)
            - summary (str)
            - recommendations (str)
            - structured_findings (List[Dict[str, Any]])
        """
        logger.info(f"Starting AI analysis of findings for {identity.full_name}")

        if not compliance_matches:
            logger.warning(
                "No compliance matches were provided; proceeding with empty list."
            )
            compliance_matches = []

        if adverse_media is None:
            logger.warning("Adverse media data is None; setting to empty list.")
            adverse_media = []

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
    1. Identity Analysis and Quality of identity verification
    2. Compliance Screening Analysis: Coverting quality of the screening matches, making a judgement on whether they are either:
        - Confirmed matches
        - Probable matches
        - Possible matches
        - False positives
        - Items needing further investigation
        - False negatives
        - Whether they are relevant to the KYC process and the subject's risk profile
    3. Overall risk level (LOW/MEDIUM/HIGH/CRITICAL) with justification
    4. Risk Assessment from the perspective of a compliance officer in a government agency issuing business licenses
    5. KYC Summary: Detailed analysis of key findings within the context of KYC compliance in government agencies
    6. Specific recommendations with clear rationales

Important Note: Watchman screening service returns matches with a score of 1.0 (Highest) even for address only matches. If there is no name, you shall ignore this match.

Format response as:
IDENTITY_VERIFICATION: [quality]

SCREENING_SUMMARY: [compliance screening and adverse media screening summary]

RISK_LEVEL: [level]

RISK_SUMMARY: [High-level summary of risk assessment]

KYC_SUMMARY: [Detailed analysis of key findings from the prespective of a compliance officer]

RECOMMENDATIONS: [Specific action items] """,
            )
            logger.debug(f"Run created with ID: {run.id}")

            # Monitor run with new method
            run = await self._monitor_analysis_run(thread.id, run.id)
            logger.info("Run completed successfully")

            # Process response with new method
            (
                risk_level,
                identity_verification,
                screening_summary,
                match_quality,
                risk_summary,
                kyc_summary,
                recommendations,
            ) = await self._process_analysis_response(thread.id, run.id)
            logger.info(f"Analysis processed: risk level {risk_level}")

            return (
                risk_level,
                identity_verification,
                screening_summary,
                match_quality,
                risk_summary,
                kyc_summary,
                recommendations,
            )

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
    ) -> Tuple[RiskLevel, str, str, str, str, str, str]:
        """
        Parse the AI Assistant's final analysis to extract risk details and recommendations.
        Uses strict section parsing to prevent content duplication.
        """
        logger.info(f"Processing analysis response for run {run_id}")

        try:
            # Retrieve all messages from the thread
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id, order="desc", limit=10  # Get recent context
            )

            # Get the latest assistant message
            analysis_content = ""
            for message in messages.data:
                if message.role == "assistant":
                    # Process each content item
                    for content in message.content:
                        if content.type == "text":
                            analysis_content = content.text.value
                            logger.debug(f"Extracted analysis content: {analysis_content}")
                            break
                    break

            # Define a helper function to extract sections
            def extract_section(section_name: str) -> str:
                pattern = f"{section_name}:\\s*(.*?)(?=(?:IDENTITY_VERIFICATION|MATCH_QUALITY|SCREENING_SUMMARY|RISK_LEVEL|RISK_SUMMARY|KYC_SUMMARY|RECOMMENDATIONS):|$)"
                match = re.search(pattern, analysis_content, re.DOTALL)
                return match.group(1).strip() if match else ""

            # Extract each section with clear boundaries
            risk_level_str = extract_section("RISK_LEVEL")
            identity_verification = extract_section("IDENTITY_VERIFICATION")
            screening_summary = extract_section("SCREENING_SUMMARY")
            match_quality = extract_section("MATCH_QUALITY")
            risk_summary = extract_section("RISK_SUMMARY")
            kyc_summary = extract_section("KYC_SUMMARY")
            recommendations = extract_section("RECOMMENDATIONS")

            try:
                risk_level = RiskLevel[risk_level_str.upper()]
            except (KeyError, AttributeError):
                logger.error(f"Invalid risk level: {risk_level_str}")
                risk_level = RiskLevel.HIGH  # Default to HIGH if parsing fails

            # Validate that required sections are present
            required_sections = {
                "Identity Verification": identity_verification,
                "Screening Summary": screening_summary,
                "Risk Summary": risk_summary,
                "KYC Summary": kyc_summary,
                "Recommendations": recommendations,
            }

            missing_sections = [k for k, v in required_sections.items() if not v]
            if missing_sections:
                raise ValueError(f"Missing required sections: {', '.join(missing_sections)}")

            logger.info(f"Successfully processed analysis with risk level: {risk_level}")

            return (
                risk_level,
                identity_verification,
                screening_summary,
                match_quality,
                risk_summary,
                kyc_summary,
                recommendations,
            )

        except Exception as e:
            logger.error(f"Error processing analysis response: {str(e)}", exc_info=True)
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
            (
                risk_level,
                identity_verification,
                screening_summary,
                match_quality,
                risk_summary,
                kyc_summary,
                recommendations,
            ) = await self.analyze_findings(identity, compliance_matches, adverse_media)

            # Create report
            report = KYCReport(
                identity_info=identity,
                risk_level=risk_level,
                identity_verification=identity_verification,
                match_quality=match_quality,
                screening_summary=screening_summary,
                kyc_summary=kyc_summary,
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
        return f"""Please analyze the following KYC findings and provide a structured assessment. Each section should be focused and avoid duplicating information from other sections:

Subject Information:
- Name: {identity.full_name}
- Date of Birth: {identity.date_of_birth}
- Nationality: {identity.nationality}
- Document Type: {identity.document_type}

Compliance Matches: {json.dumps([m.model_dump() for m in compliance_matches if isinstance(m, ComplianceMatch)], indent=2)}

Adverse Media Findings: {json.dumps(adverse_media, indent=2)}

Please structure your response in the following specific sections without repetition:

IDENTITY_VERIFICATION:
[Focused analysis of document authenticity and identity verification results]

MATCH_QUALITY:
[Assessment of the quality and relevance of compliance matches]

SCREENING_SUMMARY:
[Overview of compliance screening and adverse media findings]

RISK_LEVEL:
[Single word: LOW/MEDIUM/HIGH/CRITICAL]

RISK_SUMMARY:
[Concise assessment of key risk factors]

KYC_SUMMARY:
[Comprehensive analysis from a compliance perspective]

RECOMMENDATIONS:
[Specific action items and next steps]

Keep each section focused on its specific purpose and avoid duplicating information across sections."""


class ReportHandler:
    """Handles storage and formatting for generated KYC reports."""

    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        self._setup_fonts()

    def _setup_fonts(self):
        """Define font configurations for consistent typography."""
        self.fonts = {
            "heading1": {"family": "FiraSans-Medium", "size": 18},
            "heading2": {"family": "FiraSans-Medium", "size": 14},
            "heading3": {"family": "FiraSans-Regular", "size": 12},
            "body": {"family": "FiraSans-Book", "size": 11},
            "table_header": {"family": "FiraSans-Regular", "size": 11},
            "table_cell": {"family": "FiraSans-Book", "size": 10},
        }

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

    def _set_font(self, pdf: FPDF, style: str):
        """Apply font configuration based on style."""
        font = self.fonts[style]
        pdf.set_font(font["family"], "", font["size"])

    def _format_markdown_text(self, pdf: FPDF, text: str, max_width: float):
        """Format markdown text with proper styling."""
        lines = text.split('\n')
        base_x = pdf.get_x()  # Store original x position once
        list_indent = 0
        in_list = False
        list_type = None  # Track type of list: 'bullet' or 'numbered'
        
        for line in lines:
            # Reset x position at start of each line
            pdf.set_x(base_x)
            
            # Handle markdown headers
            if line.startswith('###'):
                self._set_font(pdf, "heading3")
                pdf.multi_cell(max_width, 6, line.strip('# '))
                self._set_font(pdf, "body")
                in_list = False
                list_type = None
            elif line.startswith('##'):
                self._set_font(pdf, "heading2")
                pdf.multi_cell(max_width, 7, line.strip('# '))
                self._set_font(pdf, "body")
                in_list = False
                list_type = None
            elif line.startswith('#'):
                self._set_font(pdf, "heading1")
                pdf.multi_cell(max_width, 8, line.strip('# '))
                self._set_font(pdf, "body")
                in_list = False
                list_type = None
            elif line.strip():  # Non-empty lines
                if line.startswith(('- ', '* ')):  # Bullet points
                    if not in_list or list_type != 'bullet':
                        list_indent = 5
                        list_type = 'bullet'
                    in_list = True
                    pdf.set_x(base_x + list_indent)
                    content = line[2:]  # Remove bullet point marker
                    self._write_formatted_line(pdf, content, max_width - list_indent)
                elif re.match(r'^\d+\.', line):  # Numbered lists
                    if not in_list or list_type != 'numbered':
                        list_indent = 8
                        list_type = 'numbered'
                    in_list = True
                    pdf.set_x(base_x + list_indent)
                    match = re.match(r'^(\d+\.)\s*(.*)$', line)
                    if match:
                        number, content = match.groups()
                        # Write number at consistent position
                        pdf.cell(8, 5, number + ' ', 0, 0)
                        # Write content with proper indentation
                        self._write_formatted_line(pdf, content, max_width - list_indent - 8)
                else:  # Regular paragraph text
                    in_list = False
                    list_type = None
                    pdf.set_x(base_x)
                    self._write_formatted_line(pdf, line, max_width)
            else:  # Empty lines
                pdf.ln(3)
                in_list = False
                list_type = None

    def _write_formatted_line(self, pdf: FPDF, line: str, max_width: float):
        """Handle bold text formatting within a line."""
        parts = re.split(r'(\*\*.*?\*\*)', line)
        current_x = pdf.get_x()  # Remember starting position
        
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                # Bold text
                bold_text = part[2:-2]  # Remove ** markers
                self._set_font(pdf, "heading3")  # Use heading3 for bold
                pdf.write(5, bold_text)
                self._set_font(pdf, "body")
            else:
                # Regular text
                if part.strip():
                    pdf.write(5, part)
        
        pdf.ln()  # Move to next line after writing all parts

    def _add_identity_table(self, pdf: FPDF, report: KYCReport):
        """Add identity information in a structured table format."""
        self._set_font(pdf, "table_header")
        
        # Calculate column widths
        col1_width = 50
        col2_width = pdf.w - 30 - col1_width  # 30 is total margin (15 each side)
        row_height = 7

        # Define identity information rows
        identity_rows = [
            ("Report ID", report.report_id),
            ("Created At", report.created_at),
            ("Full Name", report.identity_info.full_name),
            ("Date of Birth", report.identity_info.date_of_birth),
            ("Nationality", report.identity_info.nationality or "N/A"),
            ("Document Type", report.identity_info.document_type or "N/A"),
            ("Document Number", report.identity_info.document_number or "N/A"),
            ("Document Status", "Expired" if report.identity_info.document_expired else "Valid"),
            ("Risk Level", report.risk_level.upper()),
        ]

        # Draw table
        for label, value in identity_rows:
            self._set_font(pdf, "table_header")
            pdf.cell(col1_width, row_height, label, 1)
            self._set_font(pdf, "table_cell")
            pdf.cell(col2_width, row_height, str(value), 1, 1)

        pdf.ln(5)

    def _add_section(self, pdf: FPDF, title: str, content: str):
        """Add a section with proper formatting and spacing."""
        # Map AI section names to proper English titles
        section_titles = {
            "Identity Verification": "Identity Verification Assessment",
            "Match Quality": "Compliance Match Assessment",
            "Screening Summary": "Screening Summary",
            "Risk Summary": "Risk Assessment Summary",
            "KYC Summary": "KYC Assessment",
            "Recommendations": "Recommended Actions"
        }

        display_title = section_titles.get(title, title)
        
        self._set_font(pdf, "heading2")
        pdf.cell(0, 10, display_title, 0, 1)
        pdf.ln(2)
        
        self._set_font(pdf, "body")
        # Remove any AI section markers from the content
        cleaned_content = re.sub(
            r'(IDENTITY_VERIFICATION|MATCH_QUALITY|SCREENING_SUMMARY|RISK_LEVEL|RISK_SUMMARY|KYC_SUMMARY|RECOMMENDATIONS):\s*',
            '',
            content
        )
        
        if cleaned_content:
            self._format_markdown_text(pdf, cleaned_content, pdf.w - 30)
        else:
            pdf.cell(0, 5, "No information available", 0, 1)
        pdf.ln(5)

    def _add_compliance_matches(self, pdf: FPDF, matches: List[ComplianceMatch]):
        """Add compliance matches section with proper formatting using tables."""
        if not matches:
            return

        self._set_font(pdf, "heading2")
        pdf.cell(0, 10, "Compliance Matches", 0, 1)
        pdf.ln(2)

        # Define column widths as percentages of page width
        col_widths = {
            'source': 40,
            'score': 20,
            'name': 50,
            'details': 70
        }

        # Table headers
        self._set_font(pdf, "table_header")
        pdf.cell(col_widths['source'], 7, "Source", 1)
        pdf.cell(col_widths['score'], 7, "Score", 1)
        pdf.cell(col_widths['name'], 7, "Matched Name", 1)
        pdf.cell(col_widths['details'], 7, "Additional Details", 1)
        pdf.ln()

        # Table rows
        self._set_font(pdf, "table_cell")
        for match in matches:
            # Calculate row height based on content
            details = []
            if match.matched_date_of_birth:
                details.append(f"DoB: {match.matched_date_of_birth}")
            if match.matched_nationalities:
                details.append(f"Nationalities: {', '.join(match.matched_nationalities)}")
            if match.risk_category:
                details.append(f"Risk: {match.risk_category}")
            
            details_text = "\n".join(details)
            # Calculate required height for details column
            lines = len(details)
            row_height = max(7, lines * 5)  # Minimum 7, or 5 per line

            # Print row with multi-line support
            current_y = pdf.get_y()
            
            pdf.cell(col_widths['source'], row_height, str(match.source), 1)
            pdf.cell(col_widths['score'], row_height, f"{match.match_score:.2f}", 1)
            pdf.cell(col_widths['name'], row_height, str(match.matched_name), 1)
            
            # Save position
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            
            # Print details in multi-line cell
            pdf.multi_cell(col_widths['details'], row_height/lines, details_text, 1)
            
            # Restore position for next row
            pdf.set_xy(15, y_pos + row_height)

        pdf.ln(5)

    def _add_adverse_media(self, pdf: FPDF, media: List[Dict[str, Any]]):
        """Add adverse media section with simplified formatting (headlines and links only)."""
        if not media:
            return

        self._set_font(pdf, "heading2")
        pdf.cell(0, 10, "Adverse Media Findings", 0, 1)
        pdf.ln(2)

        # Define column widths
        col_widths = {
            'date': 30,
            'category': 40,
            'headline': 110
        }

        # Table headers
        self._set_font(pdf, "table_header")
        pdf.cell(col_widths['date'], 7, "Date", 1)
        pdf.cell(col_widths['category'], 7, "Category", 1)
        pdf.cell(col_widths['headline'], 7, "Headline", 1)
        pdf.ln()

        # Table rows
        self._set_font(pdf, "table_cell")
        for item in media:
            # Format date
            date_str = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d') if 'timestamp' in item else 'N/A'
            
            # Print row with date and category
            pdf.cell(0, 7, f"Date: {date_str}", 1, 1)
            pdf.cell(0, 7, f"Category: {item.get('category', 'N/A')}", 1, 1)
            
            # Print headline
            headline = item.get('headline', 'Untitled')
            pdf.multi_cell(0, 7, f"Headline: {headline}", 1)
            
            # Add source link if available
            if item.get('source_link'):
                pdf.set_text_color(0, 0, 255)  # Blue color for links
                pdf.cell(0, 7, f"Source: {item['source_link']}", 1, 1)
                pdf.set_text_color(0, 0, 0)  # Reset to black
            
            # Add spacing between entries
            pdf.ln(5)

        pdf.ln(5)

    async def generate_pdf_report(self, report: KYCReport, output_path: Path) -> None:
        """Generate a professionally formatted PDF version of the KYC report."""
        pdf = FPDF()
        pdf.add_page()

        # Add fonts
        pdf.add_font("FiraSans-Book", "", "fonts/FiraSans-Book.ttf", uni=True)
        pdf.add_font("FiraSans-Medium", "", "fonts/FiraSans-Medium.ttf", uni=True)
        pdf.add_font("FiraSans-Regular", "", "fonts/FiraSans-Regular.ttf", uni=True)

        # Configure page layout
        pdf.set_margins(15, 15, 15)
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        self._set_font(pdf, "heading1")
        pdf.cell(0, 15, "Know Your Customer (KYC) Report", 0, 1, "C")
        pdf.ln(5)

        # Identity Information Table
        self._add_identity_table(pdf, report)

        # Main Sections
        self._add_section(pdf, "Identity Verification Assessment", report.identity_verification)
        self._add_section(pdf, "Compliance Match Assessment", report.match_quality)
        self._add_section(pdf, "Screening Summary", report.screening_summary)
        self._add_section(pdf, "Risk Assessment Summary", report.risk_summary)
        self._add_section(pdf, "KYC Assessment", report.kyc_summary)
        self._add_section(pdf, "Recommendations", report.recommendations)

        # Add a page break and detailed findings only if there are findings to show
        if report.compliance_matches or report.adverse_media:
            pdf.add_page()
            
            # Add a "Detailed Findings" heading
            self._set_font(pdf, "heading1")
            pdf.cell(0, 15, "Detailed Findings", 0, 1, "C")
            pdf.ln(5)

            # Detailed Findings
            self._add_compliance_matches(pdf, report.compliance_matches)
            self._add_adverse_media(pdf, report.adverse_media)

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
