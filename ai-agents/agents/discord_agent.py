"""
Discord Agent - Web3 Server Engagement for RepEscrow Signups.

Monitors 15+ Solana/Web3 Discord servers for conversations about:
- Escrow, payments, trust issues between vendors and buyers
- Freelancers getting scammed or not getting paid
- People looking to hire Web3 developers/artists
- Discussions about platform fees (Upwork 20%, etc.)

When a relevant conversation is detected, the agent:
1. Analyzes context with Claude (is this worth replying to?)
2. Generates a genuinely helpful reply
3. Mentions RepEscrow's FairScore-based fee system ONLY when relevant
4. Tracks the prospect in Supabase for follow-up

Goal: 1-2 signups/week from Discord engagement.
"""

import asyncio
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Optional

import discord
from discord.ext import commands

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, RateLimitExceeded
from database import Platform, Conversation
from claude_client import TaskComplexity


# ---------------------------------------------------------------------------
# Target servers (bot must be invited to these)
# ---------------------------------------------------------------------------
TARGET_SERVERS = [
    'Solana',
    'Magic Eden',
    'Phantom',
    'Metaplex',
    'Orca',
    'Raydium',
    'Star Atlas',
    'Audius',
    'Marinade Finance',
    'Tensor',
    'Jupiter Exchange',
    'Helius',
    'Superteam',
    'MonkeDAO',
    'DeGods',
]

# ---------------------------------------------------------------------------
# Keywords that signal someone needs escrow / has trust issues
# ---------------------------------------------------------------------------
# High intent — person is actively looking for a solution
HIGH_INTENT_KEYWORDS = [
    'looking for escrow', 'need escrow', 'escrow service',
    'how do i pay', 'safe way to pay', 'looking for developer',
    'looking for dev', 'hiring solana', 'need a developer',
    'want to hire', 'who can build', 'budget for',
    'how to protect', 'safe transaction',
]

# Pain point — person experienced or fears getting scammed
PAIN_KEYWORDS = [
    'got scammed', 'scammed me', 'rug pull', 'rugged',
    'never delivered', 'didn\'t deliver', 'took my money',
    'ripped off', 'lost money', 'no refund', 'ghosted me',
    'ran away with', 'stole', 'fraud',
    'upwork fees', 'fiverr takes', 'platform fees',
    '20% fee', '20 percent',
]

# General relevance — worth monitoring but lower priority
GENERAL_KEYWORDS = [
    'escrow', 'reputation', 'trust', 'trustworthy', 'vouch',
    'freelance', 'freelancer', 'commission', 'gig',
    'payment', 'milestone', 'dispute', 'middleman',
    'smart contract', 'on-chain', 'solana dev',
    'web3 work', 'web3 jobs', 'contractor',
]

# Channels worth monitoring (by name substring)
PRIORITY_CHANNELS = [
    'general', 'chat', 'discussion', 'lounge',
    'jobs', 'hiring', 'freelance', 'gigs', 'work', 'bounties',
    'help', 'support', 'questions', 'ask',
    'marketplace', 'services', 'commissions', 'trading',
    'dev', 'developer', 'building', 'solana',
]

# RepEscrow product context injected into every Claude prompt
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


