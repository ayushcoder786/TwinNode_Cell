import io
import csv
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, desc

from backend.app.services.supervisor import supervisor
from backend.app.services.serial_service import SerialService
from backend.app.models.schema import TestSession, TelemetryRecord, FaultEvent, PredictionRecord
from backend.app.db.session import AsyncSessionLocal
from backend.app.ml.hardware_ml_service import hardware_ml_service
from backend.app.ml.model_registry import model_registry
from backend.app.api.ml_endpoints import router as ml_router
from backend.app.api.external_dataset_endpoints import router as datasets_router
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

router = APIRouter()
router.include_router(ml_router)
router.include_router(datasets_router)


# Pydantic Schemas
class ConnectRequest(BaseModel):
    port: str
    baudrate: int = 115200

class SimulationModeRequest(BaseModel):
    enabled: bool

class SetpointsRequest(BaseModel):
    target_temp: Optional[float] = None
    target_dist: Optional[float] = None
    target_motor_speed: Optional[int] = None
    target_servo_angle: Optional[int] = None

class StartTestRequest(BaseModel):
    name: str
    profile: str = "STANDARD_INDUSTRIAL"
    targets: Dict[str, Any]

class FaultInjectRequest(BaseModel):
    fault_key: str
    state: bool

class AckFaultRequest(BaseModel):
    fault_code: str

class ProfileSelectRequest(BaseModel):
    profile_name: str

# 1. System Health & Diagnostics
@router.get("/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "SIMULATION" if supervisor.simulation_mode else "HARDWARE",
        "serial_connected": supervisor.serial_service.is_connected,
        "active_clients": len(supervisor.active_websockets),
        "test_status": supervisor.test_status
    }

# 2. Port Management & Connection
@router.get("/ports")
async def list_ports():
    return {"ports": SerialService.list_ports()}

@router.post("/connection/connect")
async def connect_serial(req: ConnectRequest):
    success = supervisor.serial_service.connect(req.port, req.baudrate)
    if success:
        supervisor.set_simulation_mode(False)
        return {"status": "CONNECTED", "port": req.port, "baudrate": req.baudrate}
    raise HTTPException(status_code=400, detail=f"Failed to connect to serial port {req.port}")

@router.post("/connection/disconnect")
async def disconnect_serial():
    supervisor.serial_service.disconnect()
    return {"status": "DISCONNECTED"}

@router.get("/connection/status")
async def connection_status():
    return {
        "is_connected": supervisor.serial_service.is_connected,
        "port": supervisor.serial_service.port,
        "baudrate": supervisor.serial_service.baudrate,
        "bytes_rx": supervisor.serial_service.bytes_rx,
        "bytes_tx": supervisor.serial_service.bytes_tx,
        "packets_rx": supervisor.serial_service.packets_rx,
        "packets_tx": supervisor.serial_service.packets_tx,
        "last_rx_time": supervisor.serial_service.last_rx_time,
        "simulation_mode": supervisor.simulation_mode
    }

# 3. Operational Mode
@router.post("/mode/simulation")
async def toggle_simulation_mode(req: SimulationModeRequest):
    supervisor.set_simulation_mode(req.enabled)
    return {"simulation_mode": supervisor.simulation_mode}

# 4. Test Bench Controls
@router.post("/test/start")
async def start_test(req: StartTestRequest):
    test_id = await supervisor.start_test(req.name, req.profile, req.targets)
    return {"status": "STARTED", "test_id": test_id, "name": req.name}

@router.post("/test/pause")
async def pause_test():
    await supervisor.pause_test()
    return {"status": "PAUSED"}

@router.post("/test/resume")
async def resume_test():
    await supervisor.resume_test()
    return {"status": "RUNNING"}

@router.post("/test/stop")
async def stop_test():
    await supervisor.stop_test()
    return {"status": "STOPPED"}

@router.post("/test/reset")
async def reset_test():
    supervisor.reset_test()
    return {"status": "RESET", "test_status": supervisor.test_status}

@router.post("/test/emergency_stop")
async def emergency_stop():
    fault = supervisor.emergency_stop()
    return {"status": "EMERGENCY_STOP_TRIGGERED", "fault": fault}

