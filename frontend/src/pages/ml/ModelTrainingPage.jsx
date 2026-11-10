import React, { useState, useEffect } from 'react';
import {
  Brain,
  Play,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Layers,
  Sliders,
  Clock,
  ShieldCheck,
  RefreshCw,
  Zap
} from 'lucide-react';

export const ModelTrainingPage = ({ onTrainingComplete }) => {
  const [algorithm, setAlgorithm] = useState('RandomForest');
  const [modelName, setModelName] = useState('');
  const [scalerType, setScalerType] = useState('standard');
  const [isTraining, setIsTraining] = useState(false);
  const [trainStatus, setTrainStatus] = useState(null);
  const [benchmarkModels, setBenchmarkModels] = useState([]);

  // Dataset Provenance Selector
  const [datasetCategory, setDatasetCategory] = useState('TWINNODE_SIMULATION');
  const [publicDatasetId, setPublicDatasetId] = useState('ton_iot_thermostat');
  const [externalDatasets, setExternalDatasets] = useState([]);

  const ALGORITHMS = [
    { id: 'RandomForest', name: 'Random Forest Classifier', type: 'Supervised', desc: 'Ensemble of decision trees. Resilient against non-linear sensor correlations.' },
    { id: 'DecisionTree', name: 'Decision Tree Classifier', type: 'Supervised', desc: 'Fast, interpretable, deterministic rule branching for embedded diagnostics.' },
    { id: 'LogisticRegression', name: 'Logistic Regression', type: 'Supervised', desc: 'Linear boundary classification with calibrated probabilistic confidence scores.' },
    { id: 'SVM', name: 'Support Vector Machine (RBF)', type: 'Supervised', desc: 'High-dimensional margin separation with CalibratedClassifierCV.' },
    { id: 'IsolationForest', name: 'Isolation Forest', type: 'Unsupervised', desc: 'Unsupervised anomaly detector for unlabelled drift and unexpected conditions.' },
    { id: 'KMeans', name: 'K-Means Clustering', type: 'Unsupervised', desc: 'Cluster-based grouping for multi-modal operation envelopes.' },
    { id: 'PCA', name: 'Principal Component Analysis (PCA)', type: 'Dimensionality', desc: 'Orthogonal linear projection for variance decomposition.' }
  ];

  const fetchExistingModels = async () => {
    try {
      const res = await fetch('/api/ml/models');
      const data = await res.json();
      setBenchmarkModels(data || []);
    } catch (err) {
      console.error('Failed to load benchmark models:', err);
    }
  };

  const fetchExternalDatasets = async () => {
    try {
      const res = await fetch('/api/datasets/external');
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        setExternalDatasets(data.datasets || []);
      }
    } catch (err) {
      console.error('Failed to load external datasets:', err);
    }
  };

  useEffect(() => {
    fetchExistingModels();
    fetchExternalDatasets();
  }, []);

  const handleStartTraining = async (e) => {
    e.preventDefault();
    setIsTraining(true);
    setTrainStatus({ status: 'RUNNING', message: `Fitting ${algorithm} pipeline on [${datasetCategory}] data...` });

    try {
      let res, data;
      if (datasetCategory === 'PUBLIC_DATASET') {
        res = await fetch('/api/datasets/train', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            dataset_id: publicDatasetId,
            algorithm,
            experiment_type: 'EXTERNAL_BENCHMARK',
            test_size: 0.20,
            use_processed: true
          })
        });
        data = await res.json();
        if (res.ok) {
          const accText = data.metrics.accuracy !== undefined ? `Accuracy: ${(data.metrics.accuracy * 100).toFixed(1)}%` : `Type: ${data.metrics.algorithm_type}`;
          setTrainStatus({
            status: 'SUCCESS',
            message: `External Benchmark [${data.dataset_name}] trained in ${data.training_time_ms} ms! ${accText}`,
            result: data
          });
        } else {
          setTrainStatus({ status: 'ERROR', message: data.detail || 'Training failed.' });
        }
      } else {
        // TwinNode Simulation or Hardware
        res = await fetch('/api/ml/train', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            algorithm,
            model_name: modelName || `TwinNode_${algorithm}`,
            scaler_type: scalerType,
            set_active: true
          })
        });
        data = await res.json();
        if (res.ok) {
          setTrainStatus({
            status: 'SUCCESS',
            message: `Model ${data.model_name} trained successfully in ${data.training_time_ms} ms! Accuracy: ${(data.metrics.accuracy * 100).toFixed(1)}%`,
            result: data
          });
          fetchExistingModels();
          if (onTrainingComplete) onTrainingComplete(data);
        } else {
          setTrainStatus({ status: 'ERROR', message: data.detail || 'Training failed.' });
        }
      }
    } catch (err) {
      setTrainStatus({ status: 'ERROR', message: err.message });
    } finally {
      setIsTraining(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-emerald-400" />
          <h1 className="text-xl font-bold text-white tracking-tight">Model Training & Algorithm Benchmark</h1>
        </div>
        <p className="text-slate-400 text-xs mt-1">
          Train supervised and unsupervised machine learning algorithms with chronological cross-session validation.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Training Form */}
        <div className="lg:col-span-2 bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-5">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sliders className="w-4 h-4 text-sky-400" />
            Training Configuration
          </h3>

          <form onSubmit={handleStartTraining} className="space-y-4">
            {/* Dataset Provenance Selector */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3.5 space-y-3">
              <label className="text-xs font-semibold text-slate-200 block">Dataset Source & Provenance</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'TWINNODE_SIMULATION', label: 'TwinNode Simulation', desc: '16,523 synthetic samples' },
                  { id: 'PUBLIC_DATASET', label: 'Public Dataset', desc: 'TON_IoT, SWaT, Edge-IIoTset' },
                  { id: 'REAL_HARDWARE', label: 'Physical Hardware', desc: 'STM32 bench records' }
                ].map(p => (
                  <div
                    key={p.id}
                    onClick={() => setDatasetCategory(p.id)}
                    className={`p-2.5 rounded-lg border cursor-pointer text-left transition-all ${
                      datasetCategory === p.id
                        ? 'bg-sky-500/15 border-sky-500/60 text-white shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold truncate">{p.label}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5 truncate">{p.desc}</div>
                  </div>
                ))}
              </div>

              {datasetCategory === 'PUBLIC_DATASET' && (
                <div className="pt-2 border-t border-slate-800 animate-fadeIn">
                  <label className="text-xs text-slate-400 block mb-1">Select Downloaded Public Dataset</label>
                  <select
                    value={publicDatasetId}
                    onChange={(e) => setPublicDatasetId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-sky-300 font-mono"
                  >
                    <option value="ton_iot_thermostat">TON_IoT Smart Thermostat (Temperature & Status)</option>
                    <option value="ton_iot_fridge">TON_IoT Smart Fridge Telemetry</option>
                    <option value="ton_iot_weather">TON_IoT Weather Station Telemetry</option>
                    <option value="ton_iot_modbus">TON_IoT Modbus Industrial Telemetry</option>
                    <option value="swat_water_treatment">SWaT Water Treatment (Imported)</option>
                    <option value="edge_iiotset">Edge-IIoTset Industrial IoT (Imported)</option>
                  </select>
                </div>
              )}
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-2">Algorithm Selection</label>
              <div className="space-y-2">
                {ALGORITHMS.map(a => (
                  <div
                    key={a.id}
                    onClick={() => setAlgorithm(a.id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      algorithm === a.id
                        ? 'bg-emerald-500/15 border-emerald-500/50 text-white'
                        : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">{a.name}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {a.type}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{a.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Model Name (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. TwinNode_Industrial_RF_v1"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Feature Scaler</label>
                <select
                  value={scalerType}
                  onChange={(e) => setScalerType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                >
                  <option value="standard">StandardScaler (Z-Score)</option>
                  <option value="robust">RobustScaler (Median / IQR)</option>
                  <option value="minmax">MinMaxScaler (0 - 1)</option>
                </select>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isTraining}
                className={`w-full py-3 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-lg ${
                  isTraining
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 shadow-emerald-500/20'
                }`}
              >
                {isTraining ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-400" />
                    Fitting Pipeline & Validating Test Split...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Train & Deploy Model Pipeline
                  </>
                )}
              </button>
            </div>
          </form>

          {trainStatus && (
            <div className={`p-4 rounded-xl border text-xs ${
              trainStatus.status === 'SUCCESS'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : trainStatus.status === 'ERROR'
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                : 'bg-sky-500/10 border-sky-500/30 text-sky-300'
            }`}>
              <div className="font-semibold">{trainStatus.message}</div>
              {trainStatus.result && (
                <div className="mt-2 text-[11px] font-mono text-slate-400 space-y-0.5">
                  <div>Model ID: <strong className="text-white">{trainStatus.result.model_id}</strong></div>
                  <div>Test Samples: {trainStatus.result.test_samples}</div>
                  <div>Inference Latency: {trainStatus.result.metrics.inference_latency_ms} ms / sample</div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Algorithm Comparison Table */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-white">Algorithm Benchmark Comparison</h3>
            <button onClick={fetchExistingModels} className="text-slate-400 hover:text-white">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {benchmarkModels.length === 0 ? (
              <div className="text-xs text-slate-500 py-4 text-center">No models trained yet.</div>
            ) : (
              benchmarkModels.slice(0, 6).map((m) => (
                <div key={m.model_id} className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{m.algorithm}</span>
                    {m.is_active && (
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Accuracy:</span>
                    <strong className="text-emerald-400">
                      {m.accuracy !== null ? `${(m.accuracy * 100).toFixed(1)}%` : 'N/A'}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Macro F1:</span>
                    <strong className="text-slate-300">
                      {m.f1_score !== null ? `${(m.f1_score * 100).toFixed(1)}%` : 'N/A'}
                    </strong>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
