"""
Community Agent - RepEscrow's Own Discord Server Management.

Manages the RepEscrow Discord community server:
- Welcome new members with onboarding message
- Facilitate vendor-buyer connections
- Share daily tips and success stories
- Answer support questions
- Post engagement prompts

This is NOT the same as the Discord agent (which monitors external servers).
This agent manages YOUR server to retain and activate signups.

Goal: Keep community engaged, drive activation (wallet connect + first escrow).
"""

import asyncio
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Dict

import discord
from discord.ext import commands, tasks

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, RateLimitExceeded
from database import Platform
from claude_client import TaskComplexity


# RepEscrow product context
PRODUCT_CONTEXT = """
RepEscrow is a reputation-weighted escrow platform on Solana.
Your FairScore determines your escrow fees (0.5% to 2.5%).
Higher reputation = lower fees. Built on Solana.
Website: repescrow.xyz
"""

# Channel names for the RepEscrow community server
CHANNELS = {
    'welcome': 'welcome',
    'vendor_showcase': 'vendor-showcase',
    'buyer_requests': 'buyer-requests',
    'completed_deals': 'completed-deals',
    'support': 'support',
    'feedback': 'feedback',
    'general': 'general',
    'announcements': 'announcements',
}

# Daily content topics (rotated by day of week)
DAILY_TOPICS = {
    0: 'motivation_monday',    # Vendor success story
    1: 'tip_tuesday',          # Platform tip or Web3 insight
    2: 'wisdom_wednesday',     # Escrow/trust best practices
    3: 'throwback_thursday',   # Building journey update
    4: 'feature_friday',       # New feature or upcoming release
    5: 'showcase_saturday',    # Highlight a vendor
    6: 'stats_sunday',         # Weekly stats and metrics
}


