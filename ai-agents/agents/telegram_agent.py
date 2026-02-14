"""
Telegram Agent - Crypto Group Engagement for RepEscrow Signups.

Monitors 20+ Solana/crypto Telegram groups for conversations about:
- Escrow, payments, trust between vendors and buyers
- Freelancers getting scammed or ghosted
- People looking to hire Web3 devs/artists
- Complaints about Upwork/Fiverr fees

When a relevant message is detected, the bot:
1. Classifies intent (high_intent / pain_point / general)
2. Claude decides if a reply is warranted
3. Generates a helpful reply with FairScore pitch when relevant
4. Tracks prospect in Supabase

Goal: 2-3 signups/week from Telegram engagement.
Rate limit: 25 messages/day (from .env).
"""

import time
import asyncio
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Optional

from telegram import Update, Message
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, RateLimitExceeded
from database import Platform, Conversation
from claude_client import TaskComplexity


# ---------------------------------------------------------------------------
# Target groups (bot must be added to these)
# ---------------------------------------------------------------------------
TARGET_GROUPS = [
    'Solana',
    'Solana Trading',
    'Solana Floor',
    'Magic Eden',
    'Tensor Trade',
    'Jupiter Exchange',
    'Marinade Finance',
    'Raydium',
    'Orca DEX',
    'Superteam',
    'MonkeDAO',
    'DeGods',
    'Helius',
    'Metaplex',
    'DRiP',
    'Solana Developers',
    'Solana NFT',
    'Web3 Jobs',
    'Crypto Freelancers',
    'DAO Jobs',
]

# ---------------------------------------------------------------------------
# Keywords (same 3-tier system as Discord agent)
# ---------------------------------------------------------------------------
HIGH_INTENT_KEYWORDS = [
    'looking for escrow', 'need escrow', 'escrow service',
    'how do i pay safely', 'safe way to pay', 'looking for developer',
    'looking for dev', 'hiring solana', 'need a developer',
    'want to hire', 'who can build', 'budget for',
    'how to protect payment', 'safe transaction',
    'need smart contract dev', 'solana developer needed',
]

PAIN_KEYWORDS = [
    'got scammed', 'scammed me', 'rug pull', 'rugged',
    'never delivered', 'didn\'t deliver', 'took my money',
    'ripped off', 'lost money', 'no refund', 'ghosted me',
    'ran away with', 'stole', 'fraud', 'fake dev',
    'upwork fees', 'fiverr takes', 'platform fees',
    '20% fee', '20 percent', 'high fees',
]

GENERAL_KEYWORDS = [
    'escrow', 'reputation', 'trust', 'trustworthy', 'vouch',
    'freelance', 'freelancer', 'commission', 'gig',
    'payment', 'milestone', 'dispute', 'middleman',
    'smart contract', 'on-chain', 'solana dev',
    'web3 work', 'web3 jobs', 'contractor',
]

# RepEscrow product context for Claude prompts
PRODUCT_CONTEXT = """
ABOUT REPESCROW:
RepEscrow is a reputation-weighted escrow platform on Solana.

CORE IDEA: Your FairScore (on-chain reputation from FairScale) determines your escrow fees.
- FairScore 4.5-5.0 → 0.5% fee, instant payment release
- FairScore 3.5-4.4 → 1.0% fee, 24hr hold
- FairScore 2.5-3.4 → 1.5% fee, 72hr hold
- FairScore 1.5-2.4 → 2.0% fee, 7-day hold
- FairScore <1.5    → 2.5% fee, 14-day hold

WHY IT MATTERS:
- Upwork charges 20% regardless of your track record
- Traditional escrow charges flat 2-3% for everyone
- RepEscrow rewards good reputation with lower fees
- Built on Solana = fast, cheap transactions
- Milestone payments, dispute resolution built in

Website: repescrow.xyz
"""


