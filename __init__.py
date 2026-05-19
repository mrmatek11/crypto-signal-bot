"""
Crypto Stoch Signal Bot — Discord Notifier + GLM AI + KOMBAJN

Monitoruje krypto, surowce, forex i indeksy na żywo,
wykrywa sygnały Stochastic (7,3,2) + NWO + CVD,
wysyła alerty na Discord + AI analiza GLM + Market Scanner KOMBAJN.
"""

from .config import BotConfig
from .signal_detector import SignalDetector, Signal
from .data_fetcher import DataFetcher
from .discord_notifier import DiscordNotifier
from .custom_strategy import STRATEGY_REGISTRY
