"""Database Layer - Supabase Client with Type Safety."""

from typing import Any
from datetime import datetime, date
from enum import Enum

from supabase import create_client, Client
from pydantic import BaseModel, Field

from config import get_settings
from logging_config import get_logger

logger = get_logger(__name__)


class Platform(str, Enum):
    """Social media platforms."""
    REDDIT = "reddit"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    EMAIL = "email"
    TWITTER = "twitter"
    FORUM = "forum"


class ProspectStatus(str, Enum):
    """Prospect status in the funnel."""
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"
    REJECTED = "rejected"


class Prospect(BaseModel):
    """Prospect/lead model."""
    id: int | None = None
    platform: Platform
    handle: str = Field(..., min_length=1, max_length=255)
    email: str | None = Field(None, max_length=255)
    score: int = Field(default=5, ge=1, le=10)
    status: ProspectStatus = ProspectStatus.NEW
    first_contact: datetime | None = None
    last_contact: datetime | None = None
    response_received: bool = False
    converted: bool = False
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class Conversation(BaseModel):
    """Conversation/interaction model."""
    id: int | None = None
    prospect_id: int
    platform: Platform
    message: str
    response: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class DailyMetrics(BaseModel):
    """Daily performance metrics."""
    id: int | None = None
    date: date = Field(default_factory=date.today)
    platform: Platform
    impressions: int = 0
    engagements: int = 0
    conversations: int = 0
    signups: int = 0
    
    class Config:
        use_enum_values = True


class DatabaseClient:
    """Type-safe database client for Supabase."""
    
    def __init__(self) -> None:
        """Initialize database client."""
        settings = get_settings()
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        logger.info("database_client_initialized")
    
    def create_prospect(self, prospect: Prospect) -> Prospect:
        """Create a new prospect."""
        try:
            data = prospect.model_dump(exclude={'id'}, exclude_none=True)
            result = self._client.table('prospects').insert(data).execute()
            
            if not result.data:
                raise Exception("Failed to create prospect")
            
            created = Prospect(**result.data[0])
            logger.info("prospect_created", prospect_id=created.id, platform=created.platform)
            return created
            
        except Exception as e:
            logger.error("prospect_creation_failed", error=str(e))
            raise
    
    def find_prospect_by_handle(self, platform: Platform, handle: str) -> Prospect | None:
        """Find prospect by platform and handle."""
        try:
            result = (
                self._client.table('prospects')
                .select('*')
                .eq('platform', platform.value)
                .eq('handle', handle)
                .execute()
            )
            if result.data:
                return Prospect(**result.data[0])
            return None
        except Exception as e:
            logger.error("prospect_lookup_failed", error=str(e))
            return None
    
    def update_prospect_status(self, prospect_id: int, status: ProspectStatus) -> bool:
        """Update prospect status."""
        try:
            result = (
                self._client.table('prospects')
                .update({'status': status.value})
                .eq('id', prospect_id)
                .execute()
            )
            success = bool(result.data)
            if success:
                logger.info("prospect_status_updated", prospect_id=prospect_id, new_status=status.value)
            return success
        except Exception as e:
            logger.error("prospect_status_update_failed", error=str(e))
            return False
    
    def create_conversation(self, conversation: Conversation) -> Conversation:
        """Log a conversation."""
        try:
            data = conversation.model_dump(exclude={'id'}, exclude_none=True)
            result = self._client.table('conversations').insert(data).execute()
            
            if not result.data:
                raise Exception("Failed to create conversation")
            
            created = Conversation(**result.data[0])
            logger.info("conversation_logged", conversation_id=created.id)
            return created
        except Exception as e:
            logger.error("conversation_logging_failed", error=str(e))
            raise
    
    def record_metrics(self, metrics: DailyMetrics) -> DailyMetrics:
        """Record daily metrics."""
        try:
            data = metrics.model_dump(exclude={'id'}, exclude_none=True)
            result = self._client.table('metrics').insert(data).execute()
            
            if not result.data:
                raise Exception("Failed to record metrics")
            
            created = DailyMetrics(**result.data[0])
            logger.info("metrics_recorded", date=str(created.date), platform=created.platform)
            return created
        except Exception as e:
            logger.error("metrics_recording_failed", error=str(e))
            raise
    
    def get_total_signups(self, start_date: date | None = None) -> int:
        """Get total signups across all platforms."""
        try:
            query = self._client.table('metrics').select('signups')
            if start_date:
                query = query.gte('date', str(start_date))
            result = query.execute()
            return sum(m['signups'] for m in result.data)
        except Exception as e:
            logger.error("total_signups_fetch_failed", error=str(e))
            return 0


_db_client: DatabaseClient | None = None


def get_db() -> DatabaseClient:
    """Get database client (singleton)."""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client