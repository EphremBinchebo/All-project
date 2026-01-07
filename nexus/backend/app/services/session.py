from datetime import datetime
import pytz

class SessionService:
    def detect(self):
        utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        hour = utc.hour

        # Crypto sessions (UTC-based)
        if 0 <= hour < 7:
            return self._asia()
        elif 7 <= hour < 13:
            return self._eu()
        elif 13 <= hour < 21:
            return self._us()
        else:
            return self._weekend()

    def _asia(self):
        return {
            "name": "ASIA",
            "liquidity": "low",
            "risk_multiplier": 0.7,
            "note": "Lower volatility, prone to fake moves."
        }

    def _eu(self):
        return {
            "name": "EU",
            "liquidity": "medium",
            "risk_multiplier": 0.9,
            "note": "Trend formation and structure building."
        }

    def _us(self):
        return {
            "name": "US",
            "liquidity": "high",
            "risk_multiplier": 1.0,
            "note": "Highest liquidity and strongest moves."
        }

    def _weekend(self):
        return {
            "name": "WEEKEND",
            "liquidity": "very low",
            "risk_multiplier": 0.5,
            "note": "Avoid trading unless exceptional setup."
        }
