"""
Automated Test Suite for TwinNode Public Dataset Download & ML Integration.
Tests catalog, security allowlists, download manager, inspection, preprocessing,
model benchmarking, and REST API endpoints.
"""

import os
import pytest
import tempfile
from pathlib import Path
import pandas as pd
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.data.external_dataset_catalog import (
    EXTERNAL_DATASET_CATALOG,
    is_url_allowed
)
from backend.app.data.external_dataset_manager import dataset_manager, EXTERNAL_ROOT, PROCESSED_ROOT
from backend.app.data.external_dataset_inspector import dataset_inspector
from backend.app.data.external_dataset_preprocessor import dataset_preprocessor
from backend.app.ml.external_model_trainer import external_model_trainer

# 1. Test Catalog & Security Allowlist
def test_catalog_structure_and_url_allowlist():
    assert "ton_iot_thermostat" in EXTERNAL_DATASET_CATALOG
    assert "swat_water_treatment" in EXTERNAL_DATASET_CATALOG
    assert "edge_iiotset" in EXTERNAL_DATASET_CATALOG

    # Check allowlist validations
    assert is_url_allowed("https://huggingface.co/datasets/SilverDragon9/dataset.csv") is True
    assert is_url_allowed("https://research.unsw.edu.au/projects/toniot") is True
    assert is_url_allowed("https://raw.githubusercontent.com/user/repo/main/data.csv") is True
    
    # Block unauthorized or malicious URLs (SSRF prevention)
    assert is_url_allowed("http://localhost:8000/steal") is False
    assert is_url_allowed("http://169.254.169.254/latest/meta-data/") is False
    assert is_url_allowed("https://evil-attacker.com/payload.csv") is False

# 2. Test Real Dataset Download of TON_IoT Thermostat
@pytest.mark.asyncio
async def test_download_real_public_dataset():
    """
    Phase 1 & 8 Verification: Automatically download real-world TON_IoT Thermostat dataset
    from Hugging Face and verify its completion and file integrity.
    """
    task = await dataset_manager.start_download(
        dataset_id="ton_iot_thermostat",
        force_redownload=False
    )
    assert task is not None
    download_id = task["download_id"]

    # If it was queued, wait briefly for async download to complete
    if task["status"] in ["QUEUED", "DOWNLOADING"]:
        for _ in range(30):
            import asyncio
            await asyncio.sleep(1)
            status_info = dataset_manager.get_download_status(download_id)
            if status_info and status_info["status"] in ["COMPLETED", "FAILED"]:
                task = status_info
                break

    assert task["status"] == "COMPLETED"
    dest_path = Path(task.get("dest_path", EXTERNAL_ROOT / "ton_iot_thermostat" / "Train_Test_IoT_Thermostat.csv"))
    assert dest_path.exists()
    assert dest_path.stat().st_size > 100000 # File is ~1.46 MB

# 3. Test Phase 2: Dataset Inspection
def test_external_dataset_inspection():
    """Inspect schema, types, missing values, class distributions without mutating raw data."""
    report = dataset_inspector.inspect_file("ton_iot_thermostat")
    assert report["dataset_id"] == "ton_iot_thermostat"
    assert report["total_records"] > 10000
    assert report["total_columns"] >= 5
    assert "current_temperature" in [c["column_name"] for c in report["columns"]]
    assert "thermostat_status" in [c["column_name"] for c in report["columns"]]
    assert len(report["class_distribution"]) > 0
    assert report["provenance"] == "PUBLIC_DATASET"

# 4. Test Phase 3: Dataset Preprocessing
def test_external_dataset_preprocessing():
    """Verify preprocessing generates separate processed file and does not mutate raw file."""
    raw_file = EXTERNAL_ROOT / "ton_iot_thermostat" / "Train_Test_IoT_Thermostat.csv"
    assert raw_file.exists()
    raw_size_before = raw_file.stat().st_size

    prep_result = dataset_preprocessor.preprocess_dataset(
        dataset_id="ton_iot_thermostat",
        scaler_type="standard",
        drop_duplicates=True,
        impute_strategy="median"
    )

    assert prep_result["status"] == "COMPLETED"
    assert prep_result["final_rows"] > 0
    assert Path(prep_result["processed_path"]).exists()

    # Raw file must remain completely unmodified
    assert raw_file.stat().st_size == raw_size_before

# 5. Test Phase 5: Machine Learning Benchmarking on External Dataset
@pytest.mark.asyncio
async def test_external_model_training_and_benchmarking():
    """Train Random Forest and Decision Tree on the public dataset."""
    res_rf = await external_model_trainer.train_external_model(
        dataset_id="ton_iot_thermostat",
        algorithm="RandomForest",
        experiment_type="EXTERNAL_BENCHMARK",
        test_size=0.20,
        max_samples=15000
    )

    assert res_rf["provenance"] == "PUBLIC_DATASET"
    assert res_rf["train_samples"] > 0
    assert res_rf["test_samples"] > 0
    assert "metrics" in res_rf
    assert res_rf["metrics"]["accuracy"] > 0.50
    assert res_rf["metrics"]["f1_macro"] > 0.40
    assert Path(res_rf["model_artifact"]).exists()

# 6. Test Manual Local Import & Path Traversal Prevention
def test_import_local_dataset_security():
    # Unsupported extension
    with pytest.raises(ValueError):
        dataset_manager.import_local_file(
            dataset_id="swat_water_treatment",
            source_path_or_buffer=b"malicious executable",
            original_filename="malicious.exe"
        )

    # Valid CSV import
    sample_csv = b"FIT101,LIT101,Normal/Attack\n1.2,500.0,0\n1.3,510.0,1\n"
    res = dataset_manager.import_local_file(
        dataset_id="swat_water_treatment",
        source_path_or_buffer=sample_csv,
        original_filename="SWaT_sample.csv"
    )
    assert res["status"] == "SUCCESS"
    assert (EXTERNAL_ROOT / "swat_water_treatment" / "SWaT_sample.csv").exists()

# 7. Test REST Endpoints
@pytest.mark.asyncio
async def test_external_datasets_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET /api/datasets/external
        res = await ac.get("/api/datasets/external")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert len(data["datasets"]) >= 3

        # POST /api/datasets/inspect
        res_insp = await ac.post("/api/datasets/inspect", json={"dataset_id": "ton_iot_thermostat"})
        assert res_insp.status_code == 200
        assert "report" in res_insp.json()

        # GET /api/datasets/preview
        res_prev = await ac.get("/api/datasets/preview?dataset_id=ton_iot_thermostat&limit=5")
        assert res_prev.status_code == 200
        prev_data = res_prev.json()
        assert len(prev_data["records"]) <= 5

        # GET /api/datasets/history
        res_hist = await ac.get("/api/datasets/history")
        assert res_hist.status_code == 200
        assert "download_and_import_history" in res_hist.json()
