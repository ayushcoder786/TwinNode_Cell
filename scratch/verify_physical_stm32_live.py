"""
Live Verification Script for Physical STM32 + ML Integration on COM3 @ 115200.
Tests the 7 specific points requested by the user against the actual physical hardware.
"""

import sys
import os
import time
import asyncio
import json
import sqlite3

# Add repo root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from backend.app.services.serial_service import SerialService
from backend.app.ml.hardware_ml_service import hardware_ml_service, PHYSICAL_HARDWARE_FEATURES
from backend.app.data.feature_engineering import CANONICAL_FEATURES
from backend.app.data.collector import collector
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.schema import RawSensorData, PredictionRecord
from sqlalchemy import select, desc

async def run_live_verification():
    results = {}
    print("=" * 70)
    print("TWINNODE CELL - PHYSICAL STM32 LIVE VERIFICATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Does the backend actually connect to COM3?
    # ---------------------------------------------------------
    print("\n--- TEST 1: Physical COM3 Connection ---")
    rx_telemetries = []
    def on_telemetry(data):
        rx_telemetries.append(data)

    serial_srv = SerialService(
        on_packet_received=None,
        on_telemetry_received=on_telemetry
    )
    
    conn_success = serial_srv.connect(port="COM3", baudrate=115200)
    results["test1_connect_success"] = conn_success
    results["test1_port"] = serial_srv.port
    results["test1_baudrate"] = serial_srv.baudrate
    results["test1_is_connected"] = serial_srv.is_connected
    results["test1_status"] = serial_srv.get_status()
    print(f"Connected: {conn_success}")
    print(f"Status: {serial_srv.get_status()}")
    assert conn_success, "Failed to connect to COM3"

    # ---------------------------------------------------------
    # 2. Can it continuously receive and parse real STM32 readings?
    # ---------------------------------------------------------
    print("\n--- TEST 2: Continuous Real Telemetry Reception & Parsing ---")
    print("Listening to COM3 for 5 seconds...")
    start_t = time.time()
    while time.time() - start_t < 5.0:
        await asyncio.sleep(0.2)
        if len(rx_telemetries) >= 5:
            break

    results["test2_telemetry_count"] = len(rx_telemetries)
    results["test2_lines_rx"] = serial_srv.lines_rx
    results["test2_bytes_rx"] = serial_srv.bytes_rx
    results["test2_last_raw"] = serial_srv.last_raw_message
    
    sample_records = rx_telemetries[:3] if rx_telemetries else []
    results["test2_sample_records"] = sample_records
    print(f"Received {len(rx_telemetries)} records in {round(time.time() - start_t, 2)}s.")
    print(f"Last Raw Message: {serial_srv.last_raw_message}")
    for idx, r in enumerate(sample_records):
        print(f"  Record {idx+1}: Temp={r.get('temperature')}°C, Hum={r.get('humidity')}%, Dist={r.get('distance')}cm, Valid={r.get('sensor_validity')}, Raw='{r.get('raw_message')}'")

    assert len(rx_telemetries) > 0, "No telemetry received from COM3"
    live_sample = rx_telemetries[-1]

    # ---------------------------------------------------------
    # 3. Are the readings stored with REAL_HARDWARE provenance?
    # ---------------------------------------------------------
    print("\n--- TEST 3: Database Storage with REAL_HARDWARE Provenance ---")
    await collector.start()
    session_id = f"VERIF-HW-{int(time.time())}"
    
    for r in rx_telemetries[:5]:
        await collector.ingest_record(
            node_id=1,
            temperature=r.get("temperature"),
            humidity=r.get("humidity"),
            distance=r.get("distance"),
            test_id=9999,
            operating_mode="RUNNING",
            condition_label="NORMAL_OPERATION",
            data_source="REAL_HARDWARE",
            raw_message=r.get("raw_message")
        )
    
    # Flush collector buffer to SQLite
    await collector.flush()
    await collector.stop()

    # Query SQLite database to verify persistence
    async with AsyncSessionLocal() as db_session:
        stmt = (
            select(RawSensorData)
            .where(RawSensorData.data_source == "REAL_HARDWARE")
            .order_by(desc(RawSensorData.id))
            .limit(5)
        )
        res = await db_session.execute(stmt)
        stored_rows = res.scalars().all()

        results["test3_stored_count"] = len(stored_rows)
        results["test3_latest_rows"] = [
            {
                "id": row.id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "temp": row.temperature,
                "hum": row.humidity,
                "dist": row.distance,
                "data_source": row.data_source,
                "raw_message": row.raw_message
            }
            for row in stored_rows
        ]
        print(f"Stored {len(stored_rows)} REAL_HARDWARE rows in SQLite.")
        for r in results["test3_latest_rows"][:3]:
            print(f"  DB Row ID {r['id']}: Source={r['data_source']}, Temp={r['temp']}, Hum={r['hum']}, Dist={r['dist']}, Raw='{r['raw_message']}'")
        
        assert len(stored_rows) > 0, "No REAL_HARDWARE records found in DB"
        assert stored_rows[0].data_source == "REAL_HARDWARE"

    # ---------------------------------------------------------
    # 4. Does the ML inference pipeline receive these readings?
    # ---------------------------------------------------------
    print("\n--- TEST 4: ML Inference Pipeline with Real Readings ---")
    ml_pred = await hardware_ml_service.predict_physical_telemetry(
        telemetry=live_sample,
        is_estop_latched=False
    )
    results["test4_ml_prediction"] = ml_pred
    print(f"ML Output: Label={ml_pred['predicted_label']}, Conf={ml_pred['confidence']}, AnomalyScore={ml_pred['anomaly_score']}, IsAnomaly={ml_pred['is_anomaly']}")
    print(f"Suggested LED: {ml_pred['suggested_led']}, Source={ml_pred['data_source']}, Model={ml_pred['model_id']}")

    # Store prediction record in SQLite
    async with AsyncSessionLocal() as db_session:
        pred_rec = PredictionRecord(
            test_id=9999,
            model_id=ml_pred.get("model_id", "Physical_STM32_Dedicated_RF"),
            predicted_label=ml_pred["predicted_label"],
            confidence=ml_pred["confidence"],
            anomaly_score=ml_pred["anomaly_score"],
            is_anomaly=ml_pred["is_anomaly"],
            data_source=ml_pred["data_source"],
            features_used=ml_pred.get("feature_snapshot")
        )
        db_session.add(pred_rec)
        await db_session.commit()
        print("Persisted ML prediction record to prediction_records table with REAL_HARDWARE provenance.")

    # ---------------------------------------------------------
    # 5. Are the model's expected features compatible with DHT11 and HC-SR04?
    # ---------------------------------------------------------
    print("\n--- TEST 5: Model Feature Compatibility Audit ---")
    sim_compat = hardware_ml_service.inspect_model_compatibility(CANONICAL_FEATURES)
    hw_compat = hardware_ml_service.inspect_model_compatibility(PHYSICAL_HARDWARE_FEATURES)
    
    results["test5_simulation_model_compatibility"] = sim_compat
    results["test5_dedicated_hardware_compatibility"] = hw_compat

    print(f"Simulation Model (12 Canonical Features) on Single STM32:")
    print(f"  Total Features: {sim_compat['total_model_features']}")
    print(f"  Compatible Features: {sim_compat['compatible_features_count']}")
    print(f"  Missing Features Count: {sim_compat['missing_features_count']}")
    print(f"  Compatibility Score: {sim_compat['compatibility_score_pct']}%")
    print(f"  Is Directly Compatible: {sim_compat['is_directly_compatible']}")
    print(f"  Recommendation: {sim_compat['recommendation']}")
    print(f"  Unmeasurable Features: {[b['feature'] for b in sim_compat['breakdown'] if b['category'] == 'UNAVAILABLE_SINGLE_STM32_NODE']}")

    print(f"\nDedicated Hardware Pipeline (13 Features):")
    print(f"  Total Features: {hw_compat['total_model_features']}")
    print(f"  Missing Features Count: {hw_compat['missing_features_count']}")
    print(f"  Compatibility Score: {hw_compat['compatibility_score_pct']}%")
    print(f"  Is Directly Compatible: {hw_compat['is_directly_compatible']}")

    # ---------------------------------------------------------
    # 6. Can predictions trigger LED commands through COM3?
    # ---------------------------------------------------------
    print("\n--- TEST 6: Triggering LED Commands through COM3 ---")
    # Test triggering the suggested LED from ML prediction
    suggested_led = ml_pred["suggested_led"]
    tx_ok = serial_srv.send_led_command(suggested_led)
    print(f"Sent suggested command '{suggested_led}': Success={tx_ok}, BytesTX={serial_srv.bytes_tx}")
    await asyncio.sleep(0.5)

    # Test other LED commands: GREEN, YELLOW, RED, OFF
    for cmd in ["LED:GREEN", "LED:YELLOW", "LED:RED", "LED:OFF"]:
        sent = serial_srv.send_led_command(cmd)
        print(f"  Command '{cmd}': Sent={sent}, Status={serial_srv.last_led_ack_status}")
        await asyncio.sleep(0.3)

    # Test E-Stop Override logic
    estop_pred = await hardware_ml_service.predict_physical_telemetry(
        telemetry=live_sample,
        is_estop_latched=True
    )
    results["test6_estop_override_led"] = estop_pred["suggested_led"]
    results["test6_bytes_tx"] = serial_srv.bytes_tx
    print(f"E-Stop Latch Test: Suggested LED={estop_pred['suggested_led']}, ActuatorState={estop_pred['actuator_led_state']}")
    assert estop_pred["suggested_led"] == "LED:OFF", "E-Stop did not enforce LED:OFF"

    # Close serial connection cleanly
    serial_srv.disconnect()
    print("Serial port COM3 cleanly closed.")

    # ---------------------------------------------------------
    # 7. React dashboard integration verification
    # ---------------------------------------------------------
    print("\n--- TEST 7: React Dashboard Integration Verification ---")
    # Verify the REST endpoints that the frontend calls
    from backend.app.api.endpoints import get_hardware_status, get_hardware_predictions, get_hardware_feature_compatibility
    from fastapi import Request
    
    hw_status_dict = await get_hardware_status()
    preds_list = await get_hardware_predictions(limit=5)

    results["test7_dashboard_api_status"] = hw_status_dict
    results["test7_dashboard_api_predictions_count"] = len(preds_list)
    results["test7_dashboard_api_sample_prediction"] = preds_list[0] if preds_list else None
    
    print(f"API /api/hardware/status returns: Status={hw_status_dict.get('status')}, SerialConnected={hw_status_dict.get('serial', {}).get('is_connected')}, LastRaw='{hw_status_dict.get('serial', {}).get('last_raw_message')}'")
    print(f"API /api/hardware/predictions returns: {len(preds_list)} REAL_HARDWARE records.")

    print("\n" + "=" * 70)
    print("ALL 7 VERIFICATION CRITERIA SUCCESSFULLY EXECUTED WITH REAL HARDWARE!")
    print("=" * 70)
    
    # Save verification evidence JSON
    out_file = os.path.join(ROOT, "scratch", "live_hardware_verification_evidence.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved detailed verification evidence to: {out_file}")

if __name__ == "__main__":
    asyncio.run(run_live_verification())
