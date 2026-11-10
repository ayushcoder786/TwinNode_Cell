import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  BarChart3,
  RefreshCw,
  Zap,
  Clock,
  Layers,
  ChevronDown
} from 'lucide-react';

export const ModelEvaluationPage = () => {
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchModelsAndMetrics = async (modelIdToLoad) => {
    try {
      setLoading(true);
      const mRes = await fetch('/api/ml/models');
      const mList = await mRes.json();
      setModels(mList || []);

      const targetId = modelIdToLoad || (mList.find(m => m.is_active)?.model_id) || mList[0]?.model_id;
      if (targetId) {
        setSelectedModelId(targetId);
        const metRes = await fetch(`/api/ml/metrics?model_id=${targetId}`);
        const metData = await metRes.json();
        setMetrics(metData);
      }
    } catch (err) {
      console.error('Failed to load evaluation metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModelsAndMetrics();
  }, []);

  const handleModelChange = (id) => {
    setSelectedModelId(id);
    fetchModelsAndMetrics(id);
  };

  const currentModelMeta = models.find(m => m.model_id === selectedModelId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">Model Evaluation & Diagnostic Metrics</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Multi-class confusion matrices, macro-averaged precision/recall/F1, and physical feature importances.
          </p>
        </div>

        {/* Model Selector */}
        <div className="flex items-center gap-2">
          <select
            value={selectedModelId}
            onChange={(e) => handleModelChange(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
          >
            {models.map(m => (
              <option key={m.model_id} value={m.model_id}>
                {m.algorithm} ({m.model_id.slice(-8)}) {m.is_active ? '★ ACTIVE' : ''}
              </option>
            ))}
          </select>
          <button
            onClick={() => fetchModelsAndMetrics(selectedModelId)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </div>

      {metrics && metrics.accuracy !== undefined ? (
        <>
          {/* Key Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">TEST ACCURACY</span>
              <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                {(metrics.accuracy * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Holdout test split</span>
            </div>

            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">PRECISION (MACRO)</span>
              <div className="text-2xl font-bold font-mono text-sky-400 mt-1">
                {(metrics.precision_macro * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Unweighted average</span>
            </div>

            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">RECALL (MACRO)</span>
              <div className="text-2xl font-bold font-mono text-indigo-400 mt-1">
                {(metrics.recall_macro * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">True positive rate</span>
            </div>

            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">F1-SCORE (MACRO)</span>
              <div className="text-2xl font-bold font-mono text-teal-400 mt-1">
                {(metrics.f1_macro * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Harmonic mean</span>
            </div>

            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">INFERENCE LATENCY</span>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                {metrics.inference_latency_ms} ms
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Per sample pass</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Confusion Matrix */}
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-white">Multi-Class Confusion Matrix</h3>
                <span className="text-xs font-mono text-slate-400">True vs Predicted</span>
              </div>

              {metrics.confusion_matrix && (
                <div className="overflow-x-auto">
                  <table className="w-full text-center text-xs font-mono border-collapse">
                    <thead>
                      <tr>
                        <th className="p-2 text-left text-slate-500">True \ Pred</th>
                        {['NORMAL', 'SETPOINT', 'SENSOR', 'COMM', 'UNEXP', 'ACTUAT'].map(col => (
                          <th key={col} className="p-2 text-slate-300 truncate max-w-[65px]">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {metrics.confusion_matrix.map((row, rIdx) => {
                        const rowNames = ['NORMAL', 'SETPOINT', 'SENSOR', 'COMM', 'UNEXP', 'ACTUAT'];
                        return (
                          <tr key={rIdx}>
                            <td className="p-2 text-left text-slate-400 font-semibold">{rowNames[rIdx] || `C${rIdx}`}</td>
                            {row.map((val, cIdx) => (
                              <td
                                key={cIdx}
                                className={`p-2.5 font-bold ${
                                  rIdx === cIdx
                                    ? val > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-600'
                                    : val > 0 ? 'bg-rose-500/20 text-rose-400' : 'text-slate-700'
                                }`}
                              >
                                {val}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Feature Importance */}
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-white">Feature Importance / Weights</h3>
                <span className="text-xs font-mono text-slate-400">Physical impact factor</span>
              </div>

              {metrics.feature_importance && Object.keys(metrics.feature_importance).length > 0 ? (
                <div className="space-y-2.5">
                  {Object.entries(metrics.feature_importance)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 8)
                    .map(([name, weight]) => (
                      <div key={name} className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-slate-300 truncate max-w-[200px]">{name}</span>
                          <span className="text-sky-400 font-bold">{(weight * 100).toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-sky-500 to-indigo-500 h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, Math.max(5, weight * 100))}%` }}
                          />
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500 py-6 text-center">
                  Feature importances not applicable to this model type.
                </div>
              )}
            </div>
          </div>

          {/* Classification Report Table */}
          {metrics.classification_report && (
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">Full Classification Report per Operational Condition</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono border-collapse">
                  <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3">Condition Class</th>
                      <th className="py-2 px-3">Precision</th>
                      <th className="py-2 px-3">Recall</th>
                      <th className="py-2 px-3">F1-Score</th>
                      <th className="py-2 px-3">Support (Samples)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {Object.entries(metrics.classification_report)
                      .filter(([k]) => !['accuracy', 'macro avg', 'weighted avg'].includes(k))
                      .map(([className, cr]) => (
                        <tr key={className} className="hover:bg-slate-900/40">
                          <td className="py-2 px-3 font-semibold text-white">{className}</td>
                          <td className="py-2 px-3 text-sky-400">{cr.precision !== undefined ? (cr.precision * 100).toFixed(1) + '%' : '--'}</td>
                          <td className="py-2 px-3 text-indigo-400">{cr.recall !== undefined ? (cr.recall * 100).toFixed(1) + '%' : '--'}</td>
                          <td className="py-2 px-3 text-emerald-400 font-bold">{cr['f1-score'] !== undefined ? (cr['f1-score'] * 100).toFixed(1) + '%' : '--'}</td>
                          <td className="py-2 px-3 text-slate-400">{cr.support || 0}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="p-8 text-center bg-[#0f172a] border border-slate-800 rounded-xl text-slate-500">
          No metrics found for this model. Train or select an evaluated model.
        </div>
      )}
    </div>
  );
};
