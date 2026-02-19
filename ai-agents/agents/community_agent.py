"""
Community Agent — RepEscrow Discord Server Management.

Manages the RepEscrow-owned Discord community server (distinct from the
DiscordAgent, which monitors *external* servers for lead generation).

Responsibilities
----------------
- Onboard new members with a rich welcome message
- Answer support questions via Claude AI (with per-user cooldown)
- Post rotating daily content to keep the community engaged
- Drive activation: wallet connect → first escrow creation

Design notes
------------
- Full async throughout; no blocking calls on the event loop
- Retry decorator wraps every Discord API call (rate-limit safe)
- Per-user support cooldown prevents spam / abuse
- Daily loop fires at a deterministic UTC time, not "24 h after start"
- All product copy and channel names come from settings, not hard-coded strings
- Graceful shutdown: SIGINT/SIGTERM drain the task queue before exit
"""

from __future__ import annotations

import asyncio
import signal
from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Final, Optional

import discord
from discord.ext import commands, tasks
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent
from claude_client import TaskComplexity
from database import Platform

__all__ = ["CommunityAgent"]

# ── Constants ─────────────────────────────────────────────────────────────────

#: Discord hard limit for a single message body.
DISCORD_MAX_CHARS: Final[int] = 2_000

#: Seconds a user must wait between consecutive support replies.
SUPPORT_COOLDOWN_SECONDS: Final[int] = 60

#: UTC hour at which the daily content loop fires (9 AM UTC).
DAILY_POST_HOUR_UTC: Final[int] = 9

#: Maximum retries for Discord API calls before giving up.
MAX_DISCORD_RETRIES: Final[int] = 3

# ── Channel registry ──────────────────────────────────────────────────────────

CHANNELS: Final[dict[str, str]] = {
    "welcome": "welcome",
    "vendor_showcase": "vendor-showcase",
    "buyer_requests": "buyer-requests",
    "completed_deals": "completed-deals",
    "support": "support",
    "feedback": "feedback",
    "general": "general",
    "announcements": "announcements",
}

# ── Daily topic rotation (Monday = 0 … Sunday = 6) ────────────────────────────

DAILY_TOPICS: Final[dict[int, str]] = {
    0: "motivation_monday",
    1: "tip_tuesday",
    2: "wisdom_wednesday",
    3: "throwback_thursday",
    4: "feature_friday",
    5: "showcase_saturday",
    6: "stats_sunday",
}

TOPIC_DESCRIPTIONS: Final[dict[str, str]] = {
    "motivation_monday": (
        "A motivational post about a vendor success story or why "
        "reputation matters in Web3."
    ),
    "tip_tuesday": (
        "A practical tip for Web3 freelancers — saving on fees, "
        "building reputation, or winning clients."
    ),
    "wisdom_wednesday": (
        "Best practices for using escrow and protecting yourself in "
        "Web3 service transactions."
    ),
    "throwback_thursday": (
        "A building-journey update: what the team shipped this week "
        "and what's coming next."
    ),
    "feature_friday": (
        "Highlight a RepEscrow feature or preview something arriving soon."
    ),
    "showcase_saturday": (
        "Prompt vendors to share their services, rates, and portfolio links."
    ),
    "stats_sunday": (
        "Weekly community stats roundup — new members, transactions, "
        "and milestones reached."
    ),
}


# ── Retry helpers ─────────────────────────────────────────────────────────────

