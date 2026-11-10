import React, { useState, useEffect } from 'react';
import {
  Globe,
  Download,
  Upload,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileText,
  Sliders,
  Database,
  Layers,
  Sparkles,
  ShieldCheck,
  Zap,
  Clock,
  ArrowRight,
  ExternalLink,
  Table,
  BarChart2,
  PieChart,
  Lock,
  Cpu,
  Info
} from 'lucide-react';

export const ExternalDatasetManagerPage = ({ onNavigate }) => {
  const [catalog, setCatalog] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDatasetId, setSelectedDatasetId] = useState('ton_iot_thermostat');
  const [activeDownload, setActiveDownload] = useState(null);
  const [inspectionReport, setInspectionReport] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  
  // Preprocessing State
  const [scalerType, setScalerType] = useState('standard');
  const [imputeStrategy, setImputeStrategy] = useState('median');
  const [dropDuplicates, setDropDuplicates] = useState(true);
  const [isPreprocessing, setIsPreprocessing] = useState(false);
  const [preprocessResult, setPreprocessResult] = useState(null);

  // Model Training State
  const [trainingAlgo, setTrainingAlgo] = useState('RandomForest');
  const [isTraining, setIsTraining] = useState(false);
  const [trainingResult, setTrainingResult] = useState(null);

  // Import Modal State
  const [showImportModal, setShowImportModal] = useState(false);
  const [importDatasetId, setImportDatasetId] = useState('swat_water_treatment');
  const [importFile, setImportFile] = useState(null);
  const [importStatus, setImportStatus] = useState(null);

  // Auth Info Modal for SWaT / Edge-IIoTset
  const [authModalDataset, setAuthModalDataset] = useState(null);

  // Active view tab: 'overview' | 'schema' | 'preview' | 'preprocess' | 'train'
  const [activeTab, setActiveTab] = useState('overview');

  const fetchCatalog = async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/datasets/external');
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        setCatalog(data.datasets);
      }
    } catch (err) {
      console.error('Failed to load dataset catalog:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  // Poll download progress if active
  useEffect(() => {
    let interval = null;
    if (activeDownload && activeDownload.status === 'DOWNLOADING') {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`/api/datasets/download-status/${activeDownload.download_id}`);
          if (res.ok) {
            const data = await res.json();
            setActiveDownload(data);
            if (data.status === 'COMPLETED' || data.status === 'FAILED') {
              clearInterval(interval);
              fetchCatalog();
            }
          }
        } catch (err) {
          console.error('Download status poll error:', err);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeDownload]);

  // Load inspection and preview when selected dataset changes
  useEffect(() => {
    if (selectedDatasetId) {
      handleInspect(selectedDatasetId);
      handlePreview(selectedDatasetId);
    }
  }, [selectedDatasetId]);

  const handleTriggerDownload = async (datasetId) => {
    try {
      const res = await fetch('/api/datasets/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, force_redownload: false })
      });
      const data = await res.json();
      if (res.ok) {
        setActiveDownload(data.task);
        if (data.task.status === 'COMPLETED') {
          fetchCatalog();
          setSelectedDatasetId(datasetId);
        }
      } else {
        alert(data.detail || 'Download request failed.');
      }
    } catch (err) {
      alert(`Download error: ${err.message}`);
    }
  };

  const handleInspect = async (datasetId, isProcessed = false) => {
    try {
      setIsInspecting(true);
      const res = await fetch('/api/datasets/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, is_processed: isProcessed })
      });
      if (res.ok) {
        const data = await res.json();
        setInspectionReport(data.report);
      } else {
        setInspectionReport(null);
      }
    } catch (err) {
      setInspectionReport(null);
    } finally {
      setIsInspecting(false);
    }
  };

  const handlePreview = async (datasetId, isProcessed = false) => {
    try {
      setIsPreviewLoading(true);
      const res = await fetch(`/api/datasets/preview?dataset_id=${datasetId}&is_processed=${isProcessed}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setPreviewData(data);
      } else {
        setPreviewData(null);
      }
    } catch (err) {
      setPreviewData(null);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleRunPreprocessor = async () => {
    try {
      setIsPreprocessing(true);
      setPreprocessResult(null);
      const res = await fetch('/api/datasets/preprocess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: selectedDatasetId,
          scaler_type: scalerType,
          impute_strategy: imputeStrategy,
          drop_duplicates: dropDuplicates
        })
      });
      const data = await res.json();
      if (res.ok) {
        setPreprocessResult(data);
        fetchCatalog();
      } else {
        alert(data.detail || 'Preprocessing failed.');
      }
    } catch (err) {
      alert(`Preprocessing error: ${err.message}`);
    } finally {
      setIsPreprocessing(false);
    }
  };

  const handleTrainModel = async () => {
    try {
      setIsTraining(true);
      setTrainingResult(null);
      const res = await fetch('/api/datasets/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: selectedDatasetId,
          algorithm: trainingAlgo,
          experiment_type: 'EXTERNAL_BENCHMARK',
          test_size: 0.20,
          use_processed: true
        })
      });
      const data = await res.json();
      if (res.ok) {
        setTrainingResult(data);
      } else {
        alert(data.detail || 'Training failed.');
      }
    } catch (err) {
      alert(`Training error: ${err.message}`);
    } finally {
      setIsTraining(false);
    }
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    if (!importFile) {
      alert('Please select a file to import.');
      return;
    }
    const formData = new FormData();
    formData.append('dataset_id', importDatasetId);
    formData.append('file', importFile);

    try {
      setImportStatus({ status: 'UPLOADING', message: 'Importing local dataset...' });
      const res = await fetch('/api/datasets/import', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setImportStatus({ status: 'SUCCESS', message: 'Dataset imported successfully!' });
        fetchCatalog();
        setSelectedDatasetId(importDatasetId);
        setTimeout(() => setShowImportModal(false), 1500);
      } else {
        setImportStatus({ status: 'ERROR', message: data.detail || 'Import failed.' });
      }
    } catch (err) {
      setImportStatus({ status: 'ERROR', message: err.message });
    }
  };

  const currentDataset = catalog.find(d => d.id === selectedDatasetId);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-sky-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">Public Dataset Hub & External Benchmark Manager</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Download, inspect, preprocess, and benchmark real-world IoT datasets (TON_IoT, SWaT, Edge-IIoTset) with strict provenance separation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 rounded font-mono text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            PUBLIC_DATASET PROVENANCE
          </span>
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-all shadow-sm"
          >
            <Upload className="w-3.5 h-3.5 text-sky-400" />
            Import Local Dataset
          </button>
          <button
            onClick={fetchCatalog}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Refresh Catalog"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Active Download Progress Banner */}
      {activeDownload && (
        <div className="bg-[#0f172a] border border-sky-500/40 rounded-xl p-4 space-y-2 shadow-lg animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Download className={`w-4 h-4 ${activeDownload.status === 'DOWNLOADING' ? 'animate-bounce text-sky-400' : 'text-emerald-400'}`} />
              <span className="text-xs font-semibold text-white">
                {activeDownload.status === 'COMPLETED' ? 'Download Completed:' : 'Downloading Public Dataset:'}
              </span>
              <span className="text-xs font-mono text-sky-300">{activeDownload.filename}</span>
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
              activeDownload.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
              activeDownload.status === 'DOWNLOADING' ? 'bg-sky-500/20 text-sky-400 animate-pulse' :
              'bg-rose-500/20 text-rose-400'
            }`}>
              {activeDownload.status}
            </span>
          </div>

          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${activeDownload.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-sky-500'}`}
              style={{ width: `${activeDownload.progress_percent || 0}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>
              {((activeDownload.bytes_downloaded || 0) / (1024 * 1024)).toFixed(2)} MB / {((activeDownload.total_bytes || 0) / (1024 * 1024)).toFixed(2)} MB ({activeDownload.progress_percent}%)
            </span>
            {activeDownload.speed_kbps > 0 && <span>Speed: {activeDownload.speed_kbps} KB/s</span>}
            {activeDownload.sha256 && <span>SHA256: {activeDownload.sha256.substring(0, 12)}...</span>}
          </div>
        </div>
      )}

      {/* Dataset Catalog Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {catalog.map((item) => {
          const isSelected = item.id === selectedDatasetId;
          const isDownloaded = item.is_downloaded;
          return (
            <div
              key={item.id}
              onClick={() => setSelectedDatasetId(item.id)}
              className={`rounded-xl border p-4 transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'bg-slate-900 border-sky-500/60 shadow-[0_0_15px_rgba(56,189,248,0.15)] ring-1 ring-sky-500/40'
                  : 'bg-[#0f172a]/80 border-slate-800 hover:border-slate-700 hover:bg-slate-900/50'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-sky-400 font-bold">{item.family}</span>
                    <h3 className="text-sm font-semibold text-white leading-tight">{item.name}</h3>
                  </div>
                  {isDownloaded ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 shrink-0">
                      <CheckCircle2 className="w-3 h-3" /> READY
                    </span>
                  ) : item.requires_auth ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1 shrink-0">
                      <Lock className="w-3 h-3" /> RESTRICTED
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1 shrink-0">
                      AVAILABLE
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {item.description}
                </p>

                <div className="text-[11px] font-mono text-slate-400 flex flex-wrap gap-2 pt-1">
                  <span className="px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/80">{item.category}</span>
                  {item.approx_size_mb && <span className="px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/80">~{item.approx_size_mb} MB</span>}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800/80 mt-3 flex items-center justify-between">
                <span className="text-[10px] text-slate-500 font-mono truncate max-w-[140px]">{item.license}</span>
                
                {isDownloaded ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedDatasetId(item.id);
                      setActiveTab('schema');
                    }}
                    className="text-xs font-mono font-semibold text-sky-400 hover:text-sky-300 flex items-center gap-1"
                  >
                    Inspect <ArrowRight className="w-3 h-3" />
                  </button>
                ) : item.is_public_download ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTriggerDownload(item.id);
                    }}
                    className="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-sm transition-all"
                  >
                    <Download className="w-3 h-3" /> Download
                  </button>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setAuthModalDataset(item);
                    }}
                    className="text-xs font-mono text-amber-400 hover:text-amber-300 flex items-center gap-1"
                  >
                    Access Info <Info className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Dataset Detail Workspace */}
      {currentDataset && (
        <div className="bg-[#0f172a] border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          {/* Workspace Tabs Header */}
          <div className="border-b border-slate-800 bg-slate-900/60 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center">
                <Database className="w-4 h-4 text-sky-400" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  {currentDataset.name}
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {currentDataset.provenance}
                  </span>
                </h2>
                <span className="text-[11px] text-slate-400 font-mono">
                  {currentDataset.filename}
                </span>
              </div>
            </div>

            {/* Sub-tabs */}
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800">
              {[
                { id: 'overview', label: 'Inspection Overview', icon: FileText },
                { id: 'schema', label: 'Schema & Types', icon: Table },
                { id: 'preview', label: 'Data Preview', icon: BarChart2 },
                { id: 'preprocess', label: 'Preprocessing', icon: Sliders },
                { id: 'train', label: 'Model Benchmark', icon: Sparkles }
              ].map(t => {
                const Icon = t.icon;
                const isActive = activeTab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span className="hidden md:inline">{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="p-6">
            {/* TAB 1: Inspection Overview */}
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {inspectionReport ? (
                  <>
                    {/* Key Metrics Banner */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">Total Records</span>
                        <div className="text-lg font-bold font-mono text-white mt-0.5">
                          {inspectionReport.total_records.toLocaleString()}
                        </div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">Total Features</span>
                        <div className="text-lg font-bold font-mono text-sky-400 mt-0.5">
                          {inspectionReport.total_columns} cols
                        </div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">File Size</span>
                        <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                          {inspectionReport.file_size_mb} MB
                        </div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">Missing Cells</span>
                        <div className="text-lg font-bold font-mono text-white mt-0.5">
                          {inspectionReport.total_missing_cells} ({inspectionReport.missing_percentage}%)
                        </div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">Duplicates</span>
                        <div className="text-lg font-bold font-mono text-amber-400 mt-0.5">
                          {inspectionReport.duplicate_records}
                        </div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">Sampling Interval</span>
                        <div className="text-xs font-bold font-mono text-slate-300 mt-1 truncate">
                          {inspectionReport.sampling_frequency}
                        </div>
                      </div>
                    </div>

                    {/* Class Distribution & Suitability */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Class Distribution */}
                      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
                        <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                          <PieChart className="w-4 h-4 text-sky-400" />
                          Target Label Distribution ({inspectionReport.target_column})
                        </h4>
                        <div className="space-y-2 max-h-[220px] overflow-y-auto pr-2">
                          {Object.entries(inspectionReport.class_distribution || {}).map(([cls, info]) => (
                            <div key={cls} className="space-y-1">
                              <div className="flex items-center justify-between text-xs font-mono">
                                <span className="text-slate-300 font-semibold">{cls}</span>
                                <span className="text-slate-400">{info.count.toLocaleString()} ({info.percentage}%)</span>
                              </div>
                              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className="h-full bg-sky-500 rounded-full"
                                  style={{ width: `${info.percentage}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Suitability & Provenance Notes */}
                      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
                        <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-emerald-400" />
                          Provenance & IoT Domain Relevance
                        </h4>
                        <div className="space-y-2 text-xs text-slate-400">
                          <p><strong className="text-slate-200">Domain Category:</strong> {inspectionReport.category}</p>
                          <p><strong className="text-slate-200">Official Source:</strong> <a href={inspectionReport.official_url} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline inline-flex items-center gap-1">{inspectionReport.official_url} <ExternalLink className="w-3 h-3" /></a></p>
                          <p><strong className="text-slate-200">Priority Telemetry:</strong> <span className="font-mono text-sky-300">{inspectionReport.priority_telemetry.join(', ') || 'General attributes'}</span></p>
                          <p><strong className="text-slate-200">TwinNode Alignment:</strong> {inspectionReport.suitability_note}</p>
                          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300">
                            <strong>Provenance Boundary:</strong> This dataset is tagged strictly as <code className="font-mono">PUBLIC_DATASET</code>. Models trained on this data remain separate from STM32 physical sensor models.
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-8 text-center text-slate-400 space-y-2">
                    <p>Dataset file not yet downloaded or inspected.</p>
                    {currentDataset.is_public_download && (
                      <button
                        onClick={() => handleTriggerDownload(currentDataset.id)}
                        className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium"
                      >
                        Download {currentDataset.name}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Schema & Types */}
            {activeTab === 'schema' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-white">Feature Definitions & Inferred Types</h4>
                  <span className="text-xs font-mono text-slate-400">{inspectionReport?.columns?.length || 0} columns detected</span>
                </div>

                <div className="overflow-x-auto border border-slate-800 rounded-xl">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-3">Column Name</th>
                        <th className="p-3">Storage Dtype</th>
                        <th className="p-3">Inferred Type</th>
                        <th className="p-3">Non-Null Count</th>
                        <th className="p-3">Missing %</th>
                        <th className="p-3">Unique Values</th>
                        <th className="p-3">Sample Values</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-900/30">
                      {inspectionReport?.columns?.map((col, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40">
                          <td className="p-3 font-bold text-white">{col.column_name}</td>
                          <td className="p-3 text-sky-400">{col.data_type}</td>
                          <td className="p-3">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                              col.inferred_type === 'numeric' ? 'bg-emerald-500/20 text-emerald-400' :
                              col.inferred_type === 'datetime' ? 'bg-purple-500/20 text-purple-400' :
                              'bg-amber-500/20 text-amber-400'
                            }`}>
                              {col.inferred_type}
                            </span>
                          </td>
                          <td className="p-3 text-slate-300">{col.non_null_count.toLocaleString()}</td>
                          <td className="p-3 text-slate-400">{col.missing_percentage}%</td>
                          <td className="p-3 text-slate-300">{col.unique_values_count.toLocaleString()}</td>
                          <td className="p-3 text-slate-500 truncate max-w-[200px]">{col.sample_values.join(', ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB 3: Data Preview */}
            {activeTab === 'preview' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-white">Live Record Preview (Top 20 rows)</h4>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePreview(selectedDatasetId, false)}
                      className="px-2.5 py-1 rounded bg-slate-800 text-xs text-slate-300 hover:text-white"
                    >
                      Raw View
                    </button>
                    <button
                      onClick={() => handlePreview(selectedDatasetId, true)}
                      className="px-2.5 py-1 rounded bg-slate-800 text-xs text-slate-300 hover:text-white"
                    >
                      Processed View
                    </button>
                  </div>
                </div>

                {previewData && previewData.records && previewData.records.length > 0 ? (
                  <div className="overflow-x-auto border border-slate-800 rounded-xl max-h-[400px]">
                    <table className="w-full text-left text-xs font-mono whitespace-nowrap">
                      <thead className="bg-slate-900 text-slate-400 sticky top-0 border-b border-slate-800">
                        <tr>
                          {previewData.columns.map((c, i) => (
                            <th key={i} className="p-3">{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-slate-900/30">
                        {previewData.records.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-800/40">
                            {previewData.columns.map((c, cIdx) => (
                              <td key={cIdx} className="p-3 text-slate-300">
                                {String(row[c] !== undefined ? row[c] : '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-400">
                    {isPreviewLoading ? 'Loading preview...' : 'No preview records available. Please download the dataset first.'}
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: Preprocessing */}
            {activeTab === 'preprocess' && (
              <div className="space-y-6">
                <div className="border border-slate-800 rounded-xl p-5 bg-slate-900/40 space-y-4">
                  <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-sky-400" />
                    Configure Dataset Preprocessing Recipe
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Feature Scaler</label>
                      <select
                        value={scalerType}
                        onChange={(e) => setScalerType(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-white"
                      >
                        <option value="standard">StandardScaler (Zero Mean, Unit Var)</option>
                        <option value="minmax">MinMaxScaler [0, 1]</option>
                        <option value="robust">RobustScaler (Median / IQR)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Imputation Strategy</label>
                      <select
                        value={imputeStrategy}
                        onChange={(e) => setImputeStrategy(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-white"
                      >
                        <option value="median">Median (Continuous) & Mode (Categorical)</option>
                        <option value="mean">Mean (Continuous) & Mode (Categorical)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Duplicate Handling</label>
                      <div className="pt-2">
                        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={dropDuplicates}
                            onChange={(e) => setDropDuplicates(e.target.checked)}
                            className="rounded bg-slate-900 border-slate-800"
                          />
                          Deduplicate Records
                        </label>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      Raw file remains completely unchanged; output saved to <code className="font-mono text-sky-300">backend/datasets/processed/{selectedDatasetId}/</code>
                    </span>
                    <button
                      onClick={handleRunPreprocessor}
                      disabled={isPreprocessing}
                      className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-sm"
                    >
                      <Sliders className={`w-3.5 h-3.5 ${isPreprocessing ? 'animate-spin' : ''}`} />
                      {isPreprocessing ? 'Preprocessing...' : 'Run Preprocessor'}
                    </button>
                  </div>
                </div>

                {preprocessResult && (
                  <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 space-y-2 animate-fadeIn">
                    <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" /> Preprocessing Completed Successfully!
                    </div>
                    <div className="text-xs font-mono text-slate-300 grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                      <div>Initial Records: <strong>{preprocessResult.initial_rows}</strong></div>
                      <div>Final Clean Records: <strong>{preprocessResult.final_rows}</strong></div>
                      <div>Duplicates Removed: <strong>{preprocessResult.duplicates_removed}</strong></div>
                      <div>Output: <strong className="text-sky-300">{preprocessResult.processed_filename}</strong></div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 5: Model Benchmark */}
            {activeTab === 'train' && (
              <div className="space-y-6">
                <div className="border border-slate-800 rounded-xl p-5 bg-slate-900/40 space-y-4">
                  <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    External Dataset Algorithm Benchmark
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Algorithm Selection</label>
                      <select
                        value={trainingAlgo}
                        onChange={(e) => setTrainingAlgo(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-white"
                      >
                        <option value="RandomForest">Random Forest Classifier (Supervised Ensemble)</option>
                        <option value="DecisionTree">Decision Tree Classifier (Supervised Interpretable)</option>
                        <option value="LogisticRegression">Logistic Regression (Linear Calibrated)</option>
                        <option value="SVM">Support Vector Machine (Calibrated RBF)</option>
                        <option value="IsolationForest">Isolation Forest (Unsupervised Anomaly Detection)</option>
                        <option value="KMeans">K-Means Clustering (Unsupervised Multi-modal)</option>
                        <option value="PCA">PCA (Principal Component Analysis Dimensionality)</option>
                      </select>
                    </div>

                    <div className="flex flex-col justify-end">
                      <button
                        onClick={handleTrainModel}
                        disabled={isTraining}
                        className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-md"
                      >
                        <Zap className={`w-4 h-4 ${isTraining ? 'animate-bounce' : ''}`} />
                        {isTraining ? 'Training Model on External Data...' : `Benchmark ${trainingAlgo}`}
                      </button>
                    </div>
                  </div>
                </div>

                {trainingResult && (
                  <div className="border border-slate-800 rounded-xl p-5 bg-slate-900/60 space-y-5 animate-fadeIn">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <h4 className="text-sm font-bold text-white">Benchmark Results: {trainingResult.algorithm}</h4>
                      </div>
                      <span className="text-xs font-mono text-slate-400">
                        Trained in {trainingResult.training_time_ms} ms | Latency: {trainingResult.metrics.inference_latency_ms} ms
                      </span>
                    </div>

                    {/* Metrics Summary Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {trainingResult.metrics.accuracy !== undefined && (
                        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                          <span className="text-[10px] text-slate-400 font-mono uppercase">Accuracy</span>
                          <div className="text-xl font-bold font-mono text-emerald-400">
                            {(trainingResult.metrics.accuracy * 100).toFixed(2)}%
                          </div>
                        </div>
                      )}
                      {trainingResult.metrics.f1_macro !== undefined && (
                        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                          <span className="text-[10px] text-slate-400 font-mono uppercase">Macro F1</span>
                          <div className="text-xl font-bold font-mono text-sky-400">
                            {(trainingResult.metrics.f1_macro * 100).toFixed(2)}%
                          </div>
                        </div>
                      )}
                      {trainingResult.metrics.precision_macro !== undefined && (
                        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                          <span className="text-[10px] text-slate-400 font-mono uppercase">Macro Precision</span>
                          <div className="text-xl font-bold font-mono text-white">
                            {(trainingResult.metrics.precision_macro * 100).toFixed(2)}%
                          </div>
                        </div>
                      )}
                      {trainingResult.metrics.recall_macro !== undefined && (
                        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                          <span className="text-[10px] text-slate-400 font-mono uppercase">Macro Recall</span>
                          <div className="text-xl font-bold font-mono text-white">
                            {(trainingResult.metrics.recall_macro * 100).toFixed(2)}%
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Confusion Matrix if available */}
                    {trainingResult.metrics.confusion_matrix && (
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-white">Confusion Matrix ({trainingResult.metrics.labels.join(', ')})</span>
                        <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 overflow-x-auto">
                          <table className="text-xs font-mono text-center">
                            <tbody>
                              {trainingResult.metrics.confusion_matrix.map((row, rIdx) => (
                                <tr key={rIdx}>
                                  {row.map((val, cIdx) => (
                                    <td key={cIdx} className={`p-2 border border-slate-800/60 ${rIdx === cIdx ? 'bg-emerald-500/10 text-emerald-300 font-bold' : 'text-slate-400'}`}>
                                      {val}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manual Local Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Upload className="w-4 h-4 text-sky-400" />
                Import Local / Offline Dataset
              </h3>
              <button onClick={() => setShowImportModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleImportSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Target Dataset Category</label>
                <select
                  value={importDatasetId}
                  onChange={(e) => setImportDatasetId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-white"
                >
                  <option value="swat_water_treatment">SWaT (Secure Water Treatment Testbed)</option>
                  <option value="edge_iiotset">Edge-IIoTset Industrial IoT Dataset</option>
                  <option value="ton_iot_thermostat">TON_IoT Thermostat Telemetry</option>
                  <option value="ton_iot_fridge">TON_IoT Smart Fridge Telemetry</option>
                  <option value="ton_iot_weather">TON_IoT Weather Station Telemetry</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Select File (.csv, .parquet, .zip)</label>
                <input
                  type="file"
                  accept=".csv,.parquet,.zip"
                  onChange={(e) => setImportFile(e.target.files[0])}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-300"
                />
              </div>

              {importStatus && (
                <div className={`text-xs p-2.5 rounded-lg border ${
                  importStatus.status === 'SUCCESS' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                  importStatus.status === 'UPLOADING' ? 'bg-sky-500/10 border-sky-500/30 text-sky-400 animate-pulse' :
                  'bg-rose-500/10 border-rose-500/30 text-rose-400'
                }`}>
                  {importStatus.message}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
                >
                  Confirm Import
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Restricted Access Instructions Modal */}
      {authModalDataset && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Lock className="w-4 h-4 text-amber-400" />
                Access Instructions: {authModalDataset.name}
              </h3>
              <button onClick={() => setAuthModalDataset(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
              <p>{authModalDataset.auth_instructions}</p>
              <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400">
                Official Portal: <a href={authModalDataset.official_url} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">{authModalDataset.official_url}</a>
              </div>
              <p className="text-slate-400 text-[11px]">
                Once you have obtained the authorized research files from the official portal, click <strong>"Import Local Dataset"</strong> in the top navigation to integrate them into TwinNode ML Studio.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setAuthModalDataset(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setImportDatasetId(authModalDataset.id);
                  setAuthModalDataset(null);
                  setShowImportModal(true);
                }}
                className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
              >
                Import Local File Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
