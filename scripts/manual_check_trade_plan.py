from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.trade_plan_service import generate_trade_plan


analysis = {
    "symbol": "FPT",
    "last_price": 120.0,
    "trend": "neutral",
    "momentum": "neutral",
}

print(generate_trade_plan(analysis))
