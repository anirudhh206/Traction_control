"""
Orchestrator - Master Coordinator for All RepEscrow AI Agents.

Manages the daily schedule of all 7 agents:
- Discord & Telegram: Always-on (separate processes)
- Community: Always-on (separate process, RepEscrow's own server)
- Email: Scheduled (6 AM - cold outreach + follow-ups)
- Forum: Scheduled (10 AM + 3 PM - HN/IndieHackers engagement)
- Twitter: Skipped for now (API access pending)
- Reddit: Deprioritized (API approval takes weeks)

The orchestrator:
1. Starts always-on agents in separate processes
2. Runs scheduled agents at configured times
3. Collects daily metrics from all agents
4. Handles process lifecycle (restarts on crash)
5. Saves daily summary to Supabase

Goal: Coordinate all agents to hit 100-200 signups in 30 days.
"""

import time
import signal
import multiprocessing
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Optional
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_settings
from database import get_db, Platform
from logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class AgentType(str, Enum):
    """Agent types managed by the orchestrator."""
    DISCORD = "discord"
    TELEGRAM = "telegram"
    COMMUNITY = "community"
    EMAIL = "email"
    FORUM = "forum"
    TWITTER = "twitter"
    REDDIT = "reddit"


class AgentStatus(str, Enum):
    """Runtime status of an agent."""
    STOPPED = "stopped"
    RUNNING = "running"
    CRASHED = "crashed"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------
# Daily Schedule (UTC hours)
# ---------------------------------------------------------------------------
SCHEDULE = {
    # hour: list of (agent_type, task_name)
    6:  [(AgentType.EMAIL, "cold_outreach")],
    10: [(AgentType.FORUM, "morning_engagement")],
    15: [(AgentType.FORUM, "afternoon_engagement")],
    22: [(AgentType.EMAIL, "follow_ups")],
}

# Always-on agents that run in their own processes
ALWAYS_ON_AGENTS = [
    AgentType.DISCORD,
    AgentType.TELEGRAM,
    AgentType.COMMUNITY,
]

# Max restart attempts before giving up on a crashed agent
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN_SECONDS = 60