class DiscordAgent(BaseAgent):
    """
    Monitors Web3 Discord servers and drives RepEscrow signups.

    Engagement strategy:
    - Be genuinely helpful FIRST (answer their question)
    - Mention RepEscrow only when directly relevant to their problem
    - Never hard sell, never spam
    - Focus on the FairScore → lower fees angle

    Rate Limits:
        - 30 messages/day global (from .env)
        - 5 messages/server/day (avoid looking spammy)
        - 2 min cooldown between messages
    """

    MAX_PER_SERVER_PER_DAY: int = 5
    MESSAGE_COOLDOWN_SECONDS: int = 120
    MAX_MESSAGE_LENGTH: int = 2000

    def __init__(self) -> None:
        """Initialize Discord agent."""
        super().__init__(platform=Platform.DISCORD)

        self._bot: Optional[commands.Bot] = None
        self._server_message_counts: Dict[int, int] = {}
        self._last_message_time: Optional[datetime] = None
        self._replied_message_ids: set = set()

        self._initialize_bot()

    def _initialize_bot(self) -> None:
        """Initialize Discord bot with required intents."""
        try:
            if not self.settings.discord_bot_token:
                self.logger.warning("discord_bot_token_not_configured")
                return

            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.members = True

            self._bot = commands.Bot(
                command_prefix='!rep ',
                intents=intents,
                help_command=None
            )

            self._register_event_handlers()
            self.logger.info("discord_bot_initialized")

        except Exception as e:
            self.logger.error("discord_bot_init_failed", error=str(e))
            self._bot = None

    def _register_event_handlers(self) -> None:
        """Register Discord event handlers."""

        @self._bot.event
        async def on_ready():
            server_names = [g.name for g in self._bot.guilds]
            self.logger.info(
                "discord_bot_connected",
                username=str(self._bot.user),
                guild_count=len(self._bot.guilds),
                servers=server_names
            )

        @self._bot.event
        async def on_message(message: discord.Message):
            if message.author == self._bot.user:
                return
            if message.author.bot:
                return
            if not message.guild:
                return

            if self._is_relevant_message(message):
                await self._handle_relevant_message(message)

    def get_name(self) -> str:
        """Get agent name."""
        return "DiscordAgent"

    def health_check(self) -> bool:
        """Check if Discord bot is operational."""
        return self._bot is not None

    def run(self) -> None:
        """
        Start the bot (blocks forever, monitors in real-time).

        The orchestrator runs this in a separate thread/process.
        """
        self.logger.info(
            "discord_agent_starting",
            date=str(date.today()),
            target_servers=len(TARGET_SERVERS)
        )

        if not self.health_check():
            self.logger.error("discord_agent_not_healthy")
            return

        try:
            self._bot.run(self.settings.discord_bot_token)
        except Exception as e:
            self.logger.error("discord_agent_run_failed", error=str(e))

    def run_scan(self) -> None:
        """
        One-shot scan of recent messages (for orchestrator scheduling).

        Does NOT block. Scans the last hour of messages in priority channels.
        """
        self.logger.info("discord_scan_starting")

        if not self.health_check():
            self.logger.error("discord_scan_not_healthy")
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._scan_servers())
            else:
                loop.run_until_complete(self._scan_servers())
        except Exception as e:
            self.logger.error("discord_scan_failed", error=str(e))

    # -------------------------------------------------------------------------
    # Message Filtering
    # -------------------------------------------------------------------------

    def _is_relevant_message(self, message: discord.Message) -> bool:
        """
        Fast keyword check — does this message warrant a Claude analysis?

        Returns True if the message contains any engagement keyword
        and passes basic filters.
        """
        # Already replied to this message
        if message.id in self._replied_message_ids:
            return False

        content_lower = message.content.lower()

        # Skip very short or link-only messages
        if len(message.content) < 15:
            return False
        if message.content.startswith('http') and ' ' not in message.content.strip():
            return False

        # Check all keyword lists
        all_keywords = HIGH_INTENT_KEYWORDS + PAIN_KEYWORDS + GENERAL_KEYWORDS
        return any(kw in content_lower for kw in all_keywords)

    def _classify_intent(self, message: discord.Message) -> str:
        """
        Classify the message intent for scoring and prompt tuning.

        Returns: 'high_intent', 'pain_point', or 'general'
        """
        content_lower = message.content.lower()

        if any(kw in content_lower for kw in HIGH_INTENT_KEYWORDS):
            return 'high_intent'
        if any(kw in content_lower for kw in PAIN_KEYWORDS):
            return 'pain_point'
        return 'general'

    # -------------------------------------------------------------------------
    # Engagement Pipeline
    # -------------------------------------------------------------------------

    async def _handle_relevant_message(self, message: discord.Message) -> None:
        """
        Full pipeline: rate check → Claude analysis → generate → send → track.
        """
        try:
            # Rate limit checks
            if self.check_rate_limit("message", self.settings.max_discord_messages_per_day):
                return

            guild_id = message.guild.id
            if self._server_message_counts.get(guild_id, 0) >= self.MAX_PER_SERVER_PER_DAY:
                return

            if not self._check_cooldown():
                return

            # Claude decides: should we reply?
            intent = self._classify_intent(message)
            should_reply = await self._should_engage(message, intent)
            if not should_reply:
                return

            # Generate reply
            reply = await self._generate_reply(message, intent)
            if not reply:
                return

            # Send and track
            await self._send_reply(message, reply)

        except Exception as e:
            self.logger.error(
                "handle_message_failed",
                error=str(e),
                guild=message.guild.name if message.guild else "DM"
            )

    def _check_cooldown(self) -> bool:
        """Enforce minimum gap between our messages."""
        if self._last_message_time is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_message_time).total_seconds()
        return elapsed >= self.MESSAGE_COOLDOWN_SECONDS

    async def _get_channel_context(self, message: discord.Message, limit: int = 5) -> str:
        """Fetch recent messages before the target message for context."""
        context_messages = []
        try:
            async for msg in message.channel.history(limit=limit, before=message):
                context_messages.append(
                    f"{msg.author.display_name}: {msg.content[:200]}"
                )
            context_messages.reverse()
        except discord.Forbidden:
            pass
        return '\n'.join(context_messages) if context_messages else '(no prior messages visible)'

    # -------------------------------------------------------------------------
    # Claude: Should We Engage?
    # -------------------------------------------------------------------------

    async def _should_engage(self, message: discord.Message, intent: str) -> bool:
        """
        Ask Claude whether this message is worth replying to.

        High-intent and pain-point messages get a lower bar.
        """
        # High intent → always try (skip Claude check to save tokens)
        if intent == 'high_intent':
            self.logger.info("auto_engage_high_intent", author=str(message.author))
            return True

        context = await self._get_channel_context(message)

        prompt = f"""Should we reply to this Discord message? Answer YES or NO with a brief reason.

CHANNEL CONTEXT:
{context}

TARGET MESSAGE:
Author: {message.author.display_name}
Server: {message.guild.name} | Channel: #{getattr(message.channel, 'name', 'unknown')}
Message: "{message.content}"

{PRODUCT_CONTEXT}

DECISION CRITERIA:
1. Is this person dealing with a trust/payment/escrow problem we can help with?
2. Would our reply feel natural and helpful (not promotional)?
3. Is this a real concern (not sarcasm, memes, or jokes)?
4. Would mentioning reputation-based fees be relevant here?

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

    async def _generate_reply(self, message: discord.Message, intent: str) -> Optional[str]:
        """Generate a contextual reply tailored to the message intent."""
        context = await self._get_channel_context(message, limit=8)

        # Tailor instructions based on intent
        if intent == 'pain_point':
            tone_instruction = """TONE: This person got burned. Lead with empathy.
