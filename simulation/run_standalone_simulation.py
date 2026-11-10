"""
TwinNode Standalone Distributed Simulation Runner
Runs without backend/frontend for headless CLI validation.
"""

import time
import sys
from backend.app.services.simulation_service import SimulationEngine
from backend.app.services.condition_engine import ConditionEngine

def main():
    print("=" * 70)
    print("  TWINNODE CELL - STANDALONE DISTRIBUTED SYSTEM SIMULATION")
    print("  Emulating Node 1 (Generator) & Node 2 (Actuator/Sensor)")
    print("=" * 70)
    print("\nPress Ctrl+C to terminate simulation.\n")

    sim = SimulationEngine()
    engine = ConditionEngine()

    sim.update_targets({
        "target_temp": 28.0,
        "target_dist": 20.0,
        "target_motor_speed": 45,
        "target_servo_angle": 135
    })

    step_count = 0
    try:
        while True:
            step_count += 1
            data = sim.step()

            # At step 25, demonstrate fault injection (sensor out of range)
            if step_count == 25:
                print("\n[FAULT INJECTION] Injecting Temperature Out of Range (115°C)...")
                sim.set_fault_injection("temp_out_of_range", True)
            elif step_count == 40:
                print("\n[CLEAR FAULT] Restoring normal temperature dynamics...")
                sim.clear_fault_injections()
                engine.reset_faults()
            elif step_count == 55:
                print("\n[FAULT INJECTION] Injecting Inter-Node UART Communication Drop...")
                sim.set_fault_injection("comm_drop", True)
            elif step_count == 70:
                print("\n[CLEAR FAULT] Restoring communication bus...")
                sim.clear_fault_injections()
                engine.reset_faults()

            target = {
                "target_temp": sim.target_temp,
                "target_dist": sim.target_dist,
                "target_motor_speed": sim.target_motor_speed,
                "target_servo_angle": sim.target_servo_angle
            }
            faults = engine.evaluate(data, target)

            fault_str = "NORMAL" if not faults else f"ALARM({faults[0]['fault_code']}: {faults[0]['severity']})"

            sys.stdout.write(
                f"\r[Step {step_count:04d}] "
                f"N1:{data['node1_status']} | N2:{data['node2_status']} | "
                f"Temp:{data['actual_temp']:5.1f}°C (Tgt:{target['target_temp']}°C) | "
                f"Dist:{data['actual_dist']:5.1f}cm (Tgt:{target['target_dist']}cm) | "
                f"Motor:{data['actual_motor_speed']:+4d}% | "
                f"Servo:{data['actual_servo_angle']:3d}° | "
                f"Status: {fault_str}   "
            )
            sys.stdout.flush()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nSimulation terminated cleanly by user.")

if __name__ == "__main__":
    main()
