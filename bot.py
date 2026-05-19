#!/usr/bin/env python3
"""
Multi-Asset Signal Bot - NWO + Stoch(7,3,2) + CVD + GLM AI Analyst -> Discord

Neural Weight Oscillator (Zeiierman) + Stochastic + CVD
Monitoruje krypto, surowce, forex i indeksy na zywo
Wysyla alerty na Discord z AI news sentiment i GLM AI Analyst

v4: + Market Scanner KOMBAJN (Market Pulse, Volatility Scanner, S/R Monitor,
    Session Reporter, Correlation Alert)
v3: + GLM AI Analyst (Signal Scorer, Daily Briefing, Regime Detector,
    Multi-TF Confluence, EOD Summary)
    + Multi-asset (zloto, srebro, EUR/USD, WIG, S&P 500, DAX, Nikkei 225)

Uzycie:
  python bot.py --test --scan
  python bot.py --webhook URL --strategy nwo_stoch_cvd
  python bot.py --config aggressive --sentiment --glm-key KEY
  python bot.py --market both --symbols BTC/USDT,XAU/USD,SP500,EUR/USD,WIG
"""

import sys
import os
import time
import signal
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

# Dodaj sciezke projektu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig, config_aggressive, config_conservative, config_scalping, config_multi_asset
from signal_detector import SignalDetector, Signal
from data_fetcher import DataFetcher
from discord_notifier import DiscordNotifier
from custom_strategy import STRATEGY_REGISTRY, get_sentiment_engine

# --- Logging ---

def setup_logging(level: str = "INFO"):
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%H:%M:%S"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt, datefmt=datefmt)
    return logging.getLogger("MultiAssetBot")

logger = setup_logging()


# ==============================================================================
# MAIN BOT CLASS
# ==============================================================================