Acknowledge what happened to them. Then offer practical advice.
Only mention RepEscrow if escrow would have prevented their problem."""

        elif intent == 'high_intent':
            tone_instruction = """TONE: This person is actively looking for a solution.
Be direct and helpful. Explain how FairScore-based fees work.
Give them a clear reason to check out repescrow.xyz."""

        else:
            tone_instruction = """TONE: Casual and helpful. This is a general discussion.
Add value to the conversation first. Only mention RepEscrow
if it naturally fits — don't force it."""

        prompt = f"""Write a Discord reply to this message.

CONVERSATION CONTEXT:
{context}

MESSAGE TO REPLY TO:
{message.author.display_name}: "{message.content}"

{PRODUCT_CONTEXT}

{tone_instruction}

RULES:
1. Be genuinely helpful FIRST — answer their actual question
2. Max 150 words (Discord users skip long messages)
3. Match casual Discord tone — no corporate speak
4. DON'T start with "Hey!" or "Great question!" or any filler
5. If mentioning RepEscrow, explain the FairScore fee tiers briefly
6. Include repescrow.xyz ONLY if you mention the product
7. Use line breaks for readability
8. If someone got scammed: empathy first, solution second
9. Never say "I'm an AI" or "as a bot"
10. Sound like a knowledgeable community member, not a marketer

Return ONLY the reply text."""

        try:
            reply = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.COMPLEX,
                max_tokens=350,
                temperature=0.8
            )

            reply = reply.strip()
            if len(reply) > self.MAX_MESSAGE_LENGTH:
                reply = reply[:self.MAX_MESSAGE_LENGTH - 3] + "..."

            return reply

        except Exception as e:
            self.logger.error("reply_generation_failed", error=str(e))
            return None

    # -------------------------------------------------------------------------
    # Send & Track
    # -------------------------------------------------------------------------

    async def _send_reply(self, message: discord.Message, reply: str) -> bool:
        """Send reply, update rate limits, track prospect in Supabase."""
        try:
            await message.reply(reply, mention_author=False)

            # Update rate tracking
            self._last_message_time = datetime.now(timezone.utc)
            self._replied_message_ids.add(message.id)
            self.increment_action_count("message")
            self.record_engagement()

            guild_id = message.guild.id
            self._server_message_counts[guild_id] = (
                self._server_message_counts.get(guild_id, 0) + 1
            )

            # Track prospect in Supabase
            intent = self._classify_intent(message)
            score = self._score_prospect(message, intent)

            prospect = self.track_prospect(
                handle=str(message.author),
                score=score
            )

            # Log conversation
            self.db.create_conversation(Conversation(
                prospect_id=prospect.id,
                platform=Platform.DISCORD,
                message=message.content[:500],
                response=reply[:500]
            ))

            self.logger.info(
                "discord_reply_sent",
                guild=message.guild.name,
                channel=getattr(message.channel, 'name', 'unknown'),
                author=str(message.author),
                intent=intent,
                score=score,
                reply_length=len(reply)
            )

            return True

        except discord.Forbidden:
            self.logger.warning(
                "discord_reply_forbidden",
                guild=message.guild.name,
                channel=getattr(message.channel, 'name', 'unknown')
            )
            return False

        except Exception as e:
            self.logger.error("discord_reply_failed", error=str(e))
            return False

    # -------------------------------------------------------------------------
    # Server Scanning (orchestrator-driven batch mode)
    # -------------------------------------------------------------------------

    async def _scan_servers(self) -> None:
        """Scan all servers for recent relevant messages."""
        if not self._bot.is_ready():
            async with self._bot:
                await self._bot.login(self.settings.discord_bot_token)
                await self._perform_scan()
        else:
            await self._perform_scan()

    async def _perform_scan(self) -> None:
        """Walk priority channels in all guilds, process recent messages."""
        messages_engaged = 0
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        for guild in self._bot.guilds:
            self.logger.info("scanning_guild", guild=guild.name)

            for channel in guild.text_channels:
                if not any(name in channel.name.lower() for name in PRIORITY_CHANNELS):
                    continue

                try:
                    async for message in channel.history(limit=50, after=one_hour_ago):
                        if message.author == self._bot.user or message.author.bot:
                            continue
                        if self._is_relevant_message(message):
                            await self._handle_relevant_message(message)
                            messages_engaged += 1

                except discord.Forbidden:
                    continue

        self.save_daily_metrics()
        self.logger.info(
            "discord_scan_completed",
            messages_engaged=messages_engaged
        )

    # -------------------------------------------------------------------------
    # Prospect Scoring
    # -------------------------------------------------------------------------

    def _score_prospect(self, message: discord.Message, intent: str) -> int:
        """
        Score prospect 1-10 based on intent and message signals.

        Scoring:
        - Base: 5
        - high_intent: +3 (actively looking for escrow/hiring)
        - pain_point: +2 (got scammed, needs trust solution)
        - Detailed message (100+ chars): +1
        - In hiring/jobs channel: +1
        """
        score = 5

        if intent == 'high_intent':
            score += 3
        elif intent == 'pain_point':
            score += 2

        if len(message.content) > 100:
            score += 1

        channel_name = getattr(message.channel, 'name', '').lower()
        if any(kw in channel_name for kw in ['job', 'hiring', 'freelance', 'bounty', 'gig']):
            score += 1

        return min(score, 10)
