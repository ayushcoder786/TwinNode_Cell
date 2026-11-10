"""
TwinNode Sensor Data Validation Module
Performs real-time and batch validation on raw sensor readings.
Detects missing, out-of-range, NaN, and duplicate records.
"""

from typing import Dict, Any, Tuple, Optional
import math
from datetime import datetime

# Sensor Physical Specifications
LM35_MIN_TEMP_C = -10.0   # Physical LM35 lower limit in standard supply
LM35_MAX_TEMP_C = 110.0   # Practical upper bound for instrument enclosure
HCSR04_MIN_DIST_CM = 2.0  # HC-SR04 minimum blind-zone limit
HCSR04_MAX_DIST_CM = 400.0 # HC-SR04 max range

# Default tolerance for rate-of-change per second
MAX_TEMP_RATE_C_PER_SEC = 15.0 # Unphysical jump in thermal mass
MAX_DIST_RATE_CM_PER_SEC = 250.0 # Extreme speed jump

class DataValidator:
    """
    Validates sensor records against physical limits and operational consistency.
    """

    def __init__(self):
        self._last_records: Dict[int, Dict[str, Any]] = {} # keyed by node_id
        self._seen_signatures = set() # For duplicate tracking (seq, test_id, timestamp_str)

    def validate_reading(
        self,
        node_id: int,
        temp: Optional[float],
        dist: Optional[float],
        seq: int,
        test_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate single incoming sensor packet.
        Returns (is_valid, validation_status, anomaly_details).
        """
        issues = []
        is_valid = True

        # 1. Missing / NaN Checks
        if temp is None or math.isnan(temp) or math.isinf(temp):
            issues.append("MISSING_OR_INVALID_TEMPERATURE")
            is_valid = False
        elif temp < LM35_MIN_TEMP_C or temp > LM35_MAX_TEMP_C:
            issues.append(f"TEMPERATURE_OUT_OF_BOUNDS_{temp:.1f}C")
            is_valid = False

        if dist is None or math.isnan(dist) or math.isinf(dist):
            issues.append("MISSING_OR_INVALID_DISTANCE")
            is_valid = False
        elif dist < HCSR04_MIN_DIST_CM or dist > HCSR04_MAX_DIST_CM:
            issues.append(f"DISTANCE_OUT_OF_BOUNDS_{dist:.1f}CM")
            is_valid = False

        # 2. Duplicate Detection
        is_duplicate = False
        if timestamp:
            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            sig = (node_id, test_id, seq, time_str)
            if sig in self._seen_signatures:
                is_duplicate = True
                issues.append("DUPLICATE_PACKET_DETECTED")
            else:
                self._seen_signatures.add(sig)
                if len(self._seen_signatures) > 10000:
                    self._seen_signatures.clear()

        # 3. Dynamic Rate-of-Change Check against previous record
        prev = self._last_records.get(node_id)
        temp_rate = 0.0
        dist_rate = 0.0
        if prev and is_valid and timestamp and prev.get("timestamp"):
            dt = (timestamp - prev["timestamp"]).total_seconds()
            if 0.01 <= dt <= 2.0:
                temp_rate = (temp - prev["temp"]) / dt
                dist_rate = (dist - prev["dist"]) / dt
                if abs(temp_rate) > MAX_TEMP_RATE_C_PER_SEC:
                    issues.append(f"EXTREME_TEMP_SPIKE_{temp_rate:+.1f}C/s")
                if abs(dist_rate) > MAX_DIST_RATE_CM_PER_SEC:
                    issues.append(f"EXTREME_DIST_STEP_{dist_rate:+.1f}cm/s")

        # Cache last valid reading
        if is_valid and temp is not None and dist is not None:
            self._last_records[node_id] = {
                "temp": temp,
                "dist": dist,
                "timestamp": timestamp or datetime.utcnow(),
                "seq": seq
            }

        status_str = "VALID" if is_valid and not issues else ";".join(issues)
        details = {
            "is_valid": is_valid,
            "is_duplicate": is_duplicate,
            "issues": issues,
            "temp_rate": temp_rate,
            "dist_rate": dist_rate
        }
        return is_valid, status_str, details

validator = DataValidator()