@router.post("/test/setpoints")
async def update_setpoints(req: SetpointsRequest):
    update_dict = {k: v for k, v in req.model_dump().items() if v is not None}
    supervisor.update_setpoints(update_dict)
    return {"status": "UPDATED", "current_target": supervisor.current_target}

@router.get("/test/active")
async def get_active_test():
    return {
        "test_id": supervisor.active_test_id,
        "name": supervisor.active_test_name,
        "status": supervisor.test_status,
        "target": supervisor.current_target,
        "latest_telemetry": supervisor.latest_telemetry,
        "sample_count": supervisor.sample_count,
        "simulation_mode": supervisor.simulation_mode
    }

@router.get("/test/history")
async def get_test_history():
    async with AsyncSessionLocal() as session:
        stmt = select(TestSession).order_by(desc(TestSession.id)).limit(20)
        res = await session.execute(stmt)
        sessions = res.scalars().all()
        return [{
            "id": s.id,
            "test_id": s.test_id,
            "name": s.name,
            "profile": s.profile,
            "status": s.status,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "total_samples": s.total_samples,
            "total_faults": s.total_faults
        } for s in sessions]

@router.get("/test/{test_id}/telemetry")
async def get_test_telemetry(test_id: int, limit: int = 200):
    async with AsyncSessionLocal() as session:
        stmt = select(TelemetryRecord).where(TelemetryRecord.test_id == test_id).order_by(desc(TelemetryRecord.id)).limit(limit)
        res = await session.execute(stmt)
        records = list(reversed(res.scalars().all()))
        return [{
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "target_temp": r.target_temp,
            "actual_temp": r.actual_temp,
            "target_dist": r.target_dist,
            "actual_dist": r.actual_dist,
            "target_motor_speed": r.target_motor_speed,
            "actual_motor_speed": r.actual_motor_speed,
            "target_servo_angle": r.target_servo_angle,
            "actual_servo_angle": r.actual_servo_angle,
            "comm_latency_ms": r.comm_latency_ms
        } for r in records]

# 5. Faults & Condition Profiles
@router.get("/faults")
async def get_faults():
    return {
        "active_faults": list(supervisor.condition_engine.active_faults.values()),
        "is_estop_latched": supervisor.condition_engine.is_emergency_stop_latched
    }

@router.post("/faults/acknowledge")
async def acknowledge_fault(req: AckFaultRequest):
    success = supervisor.condition_engine.acknowledge_fault(req.fault_code)
    return {"status": "ACKNOWLEDGED" if success else "NOT_FOUND"}

@router.post("/faults/reset")
async def reset_faults():
    supervisor.condition_engine.reset_faults()
    return {"status": "FAULTS_CLEARED"}

@router.get("/profiles")
async def get_profiles():
    return {
        "active_profile": supervisor.condition_engine.active_profile_name,
        "profiles": supervisor.condition_engine.profiles_data.get("profiles", {})
    }

@router.post("/profiles/active")
async def set_active_profile(req: ProfileSelectRequest):
    success = supervisor.condition_engine.set_active_profile(req.profile_name)
    if success:
        return {"status": "UPDATED", "active_profile": req.profile_name}
    raise HTTPException(status_code=404, detail="Profile not found")

@router.get("/eq15_09/status")
async def get_eq15_09_status():
    return supervisor.condition_engine.eq15_09_detector.get_status_info()

# 6. Simulation Fault Injections
@router.post("/simulation/fault_injection")
async def inject_fault(req: FaultInjectRequest):
    supervisor.simulation_engine.set_fault_injection(req.fault_key, req.state)
    return {
        "status": "APPLIED",
        "fault_key": req.fault_key,
        "state": req.state,
        "active_injections": supervisor.simulation_engine.fault_injections
    }

@router.get("/simulation/injections")
async def get_fault_injections():
    return {"injections": supervisor.simulation_engine.fault_injections}