class CommunityAgent(BaseAgent):
    """
    Manages the RepEscrow Discord community server.

    Runs as an always-on bot in YOUR server (not external servers).

    Features:
    - Auto-welcome new members
    - Daily content posting (tips, stories, stats)
    - Support question answering via Claude
    - Vendor-buyer matchmaking prompts
    """

    def __init__(self) -> None:
        """Initialize Community agent."""
        # Community uses the same DISCORD platform for DB tracking
        super().__init__(platform=Platform.DISCORD)

        self._bot: Optional[commands.Bot] = None
        self._guild_id: Optional[int] = None

        self._initialize_bot()

    def _initialize_bot(self) -> None:
        """Initialize Discord bot for the community server."""
        try:
            if not self.settings.discord_bot_token:
                self.logger.warning("discord_bot_token_not_configured")
                return

            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.members = True

            self._bot = commands.Bot(
                command_prefix='!escrow ',
                intents=intents,
                help_command=None
            )

            self._register_handlers()
            self.logger.info("community_bot_initialized")

        except Exception as e:
            self.logger.error("community_bot_init_failed", error=str(e))
            self._bot = None

    def _register_handlers(self) -> None:
        """Register event handlers and scheduled tasks."""

        @self._bot.event
        async def on_ready():
            self.logger.info(
                "community_bot_connected",
                username=str(self._bot.user),
                guild_count=len(self._bot.guilds)
            )
            # Start scheduled tasks
            if not self._daily_content_loop.is_running():
                self._daily_content_loop.start()

        @self._bot.event
        async def on_member_join(member: discord.Member):
            await self._welcome_member(member)

        @self._bot.event
        async def on_message(message: discord.Message):
            if message.author == self._bot.user:
                return
            if message.author.bot:
                return

            # Answer support questions
            channel_name = getattr(message.channel, 'name', '')
            if channel_name == CHANNELS['support']:
                await self._handle_support(message)

    def get_name(self) -> str:
        """Get agent name."""
        return "CommunityAgent"

    def health_check(self) -> bool:
        """Check if bot is operational."""
        return self._bot is not None

    def run(self) -> None:
        """Start the community bot (blocks forever)."""
        self.logger.info(
            "community_agent_starting",
            date=str(date.today())
        )

        if not self.health_check():
            self.logger.error("community_agent_not_healthy")
            return

        try:
            self._bot.run(self.settings.discord_bot_token)
        except Exception as e:
            self.logger.error("community_agent_run_failed", error=str(e))

    # -------------------------------------------------------------------------
    # Welcome New Members
    # -------------------------------------------------------------------------

    async def _welcome_member(self, member: discord.Member) -> None:
        """Send a personalized welcome message to new members."""
        try:
            welcome_channel = discord.utils.get(
                member.guild.text_channels,
                name=CHANNELS['welcome']
            )

            if not welcome_channel:
                return

            welcome_msg = (
                f"Welcome to RepEscrow, {member.mention}!\n\n"
                f"We're building reputation-weighted escrow on Solana. "
                f"Your FairScore determines your fees — better reputation = lower costs.\n\n"
                f"**Get started:**\n"
                f"1. Connect your wallet at repescrow.xyz\n"
                f"2. Check out #{CHANNELS['vendor_showcase']} to see vendors\n"
                f"3. Post in #{CHANNELS['buyer_requests']} if you need work done\n"
                f"4. Questions? Ask in #{CHANNELS['support']}\n\n"
                f"Glad to have you here!"
            )

            await welcome_channel.send(welcome_msg)

            # Track as prospect
            self.track_prospect(
                handle=str(member),
                score=6  # They joined the community — decent signal
            )

            self.record_impression()

            self.logger.info(
                "member_welcomed",
                member=str(member),
                guild=member.guild.name
            )

        except Exception as e:
            self.logger.error("welcome_failed", error=str(e), member=str(member))

    # -------------------------------------------------------------------------
    # Support Handling
    # -------------------------------------------------------------------------

    async def _handle_support(self, message: discord.Message) -> None:
        """Answer support questions in the support channel using Claude."""
        try:
            prompt = f"""Answer this RepEscrow support question.

QUESTION: "{message.content}"
ASKED BY: {message.author.display_name}

{PRODUCT_CONTEXT}

COMMON TOPICS:
- How to connect wallet (Phantom/Solflare on repescrow.xyz)
- How FairScore tiers work (see tiers above)
- How to create/fund an escrow
- How milestone payments work
- How disputes are resolved
- Transaction fees by tier

RULES:
1. Be helpful and concise (under 150 words)
2. If you don't know the answer, say "Let me check with the team"
3. Friendly Discord tone
4. Include links to repescrow.xyz when relevant
5. If it's a bug report, acknowledge it and say the team will look into it

Return ONLY the reply."""

            reply = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.SIMPLE,
                max_tokens=300,
                temperature=0.5
            )

            await message.reply(reply.strip(), mention_author=False)

            self.logger.info(
                "support_answered",
                author=str(message.author),
                question_length=len(message.content)
            )

        except Exception as e:
            self.logger.error("support_handler_failed", error=str(e))

    # -------------------------------------------------------------------------
    # Daily Content (scheduled task)
    # -------------------------------------------------------------------------

    @tasks.loop(hours=24)
    async def _daily_content_loop(self):
        """Post daily content based on the day of the week."""
        try:
            today = date.today()
            topic = DAILY_TOPICS.get(today.weekday(), 'tip_tuesday')

            content = self._generate_daily_content(topic)
            if not content:
                return

            # Find the general or announcements channel
            for guild in self._bot.guilds:
                channel = discord.utils.get(
                    guild.text_channels,
                    name=CHANNELS['general']
                )
                if channel:
                    await channel.send(content)
                    self.record_impression()
                    self.logger.info(
                        "daily_content_posted",
                        topic=topic,
                        guild=guild.name
                    )

        except Exception as e:
            self.logger.error("daily_content_failed", error=str(e))

    def _generate_daily_content(self, topic: str) -> Optional[str]:
        """Generate daily community content using Claude."""
        topic_descriptions = {
            'motivation_monday': 'A motivational post about a vendor success story or why reputation matters in Web3',
            'tip_tuesday': 'A practical tip for Web3 freelancers (saving on fees, building reputation, getting clients)',
            'wisdom_wednesday': 'Best practices for using escrow, protecting yourself in Web3 transactions',
            'throwback_thursday': 'A building journey update — what the team shipped this week',
            'feature_friday': 'Highlight a feature of RepEscrow or preview something coming soon',
            'showcase_saturday': 'Prompt for vendors to share their services and portfolio',
            'stats_sunday': 'Weekly community stats roundup (new members, transactions, milestones)',
        }

        description = topic_descriptions.get(topic, 'A helpful community post')

        prompt = f"""Write a Discord community post for RepEscrow.

TOPIC: {topic.replace('_', ' ').title()}
DESCRIPTION: {description}

{PRODUCT_CONTEXT}

RULES:
1. Engaging and conversational (Discord community tone)
2. 100-200 words
3. End with a question or call-to-action to drive replies
4. Use 1-2 relevant emojis (but don't overdo it)
5. Make it feel authentic, not corporate
6. If it's showcase_saturday, prompt vendors to share their skills
7. If it's stats_sunday, you can make up realistic early-stage numbers

Return ONLY the post text."""

        try:
            content = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.MEDIUM,
                max_tokens=400,
                temperature=0.9
            )
            return content.strip()

        except Exception as e:
            self.logger.error("daily_content_generation_failed", error=str(e))
            return None
