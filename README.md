# Multi-Asset Signal Bot v4 — NWO + Stoch(7,3,2) + CVD + GLM AI Analyst + Market Scanner

> **Real-time trading signal bot** with Neural Weight Oscillator, Stochastic RSI, CVD analysis, AI-powered signal scoring, daily briefings, market scanner, and end-of-day summaries — all delivered to **Discord**.

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![Discord](https://img.shields.io/badge/Discord-Webhooks-5865F2?logo=discord)
![GLM AI](https://img.shields.io/badge/AI-GLM_4_Flash-9C27B0?logo=openai)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Market Scanner (NEW)](#-market-scanner-kombajn)
- [Strategy Details](#-strategy-details-nwo--stoch--cvd)
- [GLM AI Analyst](#-glm-ai-analyst)
- [Supported Markets](#-supported-markets)
- [Discord Notifications](#-discord-notifications)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [CLI Reference](#-cli-reference)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)

---

## 🎯 Overview

Multi-Asset Signal Bot is a Python-based trading signal scanner that continuously monitors cryptocurrency, commodities, forex, and stock index markets. It combines three powerful indicators — **Neural Weight Oscillator (NWO)**, **Stochastic (7,3,2)**, and **CVD (Cumulative Volume Delta)** — to generate high-quality trading signals. Signals are optionally evaluated by a **GLM AI Analyst** (Zhipu AI ChatGLM) and delivered to Discord with rich embeds.

The bot features a **Market Scanner** that continuously analyzes the market — volatility spikes, support/resistance levels, trading sessions, and correlation divergences — keeping you informed even when there are no signals.

The bot can operate in **ALERT ONLY** mode (default) or **AUTO-TRADE** mode with position tracking, stop-loss/take-profit management, and automatic position closing.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Data Fetch  │───▶│  NWO+Stoch   │───▶│  GLM AI      │───▶│  Score/Filter│───▶│   Discord    │
│  Binance/YF  │    │  + CVD Det.  │    │  Analyst     │    │  + Cooldown  │    │  Webhook     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## ✨ Key Features

### Core Trading Engine
- **Neural Weight Oscillator (NWO)** — Custom indicator inspired by Zeiierman's PineScript oscillator, combining price momentum, volume, and volatility into a single neural-weighted signal
- **Stochastic Oscillator (7,3,2)** — %K/%D crossover detection with oversold (<20) / overbought (>80) zones
- **CVD (Cumulative Volume Delta)** — Volume flow analysis confirming buying/selling pressure
- **Multi-Timeframe Confluence** — Scans multiple timeframes (5m, 15m, 1h, 4h, 1d) and checks for signal alignment
- **Trend Filter** — EMA-based trend detection (200 EMA) with 3 modes: `alert`, `block`, or `off`

### AI-Powered Analysis (GLM AI Analyst)
- **Signal Scorer** — Every signal is scored 1-10 by AI with TAKE/WATCH/SKIP recommendation
- **Daily Market Briefing** — Morning report with market bias, key pairs, risk events, and watchlist
- **End-of-Day (EOD) Summary** — Evening recap with lessons learned, best/worst signals, and next-day outlook
- **Regime Detector** — Identifies market regime (trending/ranging/volatile/quiet) per symbol
- **Multi-TF Confluence Check** — AI validates signals against higher timeframe context

### Multi-Asset Support
- **Crypto** — BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK (via Binance/CCXT)
- **Commodities** — Gold (XAU/USD), Silver (XAG/USD) (via YFinance)
- **Forex** — EUR/USD, GBP/USD, USD/JPY, USD/PLN (via YFinance)
- **Indices** — S&P 500, DAX, Nikkei 225, WIG (Polish stock index) (via YFinance)

### Notifications & Alerts
- **Discord Rich Embeds** — Color-coded signal cards with all indicator values
- **Role Mentions** — `@role` pings for LONG/SHORT signals (configurable per direction)
- **Quiet Hours** — Suppress notifications during specified hours (e.g., 23:00–07:00 UTC)
- **Error Alerts** — Automatic error notifications (first 3 errors)
- **Status Updates** — Periodic bot health/indicator status messages

### Position Tracking
- **SQLite Database** — Persistent position storage with PnL tracking
- **Auto SL/TP** — ATR-based stop-loss and take-profit calculation
- **Position Timeout** — Auto-close positions after configurable hours
- **Max Open Positions** — Limit concurrent open positions
- **Auto-Trade Mode** — Optionally auto-open positions on confirmed signals
- **Win Rate Stats** — Track win rate, total PnL, and trade history

### News Sentiment (Optional)
- **CryptoPanic** — Crypto news aggregator sentiment
- **Finnhub** — Traditional finance news sentiment
- **NewsAPI** — General news sentiment analysis
- Signals filtered/boosted by current news sentiment

---

## 🔍 Market Scanner (KOMBAJN)

The Market Scanner runs continuously alongside signal detection, keeping you informed even when there are no trading signals. It's purely algorithmic — **zero additional API costs**.

### Features

| Feature | Frequency | Description |
|---------|-----------|-------------|
| **Market Pulse** | Every 1h | Quick market summary: top movers, fear/greed estimate, regime counts |
| **Volatility Scanner** | Every cycle | Detects unusual volatility spikes (current vol > 2x average) |
| **S/R Monitor** | Every 5th cycle | Tracks key support/resistance levels, alerts on approach/breakout |
| **Session Reporter** | Every cycle | Reports Asian, European, and US session open/close events |
| **Correlation Alert** | Every 10th cycle | Detects correlation divergences between correlated pairs |

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    MARKET SCANNER (KOMBAJN)                      │
│                                                                   │
│  1. Market Pulse (1h)    ──── Top movers, Fear/Greed, Regimes   │
│  2. Volatility Scanner   ──── Unusual vol spikes (2x threshold)  │
│  3. S/R Monitor          ──── Key levels approach/breakout        │
│  4. Session Reporter     ──── Asian/EU/US open/close alerts      │
│  5. Correlation Alert    ──── BTC vs ETH, Gold vs Silver, etc.   │
│                                                                   │
│  All alerts → Discord embeds (color-coded, zero AI cost)         │
└─────────────────────────────────────────────────────────────────┘
```

### Correlated Pairs Monitored
- BTC/USDT vs ETH/USDT
- XAU/USD vs XAG/USD (Gold vs Silver)
- SP500 vs DAX (Global indices)
- BTC/USDT vs XAU/USD (Risk-on / Risk-off)

### CLI Flags

```bash
python bot.py --no-scanner          # Disable Market Scanner entirely
python bot.py --no-scanner-pulse    # Disable Market Pulse
python bot.py --no-scanner-vol      # Disable Volatility Scanner
python bot.py --no-scanner-sr       # Disable S/R Monitor
python bot.py --no-scanner-sessions # Disable Session Reporter
python bot.py --no-scanner-corr     # Disable Correlation Alert
python bot.py --scanner-pulse 1800  # Custom pulse interval (seconds)
```

---

## 🧠 Strategy Details: NWO + Stoch + CVD

The bot uses a layered strategy approach:

### Layer 1: Neural Weight Oscillator (NWO)
```
Oscillator = Weighted combination of:
  ├── Price Momentum (close vs SMA baseline)
  ├── Volume Confirmation (volume vs SMA)
  └── Volatility (ATR-based normalization)

Histogram = Oscillator - SMA(Oscillator, signal_period)
Signal Line = SMA(Oscillator, signal_period)
```

### Layer 2: Stochastic (7,3,2)
```
%K Raw = 100 × (Close - Lowest Low) / (Highest High - Lowest Low)  [7 bars]
%K Smooth = SMA(%K, 3)
%D = SMA(%K Smooth, 2)

LONG:  %K crosses above %D in oversold zone (<20)
SHORT: %K crosses below %D in overbought zone (>80)
```

### Layer 3: CVD (Cumulative Volume Delta)
```
CVD = Running sum of signed volume:
  ┌─ Positive volume (close > open) → buying pressure
  └─ Negative volume (close < open) → selling pressure

CVD SMA = SMA(CVD, 20)
Bullish: CVD > CVD SMA
Bearish: CVD < CVD SMA
```

### Signal Confluence
| Signal | Required Conditions |
|--------|-------------------|
| **LONG** | NWO bullish crossover + Stoch oversold crossover + CVD bullish |
| **SHORT** | NWO bearish crossunder + Stoch overbought crossunder + CVD bearish |
| **Strong** | All 3 indicators align + with trend (price > EMA200) |
| **Counter-trend** | Indicators align but against trend → flagged as ⚠️ RISKY |

---

## 🤖 GLM AI Analyst

The bot integrates with **Zhipu AI ChatGLM** (glm-4-flash / glm-4 / glm-4-plus) to provide AI-powered market analysis. This is one of the most powerful features of the bot.

### 1. Signal Scorer (Real-time)
Every detected signal is sent to the AI for evaluation before being posted to Discord:

- **Score**: 1–10 (quality rating)
- **Recommendation**: `TAKE`, `WATCH`, or `SKIP`
- **Analysis**: Short textual reasoning
- **Key Factors**: List of supporting factors
- **Risks**: List of risk factors
- **Filter**: Signals scored ≤2 with SKIP recommendation are **automatically filtered out**

### 2. Daily Market Briefing 🌅
**When**: Once per day, configurable time (default: morning)
**Content**:
- Overall market bias (bullish 🟢 / bearish 🔴 / neutral ⚪ / mixed 🟡)
- Key pairs to watch with reasoning
- Risk events and warnings
- AI-curated watchlist
- Market summary narrative

### 3. End-of-Day (EOD) Summary 🌙
**When**: Once per day, configurable time (default: evening)
**Content**:
- Total signals generated today
- Signals taken vs watched vs skipped
- Best signal of the day
- Worst signal of the day
- **Lessons learned** by AI
- **Tomorrow's outlook** — AI prediction for next session
- Daily summary narrative

### 4. Regime Detector
Identifies the current market regime for each symbol:
- 📈 **Trending** — Clear directional movement
- ↔️ **Ranging** — Sideways/consolidation
- ⚡ **Volatile** — High volatility environment
- 😴 **Quiet** — Low activity

### 5. Multi-Timeframe Confluence
When a signal is detected on a lower timeframe (e.g., 5m), the AI checks higher timeframes (15m, 1h, 4h) for confluence:
- All timeframes aligned → **Strong signal**
- Mixed signals → **Reduced confidence**
- Counter to higher TF → **Flagged as risky**

---

## 📊 Supported Markets

| Asset Class | Symbols | Data Source | Timeframes |
|-------------|---------|-------------|------------|
| **Crypto** | BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT, ADA/USDT, DOGE/USDT, AVAX/USDT, DOT/USDT, LINK/USDT | Binance (CCXT) | 5m, 15m, 1h, 4h, 1d |
| **Commodities** | XAU/USD (Gold), XAG/USD (Silver) | YFinance | 1h, 4h, 1d |
| **Forex** | EUR/USD, GBP/USD, USD/JPY, USD/PLN | YFinance | 1h, 4h, 1d |
| **Indices** | SP500, DAX, NIKKEI, WIG | YFinance | 1h, 4h, 1d |

> Custom symbols can be added via CLI `--symbols` or config.

---

## 📬 Discord Notifications

### Signal Alert Example
```
🟢 LONG SIGNAL — BTC/USDT (15m)
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Price: $67,432.50
📊 Stoch K: 18.5 | D: 15.2 (Oversold crossover)
📈 NWO Osc: 2.34 | Histogram: +1.12
📉 CVD: +0.85 (Bullish)
🏷️ Trend: BULLISH (above EMA200)
📏 SL: $66,800 | TP: $68,500 (ATR-based)
🎯 Confidence: HIGH
━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GLM AI Score: 8/10 — TAKE
   Key: Strong oversold bounce + volume confirmation
   Risk: Resistance at $68,000
```

### Notification Types
| Type | Color | Description |
|------|-------|-------------|
| 🟢 **LONG Signal** | Green | Buy signal with full indicator data |
| 🔴 **SHORT Signal** | Red | Sell signal with full indicator data |
| 🧠 **Daily Briefing** | Purple | Morning AI market analysis |
| 🧠 **EOD Summary** | Indigo | Evening AI daily recap |
| 🏆 **Position WIN** | Green | Position closed in profit |
| 💔 **Position LOSS** | Red | Position closed at loss |
| | 🟠 **Volatility Alert** | Orange | Unusual volatility detected |
| | 🔵 **Market Pulse** | Cyan | Hourly market summary |
| | 🟣 **S/R Alert** | Pink | Support/resistance approach/breakout |
| | 🟢 **Session Open** | Green | Trading session opening |
| | 🔴 **Session Close** | Red | Trading session closing |
| | 🟣 **Correlation Alert** | Purple | Correlation divergence detected |
| ℹ️ **Status** | Blue | Periodic bot health update |
| ⚠️ **Error** | Orange | Bot error notification |
| 🚀 **Startup** | Green | Bot startup with config info |

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/crypto-signal-bot-v4-glm.git
cd crypto-signal-bot-v4-glm

# 2. Create config
cp .env.example .env

# 3. Edit .env with your keys
nano .env

# 4. Start the bot
docker compose up -d

# 5. View logs
docker compose logs -f
```

### Option 2: Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/crypto-signal-bot-v4-glm.git
cd crypto-signal-bot-v4-glm

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Optional: Install AI/news dependencies
pip install pyjwt      # Required for GLM AI Analyst
pip install websocket-client  # Optional: for enhanced data

# 5. Test run (no Discord, single scan)
python bot.py --test --scan

# 6. Run with Discord
python bot.py --webhook https://discord.com/api/webhooks/.../...
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# ═══ DISCORD (REQUIRED) ═══
DISCORD_WEBHOOK=https://discord.com/api/webhooks/XXXXXXXXXX/XXXXXXXXXXXXXXXXXXXX

# ═══ GLM AI ANALYST (OPTIONAL) ═══
# Get API key at: https://open.bigmodel.cn
# Format: <id>.<secret>
GLM_API_KEY=

# ═══ NEWS SENTIMENT (OPTIONAL) ═══
# Finnhub (free): https://finnhub.io/
FINNHUB_KEY=
# NewsAPI (free): https://newsapi.org/
NEWSAPI_KEY=
# CryptoPanic (optional): https://cryptopanic.com/
CRYPTOPANIC_KEY=
```

### Configuration Presets

| Preset | Description | Stoch Thresholds | Interval |
|--------|-------------|-------------------|----------|
| `default` | Balanced signals | 20/80 | 60s |
| `aggressive` | More signals, lower bar | 25/75 | 30s |
| `conservative` | Fewer, higher quality | 15/85 | 120s |
| `scalping` | Fast, short-term | 20/80 | 15s |
| `multi_asset` | All asset classes | 20/80 | 90s |

```bash
# Use a preset
python bot.py --config aggressive --webhook URL
```

---

## 🖥️ CLI Reference

### Basic Usage

```bash
# Test mode (no Discord, single scan)
python bot.py --test --scan

# Run live with Discord
python bot.py --webhook https://discord.com/api/webhooks/...

# Use configuration preset
python bot.py --config aggressive --webhook URL

# Custom symbols and timeframes
python bot.py --symbols BTC/USDT,ETH/USDT,SOL/USDT --timeframes 5m,15m,1h --webhook URL
```

### Multi-Asset

```bash
# Monitor all markets (crypto + stocks/commodities/forex/indices)
python bot.py --market both --webhook URL

# Stocks only (YFinance)
python bot.py --market stocks --webhook URL

# Custom multi-asset watchlist
python bot.py --market both --symbols BTC/USDT,XAU/USD,EUR/USD,SP500,WIG,DAX,NIKKEI --webhook URL
```

### GLM AI Analyst

```bash
# Enable GLM AI Analyst
python bot.py --glm-key YOUR_API_KEY --webhook URL

# Choose model (flash = fast/cheap, plus = best quality)
python bot.py --glm-key KEY --glm-model glm-4-flash --webhook URL
python bot.py --glm-key KEY --glm-model glm-4-plus --webhook URL

# Response language (pl or en)
python bot.py --glm-key KEY --glm-lang pl --webhook URL

# Disable GLM (use only technical signals)
python bot.py --no-glm --webhook URL
```

### Advanced Options

```bash
# Strategy selection
python bot.py --strategy nwo_stoch_cvd --webhook URL     # Full NWO + Stoch + CVD (default)
python bot.py --strategy stoch_7_3_2 --webhook URL       # Stochastic only

# Trend filter modes
python bot.py --trend-filter alert --webhook URL   # Flag counter-trend signals (default)
python bot.py --trend-filter block --webhook URL   # Block counter-trend signals entirely
python bot.py --trend-filter off --webhook URL     # No trend filtering

# Position tracking & auto-trade
python bot.py --auto-trade --position-size 100 --webhook URL
python bot.py --no-positions --webhook URL         # Disable position tracking

# Sentiment filter
python bot.py --sentiment --cryptopanic-key KEY --finnhub-key KEY --webhook URL

# Custom Stochastic thresholds
python bot.py --oversold 15 --overbought 85 --webhook URL

# Interval and exchange
python bot.py --interval 30 --exchange binance --webhook URL

# Discord role mentions
python bot.py --role-id 123456789 --webhook URL

# Logging
python bot.py --log DEBUG --webhook URL
```

### All CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--webhook`, `-w` | Discord Webhook URL | — |
| `--test`, `-t` | Test mode (no Discord) | `false` |
| `--scan` | Single scan (no loop) | `false` |
| `--config`, `-c` | Config preset | `default` |
| `--symbols` | Comma-separated symbol list | 10 crypto pairs |
| `--timeframes`, `-tf` | Comma-separated TFs | `5m,15m,1h` |
| `--oversold` | Stochastic oversold threshold | `20` |
| `--overbought` | Stochastic overbought threshold | `80` |
| `--no-crossover` | Relax K/D crossover requirement | `false` |
| `--interval` | Scan interval in seconds | `60` |
| `--exchange` | CCXT exchange name | `binance` |
| `--role-id` | Discord role ID for mentions | — |
| `--strategy` | Strategy: `nwo_stoch_cvd` or `stoch_7_3_2` | `nwo_stoch_cvd` |
| `--sentiment` | Enable news sentiment filter | `false` |
| `--no-sentiment` | Disable sentiment | `false` |
| `--market` | Market: `crypto`, `stocks`, `both` | `crypto` |
| `--trend-filter` | Trend mode: `alert`, `block`, `off` | `alert` |
| `--position-size` | Default position size (USD) | `100` |
| `--no-positions` | Disable position tracking | `false` |
| `--auto-trade` | Enable auto position opening | `false` |
| `--glm-key` | GLM API key (Zhipu AI) | — |
| `--glm-model` | GLM model: `glm-4-flash`, `glm-4`, `glm-4-plus` | `glm-4-flash` |
| `--no-glm` | Disable GLM AI Analyst | `false` |
| `--glm-lang` | GLM language: `pl`, `en` | `pl` |
| `--no-scanner` | Disable Market Scanner KOMBAJN | `false` |
| `--scanner-pulse` | Market Pulse interval (seconds) | `3600` |
| `--no-scanner-pulse` | Disable Market Pulse | `false` |
| `--no-scanner-vol` | Disable Volatility Scanner | `false` |
| `--no-scanner-sr` | Disable S/R Monitor | `false` |
| `--no-scanner-sessions` | Disable Session Reporter | `false` |
| `--no-scanner-corr` | Disable Correlation Alert | `false` |
| `--log` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────────┐
                    │            bot.py (Main Loop)            │
                    │  StochSignalBot                         │
                    │  ┌─────────┐  ┌──────────┐  ┌────────┐ │
                    │  │ Scanner │─▶│ GLM AI   │─▶│Discord │ │
                    │  │  Loop   │  │ Analyst  │  │Notifier│ │
                    │  └────┬────┘  └──────────┘  └────────┘ │
                    │       │                                  │
                    │  ┌────┴──────────┐                       │
                    │  │Market Scanner │──▶ Discord embeds     │
                    │  │               │   (Pulse, Vol, S/R,  │
                    │  └──────────────┘    Sessions, Corr)    │
                    └───────┼─────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌──────────────┐
    │data_fetcher │ │data_fetcher │ │news_sentiment │
    │  (Binance)  │ │ _yfinance   │ │  (optional)  │
    │   CCXT      │ │  YFinance   │ │ CryptoPanic   │
    └──────┬──────┘ └─────────────┘ │ Finnhub       │
           │                        │ NewsAPI       │
           ▼                        └──────────────┘
    ┌──────────────┐
    │signal_detector│──── Stochastic (7,3,2) + RSI + ATR
    │custom_strategy│──── NWO + CVD + Trend Filter
    └──────────────┘
           │
           ▼
    ┌──────────────┐     ┌──────────────┐
    │glm_analyst   │     │position_     │
    │ Signal Scorer│     │ tracker      │
    │ Daily Brief  │     │ SQLite DB    │
    │ EOD Summary  │     │ SL/TP Mgmt   │
    │ Regime Detect│     │ PnL Tracking │
    └──────────────┘     └──────────────┘
```

---

## 📁 Project Structure

```
crypto-signal-bot-v4-glm/
├── bot.py                       # Main bot loop & CLI entry point
├── config.py                    # Configuration dataclass & presets
├── signal_detector.py           # Stochastic signal detection engine
├── custom_strategy.py           # NWO + Stoch + CVD combined strategy
├── neural_weight_oscillator.py  # NWO indicator implementation
├── glm_analyst.py               # GLM AI Analyst (scorer, briefing, EOD, regime)
├── market_scanner.py            # Market Scanner KOMBAJN (pulse, vol, S/R, sessions, corr)
├── data_fetcher.py              # Crypto data (Binance/CCXT)
├── data_fetcher_yfinance.py     # Multi-asset data (YFinance)
├── discord_notifier.py          # Discord webhook notifications
├── news_sentiment.py            # News sentiment filter (CryptoPanic, Finnhub, NewsAPI)
├── position_tracker.py          # Position tracking with SQLite
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image (Python 3.11-slim)
├── docker-compose.yml           # Docker Compose with volume persistence
├── entrypoint.sh                # Docker entrypoint script
├── start.sh                     # Quick-start shell script
├── .env.example                 # Example environment configuration
└── README.md                    # This file
```

---

## 📝 Requirements

### Core (required)
- Python 3.11+
- ccxt >= 4.0.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- requests >= 2.31.0
- yfinance >= 0.2.28

### Optional
- `pyjwt` — Required for GLM AI Analyst (JWT token generation)
- `websocket-client` — Enhanced real-time data feeds

### External Services
| Service | Required? | Purpose |
|---------|-----------|---------|
| **Discord Webhook** | ✅ Yes | Signal notifications |
| **GLM API Key** (Zhipu AI) | Optional | AI signal scoring & briefings |
| **Finnhub API Key** | Optional | News sentiment |
| **NewsAPI Key** | Optional | General news sentiment |
| **CryptoPanic API Key** | Optional | Crypto news sentiment |

---

## ⚠️ Disclaimer

This bot is for **educational and informational purposes only**. It does not constitute financial advice. Trading cryptocurrencies and other financial instruments involves significant risk. Always do your own research and never trade with money you can't afford to lose.

---

## 📜 License

MIT License — feel free to modify and use for your own purposes.

---

<p align="center">
  Built with Python | Powered by NWO + Stochastic + CVD + GLM AI + Market Scanner
</p>