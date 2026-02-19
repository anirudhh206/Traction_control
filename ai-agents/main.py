"""
Traction Control — Main Entry Point.

Launches the RepEscrow AI agent orchestrator which coordinates all
outreach agents (Discord, Telegram, Community, Email, Forum) to drive
signups and community growth.

Usage
-----
    python main.py                  # Run the full orchestrator
    python main.py --status         # Print agent config status and exit
    python main.py --agent community  # Run a single agent standalone

Environment
-----------
Requires a .env file in the project root (../.env) with API keys for
Anthropic, Supabase, Discord, Telegram, SendGrid, etc.
See config.py for the full list of required settings.
"""

import sys
import os
import argparse

# Ensure the ai-agents package root is on sys.path so internal imports resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logging_config import setup_logging, get_logger
from config import get_settings
from orchestrator import Orchestrator


logger = get_logger(__name__)

# Map of CLI names → (module_path, class_name) for standalone agent runs.
AGENT_MAP = {
    "discord":   ("agents.discord_agent",   "DiscordAgent"),
    "telegram":  ("agents.telegram_agent",  "TelegramAgent"),
    "community": ("agents.community_agent", "CommunityAgent"),
    "email":     ("agents.email_agent",     "EmailAgent"),
    "forum":     ("agents.forum_agent",     "ForumAgent"),
}


def _print_status() -> None:
    """Print the current agent configuration and exit."""
    settings = get_settings()

    agent_flags = {
        "discord":   settings.enable_discord_agent,
        "telegram":  settings.enable_telegram_agent,
        "community": settings.enable_community_agent,
        "email":     settings.enable_email_agent,
        "forum":     settings.enable_forum_agent,
        "twitter":   settings.enable_twitter_agent,
        "reddit":    settings.enable_reddit_agent,
    }

    print("\n  Traction Control — Agent Status")
    print("  " + "=" * 38)
    for name, enabled in agent_flags.items():
        marker = "[ON] " if enabled else "[OFF]"
        print(f"  {marker}  {name}")
    print(f"\n  Environment : {settings.environment}")
    print(f"  Log level   : {settings.log_level}")
    print(f"  Product URL : {settings.product_url}\n")


def _run_single_agent(name: str) -> None:
    """Import and run a single agent by CLI name."""
    if name not in AGENT_MAP:
        print(f"Unknown agent '{name}'. Choose from: {', '.join(AGENT_MAP)}")
        sys.exit(1)

    module_path, class_name = AGENT_MAP[name]

    logger.info("single_agent_mode", agent=name)


    import importlib
    module = importlib.import_module(module_path)
    agent_cls = getattr(module, class_name)

    agent = agent_cls()
    agent.run()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="traction-control",
        description="RepEscrow AI Traction Engine — drive signups with coordinated outreach agents.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print agent configuration and exit.",
    )
    parser.add_argument(
        "--agent",
        type=str,
        metavar="NAME",
        help=f"Run a single agent standalone. Choices: {', '.join(AGENT_MAP)}",
    )
    return parser


def main() -> None:
    """Entry point for the Traction Control engine."""
    setup_logging()

    parser = _build_parser()
    args = parser.parse_args()

    if args.status:
        _print_status()
        return

    if args.agent:
        _run_single_agent(args.agent)
        return

    # Default: launch the full orchestrator.
    logger.info("traction_control_starting")

    orchestrator = Orchestrator()

    status = orchestrator.get_system_status()
    for agent_name, agent_info in status["agents"].items():
        logger.info("agent_config", agent=agent_name, status=agent_info["status"])

    orchestrator.run()


if __name__ == "__main__":
    main()
