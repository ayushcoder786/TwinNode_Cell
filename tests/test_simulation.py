import pytest
from backend.app.services.simulation_service import SimulationEngine

def test_simulation_step():
    sim = SimulationEngine()
    sim.update_targets({
        "target_temp": 28.0,
        "target_dist": 30.0,
        "target_motor_speed": 50,
        "target_servo_angle": 120
    })
    
    # Run multiple steps
    data = None
    for _ in range(5):
        data = sim.step()

    assert data is not None
    assert data["node1_status"] == "ONLINE"
    assert data["node2_status"] == "ONLINE"
    assert data["target_motor_speed"] == 50
    assert data["target_servo_angle"] == 120
    assert data["is_simulated"] is True

def test_simulation_fault_injection():
    sim = SimulationEngine()
    sim.set_fault_injection("disconnect_lm35", True)
    data = sim.step()
    assert data["actual_temp"] == 0.0

    sim.set_fault_injection("disconnect_lm35", False)
    sim.set_fault_injection("comm_drop", True)
    data = sim.step()
    assert data["node2_status"] == "OFFLINE_TIMEOUT"
    assert data["comm_latency_ms"] >= 2000.0

    sim.clear_fault_injections()
    data = sim.step()
    assert data["node2_status"] == "ONLINE"
