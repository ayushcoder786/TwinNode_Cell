"""
TwinNode Public Dataset REST Gateway
Implements discovery, asynchronous downloading, inspection, local file import,
preview, preprocessing, and model benchmarking for external datasets.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel, Field

from backend.app.data.external_dataset_catalog import (
    EXTERNAL_DATASET_CATALOG,
    is_url_allowed
)
from backend.app.data.external_dataset_manager import dataset_manager
from backend.app.data.external_dataset_inspector import dataset_inspector
from backend.app.data.external_dataset_preprocessor import dataset_preprocessor
from backend.app.ml.external_model_trainer import external_model_trainer

router = APIRouter(prefix="/datasets", tags=["External Datasets"])

# Pydantic Schemas
class DownloadRequest(BaseModel):
    dataset_id: str
    custom_url: Optional[str] = None
    force_redownload: bool = False

class InspectRequest(BaseModel):
    dataset_id: str
    filename: Optional[str] = None
    is_processed: bool = False

class PreprocessRequest(BaseModel):
    dataset_id: str
    filename: Optional[str] = None
    impute_strategy: str = "median"
    scaler_type: str = "standard"
    drop_duplicates: bool = True
    remove_outliers: bool = False
    outlier_threshold: float = 3.0
    target_column: Optional[str] = None
    selected_features: Optional[List[str]] = None
    output_format: str = "csv"

class TrainExternalRequest(BaseModel):
    dataset_id: str
    algorithm: str = "RandomForest"
    experiment_type: str = "EXTERNAL_BENCHMARK"
    target_column: Optional[str] = None
    test_size: float = 0.20
    hyperparameters: Optional[Dict[str, Any]] = None
    use_processed: bool = True

# 1. GET /api/datasets/external
@router.get("/external")
async def list_external_datasets():
    """List all available public datasets in the catalog with local download and processed status."""
    catalog = dataset_manager.list_catalog()
    return {
        "status": "SUCCESS",
        "datasets": catalog,
        "count": len(catalog),
        "allowed_sources": [
            "UNSW Canberra Cyber Range (TON_IoT)",
            "iTrust Singapore SUTD (SWaT)",
            "IEEE DataPort (Edge-IIoTset)",
            "Hugging Face Datasets Hub"
        ]
    }

# 2. POST /api/datasets/download
@router.post("/download")
async def trigger_dataset_download(req: DownloadRequest):
    """Trigger background download with streaming progress tracking and integrity checks."""
    if req.dataset_id not in EXTERNAL_DATASET_CATALOG:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{req.dataset_id}' not found in catalog. Available: {list(EXTERNAL_DATASET_CATALOG.keys())}"
        )

    cat_entry = EXTERNAL_DATASET_CATALOG[req.dataset_id]
    if not cat_entry.get("is_public_download") and not req.custom_url:
        raise HTTPException(
            status_code=403,
            detail=f"Dataset '{cat_entry['name']}' requires formal registration. {cat_entry.get('auth_instructions')}"
        )

    if req.custom_url and not is_url_allowed(req.custom_url):
        raise HTTPException(
            status_code=400,
            detail="The specified download URL is not in the server-side authorized domain allowlist."
        )

    try:
        task = await dataset_manager.start_download(
            dataset_id=req.dataset_id,
            custom_url=req.custom_url,
            force_redownload=req.force_redownload
        )
        return {
            "status": "DOWNLOAD_INITIATED",
            "task": task
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate download: {str(e)}")

# 3. GET /api/datasets/download-status/{id}
@router.get("/download-status/{download_id}")
async def get_download_status(download_id: str):
    """Poll real-time progress for a specific dataset download task."""
    task = dataset_manager.get_download_status(download_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Download task '{download_id}' not found.")
    return task

# 4. POST /api/datasets/inspect
@router.post("/inspect")
async def inspect_dataset(req: InspectRequest):
    """Inspect dataset file structure, dimensions, data types, missingness, duplicates, and class distributions."""
    try:
        report = dataset_inspector.inspect_file(
            dataset_id=req.dataset_id,
            filename=req.filename,
            is_processed=req.is_processed
        )
        return {
            "status": "SUCCESS",
            "report": report
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inspection failed: {str(e)}")

# 5. POST /api/datasets/import
@router.post("/import")
async def import_local_dataset(
    dataset_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Safely import a manually uploaded or local dataset file (e.g. for SWaT or Edge-IIoTset)."""
    if dataset_id not in EXTERNAL_DATASET_CATALOG:
        raise HTTPException(status_code=404, detail=f"Unknown dataset_id: {dataset_id}")

    try:
        contents = await file.read()
        res = dataset_manager.import_local_file(
            dataset_id=dataset_id,
            source_path_or_buffer=contents,
            original_filename=file.filename
        )
        return {
            "status": "IMPORT_SUCCESS",
            "details": res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

# 6. GET /api/datasets/preview
@router.get("/preview")
async def preview_dataset(
    dataset_id: str = Query(...),
    filename: Optional[str] = Query(None),
    is_processed: bool = Query(False),
    limit: int = Query(25, ge=1, le=100)
):
    """Retrieve top N sample records from dataset for interactive UI preview table."""
    try:
        preview = dataset_inspector.preview_data(
            dataset_id=dataset_id,
            filename=filename,
            is_processed=is_processed,
            limit=limit
        )
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")

# 7. GET /api/datasets/statistics
@router.get("/statistics")
async def get_dataset_statistics(
    dataset_id: str = Query(...),
    filename: Optional[str] = Query(None),
    is_processed: bool = Query(False)
):
    """Retrieve detailed numerical and categorical statistics for the dataset."""
    try:
        report = dataset_inspector.inspect_file(
            dataset_id=dataset_id,
            filename=filename,
            is_processed=is_processed
        )
        return {
            "dataset_id": dataset_id,
            "total_records": report["total_records"],
            "total_columns": report["total_columns"],
            "missing_percentage": report["missing_percentage"],
            "duplicate_records": report["duplicate_records"],
            "class_distribution": report["class_distribution"],
            "sampling_frequency": report["sampling_frequency"],
            "sensor_units": report["sensor_units"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")

# 8. POST /api/datasets/preprocess
@router.post("/preprocess")
async def preprocess_dataset(req: PreprocessRequest):
    """Preprocess external dataset, applying scaling, encoding, and imputation while preserving raw data."""
    try:
        result = dataset_preprocessor.preprocess_dataset(
            dataset_id=req.dataset_id,
            filename=req.filename,
            impute_strategy=req.impute_strategy,
            scaler_type=req.scaler_type,
            drop_duplicates=req.drop_duplicates,
            remove_outliers=req.remove_outliers,
            outlier_threshold=req.outlier_threshold,
            target_column=req.target_column,
            selected_features=req.selected_features,
            output_format=req.output_format
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing failed: {str(e)}")

# 9. GET /api/datasets/history
@router.get("/history")
async def get_dataset_history():
    """Retrieve download, import, and experiment audit log."""
    history = dataset_manager.get_history()
    experiments = external_model_trainer.list_experiments()
    return {
        "download_and_import_history": history,
        "external_model_experiments": experiments
    }

# 10. POST /api/datasets/train
@router.post("/train")
async def train_on_external_dataset(req: TrainExternalRequest):
    """Train and evaluate an ML model on an external public dataset."""
    try:
        result = await external_model_trainer.train_external_model(
            dataset_id=req.dataset_id,
            algorithm=req.algorithm,
            experiment_type=req.experiment_type,
            target_column=req.target_column,
            test_size=req.test_size,
            hyperparameters=req.hyperparameters,
            use_processed=req.use_processed
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
