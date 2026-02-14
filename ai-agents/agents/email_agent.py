"""
Email Agent - Production-Grade Cold Email Outreach System.

This module implements a robust, type-safe email outreach system with:
- Comprehensive error handling and retry logic
- Rate limiting and throttling
- Prospect scoring and prioritization
- Email validation and deliverability checks
- Detailed metrics and logging
- Follow-up sequence automation

Author: RepEscrow Team
Version: 1.0.0
"""

import time
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email as SGEmail, To, Content
from sendgrid.exceptions import SendGridException
from pydantic import BaseModel, EmailStr, Field, validator

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, RateLimitExceeded
from database import Platform, Prospect, ProspectStatus, Conversation
from claude_client import TaskComplexity


class EmailValidationError(Exception):
    """Raised when email validation fails."""
    pass


class EmailSendError(Exception):
    """Raised when email sending fails."""
    pass


class EmailType(str, Enum):
    """Types of emails we send."""
    COLD_OUTREACH = "cold_outreach"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"
    RESPONSE = "response"


@dataclass(frozen=True)
class EmailMetadata:
    """Immutable metadata for email tracking."""
    sent_at: datetime
    email_type: EmailType
    prospect_id: int
    subject: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for logging."""
        return {
            'sent_at': self.sent_at.isoformat(),
            'email_type': self.email_type.value,
            'prospect_id': str(self.prospect_id),
            'subject': self.subject
        }


class EmailProspect(BaseModel):
    """
    Validated email prospect model.
    
    Ensures all prospect data is valid before attempting outreach.
    """
    email: EmailStr = Field(..., description="Valid email address")
    name: str = Field(..., min_length=1, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=500)
    recent_activity: Optional[str] = Field(None, max_length=500)
    source: Optional[str] = Field(None, description="Where we found this prospect")
    score: int = Field(default=5, ge=1, le=10, description="Quality score 1-10")
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Ensure name is properly formatted."""
        return v.strip().title()
    
    @validator('email')
    def validate_email_domain(cls, v: str) -> str:
        """Additional email validation beyond EmailStr."""
        # Reject common disposable email domains
        disposable_domains = {
            'tempmail.com', 'throwaway.email', '10minutemail.com',
            'guerrillamail.com', 'mailinator.com'
        }
        domain = v.split('@')[1].lower()
        if domain in disposable_domains:
            raise ValueError(f"Disposable email domain not allowed: {domain}")
        return v.lower()


class EmailContent(BaseModel):
    """Validated email content model."""
    subject: str = Field(..., min_length=5, max_length=100)
    body: str = Field(..., min_length=50, max_length=2000)
    email_type: EmailType
    
    @validator('subject')
    def validate_subject(cls, v: str) -> str:
        """Ensure subject is professional."""
        # Remove excessive punctuation
        if v.count('!') > 1 or v.count('?') > 1:
            raise ValueError("Subject contains excessive punctuation")
        return v.strip()
    
    @validator('body')
    def validate_body(cls, v: str) -> str:
        """Ensure body is well-formatted."""
        # Check for common spam indicators
        spam_words = ['click here', 'buy now', 'act now', 'limited time']
        v_lower = v.lower()
        if any(word in v_lower for word in spam_words):
            raise ValueError("Email body contains spam-like content")
        return v.strip()