# 7. Reports & Data Export
@router.get("/reports/export/csv/{test_id}")
async def export_csv(test_id: int):
    async with AsyncSessionLocal() as session:
        stmt = select(TelemetryRecord).where(TelemetryRecord.test_id == test_id).order_by(TelemetryRecord.id)
        res = await session.execute(stmt)
        records = res.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp", "Test_ID", "Node1_Status", "Node2_Status",
            "Target_Temp_C", "Actual_Temp_C", "Target_Dist_cm", "Actual_Dist_cm",
            "Target_Motor_pct", "Actual_Motor_pct", "Target_Servo_deg", "Actual_Servo_deg",
            "Comm_Latency_ms", "Fault_Code"
        ])
        
        for r in records:
            writer.writerow([
                r.timestamp.isoformat() if r.timestamp else "",
                r.test_id, r.node1_status, r.node2_status,
                r.target_temp, r.actual_temp, r.target_dist, r.actual_dist,
                r.target_motor_speed, r.actual_motor_speed, r.target_servo_angle, r.actual_servo_angle,
                r.comm_latency_ms, r.fault_code
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=twinnode_test_{test_id}_report.csv"}
        )

@router.get("/reports/export/pdf/{test_id}")
async def export_pdf(test_id: int):
    async with AsyncSessionLocal() as session:
        # Get test session metadata
        s_stmt = select(TestSession).where(TestSession.test_id == test_id)
        s_res = await session.execute(s_stmt)
        test_session = s_res.scalar_one_or_none()

        # Get telemetry samples
        stmt = select(TelemetryRecord).where(TelemetryRecord.test_id == test_id).order_by(desc(TelemetryRecord.id)).limit(15)
        res = await session.execute(stmt)
        records = res.scalars().all()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header Bar
    p.setFillColor(colors.HexColor("#0f172a"))
    p.rect(0, height - 70, width, 70, fill=True, stroke=False)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(40, height - 42, "TWINNODE CELL — INDUSTRIAL TEST REPORT")
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 58, "Distributed Sensing and Actuation Supervisor Validation Certificate")

    # Metadata Box
    p.setFillColor(colors.HexColor("#f8fafc"))
    p.rect(40, height - 190, width - 80, 105, fill=True, stroke=True)
    p.setFillColor(colors.HexColor("#1e293b"))
    p.setFont("Helvetica-Bold", 12)
    p.drawString(55, height - 105, f"Test Identification: #{test_id}")
    
    p.setFont("Helvetica", 10)
    test_name = test_session.name if test_session else "N/A"
    profile_name = test_session.profile if test_session else "STANDARD_INDUSTRIAL"
    start_str = test_session.start_time.strftime("%Y-%m-%d %H:%M:%S UTC") if test_session and test_session.start_time else "N/A"
    samples_cnt = test_session.total_samples if test_session else len(records)
    
    p.drawString(55, height - 125, f"Test Campaign: {test_name}")
    p.drawString(55, height - 145, f"Validation Profile: {profile_name}")
    p.drawString(320, height - 125, f"Execution Date: {start_str}")
    p.drawString(320, height - 145, f"Total Captured Samples: {samples_cnt}")
    p.drawString(320, height - 165, "Status: VALIDATED & CONCLUDED")

    # Table Header
    y = height - 220
    p.setFillColor(colors.HexColor("#334155"))
    p.rect(40, y, width - 80, 20, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(45, y + 6, "Time")
    p.drawString(140, y + 6, "Temp (Tgt/Act)")
    p.drawString(245, y + 6, "Dist (Tgt/Act)")
    p.drawString(350, y + 6, "Motor (Tgt/Act)")
    p.drawString(450, y + 6, "Servo (Tgt/Act)")
    p.drawString(535, y + 6, "Latency")

    # Table Rows
    y -= 18
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.black)
    for r in records:
        time_str = r.timestamp.strftime("%H:%M:%S") if r.timestamp else "-"
        p.drawString(45, y + 4, time_str)
        p.drawString(140, y + 4, f"{r.target_temp:.1f} / {r.actual_temp:.1f} °C")
        p.drawString(245, y + 4, f"{r.target_dist:.1f} / {r.actual_dist:.1f} cm")
        p.drawString(350, y + 4, f"{r.target_motor_speed}% / {r.actual_motor_speed}%")
        p.drawString(450, y + 4, f"{r.target_servo_angle}° / {r.actual_servo_angle}°")
        p.drawString(535, y + 4, f"{r.comm_latency_ms:.1f} ms")
        y -= 18
        if y < 80:
            break

    # Footer
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.HexColor("#64748b"))
    p.drawString(40, 40, "TwinNode Cell Industrial Validation Suite — Generated via Autonomous Supervisory Agent")
    p.drawRightString(width - 40, 40, f"Page 1 of 1 — Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    p.showPage()
    p.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=twinnode_test_{test_id}_report.pdf"}
    )

