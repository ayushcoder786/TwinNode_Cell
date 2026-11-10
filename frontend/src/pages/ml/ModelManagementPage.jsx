import React, { useState, useEffect } from 'react';
import {
  Layers,
  Download,
  CheckCircle,
  RefreshCw,
  Clock,
  Sparkles,
  ShieldCheck,
  Brain,
  Trash2,
  Play
} from 'lucide-react';

export const ModelManagementPage = ({ onNavigate }) => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState(null);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/ml/models');
      const data = await res.json();
      setModels(data || []);
    } catch (err) {
      console.error('Failed to load models:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleActivate = async (modelId) => {
    try {
      const res = await fetch(`/api/ml/models/activate/${modelId}`, { method: 'POST' });
      if (res.ok) {
        setActionMsg(`Model ${modelId} is now set as the active production model.`);
        fetchModels();
      }
    } catch (err) {
      setActionMsg('Failed to activate model.');
    }
  };

  const handleDownload = (modelId) => {
    window.open(`/api/ml/models/download/${modelId}`, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">Model Registry & Lifecycle Management</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Maintain serialized Scikit-learn pipelines (.joblib), metadata tracking, and active deployment controls.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate('ml_training')}
            className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-sm"
          >
            <Brain className="w-3.5 h-3.5" />
            Retrain / New Model
          </button>
          <button
            onClick={fetchModels}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Model Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {models.length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-500 bg-[#0f172a] border border-slate-800 rounded-xl">
            {loading ? 'Loading registered models...' : 'No models registered in the system.'}
          </div>
        ) : (
          models.map((m) => (
            <div
              key={m.model_id}
              className={`bg-[#0f172a] border rounded-xl p-5 space-y-4 transition-all relative overflow-hidden ${
                m.is_active
                  ? 'border-emerald-500/50 shadow-[0_0_25px_rgba(16,185,129,0.15)]'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              {m.is_active && (
                <div className="absolute top-0 right-0 bg-emerald-500 text-slate-950 text-[9px] font-mono font-bold px-3 py-0.5 rounded-bl-lg tracking-wider">
                  ACTIVE DEPLOYMENT
                </div>
              )}

              <div>
                <span className="text-[10px] font-mono text-slate-400">{m.algorithm_type}</span>
                <h3 className="text-base font-bold text-white mt-0.5 truncate">{m.model_name}</h3>
                <span className="text-xs font-mono text-sky-400">{m.algorithm}</span>
              </div>

              <div className="grid grid-cols-2 gap-2 bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-xs font-mono">
                <div>
                  <span className="text-[10px] text-slate-500 block">TEST ACCURACY</span>
                  <span className="text-sm font-bold text-emerald-400">
                    {m.accuracy !== null ? `${(m.accuracy * 100).toFixed(1)}%` : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">MACRO F1</span>
                  <span className="text-sm font-bold text-slate-300">
                    {m.f1_score !== null ? `${(m.f1_score * 100).toFixed(1)}%` : 'N/A'}
                  </span>
                </div>
              </div>

              <div className="text-[11px] font-mono text-slate-400 space-y-1">
                <div className="truncate">ID: <span className="text-slate-300">{m.model_id}</span></div>
                <div>Date: <span className="text-slate-300">{m.created_at ? m.created_at.slice(0, 10) : '--'}</span></div>
                <div>Features: <span className="text-slate-300">{m.feature_list?.length || 12} canonical</span></div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2">
                {!m.is_active && (
                  <button
                    onClick={() => handleActivate(m.model_id)}
                    className="flex-1 py-1.5 px-3 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/30 text-xs font-semibold transition-all"
                  >
                    Activate
                  </button>
                )}
                <button
                  onClick={() => handleDownload(m.model_id)}
                  className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                  title="Download .joblib pipeline file"
                >
                  <Download className="w-3.5 h-3.5" />
                  .joblib
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