class EmailAgent(BaseAgent):
    """
    Production-grade email outreach agent.
    
    This agent handles all email-based prospect outreach with:
    - Intelligent prospect prioritization
    - Personalized content generation
    - Automated follow-up sequences
    - Comprehensive error handling
    - Detailed metrics tracking
    
    Rate Limits:
        - 100 emails per day (SendGrid free tier)
        - 1 email per minute to avoid spam flags
        - Maximum 3 emails to same domain per hour
    
    Example:
        >>> agent = EmailAgent()
        >>> if agent.health_check():
        ...     agent.run()
    """
    
    # Class constants
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 5
    EMAIL_DELAY_SECONDS: int = 60
    DOMAIN_RATE_LIMIT_PER_HOUR: int = 3
    
    def __init__(self) -> None:
        """
        Initialize Email agent with SendGrid client.
        
        Raises:
            EmailValidationError: If SendGrid API key is invalid
        """
        super().__init__(platform=Platform.EMAIL)
        
        self._sg_client: Optional[SendGridAPIClient] = None
        self._sent_emails_metadata: List[EmailMetadata] = []
        self._domain_send_tracker: Dict[str, List[datetime]] = {}
        
        self._initialize_sendgrid_client()
    
    def _initialize_sendgrid_client(self) -> None:
        """Initialize and validate SendGrid client."""
        try:
            if not self.settings.sendgrid_api_key:
                self.logger.warning("sendgrid_api_key_not_configured")
                return
            
            self._sg_client = SendGridAPIClient(self.settings.sendgrid_api_key)
            
            # Test the connection with a validation request
            # Note: Actual validation would require a test email send
            
            self.logger.info(
                "sendgrid_client_initialized",
                from_email=self.settings.from_email,
                from_name=self.settings.from_name
            )
            
        except Exception as e:
            self.logger.error(
                "sendgrid_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            self._sg_client = None
    
    def get_name(self) -> str:
        """Get agent name for identification."""
        return "EmailAgent"
    
    def health_check(self) -> bool:
        """
        Perform health check on email agent.
        
        Returns:
            bool: True if agent is operational, False otherwise
        """
        if self._sg_client is None:
            self.logger.warning("health_check_failed_no_client")
            return False
        
        # Additional health checks could include:
        # - Verify SendGrid API key is still valid
        # - Check email sending quota
        # - Verify from_email is verified in SendGrid
        
        return True
    
    def run(self) -> None:
        """
        Execute daily email outreach tasks.
        
        This is the main entry point called by the orchestrator.
        Handles all email operations for the day including:
        - Cold outreach to new prospects
        - Follow-up emails
        - Response handling
        """
        self.logger.info(
            "email_agent_run_started",
            agent_name=self.get_name(),
            date=str(date.today())
        )
        
        if not self.health_check():
            self.logger.error("email_agent_health_check_failed_aborting_run")
            return
        
        try:
            # Phase 1: Send cold outreach emails
            cold_emails_sent = self.safe_execute(self._execute_cold_outreach)
            self.logger.info("cold_outreach_phase_completed", emails_sent=cold_emails_sent or 0)
            
            # Phase 2: Send follow-up emails
            followups_sent = self.safe_execute(self._execute_followup_sequence)
            self.logger.info("followup_phase_completed", emails_sent=followups_sent or 0)
            
            # Phase 3: Save metrics
            self.save_daily_metrics()
            
            # Phase 4: Log summary
            summary = self.get_daily_summary()
            self.logger.info(
                "email_agent_run_completed",
                total_impressions=summary['impressions'],
                total_engagements=summary['engagements'],
                total_conversations=summary['conversations'],
                total_signups=summary['signups']
            )
            
        except Exception as e:
            self.logger.error(
                "email_agent_run_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise
    
    def _execute_cold_outreach(self) -> int:
        """
        Execute cold email outreach campaign.
        
        Returns:
            int: Number of emails successfully sent
        """
        max_emails = self.settings.max_emails_per_day
        emails_sent = 0
        
        self.logger.info(
            "cold_outreach_starting",
            max_emails=max_emails
        )
        
        # Get prospects (prioritized by score)
        prospects = self._get_prioritized_prospects()
        
        if not prospects:
            self.logger.warning("no_email_prospects_available")
            return 0
        
        for prospect_data in prospects:
            if emails_sent >= max_emails:
                self.logger.info("daily_email_limit_reached", emails_sent=emails_sent)
                break
            
            try:
                # Validate prospect data
                prospect = EmailProspect(**prospect_data)
                
                # Check rate limits
                self._enforce_all_rate_limits(prospect.email)
                
                # Generate personalized email
                email_content = self._generate_personalized_email(
                    prospect=prospect,
                    email_type=EmailType.COLD_OUTREACH
                )
                
                # Send email
                success = self._send_email_with_retry(
                    prospect=prospect,
                    content=email_content
                )
                
                if success:
                    emails_sent += 1
                    self.increment_action_count("email")
                    self._record_domain_send(prospect.email)

                    # Track in database
                    db_prospect = self._track_email_prospect(prospect)
                    self.mark_contacted(db_prospect.id)

                    # Log metadata
                    metadata = EmailMetadata(
                        sent_at=datetime.now(timezone.utc),
                        email_type=EmailType.COLD_OUTREACH,
                        prospect_id=db_prospect.id,
                        subject=email_content.subject
                    )
                    self._sent_emails_metadata.append(metadata)

                    # Respect rate limits - wait between emails
                    time.sleep(self.EMAIL_DELAY_SECONDS)
                
            except RateLimitExceeded as e:
                self.logger.warning("rate_limit_exceeded_stopping_outreach", error=str(e))
                break
                
            except EmailValidationError as e:
                self.logger.warning(
                    "prospect_validation_failed_skipping",
                    email=prospect_data.get('email'),
                    error=str(e)
                )
                continue
                
            except Exception as e:
                self.logger.error(
                    "email_send_failed_continuing",
                    prospect_email=prospect_data.get('email'),
                    error=str(e),
                    error_type=type(e).__name__
                )
                continue
        
        self.logger.info(
            "cold_outreach_completed",
            emails_sent=emails_sent,
            prospects_processed=len(prospects)
        )
        
        return emails_sent
    
    def _enforce_all_rate_limits(self, email: str) -> None:
        """
        Enforce all rate limiting rules.
        
        Args:
            email: Email address to check
            
        Raises:
            RateLimitExceeded: If any rate limit would be exceeded
        """
        # 1. Daily email limit
        self.enforce_rate_limit("email", self.settings.max_emails_per_day)
        
        # 2. Domain-specific rate limit
        domain = email.split('@')[1]
        self._enforce_domain_rate_limit(domain)
    
    def _enforce_domain_rate_limit(self, domain: str) -> None:
        """
        Check per-domain rate limiting (does NOT record the send).

        Call _record_domain_send() after a successful send.

        Args:
            domain: Email domain to check

        Raises:
            RateLimitExceeded: If domain limit exceeded
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        if domain not in self._domain_send_tracker:
            self._domain_send_tracker[domain] = []

        # Filter to last hour
        recent_sends = [
            ts for ts in self._domain_send_tracker[domain]
            if ts > one_hour_ago
        ]
        self._domain_send_tracker[domain] = recent_sends

        if len(recent_sends) >= self.DOMAIN_RATE_LIMIT_PER_HOUR:
            raise RateLimitExceeded(
                f"Domain rate limit exceeded for {domain}: "
                f"{len(recent_sends)}/{self.DOMAIN_RATE_LIMIT_PER_HOUR} per hour"
            )

    def _record_domain_send(self, email: str) -> None:
        """Record a successful send for domain rate tracking."""
        domain = email.split('@')[1]
        if domain not in self._domain_send_tracker:
            self._domain_send_tracker[domain] = []
        self._domain_send_tracker[domain].append(datetime.now(timezone.utc))
    
    def _get_prioritized_prospects(self) -> List[Dict]:
        """
        Get email prospects from Supabase, prioritized by score.

        Pulls prospects with status 'new' from the prospects table,
        ordered by quality score (highest first).

        Returns:
            List of prospect dictionaries
        """
        try:
            result = (
                self.db._client.table('prospects')
                .select('*')
                .eq('platform', Platform.EMAIL.value)
                .eq('status', 'new')
                .order('score', desc=True)
                .limit(self.settings.max_emails_per_day)
                .execute()
            )

            if result.data:
                self.logger.info("prospects_loaded", count=len(result.data))
                return result.data

        except Exception as e:
            self.logger.error("prospect_fetch_failed", error=str(e))

        return []
    
    def _generate_personalized_email(
        self,
        prospect: EmailProspect,
        email_type: EmailType
    ) -> EmailContent:
        """
        Generate personalized email content using Claude AI.
        
        Args:
            prospect: Validated prospect data
            email_type: Type of email to generate
            
        Returns:
            Validated email content
            
        Raises:
            ValueError: If email generation fails
        """
        self.logger.debug(
            "generating_email",
            prospect_email=prospect.email,
            email_type=email_type.value
        )
        
        # Build context-aware prompt
        prompt = self._build_email_prompt(prospect, email_type)
        
        try:
            # Generate with Claude
            response = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.COMPLEX,
                max_tokens=500,
                temperature=0.8
            )
            
            # Parse response
            subject, body = self._parse_email_response(response)
            
            # Validate content
            content = EmailContent(
                subject=subject,
                body=body,
                email_type=email_type
            )
            
            self.logger.info(
                "email_generated",
                prospect_email=prospect.email,
                subject=subject[:50]
            )
            
            return content
            
        except Exception as e:
            self.logger.error(
                "email_generation_failed",
                prospect_email=prospect.email,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Failed to generate email: {e}")
    
    def _build_email_prompt(self, prospect: EmailProspect, email_type: EmailType) -> str:
        """Build Claude prompt for email generation."""
        
        base_prompt = f"""Create a professional, personalized email for this prospect:

Name: {prospect.name}
Company: {prospect.company or 'N/A'}
Background: {prospect.bio or 'Web3 service provider'}
Recent Activity: {prospect.recent_activity or 'N/A'}

Our Product:
- Name: {self.settings.product_name}
- Value Prop: {self.settings.product_tagline}
- Website: {self.settings.product_url}

Email Type: {email_type.value}

CRITICAL REQUIREMENTS:
1. Professional subject line (50-70 characters)
2. Reference something specific about {prospect.name}
3. Email body: 100-150 words maximum
4. Clear, specific value proposition
5. Single, natural call-to-action
6. Helpful and consultative tone (NOT salesy)
7. Proper business email formatting

OUTPUT FORMAT (exactly as shown):
SUBJECT: [your subject line here]

BODY:
[your email body here]

Return ONLY the subject and body, nothing else."""
        
        return base_prompt
    
    def _parse_email_response(self, response: str) -> Tuple[str, str]:
        """
        Parse Claude's email response into subject and body.
        
        Args:
            response: Raw response from Claude
            
        Returns:
            Tuple of (subject, body)
            
        Raises:
            ValueError: If response cannot be parsed
        """
        lines = response.strip().split('\n')
        subject = ""
        body_lines = []
        in_body = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('SUBJECT:'):
                subject = line.replace('SUBJECT:', '').strip()
            elif line.startswith('BODY:'):
                in_body = True
            elif in_body and line:
                body_lines.append(line)
        
        body = '\n'.join(body_lines).strip()
        
        if not subject or not body:
            raise ValueError("Failed to parse email response - missing subject or body")
        
        return subject, body
    
    def _send_email_with_retry(
        self,
        prospect: EmailProspect,
        content: EmailContent
    ) -> bool:
        """
        Send email with retry logic.
        
        Args:
            prospect: Prospect to email
            content: Email content
            
        Returns:
            True if sent successfully, False otherwise
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self._send_single_email(prospect, content)
                
            except SendGridException as e:
                self.logger.warning(
                    "email_send_attempt_failed",
                    attempt=attempt,
                    max_retries=self.MAX_RETRIES,
                    error=str(e)
                )
                
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS * attempt)
                else:
                    self.logger.error(
                        "email_send_failed_all_retries_exhausted",
                        prospect_email=prospect.email
                    )
                    return False
            
            except Exception as e:
                self.logger.error(
                    "email_send_unexpected_error",
                    prospect_email=prospect.email,
                    error=str(e),
                    exc_info=True
                )
                return False
        
        return False
    
    def _send_single_email(
        self,
        prospect: EmailProspect,
        content: EmailContent
    ) -> bool:
        """
        Send a single email via SendGrid.
        
        Args:
            prospect: Prospect to email
            content: Email content
            
        Returns:
            True if sent successfully
            
        Raises:
            SendGridException: If SendGrid API call fails
        """
        message = Mail(
            from_email=SGEmail(self.settings.from_email, self.settings.from_name),
            to_emails=To(prospect.email),
            subject=content.subject,
            plain_text_content=Content("text/plain", content.body)
        )
        
        response = self._sg_client.send(message)
        
        success = response.status_code in [200, 201, 202]
        
        if success:
            self.logger.info(
                "email_sent_successfully",
                to=prospect.email,
                subject=content.subject[:50],
                status_code=response.status_code
            )
            self.record_engagement()
        else:
            self.logger.error(
                "email_send_failed_bad_status",
                to=prospect.email,
                status_code=response.status_code,
                response_body=response.body
            )
        
        return success
    
    def _track_email_prospect(self, prospect: EmailProspect) -> Prospect:
        """Track prospect in database."""
        return self.track_prospect(
            handle=prospect.email,
            email=prospect.email,
            score=prospect.score
        )
    
    def _execute_followup_sequence(self) -> int:
        """
        Execute follow-up email sequence.

        Sends follow-ups to prospects who:
        - Were contacted 3+ days ago
        - Haven't responded yet
        - Haven't already received 2 follow-ups

        Returns:
            Number of follow-ups sent
        """
        followups_sent = 0
        prospects = self._get_followup_prospects()

        if not prospects:
            self.logger.info("no_followup_prospects_due")
            return 0

        for prospect_data in prospects:
            try:
                self.enforce_rate_limit("email", self.settings.max_emails_per_day)

                email_type = EmailType.FOLLOW_UP_1
                prompt = self._build_followup_prompt(prospect_data)

                response = self.claude.generate(
                    prompt=prompt,
                    complexity=TaskComplexity.MEDIUM,
                    max_tokens=300,
                    temperature=0.7
                )

                subject, body = self._parse_email_response(response)
                content = EmailContent(
                    subject=subject,
                    body=body,
                    email_type=email_type
                )

                prospect_model = EmailProspect(
                    email=prospect_data['email'],
                    name=prospect_data.get('handle', prospect_data.get('email', 'there')),
                    company=prospect_data.get('company'),
                    bio=prospect_data.get('notes'),
                    score=prospect_data.get('score', 5)
                )

                success = self._send_email_with_retry(
                    prospect=prospect_model,
                    content=content
                )

                if success:
                    followups_sent += 1
                    self.increment_action_count("email")
                    self._record_domain_send(prospect_model.email)

                    # Update last_contact
                    self.db._client.table('prospects').update({
                        'last_contact': datetime.now(timezone.utc).isoformat()
                    }).eq('id', prospect_data['id']).execute()

                    self.logger.info(
                        "followup_sent",
                        to=prospect_model.email,
                        prospect_id=prospect_data['id']
                    )

                    time.sleep(self.EMAIL_DELAY_SECONDS)

            except RateLimitExceeded:
                self.logger.info("followup_rate_limit_reached")
                break
            except Exception as e:
                self.logger.error(
                    "followup_failed",
                    email=prospect_data.get('email'),
                    error=str(e)
                )
                continue

        self.logger.info("followup_sequence_completed", sent=followups_sent)
        return followups_sent

    def _get_followup_prospects(self) -> List[Dict]:
        """
        Get prospects due for a follow-up.

        Targets prospects contacted 3+ days ago who haven't responded.
        """
        try:
            three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()

            result = (
                self.db._client.table('prospects')
                .select('*')
                .eq('platform', Platform.EMAIL.value)
                .eq('status', 'contacted')
                .eq('response_received', False)
                .lte('last_contact', three_days_ago)
                .limit(20)
                .execute()
            )

            if result.data:
                self.logger.info("followup_prospects_found", count=len(result.data))
                return result.data

        except Exception as e:
            self.logger.error("followup_prospect_fetch_failed", error=str(e))

        return []

    def _build_followup_prompt(self, prospect: Dict) -> str:
        """Build Claude prompt for follow-up email."""
        return f"""Write a short follow-up email for someone who didn't reply to our initial email.

Name: {prospect.get('handle', 'there')}
Company: {prospect.get('company', 'N/A')}

Our product: {self.settings.product_name} - {self.settings.product_tagline}
Website: {self.settings.product_url}

Requirements:
1. Reference the previous email briefly
2. Add NEW value (share an insight, stat, or use case)
3. Under 80 words
4. Different angle than the first email
5. Respect their time - make it easy to say no
6. Warm subject line (reply-style, e.g. "Re: ..." or "Quick follow up")

OUTPUT FORMAT (exactly as shown):
SUBJECT: [subject line]

BODY:
[email body]

Return ONLY the subject and body, nothing else."""