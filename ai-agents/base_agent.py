"""Base Agent Class - Foundation for All Social Media Agents."""

from abc import ABC, abstractmethod
from datetime import date

from database import get_db, Platform, Prospect, ProspectStatus, DailyMetrics
from claude_client import get_claude, ClaudeClient
from config import get_settings
from logging_config import LoggerMixin


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class BaseAgent(ABC, LoggerMixin):
    """Abstract base class for all social media agents."""
    
    def __init__(self, platform: Platform) -> None:
        """Initialize base agent."""
        self.platform = platform
        self.settings = get_settings()
        self.db = get_db()
        self.claude: ClaudeClient = get_claude()
        
        # Metrics for current day
        self._daily_impressions = 0
        self._daily_engagements = 0
        self._daily_conversations = 0
        self._daily_signups = 0
        
        # Track actions for rate limiting
        self._actions_today: dict[str, int] = {}
        
        self.logger.info("agent_initialized", platform=self.platform.value)
    
    @abstractmethod
    def get_name(self) -> str:
        """Get agent name."""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Execute agent's main tasks."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if agent is healthy."""
        pass
    
    def check_rate_limit(self, action_type: str, limit: int) -> bool:
        """Check if action would exceed rate limit."""
        today = date.today()
        key = f"{self.platform.value}:{action_type}:{today}"
        current_count = self._actions_today.get(key, 0)
        
        if current_count >= limit:
            self.logger.warning("rate_limit_exceeded", action_type=action_type, limit=limit)
            return True
        return False
    
    def increment_action_count(self, action_type: str) -> int:
        """Increment action counter."""
        today = date.today()
        key = f"{self.platform.value}:{action_type}:{today}"
        current_count = self._actions_today.get(key, 0)
        new_count = current_count + 1
        self._actions_today[key] = new_count
        return new_count
    
    def enforce_rate_limit(self, action_type: str, limit: int) -> None:
        """Enforce rate limit for an action."""
        if self.check_rate_limit(action_type, limit):
            raise RateLimitExceeded(f"Rate limit exceeded for {action_type}: {limit}/day")
    
    def track_prospect(self, handle: str, email: str | None = None, score: int = 5) -> Prospect:
        """Create or update prospect in database."""
        existing = self.db.find_prospect_by_handle(self.platform, handle)
        
        if existing:
            return existing
        
        prospect = Prospect(
            platform=self.platform,
            handle=handle,
            email=email,
            score=score,
            status=ProspectStatus.NEW
        )
        
        created = self.db.create_prospect(prospect)
        self.logger.info("prospect_tracked", prospect_id=created.id, handle=handle)
        return created
    
    def mark_contacted(self, prospect_id: int) -> bool:
        """Mark prospect as contacted."""
        success = self.db.update_prospect_status(prospect_id, ProspectStatus.CONTACTED)
        if success:
            self.logger.info("prospect_contacted", prospect_id=prospect_id)
        return success
    
    def mark_responded(self, prospect_id: int) -> bool:
        """Mark prospect as responded."""
        success = self.db.update_prospect_status(prospect_id, ProspectStatus.RESPONDED)
        if success:
            self._daily_conversations += 1
            self.logger.info("prospect_responded", prospect_id=prospect_id)
        return success
    
    def mark_converted(self, prospect_id: int) -> bool:
        """Mark prospect as converted (signed up)."""
        success = self.db.update_prospect_status(prospect_id, ProspectStatus.CONVERTED)
        if success:
            self._daily_signups += 1
            self.logger.info("prospect_converted", prospect_id=prospect_id)
        return success
    
    def record_impression(self, count: int = 1) -> None:
        """Record impressions (views/reach)."""
        self._daily_impressions += count
    
    def record_engagement(self, count: int = 1) -> None:
        """Record engagement (likes, replies, clicks)."""
        self._daily_engagements += count
    
    def save_daily_metrics(self) -> DailyMetrics:
        """Save accumulated metrics to database."""
        metrics = DailyMetrics(
            date=date.today(),
            platform=self.platform,
            impressions=self._daily_impressions,
            engagements=self._daily_engagements,
            conversations=self._daily_conversations,
            signups=self._daily_signups
        )
        
        saved = self.db.record_metrics(metrics)
        self.logger.info("daily_metrics_saved", platform=self.platform.value)
        
        # Reset counters
        self._daily_impressions = 0
        self._daily_engagements = 0
        self._daily_conversations = 0
        self._daily_signups = 0
        
        return saved
    
    def get_daily_summary(self) -> dict[str, int]:
        """Get summary of today's activity."""
        return {
            'impressions': self._daily_impressions,
            'engagements': self._daily_engagements,
            'conversations': self._daily_conversations,
            'signups': self._daily_signups
        }
    
    def safe_execute(self, func, *args, **kwargs):
        """Execute function with error handling."""
        try:
            return func(*args, **kwargs)
        except RateLimitExceeded as e:
            self.logger.warning("rate_limit_hit", error=str(e))
            return None
        except Exception as e:
            self.logger.error("execution_error", function=func.__name__, error=str(e))
            return None