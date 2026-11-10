"""
TwinNode Public Dataset Catalog and Security Allowlist.
Defines authoritative metadata, official sources, priority sensor telemetry files,
and security constraints for external IoT/IIoT datasets.
"""

from typing import Dict, Any, List

# Strict server-side allowlist of authorized download hosts to prevent SSRF
ALLOWED_DOWNLOAD_DOMAINS = [
    "huggingface.co",
    "cdn-lfs.huggingface.co",
    "raw.githubusercontent.com",
    "github.com",
    "research.unsw.edu.au",
    "itrust.sutd.edu.sg",
    "ieee-dataport.org"
]

EXTERNAL_DATASET_CATALOG: Dict[str, Dict[str, Any]] = {
    "ton_iot_thermostat": {
        "id": "ton_iot_thermostat",
        "family": "TON_IoT",
        "name": "TON_IoT Smart Thermostat Telemetry",
        "category": "IoT Sensor Telemetry",
        "provenance": "PUBLIC_DATASET",
        "description": "Real-world IoT thermostat telemetry capturing continuous temperature readings, binary thermostat actuator status, and multi-class anomaly/attack types (injection, backdoor, ddos, normal, etc.). Collected by UNSW Canberra Cyber Range Lab.",
        "official_url": "https://research.unsw.edu.au/projects/toniot-datasets",
        "download_url": "https://huggingface.co/datasets/SilverDragon9/UNSW_TON-IoT_Train_Test_IoT_Datasets/resolve/main/Train_Test_IoT_Thermostat.csv",
        "filename": "Train_Test_IoT_Thermostat.csv",
        "format": "csv",
        "approx_size_bytes": 1464768,
        "approx_size_mb": 1.40,
        "license": "AFL-3.0 / UNSW Academic Research License",
        "is_public_download": True,
        "requires_auth": False,
        "priority_telemetry": ["current_temperature", "thermostat_status"],
        "target_columns": ["label", "type"],
        "sensor_units": {
            "current_temperature": "°C",
            "thermostat_status": "binary_state"
        },
        "suitability": "HIGH — Directly comparable to TwinNode temperature sensing and thermal regulation setpoints."
    },
    "ton_iot_fridge": {
        "id": "ton_iot_fridge",
        "family": "TON_IoT",
        "name": "TON_IoT Smart Fridge Telemetry",
        "category": "IoT Sensor Telemetry",
        "provenance": "PUBLIC_DATASET",
        "description": "Smart refrigeration telemetry logging temperature, condition (high/low/normal), and anomaly labels under nominal and adversarial scenarios.",
        "official_url": "https://research.unsw.edu.au/projects/toniot-datasets",
        "download_url": "https://huggingface.co/datasets/SilverDragon9/UNSW_TON-IoT_Train_Test_IoT_Datasets/resolve/main/Train_Test_IoT_Fridge.csv",
        "filename": "Train_Test_IoT_Fridge.csv",
        "format": "csv",
        "approx_size_bytes": 1678744,
        "approx_size_mb": 1.60,
        "license": "AFL-3.0 / UNSW Academic Research License",
        "is_public_download": True,
        "requires_auth": False,
        "priority_telemetry": ["fridge_temperature", "temp_condition"],
        "target_columns": ["label", "type"],
        "sensor_units": {
            "fridge_temperature": "°C",
            "temp_condition": "categorical_state"
        },
        "suitability": "HIGH — Temperature monitoring and thermal condition evaluation."
    },
    "ton_iot_weather": {
        "id": "ton_iot_weather",
        "family": "TON_IoT",
        "name": "TON_IoT Weather Station Telemetry",
        "category": "IoT Environmental Telemetry",
        "provenance": "PUBLIC_DATASET",
        "description": "Environmental IoT weather station telemetry logging continuous temperature, air pressure, and relative humidity.",
        "official_url": "https://research.unsw.edu.au/projects/toniot-datasets",
        "download_url": "https://huggingface.co/datasets/SilverDragon9/UNSW_TON-IoT_Train_Test_IoT_Datasets/resolve/main/Train_Test_IoT_Weather.csv",
        "filename": "Train_Test_IoT_Weather.csv",
        "format": "csv",
        "approx_size_bytes": 2587701,
        "approx_size_mb": 2.47,
        "license": "AFL-3.0 / UNSW Academic Research License",
        "is_public_download": True,
        "requires_auth": False,
        "priority_telemetry": ["temperature", "pressure", "humidity"],
        "target_columns": ["label", "type"],
        "sensor_units": {
            "temperature": "°C",
            "pressure": "bar",
            "humidity": "%RH"
        },
        "suitability": "MEDIUM — Multi-modal environmental sensor telemetry."
    },
    "ton_iot_modbus": {
        "id": "ton_iot_modbus",
        "family": "TON_IoT",
        "name": "TON_IoT Modbus Industrial Telemetry",
        "category": "Industrial Protocol Telemetry",
        "provenance": "PUBLIC_DATASET",
        "description": "Industrial Modbus communication protocol telemetry logging packet sequences, function codes, and transaction latencies.",
        "official_url": "https://research.unsw.edu.au/projects/toniot-datasets",
        "download_url": "https://huggingface.co/datasets/SilverDragon9/UNSW_TON-IoT_Train_Test_IoT_Datasets/resolve/main/Train_Test_IoT_Modbus.csv",
        "filename": "Train_Test_IoT_Modbus.csv",
        "format": "csv",
        "approx_size_bytes": 1694191,
        "approx_size_mb": 1.62,
        "license": "AFL-3.0 / UNSW Academic Research License",
        "is_public_download": True,
        "requires_auth": False,
        "priority_telemetry": ["FC1_Read_Input_Register", "FC2_Read_Discrete_Inputs", "FC3_Read_Holding_Register"],
        "target_columns": ["label", "type"],
        "sensor_units": {
            "registers": "count/code"
        },
        "suitability": "MEDIUM — Protocol timing and serial frame latency comparison."
    },
    "swat_water_treatment": {
        "id": "swat_water_treatment",
        "family": "SWaT",
        "name": "SWaT (Secure Water Treatment Testbed)",
        "category": "Industrial Cyber-Physical Infrastructure",
        "provenance": "PUBLIC_DATASET",
        "description": "Six-stage continuous water treatment testbed (raw water supply, chemical dosing, ultrafiltration, dechlorination, reverse osmosis, backwash) capturing 51 physical sensors and actuators (flow meters, level transmitters, motorized pumps, dosing valves). Collected by iTrust Singapore.",
        "official_url": "https://itrust.sutd.edu.sg/itrust-labs_datasets/",
        "download_url": None,
        "filename": "SWaT_Dataset_Normal_v1.csv",
        "format": "csv",
        "approx_size_bytes": None,
        "approx_size_mb": None,
        "license": "Restricted Research Agreement (iTrust SUTD Approval Required)",
        "is_public_download": False,
        "requires_auth": True,
        "auth_instructions": (
            "Access to the official SWaT dataset requires submitting a formal request form to iTrust SUTD at "
            "https://itrust.sutd.edu.sg/itrust-labs_datasets/. Once your institutional application is approved, "
            "download the dataset ZIP/CSV from the private repository link provided by iTrust, then use the "
            "'Import Local Dataset' feature in TwinNode ML Studio to load the file into backend/datasets/external/swat/."
        ),
        "priority_telemetry": ["FIT101", "LIT101", "MV101", "P101", "FIT201", "AIT201", "P201"],
        "target_columns": ["Normal/Attack"],
        "sensor_units": {
            "FIT": "m3/hr",
            "LIT": "mm",
            "AIT": "pH / conductivity"
        },
        "suitability": "HIGH (CPS Benchmark) — Closed-loop level and flow control with physical actuator interlocks."
    },
    "edge_iiotset": {
        "id": "edge_iiotset",
        "family": "Edge-IIoTset",
        "name": "Edge-IIoTset Industrial IoT Dataset",
        "category": "IIoT Multi-protocol & Edge Anomaly Detection",
        "provenance": "PUBLIC_DATASET",
        "description": "Realistic cyber security dataset for IoT and IIoT applications containing 61 features across Modbus, MQTT, CoAP, and HTTP network telemetry under 14 cyber attack types and nominal industrial cycles. Co-developed by IEEE DataPort.",
        "official_url": "https://ieee-dataport.org/documents/edge-iiotset-new-comprehensive-realistic-cyber-security-dataset-iot-and-iiot-applications",
        "download_url": None,
        "filename": "ML-EdgeIIoT-dataset.csv",
        "format": "csv",
        "approx_size_bytes": None,
        "approx_size_mb": None,
        "license": "IEEE DataPort Open / Creative Commons Attribution (CC BY 4.0)",
        "is_public_download": False,
        "requires_auth": True,
        "auth_instructions": (
            "The full Edge-IIoTset archive (~12 GB uncompressed) is hosted on IEEE DataPort and Kaggle "
            "(https://www.kaggle.com/datasets/mohamedamineferrag/edgeiiotset-cyber-security-dataset-of-iot-iiot). "
            "Download the curated 'ML-EdgeIIoT-dataset.csv' from Kaggle or IEEE DataPort, then use the "
            "'Import Local Dataset' feature in TwinNode ML Studio to place it under backend/datasets/external/edge_iiotset/."
        ),
        "priority_telemetry": ["tcp.len", "frame.len", "tcp.time_delta", "mqtt.conack.flags"],
        "target_columns": ["Attack_label", "Attack_type"],
        "sensor_units": {
            "len": "bytes",
            "time_delta": "seconds"
        },
        "suitability": "SPECIALIZED — IoT network anomaly detection; not for direct STM32 analog sensor validation."
    }
}

def is_url_allowed(url: str) -> bool:
    """Validate whether download URL belongs to strict domain allowlist."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            return False
        return any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_DOWNLOAD_DOMAINS)
    except Exception:
        return False