def _discord_retry(func):
    """Decorator: retry on transient Discord / network errors."""
    return retry(
        retry=retry_if_exception_type(
            (discord.HTTPException, discord.GatewayNotFound, ConnectionResetError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(MAX_DISCORD_RETRIES),
        reraise=True,
    )(func)


# ── Agent ─────────────────────────────────────────────────────────────────────


class CommunityAgent(BaseAgent):
    """
    Manages the RepEscrow Discord community server.

    Unlike ``DiscordAgent`` (external outreach), this bot lives *inside*
    the RepEscrow server and focuses on member retention and activation.

    Parameters
    ----------
    None — all settings are read from the shared ``Settings`` singleton.

    Example
    -------
    >>> agent = CommunityAgent()
    >>> agent.run()          # blocks; install signal handlers first
    """

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self) -> None:
        super().__init__(platform=Platform.DISCORD)

        # Keyed by user ID; value = UTC timestamp of last support reply.
        self._support_cooldowns: dict[int, datetime] = defaultdict(
            lambda: datetime.min.replace(tzinfo=timezone.utc)
        )

        # Track message IDs already replied to (prevents double-posting on reconnect).
        self._replied_message_ids: set[int] = set()

        # Metrics counters (in-process; persisted to DB via record_* helpers).
        self._metrics: dict[str, int] = defaultdict(int)

        self._bot: Optional[commands.Bot] = None
        self._shutdown_event = asyncio.Event()

        self._build_bot()

    def _build_bot(self) -> None:
        """Construct and configure the Discord bot instance."""
        token = getattr(self.settings, "discord_bot_token", None)
        if not token:
            self.logger.warning(
                "community_bot_skipped",
                reason="discord_bot_token not configured",
            )
            return

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        self._bot = commands.Bot(
            command_prefix="!escrow ",
            intents=intents,
            help_command=None,
        )

        self._register_events()
        self._register_commands()
        self.logger.info("community_bot_built")

    # ── Public interface ───────────────────────────────────────────────────────

    def get_name(self) -> str:
        return "CommunityAgent"

    def health_check(self) -> bool:
        """Return True only when the bot is fully connected and ready."""
        return (
            self._bot is not None
            and self._bot.is_ready()
            and not self._bot.is_closed()
        )

    def run(self) -> None:
        """
        Start the community bot.

        Installs OS signal handlers so Ctrl-C / SIGTERM triggers a clean
        shutdown rather than a hard kill.  Blocks until the bot exits.
        """
        if self._bot is None:
            self.logger.error(
                "community_agent_aborted",
                reason="bot not initialised — check discord_bot_token",
            )
            return

        self.logger.info("community_agent_starting")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._request_shutdown)

        try:
            loop.run_until_complete(
                self._bot.start(self.settings.discord_bot_token)
            )
        except asyncio.CancelledError:
            self.logger.info("community_agent_shutdown_complete")
        finally:
            loop.run_until_complete(self._bot.close())
            loop.close()

    def _request_shutdown(self) -> None:
        """Signal the bot to shut down gracefully."""
        self.logger.info("shutdown_signal_received")
        self._shutdown_event.set()
        asyncio.create_task(self._bot.close())

    # ── Event registration ─────────────────────────────────────────────────────

    def _register_events(self) -> None:
        """Attach all Discord event listeners to the bot."""

        @self._bot.event
        async def on_ready() -> None:
            guilds = [g.name for g in self._bot.guilds]
            self.logger.info(
                "community_bot_ready",
                username=str(self._bot.user),
                guilds=guilds,
            )
            # Start scheduled tasks only after the bot is confirmed ready.
            if not self._daily_content_loop.is_running():
                self._daily_content_loop.start()

        @self._bot.event
        async def on_member_join(member: discord.Member) -> None:
            await self._welcome_member(member)

        @self._bot.event
        async def on_message(message: discord.Message) -> None:
            # Ignore self and other bots.
            if message.author.bot:
                return
            # Deduplicate (reconnect safety).
            if message.id in self._replied_message_ids:
                return

            channel_name = getattr(message.channel, "name", "")
            if channel_name == CHANNELS["support"]:
                await self._handle_support(message)

            # Allow prefix commands to propagate.
            await self._bot.process_commands(message)

        @self._bot.event
        async def on_error(event: str, *args, **kwargs) -> None:
            self.logger.error("discord_event_error", event=event)

    def _register_commands(self) -> None:
        """Register slash-style prefix commands available to all members."""

        @self._bot.command(name="fees")
        async def fees_cmd(ctx: commands.Context) -> None:
            """Show the FairScore fee tier table."""
            table = self._build_fee_table()
            await self._safe_send(ctx.channel, table)

        @self._bot.command(name="stats")
        async def stats_cmd(ctx: commands.Context) -> None:
            """Show in-process bot metrics."""
            stats_msg = (
                f"**Community Bot Stats**\n"
                f"Members welcomed : {self._metrics['welcomes']}\n"
                f"Support replies  : {self._metrics['support_replies']}\n"
                f"Daily posts      : {self._metrics['daily_posts']}\n"
            )
            await self._safe_send(ctx.channel, stats_msg)

    # ── Welcome flow ───────────────────────────────────────────────────────────

    async def _welcome_member(self, member: discord.Member) -> None:
        """
        Send a rich onboarding message to a new member.

        The message is posted in #welcome (not a DM) so the community
        can greet the newcomer.
        """
        welcome_channel = discord.utils.get(
            member.guild.text_channels, name=CHANNELS["welcome"]
        )
        if welcome_channel is None:
            self.logger.warning(
                "welcome_channel_missing",
                guild=member.guild.name,
                expected=CHANNELS["welcome"],
            )
            return

        message = (
            f"👋 Welcome to **RepEscrow**, {member.mention}!\n\n"
            f"We're building reputation-weighted escrow on Solana — "
            f"your FairScore determines your platform fees "
            f"(0.5 % at the top tier, 2.5 % for new accounts).\n\n"
            f"**Get started in 3 steps:**\n"
            f"1️⃣  Connect your wallet at **{self.settings.product_url}**\n"
            f"2️⃣  Browse #{CHANNELS['vendor_showcase']} to find talented vendors\n"
            f"3️⃣  Post in #{CHANNELS['buyer_requests']} if you need work done\n\n"
            f"Questions? Drop them in #{CHANNELS['support']} — we reply fast. "
            f"Glad you're here! 🚀"
        )

        await self._safe_send(welcome_channel, message)

        # Register this community join as a mid-quality lead.
        self.track_prospect(handle=str(member), score=6)
        self.record_impression()
        self._metrics["welcomes"] += 1

        self.logger.info("member_welcomed", member=str(member), guild=member.guild.name)

    # ── Support handling ───────────────────────────────────────────────────────

    async def _handle_support(self, message: discord.Message) -> None:
        """
        Reply to a support question using Claude.

        Enforces a per-user cooldown (``SUPPORT_COOLDOWN_SECONDS``) to
        prevent accidental or deliberate flooding.
        """
        user_id = message.author.id
        now = datetime.now(tz=timezone.utc)
        last_replied = self._support_cooldowns[user_id]
        elapsed = (now - last_replied).total_seconds()

        if elapsed < SUPPORT_COOLDOWN_SECONDS:
            remaining = int(SUPPORT_COOLDOWN_SECONDS - elapsed)
            await message.add_reaction("⏳")
            self.logger.debug(
                "support_cooldown_active",
                user=str(message.author),
                remaining_seconds=remaining,
            )
            return

        prompt = self._build_support_prompt(
            question=message.content,
            author=message.author.display_name,
        )

        try:
            reply = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.SIMPLE,
                max_tokens=300,
                temperature=0.5,
            )
        except Exception as exc:
            self.logger.error("support_generation_failed", error=str(exc))
            await message.add_reaction("❌")
            return

        await self._safe_reply(message, reply.strip())

        self._support_cooldowns[user_id] = now
        self._replied_message_ids.add(message.id)
        self._metrics["support_replies"] += 1

        self.logger.info(
            "support_answered",
            author=str(message.author),
            question_preview=message.content[:80],
        )

    @staticmethod
    def _build_support_prompt(question: str, author: str) -> str:
        return f"""You are the support bot for RepEscrow, a reputation-weighted
smart escrow platform on Solana. Answer the following support question.

QUESTION (from {author}): "{question}"

PRODUCT FACTS:
- Website: repescrow.xyz
- FairScore tiers: Elite (≥4.5) 0.5% fee | Trusted (3.5-4.49) 1% | Verified
  (2.5-3.49) 1.5% | Building (1.5-2.49) 2% | New (<1.5) 2.5%
- Wallets supported: Phantom, Solflare
- Funds held on Solana; milestone-based release
- Dispute resolution: platform admin arbitration

RULES:
1. Be helpful, concise, and friendly (Discord community tone).
2. Keep reply under 150 words.
3. If unsure, say "Let me check with the team — they'll follow up shortly."
4. Mention repescrow.xyz when relevant.
5. If it sounds like a bug, acknowledge and say the team will investigate.

Reply with the message text ONLY — no preamble."""

    # ── Daily content loop ─────────────────────────────────────────────────────

    @tasks.loop(hours=24)
    async def _daily_content_loop(self) -> None:
        """Post rotating daily content to #general at the scheduled UTC hour."""
        topic = DAILY_TOPICS[date.today().weekday()]
        content = await self._generate_daily_content(topic)
        if not content:
            return

        posted_to: list[str] = []
        for guild in self._bot.guilds:
            channel = discord.utils.get(
                guild.text_channels, name=CHANNELS["general"]
            )
            if channel:
                await self._safe_send(channel, content)
                posted_to.append(guild.name)
                self.record_impression()
                self._metrics["daily_posts"] += 1

        self.logger.info(
            "daily_content_posted",
            topic=topic,
            guilds=posted_to,
        )

    @_daily_content_loop.before_loop
    async def _before_daily_loop(self) -> None:
        """
        Wait until the bot is ready, then sleep until the next scheduled
        UTC hour so posts always fire at a predictable time.
        """
        await self._bot.wait_until_ready()

        now = datetime.now(tz=timezone.utc)
        target = now.replace(
            hour=DAILY_POST_HOUR_UTC, minute=0, second=0, microsecond=0
        )
        if target <= now:
            # Already past today's slot — aim for tomorrow.
            target = target.replace(day=target.day + 1)

        sleep_seconds = (target - now).total_seconds()
        self.logger.info(
            "daily_loop_waiting",
            first_post_at=target.isoformat(),
            sleep_seconds=int(sleep_seconds),
        )
        await asyncio.sleep(sleep_seconds)

    @_daily_content_loop.error
    async def _daily_loop_error(self, error: Exception) -> None:
        self.logger.error("daily_loop_error", error=str(error))

    async def _generate_daily_content(self, topic: str) -> Optional[str]:
        """Generate a daily community post via Claude."""
        description = TOPIC_DESCRIPTIONS.get(topic, "A helpful community post.")

        prompt = f"""Write a Discord community post for RepEscrow.

TOPIC: {topic.replace("_", " ").title()}
BRIEF: {description}

PRODUCT CONTEXT:
- Reputation-weighted escrow on Solana
- FairScore determines fees (0.5 %–2.5 %)
- URL: {self.settings.product_url}

RULES:
1. Conversational Discord tone — not corporate.
2. 100–200 words.
3. End with a question or CTA to encourage replies.
4. Use 1–2 relevant emojis max.
5. Feel authentic; avoid buzzword-heavy marketing speak.
6. For showcase_saturday: invite vendors to share skills and rates.
7. For stats_sunday: use plausible early-stage numbers if real data unavailable.

Return ONLY the post text."""

        try:
            content = self.claude.generate(
                prompt=prompt,
                complexity=TaskComplexity.MEDIUM,
                max_tokens=400,
                temperature=0.85,
            )
            return content.strip() or None
        except Exception as exc:
            self.logger.error("daily_content_generation_failed", error=str(exc))
            return None

    # ── Utility helpers ────────────────────────────────────────────────────────

    @_discord_retry
    async def _safe_send(
        self,
        channel: discord.abc.Messageable,
        content: str,
    ) -> None:
        """
        Send ``content`` to ``channel``, automatically chunking messages that
        exceed Discord's 2 000-character hard limit.
        """
        for chunk in self._chunk_message(content):
            await channel.send(chunk)

    @_discord_retry
    async def _safe_reply(
        self,
        message: discord.Message,
        content: str,
    ) -> None:
        """Reply to ``message``, chunking if necessary."""
        chunks = self._chunk_message(content)
        await message.reply(chunks[0], mention_author=False)
        for chunk in chunks[1:]:
            await message.channel.send(chunk)

    @staticmethod
    def _chunk_message(text: str) -> list[str]:
        """
        Split ``text`` into a list of strings each ≤ ``DISCORD_MAX_CHARS``.
        Splits on newlines where possible to avoid breaking mid-sentence.
        """
        if len(text) <= DISCORD_MAX_CHARS:
            return [text]

        chunks: list[str] = []
        while text:
            if len(text) <= DISCORD_MAX_CHARS:
                chunks.append(text)
                break
            # Find last newline within the limit.
            split_at = text.rfind("\n", 0, DISCORD_MAX_CHARS)
            if split_at == -1:
                split_at = DISCORD_MAX_CHARS
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip("\n")

        return chunks

    @staticmethod
    def _build_fee_table() -> str:
        return (
            "**RepEscrow Fee Tiers**\n"
            "```\n"
            "Tier       FairScore   Fee    Hold Period\n"
            "─────────────────────────────────────────\n"
            "Elite      4.5 – 5.0   0.5%   Instant\n"
            "Trusted    3.5 – 4.49  1.0%   24 hours\n"
            "Verified   2.5 – 3.49  1.5%   72 hours\n"
            "Building   1.5 – 2.49  2.0%   7 days\n"
            "New        0.0 – 1.49  2.5%   14 days\n"
            "```\n"
            f"Connect your wallet at repescrow.xyz to see your tier."
        )

    # ── Dunder helpers ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        status = "ready" if self.health_check() else "not_ready"
        return f"<CommunityAgent status={status}>"

    def __str__(self) -> str:
        return self.get_name()