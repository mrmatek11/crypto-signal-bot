#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Entrypoint for Docker — przekazuje env vars jako CLI args
# ═══════════════════════════════════════════════════════════

set -e

echo "🚀 Crypto Signal Bot — Starting..."
echo "   Mode: 📡 ALERT ONLY (no execution)"
echo "   Symbols: ${SYMBOLS:-BTC/USDT,ETH/USDT,SOL/USDT}"
echo "   Timeframes: ${TIMEFRAMES:-5m,15m,1h}"
echo "   Trend filter: ${TREND_FILTER:-alert}"
echo "   Market: ${MARKET:-crypto}"
echo "   AI Sentiment: ${SENTIMENT:-false}"
echo "═════════════════════════════════════════════════════════"

# Build command
ARGS=""

# Webhook (required)
if [ -n "$DISCORD_WEBHOOK" ]; then
    ARGS="$ARGS --webhook $DISCORD_WEBHOOK"
else
    ARGS="$ARGS --test"
    echo "⚠️ No DISCORD_WEBHOOK set — running in TEST mode"
fi

# Symbols
if [ -n "$SYMBOLS" ]; then
    ARGS="$ARGS --symbols $SYMBOLS"
fi

# Timeframes
if [ -n "$TIMEFRAMES" ]; then
    ARGS="$ARGS --timeframes $TIMEFRAMES"
fi

# Scan interval
if [ -n "$SCAN_INTERVAL" ]; then
    ARGS="$ARGS --interval $SCAN_INTERVAL"
fi

# Trend filter
if [ -n "$TREND_FILTER" ]; then
    ARGS="$ARGS --trend-filter $TREND_FILTER"
fi

# Market source
if [ -n "$MARKET" ] && [ "$MARKET" != "crypto" ]; then
    ARGS="$ARGS --market $MARKET"
fi

# Sentiment
if [ "$SENTIMENT" = "true" ]; then
    ARGS="$ARGS --sentiment"
fi

# CryptoPanic key (PŁATNY, opcjonalny)
if [ -n "$CRYPTOPANIC_KEY" ]; then
    ARGS="$ARGS --cryptopanic-key $CRYPTOPANIC_KEY"
fi

# Finnhub key (darmowy, opcjonalny)
if [ -n "$FINNHUB_KEY" ]; then
    ARGS="$ARGS --finnhub-key $FINNHUB_KEY"
fi

# Position size
if [ -n "$POSITION_SIZE" ]; then
    ARGS="$ARGS --position-size $POSITION_SIZE"
fi

# Log level
if [ -n "$LOG_LEVEL" ]; then
    ARGS="$ARGS --log $LOG_LEVEL"
fi

# Execute
exec python3 bot.py $ARGS