class TelegramAgent(BaseAgent):
    """
    Monitors crypto Telegram groups and drives RepEscrow signups.

    Strategy:
    - Be genuinely helpful first (answer their question)
    - Mention RepEscrow + FairScore only when directly relevant
    - Never spam, never hard sell
    - Focus on pain points: fees, scams, trust

    Rate Limits:
        - 25 messages/day global (from .env)
        - 3 messages/group/day (avoid looking spammy)
        - 90 second cooldown between messages
    """

    MAX_PER_GROUP_PER_DAY: int = 3
    MESSAGE_COOLDOWN_SECONDS: int = 90
    MAX_MESSAGE_LENGTH: int = 4096  # Telegram limit

    def __init__(self) -> None:
        """Initialize Telegram agent."""
        super().__init__(platform=Platform.TELEGRAM)

        self._app: Optional[Application] = None
        self._group_message_counts: Dict[int, int] = {}
        self._last_message_time: Optional[datetime] = None
        self._replied_message_ids: set = set()

        self._initialize_bot()

    def _initialize_bot(self) -> None:
        """Initialize Telegram bot application."""
        try:
            if not self.settings.telegram_bot_token:
                self.logger.warning("telegram_bot_token_not_configured")
                return

            self._app = (
                Application.builder()
                .token(self.settings.telegram_bot_token)
                .build()
            )

            # Register handler for all text messages in groups
            self._app.add_handler(
                MessageHandler(
                    filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
                    self._on_group_message
                )
            )

            self.logger.info("telegram_bot_initialized")

        except Exception as e:
            self.logger.error("telegram_bot_init_failed", error=str(e))
            self._app = None

    def get_name(self) -> str:
        """Get agent name."""
        return "TelegramAgent"

    def health_check(self) -> bool:
        """Check if Telegram bot is operational."""
        return self._app is not None

    def run(self) -> None:
        """
        Start the bot (blocks forever, monitors in real-time).

        The orchestrator runs this in a separate thread/process.
        """
        self.logger.info(
            "telegram_agent_starting",
            date=str(date.today()),
            target_groups=len(TARGET_GROUPS)
        )

        if not self.health_check():
            self.logger.error("telegram_agent_not_healthy")
            return

        try:
            self._app.run_polling(drop_pending_updates=True)
        except Exception as e:
            self.logger.error("telegram_agent_run_failed", error=str(e))

    # -------------------------------------------------------------------------
    # Message Handler
    # -------------------------------------------------------------------------

    async def _on_group_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Called for every text message in groups the bot is in.

        Filters → classifies → decides → generates → sends → tracks.
        """
        message = update.effective_message
        if not message or not message.text:
            return

        # Skip bot messages
        if message.from_user and message.from_user.is_bot:
            return

        # Skip if not relevant
        if not self._is_relevant(message.text):
            return

        # Skip already replied
        if message.message_id in self._replied_message_ids:
            return

        try:
            # Rate limit checks
            if self.check_rate_limit("message", self.settings.max_telegram_messages_per_day):
                return

            chat_id = message.chat_id
            if self._group_message_counts.get(chat_id, 0) >= self.MAX_PER_GROUP_PER_DAY:
                return

            if not self._check_cooldown():
                return

            # Classify and decide
            intent = self._classify_intent(message.text)
            should_reply = await self._should_engage(message, intent, context)
            if not should_reply:
                return

            # Generate and send
            reply_text = self._generate_reply(message, intent)
            if not reply_text:
                return

            await self._send_reply(message, reply_text, intent, context)

        except Exception as e:
            self.logger.error(
                "telegram_message_handler_failed",
                error=str(e),
                chat=message.chat.title if message.chat else "unknown"
            )

    # -------------------------------------------------------------------------
    # Filtering & Classification
    # -------------------------------------------------------------------------

    def _is_relevant(self, text: str) -> bool:
        """Fast keyword check on message text."""
        if len(text) < 15:
            return False

        text_lower = text.lower()
        all_keywords = HIGH_INTENT_KEYWORDS + PAIN_KEYWORDS + GENERAL_KEYWORDS
        return any(kw in text_lower for kw in all_keywords)

    def _classify_intent(self, text: str) -> str:
        """Classify as 'high_intent', 'pain_point', or 'general'."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in HIGH_INTENT_KEYWORDS):
            return 'high_intent'
        if any(kw in text_lower for kw in PAIN_KEYWORDS):
            return 'pain_point'
        return 'general'

    def _check_cooldown(self) -> bool:
        """Enforce minimum gap between our messages."""
        if self._last_message_time is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_message_time).total_seconds()
        return elapsed >= self.MESSAGE_COOLDOWN_SECONDS

    # -------------------------------------------------------------------------
    # Claude: Should We Engage?
    # -------------------------------------------------------------------------

    async def _should_engage(
        self,
        message: Message,
        intent: str,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Ask Claude if we should reply. High-intent skips this check.
        """
        if intent == 'high_intent':
            self.logger.info(
                "auto_engage_high_intent",
                user=message.from_user.username if message.from_user else "unknown"
            )
            return True

        # Get reply context if this is a reply to another message
        reply_context = ""
        if message.reply_to_message and message.reply_to_message.text:
            reply_context = f"(replying to: \"{message.reply_to_message.text[:200]}\")"

        author = message.from_user.first_name if message.from_user else "Someone"
        group_name = message.chat.title if message.chat else "Unknown Group"

        prompt = f"""Should we reply to this Telegram message? Answer YES or NO with a brief reason.

GROUP: {group_name}
AUTHOR: {author}
MESSAGE: "{message.text}"
{reply_context}

{PRODUCT_CONTEXT}

DECISION CRITERIA:
1. Is this person dealing with a trust/payment/escrow problem we can help with?
2. Would our reply feel natural (not promotional)?
3. Is this a real concern (not sarcasm or memes)?
4. Would mentioning reputation-based fees be relevant?

Reply: YES or NO + one sentence reason."""

        response = self.claude.generate(
            prompt=prompt,
            complexity=TaskComplexity.SIMPLE,
            max_tokens=80,
            temperature=0.2
        )

        return response.strip().upper().startswith('YES')

    # -------------------------------------------------------------------------
    # Claude: Generate Reply
    # -------------------------------------------------------------------------

    def _generate_reply(self, message: Message, intent: str) -> Optional[str]:
        """Generate a contextual reply using Claude."""
        author = message.from_user.first_name if message.from_user else "Someone"
        group_name = message.chat.title if message.chat else "Unknown Group"

        # Reply context
        reply_context = ""
        if message.reply_to_message and message.reply_to_message.text:
            reply_context = f"\nTHEY WERE REPLYING TO: \"{message.reply_to_message.text[:200]}\""

        # Tone based on intent
        if intent == 'pain_point':
            tone = """TONE: This person got burned. Lead with empathy.
Acknowledge what happened. Then offer practical advice.
Only mention RepEscrow if escrow would have prevented their problem."""

        elif intent == 'high_intent':
            tone = """TONE: This person is actively looking for a solution.
Be direct and helpful. Explain how FairScore-based fees work.
Give them a clear reason to check out repescrow.xyz."""

        else:
            tone = """TONE: Casual and helpful. General discussion.
Add value first. Only mention RepEscrow if it naturally fits."""

        prompt = f"""Write a Telegram reply to this message.

GROUP: {group_name}
AUTHOR: {author}
MESSAGE: "{message.text}"
{reply_context}

{PRODUCT_CONTEXT}

{tone}

RULES:
1. Be genuinely helpful FIRST — answer their actual question
2. Max 120 words (Telegram users skim fast)
3. Casual tone — crypto/web3 community style
4. DON'T start with "Hey!" or filler phrases
5. If mentioning RepEscrow, briefly explain FairScore fee tiers
6. Include repescrow.xyz ONLY if you mention the product
7. If someone got scammed: empathy first, solution second
8. Never say "I'm a bot" or "as an AI"
9. Sound like a knowledgeable community member
10. Use short paragraphs, not walls of text

Return ONLY the reply text."""

        try:
            reply = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.COMPLEX,
                max_tokens=300,
                temperature=0.8
            )

            reply = reply.strip()
            if len(reply) > self.MAX_MESSAGE_LENGTH:
                reply = reply[:self.MAX_MESSAGE_LENGTH - 3] + "..."

            return reply

        except Exception as e:
            self.logger.error("telegram_reply_generation_failed", error=str(e))
            return None

    # -------------------------------------------------------------------------
    # Send & Track
    # -------------------------------------------------------------------------

    async def _send_reply(
        self,
        message: Message,
        reply_text: str,
        intent: str,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Send reply, update rate limits, track prospect in Supabase."""
        try:
            await message.reply_text(
                reply_text,
                quote=True  # Quote the original message
            )

            # Update rate tracking
            self._last_message_time = datetime.now(timezone.utc)
            self._replied_message_ids.add(message.message_id)
            self.increment_action_count("message")
            self.record_engagement()

            chat_id = message.chat_id
            self._group_message_counts[chat_id] = (
                self._group_message_counts.get(chat_id, 0) + 1
            )

            # Track prospect in Supabase
            username = message.from_user.username if message.from_user else None
            display_name = message.from_user.first_name if message.from_user else "unknown"
            handle = f"@{username}" if username else display_name
            score = self._score_prospect(message.text, intent)

            prospect = self.track_prospect(
                handle=handle,
                score=score
            )

            # Log conversation
            self.db.create_conversation(Conversation(
                prospect_id=prospect.id,
                platform=Platform.TELEGRAM,
                message=message.text[:500],
                response=reply_text[:500]
            ))

            self.logger.info(
                "telegram_reply_sent",
                group=message.chat.title if message.chat else "unknown",
                author=handle,
                intent=intent,
                score=score,
                reply_length=len(reply_text)
            )

            return True

        except Exception as e:
            self.logger.error(
                "telegram_reply_failed",
                error=str(e),
                group=message.chat.title if message.chat else "unknown"
            )
            return False

    # -------------------------------------------------------------------------
    # Prospect Scoring
    # -------------------------------------------------------------------------

    def _score_prospect(self, text: str, intent: str) -> int:
        """
        Score prospect 1-10 based on intent and message signals.

        Scoring:
        - Base: 5
        - high_intent: +3
        - pain_point: +2
        - Detailed message (100+ chars): +1
        - Mentions budget/price: +1
        """
        score = 5

        if intent == 'high_intent':
            score += 3
        elif intent == 'pain_point':
            score += 2

        if len(text) > 100:
            score += 1

        text_lower = text.lower()
        if any(kw in text_lower for kw in ['budget', 'price', 'cost', 'pay', '$', 'usdc', 'sol']):
            score += 1

        return min(score, 10)
