import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db.session import engine, Base

@pytest.mark.asyncio
async def test_health_endpoint():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert "mode" in data

@pytest.mark.asyncio
async def test_ports_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/ports")
        assert res.status_code == 200
        assert "ports" in res.json()

@pytest.mark.asyncio
async def test_eq15_09_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/eq15_09/status")
        assert res.status_code == 200
        data = res.json()
        assert data["condition_id"] == "EQ-15-09"
        assert data["status"] == "PENDING_CONFIRMATION"

@pytest.mark.asyncio
async def test_testbench_controls():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start test
        start_res = await client.post("/api/test/start", json={
            "name": "INTEGRATION_TEST_01",
            "profile": "STANDARD_INDUSTRIAL",
            "targets": {
                "target_temp": 26.0,
                "target_dist": 22.0,
                "target_motor_speed": 30,
                "target_servo_angle": 100
            }
        })
        assert start_res.status_code == 200
        test_id = start_res.json()["test_id"]
        assert test_id is not None

        # Pause
        pause_res = await client.post("/api/test/pause")
        assert pause_res.status_code == 200

        # Resume
        resume_res = await client.post("/api/test/resume")
        assert resume_res.status_code == 200

        # Stop
        stop_res = await client.post("/api/test/stop")
        assert stop_res.status_code == 200

        # Emergency Stop
        estop_res = await client.post("/api/test/emergency_stop")
        assert estop_res.status_code == 200
        assert estop_res.json()["status"] == "EMERGENCY_STOP_TRIGGERED"

        # Reset
        reset_res = await client.post("/api/test/reset")
        assert reset_res.status_code == 200

@pytest.mark.asyncio
async def test_fault_injection_and_reports():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fault injection
        inj_res = await client.post("/api/simulation/fault_injection", json={
            "fault_key": "disconnect_lm35",
            "state": True
        })
        assert inj_res.status_code == 200
        assert inj_res.json()["active_injections"]["disconnect_lm35"] is True

        # Clear fault injection
        inj_clear = await client.post("/api/simulation/fault_injection", json={
            "fault_key": "disconnect_lm35",
            "state": False
        })
        assert inj_clear.status_code == 200

        # Export CSV report
        csv_res = await client.get("/api/reports/export/csv/1001")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert b"Target_Temp_C" in csv_res.content

        # Export PDF report
        pdf_res = await client.get("/api/reports/export/pdf/1001")
        assert pdf_res.status_code == 200
        assert "application/pdf" in pdf_res.headers["content-type"]
        assert pdf_res.content.startswith(b"%PDF")
