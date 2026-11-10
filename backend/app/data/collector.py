"""
TwinNode Raw Data Collection Service
Captures sensor telemetry from Real Hardware and Simulation with strict data provenance.
Stores original raw readings in SQLite without alteration, supporting continuous streaming.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging
from sqlalchemy import select, func, desc

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.schema import RawSensorData, utc_now
from backend.app.data.validator import validator

logger = logging.getLogger("twinnode.collector")

class DataCollectorService:
    """
    Dedicated Data Collection Service for TwinNode Cell.
    Collects, validates, stamps provenance, and persists raw sensor data.
    """

    def __init__(self):
        self._buffer: List[Dict[str, Any]] = []
        self._flush_lock = asyncio.Lock()
        self._max_buffer_size = 50
        self._flush_interval_sec = 1.0
        self._running = False
        self._background_task: Optional[asyncio.Task] = None
        
        # In-memory session stats
        self.total_records = 0
        self.real_hardware_records = 0
        self.simulation_records = 0
        self.invalid_records = 0
        self.duplicate_records = 0
        
        # State tracking for dynamic metrics calculation
        self._prev_state: Dict[str, Any] = {}

    async def start(self):
        """Start background buffer flusher."""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._periodic_flush_loop())
            logger.info("DataCollectorService started background flush loop.")

    async def stop(self):
        """Stop background worker and flush remaining records."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        logger.info("DataCollectorService stopped and flushed.")

    async def ingest_record(
        self,
        node_id: int,
        temperature: Optional[float],
        distance: Optional[float],
        humidity: Optional[float] = None,
        target_temperature: Optional[float] = None,
        target_distance: Optional[float] = None,
        test_id: Optional[int] = None,
        response_delay_ms: float = 0.0,
        uart_latency_ms: float = 0.0,
        packet_sequence: int = 0,
        packet_loss: float = 0.0,
        led_command: str = "GREEN_ON",
        led_acknowledgement: str = "ACK_RECEIVED",
        operating_mode: str = "NORMAL",
        condition_label: str = "NORMAL_OPERATION",
        data_source: str = "SIMULATION",
        raw_message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Ingest a raw sensor record.
        Performs validation, calculates error and rate-of-change, and buffers for DB insertion.
        """
        now = timestamp or datetime.now(timezone.utc)
        
        # Validation
        is_valid, status_str, v_details = validator.validate_reading(
            node_id=node_id,
            temp=temperature,
            dist=distance,
            seq=packet_sequence,
            test_id=test_id,
            timestamp=now
        )

        is_duplicate = v_details["is_duplicate"]
        if is_duplicate:
            self.duplicate_records += 1

        if not is_valid:
            self.invalid_records += 1

        # Errors against targets
        temp_error = (temperature - target_temperature) if (temperature is not None and target_temperature is not None) else None
        dist_error = (distance - target_distance) if (distance is not None and target_distance is not None) else None

        # Rates of change
        prev = self._prev_state.get(node_id)
        temp_rate = v_details.get("temp_rate", 0.0)
        dist_rate = v_details.get("dist_rate", 0.0)

        # Update previous state cache
        if is_valid and temperature is not None and distance is not None:
            self._prev_state[node_id] = {
                "temp": temperature,
                "dist": distance,
                "timestamp": now
            }

        # Normalize data_source
        src = "REAL_HARDWARE" if data_source.upper() == "REAL_HARDWARE" else "SIMULATION"

        record_dict = {
            "timestamp": now,
            "node_id": node_id,
            "test_id": test_id,
            "temperature": temperature,
            "humidity": humidity,
            "distance": distance,
            "target_temperature": target_temperature,
            "target_distance": target_distance,
            "temperature_error": temp_error,
            "distance_error": dist_error,
            "temperature_rate": temp_rate,
            "distance_rate": dist_rate,
            "response_delay_ms": response_delay_ms,
            "uart_latency_ms": uart_latency_ms,
            "packet_sequence": packet_sequence,
            "packet_loss": packet_loss,
            "sensor_validity": is_valid,
            "led_command": led_command,
            "led_acknowledgement": led_acknowledgement,
            "operating_mode": operating_mode,
            "condition_label": condition_label,
            "data_source": src,
            "is_duplicate": is_duplicate,
            "raw_message": raw_message
        }

        # Counters
        self.total_records += 1
        if src == "REAL_HARDWARE":
            self.real_hardware_records += 1
        else:
            self.simulation_records += 1

        async with self._flush_lock:
            self._buffer.append(record_dict)
            if len(self._buffer) >= self._max_buffer_size:
                asyncio.create_task(self.flush())

        return record_dict

    async def flush(self):
        """Commit buffered records to SQLite in a single transaction."""
        async with self._flush_lock:
            if not self._buffer:
                return
            to_insert = list(self._buffer)
            self._buffer.clear()

        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    db_objects = [RawSensorData(**item) for item in to_insert]
                    session.add_all(db_objects)
                await session.commit()
        except Exception as e:
            logger.error(f"Error flushing {len(to_insert)} raw sensor records: {e}", exc_info=True)

    async def _periodic_flush_loop(self):
        """Periodic background flush to ensure low-latency DB writes."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval_sec)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic flush error: {e}")

    async def get_summary_stats(self) -> Dict[str, Any]:
        """Fetch summary statistics from database and live service."""
        try:
            async with AsyncSessionLocal() as session:
                total = await session.scalar(select(func.count(RawSensorData.id))) or 0
                real_count = await session.scalar(
                    select(func.count(RawSensorData.id)).where(RawSensorData.data_source == "REAL_HARDWARE")
                ) or 0
                sim_count = await session.scalar(
                    select(func.count(RawSensorData.id)).where(RawSensorData.data_source == "SIMULATION")
                ) or 0
                invalid_count = await session.scalar(
                    select(func.count(RawSensorData.id)).where(RawSensorData.sensor_validity == False) # noqa
                ) or 0
                dup_count = await session.scalar(
                    select(func.count(RawSensorData.id)).where(RawSensorData.is_duplicate == True) # noqa
                ) or 0

                return {
                    "total_records": total,
                    "real_hardware_records": real_count,
                    "simulation_records": sim_count,
                    "invalid_records": invalid_count,
                    "duplicate_records": dup_count,
                    "buffer_pending": len(self._buffer)
                }
        except Exception as e:
            logger.warning(f"Failed to query DB stats: {e}")
            return {
                "total_records": self.total_records,
                "real_hardware_records": self.real_hardware_records,
                "simulation_records": self.simulation_records,
                "invalid_records": self.invalid_records,
                "duplicate_records": self.duplicate_records,
                "buffer_pending": len(self._buffer)
            }

collector = DataCollectorService()