class StochSignalBot:
    """
    Glowna klasa bota sygnalowego.
    Petla: pobierz dane -> wykryj sygnaly -> GLM AI ocen -> Market Scanner -> Discord -> czekaj.
    KOMBAJN: caly czas analizuje rynek, nie tylko czeka na sygnaly.
    """

    def __init__(self, config: BotConfig, test_mode: bool = False):
        self.config = config
        self.test_mode = test_mode
        self._running = False
        self._scan_count = 0
        self._signals_sent = 0
        self._errors = 0
        self._cooldowns: Dict[str, float] = {}
        self._last_status_time = 0

        # Inicjalizuj detektor
        self.detector = SignalDetector(
            stoch_k_length=config.stoch_k_length,
            stoch_k_smooth=config.stoch_k_smooth,
            stoch_d_smooth=config.stoch_d_smooth,
            oversold_threshold=config.oversold_threshold,
            overbought_threshold=config.overbought_threshold,
            require_crossover=config.require_crossover,
            rsi_filter=config.rsi_filter,
            rsi_oversold=config.rsi_oversold,
            rsi_overbought=config.rsi_overbought,
            volume_filter=config.volume_filter,
            volume_mult=config.volume_mult,
        )

        # --- Data fetcher (crypto / stocks / unified) ---
        self._yf_fetcher = None
        self._unified_fetcher = None

        if config.market_source in ("stocks", "both"):
            try:
                from data_fetcher_yfinance import YFinanceDataFetcher, UnifiedDataFetcher
                if config.market_source == "both":
                    self._unified_fetcher = UnifiedDataFetcher()
                    self.fetcher = self._unified_fetcher
                    logger.info("Unified data fetcher: Crypto (Binance) + TradFi (YFinance)")
                else:
                    self._yf_fetcher = YFinanceDataFetcher()
                    self.fetcher = self._yf_fetcher
                    logger.info("Stock data fetcher: YFinance (multi-asset)")
            except ImportError:
                logger.warning("yfinance nie zainstalowany! Fallback do Binance. pip install yfinance")
                self.fetcher = DataFetcher(
                    exchange_id=config.exchange,
                    rate_limit_ms=config.rate_limit_ms,
                    cache_ttl_seconds=config.cache_ttl,
                    candles_per_fetch=config.candles_per_fetch,
                )
        else:
            self.fetcher = DataFetcher(
                exchange_id=config.exchange,
                rate_limit_ms=config.rate_limit_ms,
                cache_ttl_seconds=config.cache_ttl,
                candles_per_fetch=config.candles_per_fetch,
            )

        # --- Discord notifier ---
        if not test_mode and config.discord_webhook_url:
            self.notifier = DiscordNotifier(
                webhook_url=config.discord_webhook_url,
                bot_name=config.discord_bot_name,
                avatar_url=config.discord_avatar_url,
                mention_role_id=config.discord_role_id,
                mention_on_long=config.mention_on_long,
                mention_on_short=config.mention_on_short,
                quiet_hours=config.quiet_hours,
            )
        else:
            self.notifier = None

        # --- Position tracker ---
        self.position_tracker = None
        if config.use_position_tracking:
            try:
                from position_tracker import PositionTracker
                self.position_tracker = PositionTracker(
                    db_path=config.position_db_path,
                    timeout_hours=config.position_timeout_hours,
                    default_size_usd=config.default_position_size_usd,
                    max_open=config.max_open_positions,
                )
                logger.info(f"Position tracker: ENABLED (db={config.position_db_path})")
            except Exception as e:
                logger.warning(f"Position tracker init failed: {e}")

        # --- Sentiment engine ---
        self.sentiment_engine = None
        if config.use_sentiment:
            try:
                from news_sentiment import SentimentEngine
                self.sentiment_engine = SentimentEngine(
                    cryptopanic_key=config.cryptopanic_api_key,
                    finnhub_key=config.finnhub_api_key,
                    newsapi_key=config.newsapi_key,
                    refresh_interval=config.sentiment_refresh_interval,
                )
                logger.info("AI Sentiment filter: ENABLED")
                # Propagate sentiment flag to custom_strategy module
                try:
                    from custom_strategy import set_sentiment_enabled
                    set_sentiment_enabled(True)
                    logger.info("Sentiment filter propagated to strategy")
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Sentiment engine init failed: {e}")

        # --- GLM AI Analyst ---
        self.glm_analyst = None
        if config.use_glm_analyst and config.glm_api_key:
            try:
                from glm_analyst import GLMAnalyst
                self.glm_analyst = GLMAnalyst(
                    api_key=config.glm_api_key,
                    model=config.glm_model,
                    enabled=True,
                    language=config.glm_language,
                    signal_scorer=config.glm_signal_scorer,
                    daily_briefing=config.glm_daily_briefing,
                    regime_detector=config.glm_regime_detector,
                    multi_tf_confluence=config.glm_multi_tf_confluence,
                    eod_summary=config.glm_eod_summary,
                )
                logger.info(f"GLM AI Analyst: ENABLED (model={config.glm_model})")
            except Exception as e:
                logger.warning(f"GLM AI Analyst init failed: {e}")

        # --- Market Scanner (KOMBAJN) ---
        self.market_scanner = None
        if config.use_market_scanner:
            try:
                from market_scanner import MarketScanner
                self.market_scanner = MarketScanner(
                    pulse_interval=config.scanner_pulse_interval,
                    volatility_threshold=config.scanner_volatility_threshold,
                    sr_lookback=config.scanner_sr_lookback,
                    sr_proximity_pct=config.scanner_sr_proximity_pct,
                    corr_divergence_threshold=config.scanner_corr_threshold,
                    enabled_pulse=config.scanner_pulse,
                    enabled_volatility=config.scanner_volatility,
                    enabled_sr=config.scanner_sr,
                    enabled_sessions=config.scanner_sessions,
                    enabled_correlation=config.scanner_correlation,
                )
                logger.info(f"Market Scanner KOMBAJN: ENABLED (pulse={config.scanner_pulse_interval}s)")
            except Exception as e:
                logger.warning(f"Market Scanner init failed: {e}")

        # --- Custom strategy ---
        self.custom_strategy_fn = None

        # --- Apply trend filter mode ---
        if config.trend_filter_mode:
            try:
                import custom_strategy
                custom_strategy.TREND_FILTER_MODE = config.trend_filter_mode
                logger.info(f"Trend filter mode: {config.trend_filter_mode}")
            except Exception:
                pass

    def run(self):
        """Uruchom glowna petle bota."""
        self._running = True

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        all_syms = self.config.get_all_symbols()
        
        logger.info("=" * 60)
        logger.info("  MULTI-ASSET SIGNAL BOT v4 (GLM AI + KOMBAJN)")
        logger.info(f"  Stochastic ({self.config.stoch_k_length}, {self.config.stoch_k_smooth}, {self.config.stoch_d_smooth})")
        logger.info(f"  Symbols: {', '.join(all_syms)}")
        logger.info(f"  Timeframes: {', '.join(self.config.timeframes)}")
        logger.info(f"  Interval: {self.config.scan_interval}s")
        logger.info(f"  Market: {self.config.market_source}")
        logger.info(f"  Trend filter: {self.config.trend_filter_mode}")
        logger.info(f"  GLM AI Analyst: {'ENABLED' if self.glm_analyst else 'DISABLED'}")
        logger.info(f"  Market Scanner: {'ENABLED' if self.market_scanner else 'DISABLED'}")
        logger.info(f"  Mode: {'AUTO-TRADE' if self.config.auto_open_positions else 'ALERT ONLY'}")
        logger.info("=" * 60)

        # Wiadomosc powitalna na Discord
        if self.notifier and not self.test_mode:
            try:
                self.notifier.send_startup_message({
                    "symbols": all_syms,
                    "timeframes": self.config.timeframes,
                    "stoch_k_length": self.config.stoch_k_length,
                    "stoch_k_smooth": self.config.stoch_k_smooth,
                    "stoch_d_smooth": self.config.stoch_d_smooth,
                    "oversold_threshold": self.config.oversold_threshold,
                    "overbought_threshold": self.config.overbought_threshold,
                    "scan_interval": self.config.scan_interval,
                    "require_crossover": self.config.require_crossover,
                    "strategy_name": "NWO + Stoch + CVD v3 + GLM AI",
                    "use_training": True,
                    "glm_analyst": self.glm_analyst is not None,
                    "commodity_symbols": self.config.commodity_symbols,
                    "forex_symbols": self.config.forex_symbols,
                    "index_symbols": self.config.index_symbols,
                })
            except Exception as e:
                logger.warning(f"Nie mozna wyslac wiadomosci powitalnej: {e}")

        # Glowna petla
        while self._running:
            try:
                self._scan_cycle()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self._errors += 1
                logger.error(f"Blad w cyklu skanowania: {e}")
                if self.notifier and self._errors <= 3:
                    try:
                        self.notifier.send_error(str(e))
                    except Exception:
                        pass

            # Czekaj do nastepnego skanu
            if self._running:
                wait_until_next = self._calculate_wait()
                if wait_until_next > 0:
                    waited = 0
                    while waited < wait_until_next and self._running:
                        time.sleep(min(5, wait_until_next - waited))
                        waited += 5

        logger.info("Bot zatrzymany.")

    def _scan_cycle(self):
        """Pojedynczy cykl skanowania wszystkich par i timeframe'ow."""
        self._scan_count += 1
        cycle_start = time.time()
        total_signals = 0

        logger.info(f"{'─'*50}")
        logger.info(f"Skan #{self._scan_count} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # --- Position tracker: check SL/TP closes ---
        if self.position_tracker:
            try:
                current_prices = self._get_current_prices()
                closed_positions = self.position_tracker.check_closes(current_prices)
                for pos in closed_positions:
                    emoji = "WIN" if pos.pnl and pos.pnl > 0 else "LOSS"
                    logger.info(f"  {emoji} POSITION CLOSED: {pos.direction} {pos.symbol} @ ${pos.close_price:,.2f} | PnL: ${pos.pnl:+,.2f}")
                    if self.notifier and not self.test_mode:
                        try:
                            self._send_position_close_notification(pos)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Position check error: {e}")

        # --- Scan symbols ---
        all_symbols = self.config.get_all_symbols()

        for timeframe in self.config.timeframes:
            logger.info(f"  TF: {timeframe}")

            for symbol in all_symbols:
                # Skip invalid TF/symbol combinations
                if not self._is_valid_tf_for_symbol(symbol, timeframe):
                    continue

                try:
                    signals = self._check_symbol(symbol, timeframe)
                    if signals:
                        for sig in signals:
                            # Check cooldown
                            cooldown_key = f"{sig.symbol}_{sig.timeframe}_{sig.signal_type}"
                            if self._is_on_cooldown(cooldown_key):
                                logger.debug(f"    {symbol}: sygnal {sig.signal_type} na cooldown")
                                continue

                            # --- GLM AI Signal Scorer ---
                            if self.glm_analyst and self.config.glm_signal_scorer:
                                try:
                                    score = self.glm_analyst.score_signal({
                                        "symbol": sig.symbol,
                                        "direction": sig.signal_type,
                                        "price": sig.price,
                                        "stoch_k": sig.k_value,
                                        "stoch_d": sig.d_value,
                                        "nwo_osc": sig.extra_data.get("osc", 0),
                                        "nwo_histogram": sig.extra_data.get("histogram", 0),
                                        "cvd": sig.extra_data.get("cvd", 0),
                                        "trend": sig.extra_data.get("trend", "?"),
                                        "atr": sig.extra_data.get("atr", 0),
                                        "sl": sig.extra_data.get("sl", 0),
                                        "tp": sig.extra_data.get("tp", 0),
                                        "source": sig.extra_data.get("source", ""),
                                        "confidence": sig.extra_data.get("confidence", "LOW"),
                                        "against_trend": sig.extra_data.get("against_trend", False),
                                    })
                                    if score:
                                        sig.extra_data["glm_score"] = score.score
                                        sig.extra_data["glm_recommendation"] = score.recommendation
                                        sig.extra_data["glm_analysis"] = score.analysis
                                        sig.extra_data["glm_key_factors"] = score.key_factors
                                        sig.extra_data["glm_risks"] = score.risks
                                        
                                        # Skip if GLM says SKIP and score <= 2
                                        if score.recommendation == "SKIP" and score.score <= 2:
                                            logger.debug(f"    {symbol}: GLM SKIP (score={score.score})")
                                            continue
                                except Exception as e:
                                    logger.debug(f"GLM scorer error: {e}")

                            # --- GLM AI: Market Regime Detector ---
                            if self.glm_analyst and self.config.glm_regime_detector and not self.test_mode:
                                try:
                                    regime_data = {
                                        "price": sig.price,
                                        "stoch_k": sig.k_value,
                                        "stoch_d": sig.d_value,
                                        "nwo_osc": sig.extra_data.get("osc", 0),
                                        "nwo_histogram": sig.extra_data.get("histogram", 0),
                                        "cvd": sig.extra_data.get("cvd", 0),
                                        "atr": sig.extra_data.get("atr", 0),
                                        "trend": sig.extra_data.get("trend", "?"),
                                    }
                                    regime = self.glm_analyst.detect_regime(sig.symbol, regime_data)
                                    if regime:
                                        sig.extra_data["glm_regime"] = regime.regime
                                        sig.extra_data["glm_regime_bias"] = regime.bias
                                except Exception:
                                    pass

                            # --- GLM AI: Multi-TF Confluence ---
                            if self.glm_analyst and self.config.glm_multi_tf_confluence and not self.test_mode:
                                try:
                                    tf_data = {}
                                    for tf in self.config.timeframes:
                                        try:
                                            tf_df = self.fetcher.fetch_ohlcv(sig.symbol, tf)
                                            if not tf_df.empty and len(tf_df) >= 120:
                                                from custom_strategy import get_current_nwo_state
                                                tf_state = get_current_nwo_state(tf_df, sig.symbol, tf)
                                                if tf_state:
                                                    tf_data[tf] = {
                                                        "stoch_k": tf_state.get("stoch_k", 0) or 0,
                                                        "stoch_d": tf_state.get("stoch_d", 0) or 0,
                                                        "nwo_osc": tf_state.get("osc", 0) or 0,
                                                        "nwo_histogram": tf_state.get("histogram", 0) or 0,
                                                        "cvd": tf_state.get("cvd", 0) or 0,
                                                        "trend": tf_state.get("trend", "?"),
                                                        "price": tf_state.get("price", 0),
                                                    }
                                        except Exception:
                                            continue
                                    if len(tf_data) >= 2:
                                        confluence = self.glm_analyst.analyze_confluence(sig.symbol, tf_data)
                                        if confluence:
                                            sig.extra_data["glm_confluence_score"] = confluence.score
                                            sig.extra_data["glm_confluence_direction"] = confluence.direction
                                            sig.extra_data["glm_confluence_strongest_tf"] = confluence.strongest_tf
                                except Exception:
                                    pass

                            # Send to Discord
                            sent = False
                            if self.notifier and not self.test_mode:
                                sent = self.notifier.send_signal(sig)
                            elif self.test_mode:
                                sent = True

                            if sent:
                                self._signals_sent += 1
                                self._cooldowns[cooldown_key] = time.time()
                                total_signals += 1

                                glm_tag = ""
                                if sig.extra_data.get("glm_score"):
                                    glm_tag = f" | GLM: {sig.extra_data['glm_score']}/10 {sig.extra_data['glm_recommendation']}"
                                
                                risk_tag = " RISKY" if sig.extra_data.get("against_trend") else ""
                                logger.info(f"    {sig.emoji} {symbol}: {sig.signal_type}{risk_tag} @ ${sig.price:,.2f} | K={sig.k_value} D={sig.d_value}{glm_tag}")

                                # Auto-open position (ONLY if auto_open_positions=True)
                                if self.position_tracker and self.config.auto_open_positions and not sig.extra_data.get("against_trend", False):
                                    try:
                                        self.position_tracker.open_position(
                                            symbol=sig.symbol,
                                            direction=sig.signal_type,
                                            entry_price=sig.price,
                                            sl=sig.extra_data.get("sl", 0),
                                            tp=sig.extra_data.get("tp", 0),
                                            timeframe=sig.timeframe,
                                            strategy=sig.strategy_name,
                                            signal_reason=sig.reason,
                                            atr=sig.extra_data.get("atr", 0),
                                            risk_level=sig.extra_data.get("risk_level", "NORMAL"),
                                        )
                                    except Exception as e:
                                        logger.debug(f"Position open error: {e}")

                except Exception as e:
                    logger.error(f"    X {symbol} {timeframe}: {e}")
                    continue

        elapsed = time.time() - cycle_start
        logger.info(f"  Skan zakonczony w {elapsed:.1f}s — sygnalow: {total_signals}")

        # --- GLM AI: Daily Briefing ---
        if self.glm_analyst and self.config.glm_daily_briefing:
            try:
                if self.glm_analyst.should_send_briefing():
                    self._send_daily_briefing()
            except Exception as e:
                logger.debug(f"GLM briefing error: {e}")

        # --- GLM AI: End-of-Day Summary ---
        if self.glm_analyst and self.config.glm_eod_summary:
            try:
                if self.glm_analyst.should_send_eod():
                    self._send_eod_summary()
            except Exception as e:
                logger.debug(f"GLM EOD error: {e}")

        # --- Market Scanner KOMBAJN ---
        if self.market_scanner and not self.test_mode:
            try:
                self._run_market_scanner(all_symbols)
            except Exception as e:
                logger.debug(f"Market Scanner error: {e}")

        # --- Clean stale cooldowns ---
        if self._scan_count % 20 == 0:
            now = time.time()
            stale = [k for k, v in self._cooldowns.items() if now - v > self.config.cooldown_per_signal]
            for k in stale:
                del self._cooldowns[k]

        # --- Periodic stats ---
        if self.position_tracker and self._scan_count % 10 == 0:
            try:
                stats = self.position_tracker.get_stats()
                if stats["total_trades"] > 0:
                    logger.info(f"  Positions: {stats['total_trades']} trades | WR: {stats['win_rate']}% | PnL: ${stats['total_pnl']:+,.2f}")
            except Exception:
                pass

        # Status update
        if self.notifier and not self.test_mode:
            if time.time() - self._last_status_time > self.config.status_interval:
                self._send_status_update()
                self._last_status_time = time.time()

    def _check_symbol(self, symbol: str, timeframe: str) -> List[Signal]:
        """Sprawdz jedna pare na jednym timeframe i zwroc sygnaly."""
        try:
            df = self.fetcher.fetch_ohlcv(symbol, timeframe)
            if df.empty:
                return []
        except Exception as e:
            logger.debug(f"Blad pobierania {symbol}: {e}")
            return []

        if self.custom_strategy_fn:
            return self.custom_strategy_fn(df, symbol, timeframe)
        else:
            return self.detector.detect(df, symbol, timeframe)

    def _is_valid_tf_for_symbol(self, symbol: str, timeframe: str) -> bool:
        """Check if timeframe is valid for symbol based on asset class."""
        try:
            from data_fetcher_yfinance import get_asset_class, ASSET_TF_OVERRIDES
            asset_class = get_asset_class(symbol)
            if asset_class in ASSET_TF_OVERRIDES:
                return timeframe in ASSET_TF_OVERRIDES[asset_class]
        except ImportError:
            pass
        return True

    def _get_current_prices(self) -> Dict[str, float]:
        """Pobierz aktualne ceny dla otwartych pozycji."""
        prices = {}
        if not self.position_tracker:
            return prices

        open_positions = self.position_tracker.get_open_positions()
        symbols_needed = list(set(p.symbol for p in open_positions))

        for symbol in symbols_needed:
            try:
                price = self.fetcher.get_latest_price(symbol) if hasattr(self.fetcher, 'get_latest_price') else None
                if price is not None:
                    prices[symbol] = price
                else:
                    df = self.fetcher.fetch_ohlcv(symbol, self.config.timeframes[0])
                    if not df.empty:
                        prices[symbol] = df['close'].iloc[-1]
            except Exception:
                pass

        return prices

    def _send_daily_briefing(self):
        """Generate and send GLM AI daily briefing."""
        if not self.glm_analyst or not self.notifier:
            return
        
        try:
            all_symbols = self.config.get_all_symbols()
            snapshot = self.glm_analyst.get_market_snapshot(
                self.fetcher, all_symbols[:15], "1h"  # Limit to 15 symbols
            )
            
            if not snapshot:
                return
            
            briefing = self.glm_analyst.generate_briefing(snapshot)
            if not briefing:
                return
            
            # Build Discord embed
            bias_emoji = {
                "bullish": "🟢📈", "bearish": "🔴📉",
                "neutral": "⚪↔️", "mixed": "🟡🔄"
            }.get(briefing.overall_bias, "⚪")
            
            key_pairs_text = "\n".join(
                f"• {p.get('symbol', '?')}: {p.get('reason', '')}"
                for p in (briefing.key_pairs or [])[:5]
            )
            
            risks_text = "\n".join(
                f"• {r}" for r in (briefing.risk_events or [])[:5]
            )
            
            watchlist_text = ", ".join(briefing.watchlist or [])[:200]
            
            fields = [
                {"name": "Overall Bias", "value": f"{bias_emoji} {briefing.overall_bias.upper()}", "inline": True},
                {"name": "Key Pairs", "value": key_pairs_text or "N/A", "inline": False},
                {"name": "Risk Events", "value": risks_text or "N/A", "inline": False},
                {"name": "Watchlist", "value": watchlist_text or "N/A", "inline": False},
                {"name": "Summary", "value": briefing.summary or "N/A", "inline": False},
            ]
            
            embed = {
                "title": "🧠 GLM AI Daily Market Briefing",
                "color": 0x9C27B0,  # Purple for AI
                "fields": fields,
                "footer": {"text": f"GLM AI Analyst | {self.config.glm_model}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            self.notifier.send_custom_embed(embed)
            logger.info("GLM Daily Briefing sent to Discord")
            
        except Exception as e:
            logger.warning(f"GLM briefing send error: {e}")

    def _send_eod_summary(self):
        """Generate and send GLM AI end-of-day summary."""
        if not self.glm_analyst or not self.notifier:
            return
        
        try:
            eod = self.glm_analyst.generate_eod_summary()
            if not eod:
                return
            
            lessons_text = "\n".join(f"• {l}" for l in (eod.lessons or [])[:5])
            
            fields = [
                {"name": "Total Signals", "value": str(eod.total_signals), "inline": True},
                {"name": "TAKE", "value": str(eod.signals_taken), "inline": True},
                {"name": "WATCH", "value": str(eod.signals_watched), "inline": True},
                {"name": "SKIP", "value": str(eod.signals_skipped), "inline": True},
                {"name": "Best Signal", "value": eod.best_signal, "inline": True},
                {"name": "Worst Signal", "value": eod.worst_signal, "inline": True},
                {"name": "Lessons", "value": lessons_text or "N/A", "inline": False},
                {"name": "Tomorrow Outlook", "value": eod.outlook or "N/A", "inline": False},
                {"name": "Summary", "value": eod.summary or "N/A", "inline": False},
            ]
            
            embed = {
                "title": "🧠 GLM AI End-of-Day Summary",
                "color": 0x3F51B5,  # Indigo
                "fields": fields,
                "footer": {"text": f"GLM AI Analyst | {self.config.glm_model}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            self.notifier.send_custom_embed(embed)
            logger.info("GLM EOD Summary sent to Discord")
            
        except Exception as e:
            logger.warning(f"GLM EOD send error: {e}")

    def _run_market_scanner(self, all_symbols: List[str]):
        """Uruchom Market Scanner KOMBAJN — caly czas analizuje rynek."""
        if not self.market_scanner or not self.notifier:
            return

        tf = self.config.timeframes[0] if self.config.timeframes else "1h"

        # 1. Market Pulse (co 1h)
        try:
            if self.market_scanner.should_send_pulse():
                pulse = self.market_scanner.generate_pulse(self.fetcher, all_symbols, tf)
                if pulse:
                    embed = self.market_scanner.format_pulse_discord(pulse)
                    self.notifier.send_custom_embed(embed)
                    logger.info("Market Pulse sent to Discord")
        except Exception as e:
            logger.debug(f"Pulse error: {e}")

        # 2. Volatility Scanner (co cykl)
        try:
            vol_alerts = self.market_scanner.scan_volatility(self.fetcher, all_symbols, tf)
            if vol_alerts:
                embed = self.market_scanner.format_volatility_discord(vol_alerts)
                if embed:
                    self.notifier.send_custom_embed(embed)
                    logger.info(f"Volatility alerts sent: {len(vol_alerts)} assets")
        except Exception as e:
            logger.debug(f"Volatility scan error: {e}")

        # 3. S/R Monitor (co 5 cykli)
        if self._scan_count % 5 == 0:
            try:
                sr_alerts = self.market_scanner.scan_sr_levels(self.fetcher, all_symbols, tf)
                if sr_alerts:
                    embed = self.market_scanner.format_sr_discord(sr_alerts)
                    if embed:
                        self.notifier.send_custom_embed(embed)
                        logger.info(f"S/R alerts sent: {len(sr_alerts)} levels")
            except Exception as e:
                logger.debug(f"S/R scan error: {e}")

        # 4. Session Reporter (co cykl — sprawdza czy sesja sie otwiera/zamyka)
        try:
            session_change = self.market_scanner.check_session_change()
            if session_change:
                event_type, session_key, session_info = session_change
                embed = self.market_scanner.format_session_discord(event_type, session_key, session_info)
                self.notifier.send_custom_embed(embed)
                logger.info(f"Session alert: {session_info.name} {event_type}")
        except Exception as e:
            logger.debug(f"Session check error: {e}")

        # 5. Correlation Alert (co 10 cykli)
        if self._scan_count % 10 == 0:
            try:
                corr_divs = self.market_scanner.scan_correlations(self.fetcher, tf)
                if corr_divs:
                    embed = self.market_scanner.format_correlation_discord(corr_divs)
                    if embed:
                        self.notifier.send_custom_embed(embed)
                        logger.info(f"Correlation alerts sent: {len(corr_divs)} pairs")
            except Exception as e:
                logger.debug(f"Correlation scan error: {e}")

    def _send_position_close_notification(self, pos):
        """Wyslij powiadomienie o zamknieciu pozycji na Discord."""
        if not self.notifier:
            return

        emoji = "WIN" if pos.pnl and pos.pnl > 0 else "LOSS"
        pnl_str = f"${pos.pnl:+,.2f}" if pos.pnl else "N/A"

        embed = {
            "title": f"{emoji} Position Closed — {pos.symbol}",
            "color": 0x00E676 if pos.pnl and pos.pnl > 0 else 0xFF1744,
            "fields": [
                {"name": "Direction", "value": pos.direction, "inline": True},
                {"name": "Entry", "value": f"${pos.entry_price:,.2f}", "inline": True},
                {"name": "Exit", "value": f"${pos.close_price:,.2f}" if pos.close_price else "N/A", "inline": True},
                {"name": "PnL", "value": f"{emoji} {pnl_str}", "inline": True},
                {"name": "Reason", "value": pos.close_reason or "N/A", "inline": True},
                {"name": "Holding", "value": f"{pos.holding_time_hours:.1f}h" if pos.holding_time_hours else "N/A", "inline": True},
            ],
            "footer": {"text": "Position Tracker | Multi-Asset Signal Bot"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.notifier.send_custom_embed(embed)

    def _is_on_cooldown(self, key: str) -> bool:
        """Sprawdz czy sygnal jest na cooldown (anti-spam)."""
        if key not in self._cooldowns:
            return False
        elapsed = time.time() - self._cooldowns[key]
        return elapsed < self.config.cooldown_per_signal

    def _calculate_wait(self) -> float:
        """Oblicz ile sekund czekac do nastepnego skanu."""
        return float(self.config.scan_interval)

    def _send_status_update(self):
        """Wyslij status bota na Discord."""
        logger.info("  Wysylam status na Discord...")
        for symbol in self.config.symbols[:3]:
            for timeframe in self.config.timeframes[:1]:
                try:
                    df = self.fetcher.fetch_ohlcv(symbol, timeframe)
                    if df.empty:
                        continue
                    values = self.detector.get_current_values(df)
                    if values and self.notifier:
                        self.notifier.send_status(
                            symbol, timeframe, values,
                            detector_config={
                                "k_length": self.config.stoch_k_length,
                                "k_smooth": self.config.stoch_k_smooth,
                                "d_smooth": self.config.stoch_d_smooth,
                            }
                        )
                except Exception:
                    pass

    def _handle_signal(self, signum, frame):
        """Handler sygnalow systemowych (Ctrl+C)."""
        logger.info("Otrzymano sygnal zatrzymania...")
        self._running = False

    def stop(self):
        """Zatrzymaj bota."""
        self._running = False

    @property
    def stats(self) -> dict:
        result = {
            "running": self._running,
            "scans": self._scan_count,
            "signals_sent": self._signals_sent,
            "errors": self._errors,
            "cooldowns_active": len(self._cooldowns),
            "fetcher": self.fetcher.stats if hasattr(self.fetcher, 'stats') else {},
        }
        if self.position_tracker:
            result["positions"] = self.position_tracker.get_stats()
        if self.glm_analyst:
            result["glm_analyst"] = self.glm_analyst.stats
        if self.market_scanner:
            result["market_scanner"] = self.market_scanner.stats
        return result


# ==============================================================================
# ONE-SHOT SCAN
# ==============================================================================

def run_single_scan(config: BotConfig, test_mode: bool = True, strategy: str = "nwo_stoch_cvd"):
    """Uruchom pojedynczy skan i wyswietl wyniki (bez petli, bez Discord)."""
    from custom_strategy import get_current_nwo_state, strategy_nwo_stoch_cvd, STRATEGY_REGISTRY

    use_nwo = strategy == "nwo_stoch_cvd"

    logger.info("Jednorazowy skan — sprawdzam sygnaly...")
    if use_nwo:
        logger.info("Strategia: NWO + Stoch(7,3,2) + CVD")

    # Data fetcher
    if config.market_source in ("stocks", "both"):
        try:
            from data_fetcher_yfinance import UnifiedDataFetcher
            fetcher = UnifiedDataFetcher()
        except ImportError:
            fetcher = DataFetcher(
                exchange_id=config.exchange,
                rate_limit_ms=config.rate_limit_ms,
                cache_ttl_seconds=config.cache_ttl,
                candles_per_fetch=config.candles_per_fetch,
            )
    else:
        fetcher = DataFetcher(
            exchange_id=config.exchange,
            rate_limit_ms=config.rate_limit_ms,
            cache_ttl_seconds=config.cache_ttl,
            candles_per_fetch=config.candles_per_fetch,
        )

    detector = SignalDetector(
        stoch_k_length=config.stoch_k_length,
        stoch_k_smooth=config.stoch_k_smooth,
        stoch_d_smooth=config.stoch_d_smooth,
        oversold_threshold=config.oversold_threshold,
        overbought_threshold=config.overbought_threshold,
        require_crossover=config.require_crossover,
    )

    # Combine symbols
    all_symbols = config.get_all_symbols()

    for timeframe in config.timeframes:
        logger.info(f"\n  Timeframe: {timeframe}")
        logger.info(f"  {'Symbol':<14} {'Price':>10} {'NWO':>6} {'K':>6} {'D':>6} {'CVD':>6} {'Signal'}")
        logger.info(f"  {'─'*14} {'─'*10} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*30}")

        for symbol in all_symbols:
            # Skip invalid TF/symbol combos
            try:
                from data_fetcher_yfinance import get_asset_class, ASSET_TF_OVERRIDES
                asset_class = get_asset_class(symbol)
                if asset_class in ASSET_TF_OVERRIDES and timeframe not in ASSET_TF_OVERRIDES[asset_class]:
                    continue
            except ImportError:
                pass

            try:
                df = fetcher.fetch_ohlcv(symbol, timeframe)
                if df.empty:
                    continue

                if use_nwo:
                    nwo_state = get_current_nwo_state(df, symbol, timeframe)
                    signals = strategy_nwo_stoch_cvd(df, symbol, timeframe)

                    if nwo_state:
                        signal_str = ""
                        for s in signals:
                            signal_str += f"{s.emoji} {s.signal_type} ({s.extra_data.get('source','')})"

                        risk = "HIGH" if any(s.extra_data.get("against_trend") for s in signals) else "OK"

                        logger.info(
                            f"  {symbol:<14} ${nwo_state['price']:>9,.2f} "
                            f"{nwo_state['osc']:>5.1f} "
                            f"{nwo_state['stoch_k'] or 0:>5.1f} {nwo_state['stoch_d'] or 0:>5.1f} "
                            f"{nwo_state['cvd'] or 0:>+5.2f} "
                            f"{signal_str or '—'}"
                        )

            except Exception as e:
                logger.error(f"  {symbol}: Blad — {e}")

    logger.info("\nSkan zakonczony.")


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Asset Signal Bot — Discord Notifier + GLM AI Analyst",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przyklady:
  python bot.py --webhook https://discord.com/api/webhooks/...
  python bot.py --test
  python bot.py --scan
  python bot.py --config aggressive
  python bot.py --market both --glm-key YOUR_KEY
  python bot.py --symbols BTC/USDT,XAU/USD,EUR/USD,SP500,WIG,DAX,NIKKEI
        """
    )

    parser.add_argument('--webhook', '-w', type=str, default=None,
                        help='Discord Webhook URL')
    parser.add_argument('--test', '-t', action='store_true',
                        help='Tryb testowy (bez wysylki na Discord)')
    parser.add_argument('--scan', action='store_true',
                        help='Pojedynczy skan (bez petli)')
    parser.add_argument('--config', '-c', type=str, default='default',
                        choices=['default', 'aggressive', 'conservative', 'scalping', 'multi_asset'],
                        help='Preset konfiguracji')
    parser.add_argument('--symbols', type=str, default=None,
                        help='Lista par oddzielona przecinkami')
    parser.add_argument('--timeframes', '-tf', type=str, default=None,
                        help='Timeframe\'y oddzielone przecinkami')
    parser.add_argument('--oversold', type=float, default=None)
    parser.add_argument('--overbought', type=float, default=None)
    parser.add_argument('--no-crossover', action='store_true')
    parser.add_argument('--interval', type=int, default=None)
    parser.add_argument('--exchange', type=str, default=None)
    parser.add_argument('--role-id', type=str, default=None)
    parser.add_argument('--strategy', type=str, default='nwo_stoch_cvd',
                        choices=list(STRATEGY_REGISTRY.keys()))

    # --- v3 options ---
    parser.add_argument('--sentiment', action='store_true',
                        help='Wlacz AI news sentiment filter')
    parser.add_argument('--no-sentiment', action='store_true')
    parser.add_argument('--cryptopanic-key', type=str, default='')
    parser.add_argument('--finnhub-key', type=str, default='')
    parser.add_argument('--market', type=str, default=None,
                        choices=['crypto', 'stocks', 'both'],
                        help='Rynek: crypto (Binance), stocks (YFinance), both')
    parser.add_argument('--trend-filter', type=str, default=None,
                        choices=['alert', 'block', 'off'])
    parser.add_argument('--position-size', type=float, default=None)
    parser.add_argument('--no-positions', action='store_true')
    parser.add_argument('--auto-trade', action='store_true')

    # --- GLM AI Analyst options ---
    parser.add_argument('--glm-key', type=str, default='',
                        help='GLM API key (Zhipu AI ChatGLM)')
    parser.add_argument('--glm-model', type=str, default='glm-4-flash',
                        choices=['glm-4-flash', 'glm-4', 'glm-4-plus'],
                        help='GLM model (glm-4-flash = fast/cheap)')
    parser.add_argument('--no-glm', action='store_true',
                        help='Disable GLM AI Analyst')
    parser.add_argument('--glm-lang', type=str, default='pl',
                        choices=['pl', 'en'],
                        help='GLM response language')

    # --- Market Scanner KOMBAJN options ---
    parser.add_argument('--no-scanner', action='store_true',
                        help='Disable Market Scanner KOMBAJN')
    parser.add_argument('--scanner-pulse', type=int, default=None,
                        help='Market Pulse interval in seconds (default: 3600)')
    parser.add_argument('--no-scanner-pulse', action='store_true',
                        help='Disable Market Pulse')
    parser.add_argument('--no-scanner-vol', action='store_true',
                        help='Disable Volatility Scanner')
    parser.add_argument('--no-scanner-sr', action='store_true',
                        help='Disable S/R Monitor')
    parser.add_argument('--no-scanner-sessions', action='store_true',
                        help='Disable Session Reporter')
    parser.add_argument('--no-scanner-corr', action='store_true',
                        help='Disable Correlation Alert')

    parser.add_argument('--log', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    args = parser.parse_args()

    # Wybierz preset konfiguracji
    if args.config == 'aggressive':
        config = config_aggressive()
    elif args.config == 'conservative':
        config = config_conservative()
    elif args.config == 'scalping':
        config = config_scalping()
    elif args.config == 'multi_asset':
        config = config_multi_asset()
    else:
        config = BotConfig()

    # Nadpisz konfiguracje z argumentow CLI
    if args.webhook:
        config.discord_webhook_url = args.webhook
    if args.symbols:
        config.symbols = [s.strip() for s in args.symbols.split(',')]
    if args.timeframes:
        config.timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    if args.oversold is not None:
        config.oversold_threshold = args.oversold
    if args.overbought is not None:
        config.overbought_threshold = args.overbought
    if args.no_crossover:
        config.require_crossover = False
    if args.interval:
        config.scan_interval = args.interval
    if args.exchange:
        config.exchange = args.exchange
    if args.role_id:
        config.discord_role_id = args.role_id
    config.log_level = args.log

    # v2 config overrides
    if args.sentiment:
        config.use_sentiment = True
    if args.no_sentiment:
        config.use_sentiment = False
    if args.cryptopanic_key:
        config.cryptopanic_api_key = args.cryptopanic_key
    if args.finnhub_key:
        config.finnhub_api_key = args.finnhub_key
    if args.market:
        config.market_source = args.market
    if args.trend_filter:
        config.trend_filter_mode = args.trend_filter
    if args.no_positions:
        config.use_position_tracking = False
    if args.position_size:
        config.default_position_size_usd = args.position_size
    if args.auto_trade:
        config.auto_open_positions = True

    # GLM AI Analyst config overrides
    if args.glm_key:
        config.glm_api_key = args.glm_key
        config.use_glm_analyst = True
    if args.no_glm:
        config.use_glm_analyst = False
    if args.glm_model:
        config.glm_model = args.glm_model
    if args.glm_lang:
        config.glm_language = args.glm_lang

    # --- Market Scanner KOMBAJN config overrides ---
    if args.no_scanner:
        config.use_market_scanner = False
    if args.scanner_pulse is not None:
        config.scanner_pulse_interval = args.scanner_pulse
    if args.no_scanner_pulse:
        config.scanner_pulse = False
    if args.no_scanner_vol:
        config.scanner_volatility = False
    if args.no_scanner_sr:
        config.scanner_sr = False
    if args.no_scanner_sessions:
        config.scanner_sessions = False
    if args.no_scanner_corr:
        config.scanner_correlation = False

    # Re-konfiguruj logging
    setup_logging(args.log)

    # Walidacja
    if not args.test and not args.scan:
        errors = config.validate()
        if errors:
            for err in errors:
                logger.error(f"Blad konfiguracji: {err}")
            logger.error("Uzyj --test do testowania bez Discord, lub podaj --webhook URL")
            sys.exit(1)

    # Wyswietl konfiguracje
    logger.info(f"\nKonfiguracja:\n{config.summary()}\n")

    # Uruchom
    if args.scan:
        run_single_scan(config, test_mode=args.test, strategy=args.strategy)
    else:
        bot = StochSignalBot(config, test_mode=args.test)

        if args.strategy != 'stoch_7_3_2' and STRATEGY_REGISTRY[args.strategy]['fn']:
            bot.custom_strategy_fn = STRATEGY_REGISTRY[args.strategy]['fn']
            logger.info(f"Strategia: {STRATEGY_REGISTRY[args.strategy]['name']}")

        try:
            bot.run()
        except KeyboardInterrupt:
            bot.stop()


if __name__ == "__main__":
    main()