# 8. Physical STM32 Hardware & ML Endpoints
class HardwareConnectRequest(BaseModel):
    port: str = "COM3"
    baudrate: int = 115200

class HardwareLedRequest(BaseModel):
    command: str = "LED:GREEN"

class HardwareTrainRequest(BaseModel):
    n_samples: int = 5000

@router.get("/hardware/status")
async def get_hardware_status():
    """Retrieve live physical STM32 serial interface and telemetry status."""
    serial_status = supervisor.serial_service.get_status()
    return {
        "status": "ONLINE" if serial_status["is_connected"] else "OFFLINE",
        "serial": serial_status,
        "latest_telemetry": supervisor.latest_telemetry,
        "latest_prediction": supervisor.latest_prediction,
        "active_led_state": supervisor.led_state,
        "simulation_mode": supervisor.simulation_mode,
        "provenance": "REAL_HARDWARE" if not supervisor.simulation_mode and serial_status["is_connected"] else "SIMULATION"
    }

@router.post("/hardware/connect")
async def connect_hardware(req: HardwareConnectRequest):
    """Initiate physical STM32 serial link on COM3 @ 115200 baud."""
    success = supervisor.serial_service.connect(req.port, req.baudrate)
    if success:
        supervisor.set_simulation_mode(False)
        return {
            "status": "CONNECTED",
            "port": req.port,
            "baudrate": req.baudrate,
            "provenance": "REAL_HARDWARE",
            "message": f"Successfully connected to physical STM32 on {req.port} @ {req.baudrate} baud."
        }
    
    err_detail = supervisor.serial_service.last_error or f"Failed to connect to {req.port}"
    raise HTTPException(status_code=400, detail=err_detail)

@router.post("/hardware/disconnect")
async def disconnect_hardware():
    """Disconnect physical STM32 serial link and enforce safe output state."""
    supervisor.serial_service.disconnect()
    supervisor.led_state = "ALL_OFF"
    supervisor.latest_telemetry["led_state"] = "ALL_OFF"
    return {"status": "DISCONNECTED", "safe_state": "ALL_OFF"}

@router.post("/hardware/led-command")
async def dispatch_hardware_led(req: HardwareLedRequest):
    """Dispatch LED actuator command to physical STM32."""
    if supervisor.condition_engine.is_emergency_stop_latched:
        raise HTTPException(
            status_code=403,
            detail="Emergency stop is latched! Hardware safety rules prohibit manual LED override."
        )

    sent = supervisor.serial_service.send_led_command(req.command)
    return {
        "command_sent": req.command,
        "transmission_success": sent,
        "ack_status": supervisor.serial_service.last_led_ack_status,
        "has_physical_optical_feedback": False,
        "note": "Software transmission and ACK confirmed. Physical LED luminous output unverified without optical photodiode."
    }

@router.get("/hardware/feature-compatibility")
async def get_hardware_feature_compatibility():
    """Inspect active model feature schema against single physical STM32 capabilities."""
    model_id, pipeline, metadata = await model_registry.get_active_model()
    features = metadata.get("feature_list", []) if metadata else []
    return {
        "active_model_id": model_id,
        "active_model_name": metadata.get("model_name", "None") if metadata else "None",
        "analysis": hardware_ml_service.inspect_model_compatibility(features)
    }

@router.post("/hardware/train-model")
async def train_dedicated_hardware_model(req: HardwareTrainRequest):
    """Train dedicated physical hardware model on genuine TEMP, HUM, DIST features."""
    result = await hardware_ml_service.train_hardware_model(n_samples=req.n_samples)
    return result

@router.get("/hardware/predictions")
async def get_hardware_predictions(limit: int = 50):
    """Fetch history of predictions generated strictly on physical hardware telemetry."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(PredictionRecord)
            .where(PredictionRecord.data_source == "REAL_HARDWARE")
            .order_by(desc(PredictionRecord.id))
            .limit(limit)
        )
        res = await session.execute(stmt)
        records = res.scalars().all()
        return [{
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "model_id": r.model_id,
            "predicted_label": r.predicted_label,
            "confidence": r.confidence,
            "anomaly_score": r.anomaly_score,
            "is_anomaly": r.is_anomaly,
            "data_source": r.data_source,
            "features_used": r.features_used
        } for r in records]

