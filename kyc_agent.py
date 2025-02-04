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
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("kyc_agent")


class DocumentType(Enum):
    """Type of identity document being processed"""

    PASSPORT = "passport"
    NATIONAL_ID = "national_id"


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
    """Main KYC agent class that orchestrates the entire workflow"""

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
        Create an OpenAI Assistant specialized in KYC analysis with focus on autonomous reasoning.
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
            instructions="""You are an expert KYC compliance analyst with deep experience in risk assessment and regulatory compliance. You are tasked with analyzing identity documents, compliance screening results, and adverse media findings to make informed decisions about potential risks and recommended actions.
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

You will receive information through our conversation and can request additional data or searches using the provided tools. However, all analysis and reasoning should be performed by you directly - do not defer analysis to external functions.

When you need additional information or searches, explain what you need and why, then use the appropriate tool to request it. After receiving new information, incorporate it into your ongoing analysis.

Your goal is to enable informed compliance decisions through careful analysis and clear communication.

Format your final assessments with clear sections for:
- Identity Verification Status 
- Compliance Screening Results 
- Risk Assessment 
- Recommendations 
- Rationale for Decisions""",
            tools=[],
        )

    async def process_id_document(self, document_path: str) -> IdentityInfo:
        """Process and extract information from ID document"""
        logger.info(f"Starting processing of ID document: {document_path}")

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Opening file: {document_path}")
                with open(document_path, "rb") as file:
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
        """Check various compliance lists asynchronously"""
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
                        "limit": "10",
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
        """Check adverse media and reputation using Dilisense"""
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
                    return (
                        adverse_findings
                    )

        except Exception as e:
            logger.error(f"Error checking adverse media: {str(e)}")
            raise

    async def analyze_findings(
        self,
        identity: IdentityInfo,
        compliance_matches: List[ComplianceMatch],
        adverse_media: List[Dict[str, Any]],
    ) -> Tuple[RiskLevel, str, str]:
        """
        Use OpenAI Assistant to analyze findings and determine risk level with improved
        error handling and monitoring.
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
        """
        Monitor an analysis run with enhanced state handling and logging.

        Args:
            thread_id: Thread ID to monitor
            run_id: Run ID to monitor
            timeout: Maximum wait time in seconds

        Returns:
            Completed Run object

        Raises:
            TimeoutError: If run exceeds timeout
            RuntimeError: If run fails or expires
        """
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
        """
        Process the analysis response from the Assistant with enhanced decision logic.
        """
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

    async def _handle_required_actions(self, thread_id: str, run: Run) -> Run:
        """
        Handle required actions from a run, particularly tool calls.
        """
        if not run.required_action or not run.required_action.submit_tool_outputs:
            return run

        logger.info(
            f"Processing {len(run.required_action.submit_tool_outputs.tool_calls)} tool calls"
        )

        try:
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                logger.debug(
                    f"Processing tool call {tool_call.id}: {tool_call.function.name}"
                )

                # Process the tool call and get output
                output = await self._process_tool_call(tool_call)
                tool_outputs.append({"tool_call_id": tool_call.id, "output": output})

            # Submit all tool outputs at once
            logger.info(f"Submitting {len(tool_outputs)} tool outputs")
            updated_run = self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
            )

            logger.debug(
                f"Tool outputs submitted successfully, new run status: {updated_run.status}"
            )
            return updated_run

        except Exception as e:
            logger.error(f"Error handling required actions: {str(e)}")
            raise RuntimeError(f"Failed to process tool calls: {str(e)}")

    async def _analyze_compliance_results(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze compliance check results with advanced filtering and matching logic"""
        matches = args["matches"]
        search_adjustment = args["search_adjustment"]

        # Track analysis decisions
        decisions = {
            "confirmed_matches": [],
            "potential_matches": [],
            "false_positives": [],
            "needs_investigation": [],
        }

        # Analyze each match
        for match in matches:
            # Calculate confidence score based on multiple factors
            confidence = self._calculate_match_confidence(
                match["match_score"], match["matched_name"], match.get("match_details", {})
            )

            if confidence > 0.9:
                decisions["confirmed_matches"].append(
                    {
                        "match": match,
                        "confidence": confidence,
                        "justification": "High confidence based on strong name match and supporting details",
                    }
                )
            elif confidence > 0.7:
                decisions["potential_matches"].append(
                    {
                        "match": match,
                        "confidence": confidence,
                        "justification": "Moderate confidence, requires additional verification",
                    }
                )
            elif confidence < 0.3:
                decisions["false_positives"].append(
                    {
                        "match": match,
                        "confidence": confidence,
                        "justification": "Low confidence due to weak matching criteria",
                    }
                )
            else:
                decisions["needs_investigation"].append(
                    {
                        "match": match,
                        "confidence": confidence,
                        "justification": "Unclear match quality, needs human review",
                    }
                )

        # Determine if search criteria adjustment is needed
        should_adjust = (
            len(decisions["confirmed_matches"]) == 0 and search_adjustment["broaden_search"]
        )

        return {
            "analysis_results": decisions,
            "search_adjustment_needed": should_adjust,
            "adjusted_criteria": (
                search_adjustment["adjusted_criteria"] if should_adjust else None
            ),
        }

    async def _analyze_media_results(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze adverse media findings with risk categorization"""
        media_results = args["media_results"]

        risk_categories = {"high": [], "medium": [], "low": [], "irrelevant": []}

        # Process each media result
        for result in media_results:
            risk_assessment = self._assess_media_risk(
                result["category"],
                result["headline"],
                result["body"],
                result.get("risk_level", "low"),
            )

            # Add to appropriate risk category with analysis
            risk_categories[risk_assessment["level"]].append(
                {
                    "source": result,
                    "analysis": risk_assessment["analysis"],
                    "impact": risk_assessment["impact"],
                }
            )

        return {
            "analysis_results": {
                "risk_categories": risk_categories,
                "summary": self._generate_media_summary(risk_categories),
            }
        }

    def _calculate_match_confidence(
        self, match_score: float, matched_name: str, details: Dict
    ) -> float:
        """Calculate confidence score for a compliance match using multiple factors"""
        base_confidence = match_score

        # # Adjust based on name matching quality
        # name_similarity = self._calculate_name_similarity(matched_name)
        # base_confidence *= 0.7 + (0.3 * name_similarity)

        # Adjust based on supporting details
        if details.get("date_of_birth"):
            base_confidence *= 1.2
        if details.get("nationality"):
            base_confidence *= 1.1
        if details.get("identification_documents"):
            base_confidence *= 1.15

        # Cap at 1.0
        return min(base_confidence, 1.0)

    def _assess_media_risk(
        self, category: str, headline: str, content: str, base_risk: str
    ) -> Dict[str, Any]:
        """Assess risk level and impact of media finding"""
        # Map base risk levels to numerical scores
        risk_scores = {"high": 0.8, "medium": 0.5, "low": 0.2}
        score = risk_scores[base_risk]

        # Adjust score based on category severity
        high_risk_keywords = ["fraud", "corruption", "terrorism", "sanctions"]
        medium_risk_keywords = ["investigation", "lawsuit", "violation"]

        # Check content for risk indicators
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in high_risk_keywords):
            score = min(score * 1.5, 1.0)
        elif any(keyword in content_lower for keyword in medium_risk_keywords):
            score = min(score * 1.2, 1.0)

        # Determine final risk level
        if score >= 0.7:
            level = "high"
            impact = "Significant regulatory and reputational risk"
        elif score >= 0.4:
            level = "medium"
            impact = "Moderate risk requiring enhanced due diligence"
        else:
            level = "low"
            impact = "Minor or negligible risk impact"

        return {
            "level": level,
            "score": score,
            "analysis": f"Risk assessment based on {category} classification and content analysis",
            "impact": impact,
        }

    def _generate_media_summary(self, risk_categories: Dict[str, List]) -> str:
        """Generate summary of media findings"""
        high_risk_count = len(risk_categories["high"])
        medium_risk_count = len(risk_categories["medium"])

        if high_risk_count > 0:
            return f"Found {high_risk_count} high-risk and {medium_risk_count} medium-risk media items requiring immediate attention"
        elif medium_risk_count > 0:
            return f"Found {medium_risk_count} medium-risk items requiring further review"
        else:
            return "No significant adverse media findings"

    async def generate_report(self, identity: IdentityInfo) -> KYCReport:
        """Generate complete KYC report with improved structure and error handling"""
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
            logger.info(f"Saved report files: JSON={json_path}, PDF={pdf_path}")

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
        """Prepare structured analysis prompt for the Assistant"""

        return f"""Please analyze the following KYC findings:

Subject Information:
- Name: {identity.full_name}
- DOB: {identity.date_of_birth}
- Nationality: {identity.nationality}
- Document: {identity.document_number}

Compliance Matches: {json.dumps([m.model_dump() for m in compliance_matches if isinstance(m, ComplianceMatch)], indent=2)}

Adverse Media Findings: {json.dumps(adverse_media, indent=2)}

Please provide:
1. Overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
2. Detailed analysis of key findings
3. Specific recommendations for further action

Format your response according to the instructions provided."""


class ReportHandler:
    """Handles report generation and storage"""

    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)

    def _get_report_path(self, report_id: str, format: str) -> Path:
        """Get path for report file"""
        return self.report_dir / f"kyc_{report_id}.{format}"

    async def save_report(self, report: KYCReport) -> Tuple[Path, Path]:
        """
        Save report in both JSON and PDF formats

        Args:
            report: KYCReport object to save

        Returns:
            Tuple of paths to JSON and PDF files
        """
        json_path = self._get_report_path(report.report_id, "json")
        pdf_path = self._get_report_path(report.report_id, "pdf")

        # Save JSON asynchronously
        async with aiofiles.open(json_path, "w") as f:
            await f.write(report.model_dump_json(indent=2))

        # Generate and save PDF
        await self.generate_pdf_report(report, pdf_path)

        return json_path, pdf_path

    async def generate_pdf_report(self, report: KYCReport, output_path: Path) -> None:
        """
        Generate PDF version of report with improved formatting
        """
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
    """Main function to run the KYC process"""
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