class Orchestrator:
    """
    Master coordinator for all RepEscrow AI agents.

    Manages process lifecycle, scheduling, and daily metrics collection.
    """

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        self.settings = get_settings()
        self.db = get_db()

        # Track running processes for always-on agents
        self._processes: Dict[AgentType, multiprocessing.Process] = {}
        self._agent_status: Dict[AgentType, AgentStatus] = {}
        self._restart_counts: Dict[AgentType, int] = {}

        # Track which scheduled tasks ran today
        self._tasks_run_today: set = set()
        self._last_date: date = date.today()

        # Shutdown flag
        self._shutdown = False

        self._init_agent_status()

        logger.info("orchestrator_initialized")

    def _init_agent_status(self) -> None:
        """Initialize agent status based on config."""
        agent_enable_map = {
            AgentType.DISCORD: self.settings.enable_discord_agent,
            AgentType.TELEGRAM: self.settings.enable_telegram_agent,
            AgentType.COMMUNITY: self.settings.enable_community_agent,
            AgentType.EMAIL: self.settings.enable_email_agent,
            AgentType.FORUM: self.settings.enable_forum_agent,
            AgentType.TWITTER: self.settings.enable_twitter_agent,
            AgentType.REDDIT: self.settings.enable_reddit_agent,
        }

        for agent_type, enabled in agent_enable_map.items():
            self._agent_status[agent_type] = (
                AgentStatus.STOPPED if enabled else AgentStatus.DISABLED
            )
            self._restart_counts[agent_type] = 0

        logger.info(
            "agent_status_initialized",
            enabled=[a.value for a, s in self._agent_status.items() if s != AgentStatus.DISABLED],
            disabled=[a.value for a, s in self._agent_status.items() if s == AgentStatus.DISABLED],
        )

    # -------------------------------------------------------------------------
    # Agent Factory
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_agent(agent_type: AgentType):
        """Create an agent instance by type. Import here to avoid circular deps."""
        if agent_type == AgentType.DISCORD:
            from agents.discord_agent import DiscordAgent
            return DiscordAgent()
        elif agent_type == AgentType.TELEGRAM:
            from agents.telegram_agent import TelegramAgent
            return TelegramAgent()
        elif agent_type == AgentType.COMMUNITY:
            from agents.community_agent import CommunityAgent
            return CommunityAgent()
        elif agent_type == AgentType.EMAIL:
            from agents.email_agent import EmailAgent
            return EmailAgent()
        elif agent_type == AgentType.FORUM:
            from agents.forum_agent import ForumAgent
            return ForumAgent()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    # -------------------------------------------------------------------------
    # Process Management (Always-On Agents)
    # -------------------------------------------------------------------------

    @staticmethod
    def _run_agent_process(agent_type: AgentType) -> None:
        """
        Entry point for a child process running an always-on agent.

        Each always-on agent (Discord, Telegram, Community) blocks forever
        in its own process.
        """
        setup_logging()
        proc_logger = get_logger(f"process.{agent_type.value}")

        try:
            proc_logger.info("agent_process_starting", agent=agent_type.value)
            agent = Orchestrator._create_agent(agent_type)

            if not agent.health_check():
                proc_logger.error("agent_health_check_failed", agent=agent_type.value)
                return

            agent.run()  # Blocks forever

        except Exception as e:
            proc_logger.error(
                "agent_process_crashed",
                agent=agent_type.value,
                error=str(e)
            )

    def _start_always_on_agents(self) -> None:
        """Start all always-on agents in separate processes."""
        for agent_type in ALWAYS_ON_AGENTS:
            if self._agent_status.get(agent_type) == AgentStatus.DISABLED:
                logger.info("agent_disabled_skipping", agent=agent_type.value)
                continue

            self._start_agent_process(agent_type)

    def _start_agent_process(self, agent_type: AgentType) -> bool:
        """Start a single always-on agent in a new process."""
        try:
            process = multiprocessing.Process(
                target=self._run_agent_process,
                args=(agent_type,),
                name=f"agent-{agent_type.value}",
                daemon=True,
            )
            process.start()

            self._processes[agent_type] = process
            self._agent_status[agent_type] = AgentStatus.RUNNING

            logger.info(
                "agent_process_started",
                agent=agent_type.value,
                pid=process.pid
            )
            return True

        except Exception as e:
            logger.error(
                "agent_process_start_failed",
                agent=agent_type.value,
                error=str(e)
            )
            self._agent_status[agent_type] = AgentStatus.CRASHED
            return False

    def _check_processes(self) -> None:
        """Check health of always-on agent processes. Restart if crashed."""
        for agent_type, process in list(self._processes.items()):
            if not process.is_alive():
                exit_code = process.exitcode
                logger.warning(
                    "agent_process_died",
                    agent=agent_type.value,
                    exit_code=exit_code,
                    pid=process.pid
                )

                self._agent_status[agent_type] = AgentStatus.CRASHED
                self._restart_counts[agent_type] += 1

                if self._restart_counts[agent_type] <= MAX_RESTART_ATTEMPTS:
                    logger.info(
                        "restarting_agent",
                        agent=agent_type.value,
                        attempt=self._restart_counts[agent_type],
                        max_attempts=MAX_RESTART_ATTEMPTS
                    )
                    time.sleep(RESTART_COOLDOWN_SECONDS)
                    self._start_agent_process(agent_type)
                else:
                    logger.error(
                        "agent_max_restarts_exceeded",
                        agent=agent_type.value,
                        attempts=self._restart_counts[agent_type]
                    )

    # -------------------------------------------------------------------------
    # Scheduled Agent Execution
    # -------------------------------------------------------------------------

    def _run_scheduled_task(self, agent_type: AgentType, task_name: str) -> None:
        """Run a scheduled agent task in the main process."""
        task_key = f"{agent_type.value}:{task_name}:{date.today()}"

        if task_key in self._tasks_run_today:
            return

        if self._agent_status.get(agent_type) == AgentStatus.DISABLED:
            return

        logger.info(
            "scheduled_task_starting",
            agent=agent_type.value,
            task=task_name
        )

        try:
            agent = self._create_agent(agent_type)

            if not agent.health_check():
                logger.error("scheduled_agent_unhealthy", agent=agent_type.value)
                return

            agent.run()

            self._tasks_run_today.add(task_key)

            logger.info(
                "scheduled_task_completed",
                agent=agent_type.value,
                task=task_name,
                summary=agent.get_daily_summary()
            )

        except Exception as e:
            logger.error(
                "scheduled_task_failed",
                agent=agent_type.value,
                task=task_name,
                error=str(e)
            )

    def _check_schedule(self) -> None:
        """Check if any scheduled tasks should run now."""
        now = datetime.now(timezone.utc)
        current_hour = now.hour

        tasks = SCHEDULE.get(current_hour, [])
        for agent_type, task_name in tasks:
            self._run_scheduled_task(agent_type, task_name)

    def _reset_daily_state(self) -> None:
        """Reset daily tracking when the date changes."""
        today = date.today()
        if today != self._last_date:
            logger.info(
                "daily_reset",
                old_date=str(self._last_date),
                new_date=str(today)
            )
            self._tasks_run_today.clear()
            self._last_date = today

            # Reset restart counts daily
            for agent_type in self._restart_counts:
                self._restart_counts[agent_type] = 0

    # -------------------------------------------------------------------------
    # Metrics Collection
    # -------------------------------------------------------------------------

    def get_system_status(self) -> Dict:
        """Get status of all agents and overall system health."""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'date': str(date.today()),
            'agents': {},
            'processes': {},
            'tasks_run_today': list(self._tasks_run_today),
        }

        for agent_type, agent_status in self._agent_status.items():
            process = self._processes.get(agent_type)
            status['agents'][agent_type.value] = {
                'status': agent_status.value,
                'restart_count': self._restart_counts.get(agent_type, 0),
                'pid': process.pid if process and process.is_alive() else None,
            }

        # Total signups from Supabase
        status['total_signups'] = self.db.get_total_signups()

        return status

    def _log_daily_summary(self) -> None:
        """Log a daily summary of agent activity."""
        status = self.get_system_status()

        running = sum(
            1 for a in status['agents'].values()
            if a['status'] == AgentStatus.RUNNING.value
        )
        crashed = sum(
            1 for a in status['agents'].values()
            if a['status'] == AgentStatus.CRASHED.value
        )

        logger.info(
            "daily_summary",
            date=status['date'],
            agents_running=running,
            agents_crashed=crashed,
            tasks_completed=len(status['tasks_run_today']),
            total_signups=status['total_signups'],
        )

    # -------------------------------------------------------------------------
    # Main Loop
    # -------------------------------------------------------------------------

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        logger.info("shutdown_signal_received", signal=signum)
        self._shutdown = True

    def run(self) -> None:
        """
        Start the orchestrator main loop.

        1. Starts always-on agents (Discord, Telegram, Community)
        2. Enters main loop:
           - Checks schedule for due tasks
           - Monitors always-on process health
           - Resets daily state at midnight
        3. Runs until shutdown signal received
        """
        logger.info(
            "orchestrator_starting",
            date=str(date.today()),
            enabled_agents=[
                a.value for a, s in self._agent_status.items()
                if s != AgentStatus.DISABLED
            ]
        )

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Start always-on agents in separate processes
        self._start_always_on_agents()

        # Give processes time to initialize
        time.sleep(5)

        logger.info("orchestrator_main_loop_starting")

        last_health_check = datetime.now(timezone.utc)
        last_summary = datetime.now(timezone.utc)

        while not self._shutdown:
            try:
                now = datetime.now(timezone.utc)

                # Reset daily state at midnight
                self._reset_daily_state()

                # Check scheduled tasks every minute
                self._check_schedule()

                # Health check always-on processes every 5 minutes
                if (now - last_health_check).total_seconds() >= 300:
                    self._check_processes()
                    last_health_check = now

                # Log daily summary every 6 hours
                if (now - last_summary).total_seconds() >= 21600:
                    self._log_daily_summary()
                    last_summary = now

                # Sleep for 60 seconds before next check
                time.sleep(60)

            except Exception as e:
                logger.error("orchestrator_loop_error", error=str(e))
                time.sleep(30)

        # Graceful shutdown
        self._shutdown_agents()

    def _shutdown_agents(self) -> None:
        """Terminate all running agent processes."""
        logger.info("shutting_down_agents")

        for agent_type, process in self._processes.items():
            if process.is_alive():
                logger.info("terminating_agent", agent=agent_type.value, pid=process.pid)
                process.terminate()
                process.join(timeout=10)

                if process.is_alive():
                    logger.warning("force_killing_agent", agent=agent_type.value)
                    process.kill()

        logger.info("all_agents_stopped")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the RepEscrow AI agent orchestrator."""
    setup_logging()
    logger.info("repescrow_orchestrator_boot")

    orchestrator = Orchestrator()

    # Print startup status
    status = orchestrator.get_system_status()
    for agent_name, agent_info in status['agents'].items():
        logger.info(
            "agent_config",
            agent=agent_name,
            status=agent_info['status']
        )

    orchestrator.run()


if __name__ == "__main__":
    main()
