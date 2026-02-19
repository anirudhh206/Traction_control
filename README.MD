# 🚀 Traction Control

> **AI-Powered Multi-Channel Growth Engine for Web3 Products**

An autonomous agent system that generates user signups and traction across 7+ platforms simultaneously. Built for [RepEscrow](https://repescrow.xyz), but configurable for any product.


---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Agents](#-agents)
- [Monitoring](#-monitoring)
- [Costs](#-costs)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)

---

## 🎯 Overview

**Traction Control** is an intelligent, multi-agent system designed to automate customer acquisition across multiple platforms. Instead of manually posting, commenting, and engaging on Discord, Telegram, Twitter, Reddit, and more — let AI agents do it 24/7.

### The Problem It Solves

Launching a new product (especially in Web3) requires constant presence across dozens of communities. You need to:
- Answer questions in Discord servers
- Reply to relevant Twitter threads
- Comment on HackerNews discussions
- Send personalized cold emails
- Manage your own community
- Track every interaction

**Doing this manually is exhausting and doesn't scale.**

### The Solution

7 AI-powered agents that work in parallel:
1. **Discord Agent** — Monitors 15+ external servers, responds to keywords
2. **Telegram Agent** — Engages in 20+ Web3 groups
3. **Twitter Agent** — Posts threads, replies to relevant tweets
4. **Email Agent** — Sends personalized cold outreach
5. **Forum Agent** — Comments on HackerNews, IndieHackers, Reddit
6. **Community Agent** — Manages YOUR Discord server (welcomes, support, daily content)
7. **Reddit Agent** — Finds and engages with relevant subreddit discussions

All agents use **Google Gemini** (free tier!) to generate human-like, contextually-aware responses.

---

## ✨ Features

### 🤖 Autonomous Operation
- Runs 24/7 without human intervention
- Auto-responds to keywords across platforms
- Tracks all prospects and interactions in database

### 🧠 AI-Powered Responses
- Uses Google Gemini 1.5 for natural language generation
- Context-aware replies (knows your product inside-out)
- Adjustable temperature for creative vs. factual responses

### 📊 Built-in Analytics
- Supabase database tracks every action
- Daily metrics: impressions, engagements, conversions
- Prospect scoring system (1-10 based on engagement quality)

### 🛡️ Safety Features
- Rate limiting (configurable per platform)
- Retry logic with exponential backoff
- Graceful shutdown (Ctrl+C safe)
- Dry-run mode for testing

### 🎛️ Highly Configurable
- Enable/disable agents individually
- Adjust posting frequency per platform
- Customize product copy and messaging
- Multi-environment support (dev/staging/prod)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                           │
│         (Coordinates all agents, handles scheduling)        │
└────────┬────────┬────────┬────────┬────────┬────────┬──────┘
         │        │        │        │        │        │
    ┌────▼───┐ ┌─▼────┐ ┌─▼─────┐ ┌▼─────┐ ┌▼────┐ ┌▼─────┐
    │Discord │ │Telegram│ │Twitter│ │Email │ │Forum│ │Reddit│
    │ Agent  │ │ Agent  │ │ Agent │ │Agent │ │Agent│ │Agent │
    └────┬───┘ └──┬────┘ └──┬────┘ └──┬───┘ └─┬───┘ └──┬───┘
         │        │         │         │       │        │
         └────────┴─────────┴─────────┴───────┴────────┘
                            │
                    ┌───────▼────────┐
                    │  GEMINI CLIENT │
                    │ (AI Generator) │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │    SUPABASE    │
                    │   (Database)   │
                    └────────────────┘
```

### Tech Stack

- **Language:** Python 3.11+
- **AI:** Google Gemini 1.5 (Flash & Pro)
- **Database:** Supabase (PostgreSQL)
- **Logging:** Structlog (JSON structured logs)
- **Orchestration:** Multiprocessing (one process per agent)
- **Config:** Pydantic Settings (type-safe .env loading)

### Key Libraries

```python
anthropic          # (Legacy) Claude AI SDK
google-genai       # Google Gemini SDK
discord.py         # Discord bot framework
python-telegram-bot # Telegram bot API
tweepy             # Twitter API v2
sendgrid           # Email delivery
praw               # Reddit API
supabase           # Database client
structlog          # Structured logging
tenacity           # Retry logic
pydantic           # Settings validation
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager
- Git (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/traction-control.git
cd traction-control/ai-agents
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

```bash
# Copy the example .env
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

**Minimum required keys:**
```env
GEMINI_API_KEY=your-gemini-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### 4. Set Up Database

1. Go to [supabase.com](https://supabase.com) and create a project
2. Run the schema SQL (see [docs/database-schema.sql](docs/database-schema.sql))
3. Copy your URL and anon key to `.env`

### 5. Run It!

```bash
# Test mode (no real API calls)
python main.py --dry-run

# Production mode (live agents)
python main.py

# Run specific agents only
python main.py --agents discord telegram email
```

### 6. Monitor

Watch the logs in real-time:
```bash
python main.py 2>&1 | tee logs.txt
```

Check your Supabase dashboard to see prospects being tracked!

---

## ⚙️ Configuration

### Environment Variables

All configuration happens via `.env` file:

```env
# ── AI API ────────────────────────────────────────────
GEMINI_API_KEY=your-key-here

# ── Database ──────────────────────────────────────────
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-anon-key

# ── Platform Credentials ──────────────────────────────
DISCORD_BOT_TOKEN=your-token
TELEGRAM_BOT_TOKEN=your-token
TWITTER_USERNAME=your-handle
TWITTER_PASSWORD=your-password
TWITTER_EMAIL=your-email
SENDGRID_API_KEY=your-key
REDDIT_CLIENT_ID=your-id
REDDIT_CLIENT_SECRET=your-secret
REDDIT_USERNAME=your-username
REDDIT_PASSWORD=your-password

# ── Product Info ──────────────────────────────────────
PRODUCT_NAME=RepEscrow
PRODUCT_URL=https://repescrow.xyz
PRODUCT_TAGLINE=Reputation-weighted escrow for Web3

# ── Rate Limits ───────────────────────────────────────
MAX_DISCORD_MESSAGES_PER_DAY=30
MAX_TELEGRAM_MESSAGES_PER_DAY=25
MAX_EMAILS_PER_DAY=100
MAX_TWITTER_POSTS_PER_DAY=6
MAX_TWITTER_REPLIES_PER_DAY=100
MAX_REDDIT_POSTS_PER_DAY=10
MAX_REDDIT_COMMENTS_PER_DAY=20

# ── Agent Control ─────────────────────────────────────
ENABLE_DISCORD_AGENT=true
ENABLE_TELEGRAM_AGENT=true
ENABLE_EMAIL_AGENT=true
ENABLE_TWITTER_AGENT=true
ENABLE_FORUM_AGENT=true
ENABLE_REDDIT_AGENT=true
ENABLE_COMMUNITY_AGENT=true

# ── Logging ───────────────────────────────────────────
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Agent-Specific Settings

Each agent has configurable behavior in `config.py`:

```python
class Settings(BaseSettings):
    # Rate limits (per day)
    max_discord_messages_per_day: int = 30
    max_emails_per_day: int = 100
    
    # Feature flags
    enable_discord_agent: bool = True
    enable_email_agent: bool = True
    
    # Product messaging
    product_name: str = "RepEscrow"
    product_tagline: str = "..."
```

---

## 🤖 Agents

### Discord Agent
**Purpose:** Monitor external Discord servers for relevant conversations

**How it works:**
1. Joins 15+ target servers (Solana, Phantom, Web3 communities)
2. Monitors channels for keywords: "escrow", "need developer", "hiring", etc.
3. Generates contextual replies using Gemini
4. Tracks prospects in database

**Setup:**
1. Create Discord bot at [discord.com/developers](https://discord.com/developers/applications)
2. Enable "Message Content Intent" in bot settings
3. Invite bot to target servers
4. Add token to `.env`

**Keywords monitored:**
```python
KEYWORDS = [
    "looking for developer",
    "need escrow",
    "payment protection",
    "hiring freelancer",
    "web3 developer",
    # ... 20+ more
]
```

---

### Telegram Agent
**Purpose:** Engage in Web3 Telegram groups

**How it works:**
1. Monitors 20+ target groups
2. Responds to questions about escrow, payments, Web3 services
3. Sends occasional value-add messages (not spam)
4. Tracks engagement metrics

**Setup:**
1. Create bot via [@BotFather](https://t.me/botfather)
2. Add bot to target groups (need admin permission)
3. Add token to `.env`

**Target groups:**
- Solana developers
- Web3 freelancers
- Crypto payment discussions
- DeFi communities

---

### Twitter Agent
**Purpose:** Automated Twitter presence

**How it works:**
1. Posts 2-3 threads per day about Web3, escrow, reputation systems
2. Monitors keywords: "web3", "escrow", "solana", "freelance"
3. Replies to relevant tweets (not spammy)
4. Tracks impressions and engagements

**Setup:**
1. Apply for Twitter API access ($100/month Basic tier)
2. Get API keys and tokens
3. Add credentials to `.env`

**Content strategy:**
- **Monday:** Motivational thread (building in public)
- **Wednesday:** Technical deep-dive
- **Friday:** Weekly recap + metrics

---

### Email Agent
**Purpose:** Personalized cold outreach

**How it works:**
1. Targets Web3 freelancers, dev shops, audit firms
2. Generates personalized emails using Gemini
3. Sends via SendGrid (100/day free tier)
4. Tracks opens, clicks, replies

**Setup:**
1. Get SendGrid API key ([sendgrid.com](https://sendgrid.com))
2. Verify sender email
3. Add key to `.env`

**Email types:**
- Cold outreach to vendors
- Follow-ups (3-day, 7-day)
- Newsletter (weekly product updates)

---

### Forum Agent
**Purpose:** Engage on HackerNews, IndieHackers, Reddit

**How it works:**
1. Monitors "Show HN", "Ask HN" posts
2. Comments on relevant discussions
3. Shares insights (not promotional)
4. Builds credibility over time

**Setup:**
- HackerNews: Uses API (no auth needed)
- IndieHackers: Web scraping + manual posting
- Reddit: Requires API credentials

**Best practices:**
- Contribute value first, mention product second
- Follow community rules (no spam)
- Engage authentically

---

### Community Agent
**Purpose:** Manage YOUR Discord server

**How it works:**
1. Welcomes new members with onboarding message
2. Answers support questions via AI
3. Posts daily content (tips, updates, engagement prompts)
4. Tracks community health metrics

**Setup:**
1. Create Discord server for your product
2. Add bot to YOUR server
3. Create channels: #welcome, #support, #general

**Daily content schedule:**
- **Monday:** Motivation / success story
- **Tuesday:** Platform tip
- **Wednesday:** Escrow best practices
- **Thursday:** Building journey update
- **Friday:** Feature highlight
- **Saturday:** Vendor showcase
- **Sunday:** Weekly stats

---

### Reddit Agent
**Purpose:** Find and engage with Reddit discussions

**How it works:**
1. Monitors subreddits: r/solana, r/web3, r/freelance, r/cryptocurrency
2. Comments on relevant posts
3. Answers questions, shares expertise
4. Avoids promotional content

**Setup:**
1. Create Reddit app at [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Get client ID and secret
3. Add credentials to `.env`

**Karma requirements:**
- Needs 50+ comment karma to be effective
- Build karma slowly by contributing value

---

## 📊 Monitoring

### Real-Time Logs

Logs are structured JSON (production) or colorized text (development):

```bash
# Watch logs in real-time
tail -f logs.txt

# Filter for specific agent
grep "discord_agent" logs.txt

# Count prospects tracked today
grep "prospect_tracked" logs.txt | wc -l
```

### Supabase Dashboard

Check your database for:

**Prospects Table:**
- All leads collected
- Platform source
- Engagement score (1-10)
- Conversion status

**Metrics Table:**
- Daily impressions
- Engagements
- Conversations started
- Signups driven

**Activities Table:**
- Every action taken
- Agent name
- Timestamp
- Details (JSON)

### Health Checks

Built-in health check endpoint:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "agents": {
    "discord": "running",
    "telegram": "running",
    "email": "running",
    "twitter": "running",
    "forum": "running",
    "reddit": "running",
    "community": "running"
  },
  "uptime_seconds": 86400,
  "prospects_tracked_today": 47
}
```

---

## 💰 Costs

### Free Tier (0-100 signups/month)

| Service | Cost | Notes |
|---------|------|-------|
| **Google Gemini** | $0 | 1,500 requests/day free |
| **Supabase** | $0 | 500MB database, 2GB bandwidth |
| **SendGrid** | $0 | 100 emails/day |
| **Discord Bot** | $0 | Unlimited |
| **Telegram Bot** | $0 | Unlimited |
| **Reddit API** | $0 | 60 requests/min |
| **TOTAL** | **$0/month** | 🎉 |

### Paid Tier (100-1000 signups/month)

| Service | Cost | When You Need It |
|---------|------|------------------|
| **Twitter API** | $100/month | For automated posting |
| **Gemini Pro** | ~$5-10/month | If you exceed 1,500 req/day |
| **Supabase Pro** | $25/month | If you exceed 500MB database |
| **SendGrid** | $20/month | For 1,500 emails/day |
| **TOTAL** | **~$150/month** | At scale |




### v1.0 (Current)
- ✅ 7 agent types
- ✅ Google Gemini integration
- ✅ Supabase database
- ✅ Rate limiting
- ✅ Graceful shutdown

### v1.1 (Next 30 days)
- [ ] Web dashboard for monitoring
- [ ] Email templates library
- [ ] A/B testing for messaging
- [ ] Webhook integrations
- [ ] Slack notifications

### v1.2 (Next 60 days)
- [ ] LinkedIn agent
- [ ] YouTube comment agent
- [ ] Automated lead qualification
- [ ] CRM integration (HubSpot, Salesforce)
- [ ] Multi-language support

### v2.0 (Next 90 days)
- [ ] Fine-tuned models (product-specific)
- [ ] Voice/video agents (Discord voice channels)
- [ ] Predictive analytics (which prospects convert)
- [ ] Auto-optimization (learns what works)
- [ ] White-label SaaS offering

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Ways to Contribute

1. **Report bugs** — Open an issue with reproduction steps
2. **Suggest features** — Describe your use case
3. **Improve docs** — Fix typos, add examples
4. **Add agents** — Build a new platform integration
5. **Optimize prompts** — Make AI responses better

### Development Setup

```bash
# Clone repo
git clone https://github.com/your-org/traction-control.git
cd traction-control/ai-agents

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linter
black . && flake8 .

# Run type checker
mypy .
```

### Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-agent`)
3. Make your changes
4. Add tests
5. Run linters and tests
6. Commit with clear message
7. Push to your fork
8. Open a Pull Request

### Code Style

- **Black** for formatting (line length 88)
- **Type hints** everywhere (mypy strict mode)
- **Docstrings** for all public functions (Google style)
- **Tests** for new features (pytest)

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [Google Gemini](https://deepmind.google/technologies/gemini/) — AI generation
- [Supabase](https://supabase.com) — Database
- [Discord.py](https://discordpy.readthedocs.io/) — Discord bots
- [python-telegram-bot](https://python-telegram-bot.org/) — Telegram bots
- [Tweepy](https://www.tweepy.org/) — Twitter API
- [SendGrid](https://sendgrid.com) — Email delivery

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/your-org/traction-control/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-org/traction-control/discussions)
- **Email:** support@repescrow.xyz
- **Discord:** [Join our community](https://discord.gg/repescrow)

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=your-org/traction-control&type=Date)](https://star-history.com/#your-org/traction-control&Date)

---

<p align="center">
  <b>Built with ❤️ for the Web3 community</b><br>
  <sub>Automate your growth. Focus on building.</sub>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-agents">Agents</a> •
  <a href="#-costs">Costs</a> •
  <a href="#-roadmap">Roadmap</a>
</p>