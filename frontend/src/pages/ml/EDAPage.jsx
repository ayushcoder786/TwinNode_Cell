import React, { useState, useEffect } from 'react';
import {
  BarChart2,
  PieChart as PieIcon,
  TrendingUp,
  Download,
  RefreshCw,
  Layers,
  Sparkles,
  ScatterChart as ScatterIcon
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell
} from 'recharts';

export const EDAPage = () => {
  const [eda, setEda] = useState(null);
  const [clustering, setClustering] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('distributions'); // distributions, correlation, clustering

  const loadData = async () => {
    try {
      setLoading(true);
      const [edaRes, clusRes] = await Promise.all([
        fetch('/api/ml/eda/summary'),
        fetch('/api/ml/eda/clustering?n_clusters=4')
      ]);
      const edaData = await edaRes.json();
      const clusData = await clusRes.json();
      setEda(edaData);
      setClustering(clusData);
    } catch (err) {
      console.error('Failed to load EDA data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const downloadReportImage = () => {
    window.open('/api/ml/eda/report-image', '_blank');
  };

  const CLUSTER_COLORS = ['#0284c7', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-sky-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">Exploratory Data Analysis (EDA)</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Statistical characterization, cross-correlation profiles, distribution fits, and unsupervised PCA projections.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={downloadReportImage}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            Download High-Res EDA Report (PNG)
          </button>
          <button
            onClick={loadData}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800 pb-2">
        {[
          { id: 'distributions', label: 'Feature Distributions' },
          { id: 'correlation', label: 'Correlation Heatmap' },
          { id: 'clustering', label: 'Unsupervised PCA & Clusters' }
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === t.id
                ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Distributions */}
      {activeTab === 'distributions' && eda && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Temperature Histogram */}
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">LM35 Temperature Histogram (°C)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={eda.histograms?.temperature || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="bin" tick={{ fill: '#64748b', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                    <Bar dataKey="count" fill="#0284c7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Distance Histogram */}
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">HC-SR04 Distance Histogram (cm)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={eda.histograms?.distance || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="bin" tick={{ fill: '#64748b', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                    <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Condition Class Distribution */}
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">Operational Condition Class Breakdown</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {Object.entries(eda.class_distribution || {}).map(([cls, info]) => (
                <div key={cls} className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg">
                  <span className="text-[10px] font-mono text-slate-400 block truncate" title={cls}>{cls}</span>
                  <div className="text-lg font-bold font-mono text-white mt-1">{info.count}</div>
                  <span className="text-[10px] text-sky-400 font-mono">{info.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Correlation Matrix */}
      {activeTab === 'correlation' && eda?.correlation_matrix && (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-white">Inter-Feature Pearson Correlation Matrix</h3>
            <span className="text-xs text-slate-400 font-mono">Normalized Range: -1.0 to +1.0</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center text-xs font-mono border-collapse">
              <thead>
                <tr>
                  <th className="p-2 text-left text-slate-400">Feature</th>
                  {eda.correlation_matrix.columns.map(col => (
                    <th key={col} className="p-2 text-slate-300 truncate max-w-[90px]" title={col}>
                      {col.slice(0, 8)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {eda.correlation_matrix.columns.map((rowName, rIdx) => (
                  <tr key={rowName}>
                    <td className="p-2 text-left font-semibold text-slate-300 truncate max-w-[120px]" title={rowName}>
                      {rowName}
                    </td>
                    {eda.correlation_matrix.values[rIdx].map((val, cIdx) => {
                      const isHigh = Math.abs(val) > 0.5;
                      const isPositive = val > 0;
                      return (
                        <td
                          key={cIdx}
                          className={`p-2 font-bold ${
                            rIdx === cIdx
                              ? 'text-slate-500'
                              : isPositive
                              ? isHigh ? 'bg-sky-500/20 text-sky-300' : 'text-sky-400/80'
                              : isHigh ? 'bg-rose-500/20 text-rose-300' : 'text-rose-400/80'
                          }`}
                        >
                          {val.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Unsupervised PCA & Clustering */}
      {activeTab === 'clustering' && clustering && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">K-MEANS INERTIA</span>
              <div className="text-2xl font-bold font-mono text-white mt-1">{clustering.inertia}</div>
            </div>
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">SILHOUETTE SCORE</span>
              <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">{clustering.silhouette_score}</div>
            </div>
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400">TOTAL VARIANCE (PC1+PC2)</span>
              <div className="text-2xl font-bold font-mono text-sky-400 mt-1">{clustering.total_variance_explained}%</div>
            </div>
          </div>

          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-white">2D Principal Component Projection (K-Means Clusters)</h3>
              <div className="flex items-center gap-3 text-xs font-mono">
                {Object.keys(clustering.cluster_summary || {}).map((k, idx) => (
                  <span key={k} className="flex items-center gap-1.5" style={{ color: CLUSTER_COLORS[idx % CLUSTER_COLORS.length] }}>
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CLUSTER_COLORS[idx % CLUSTER_COLORS.length] }} />
                    {k}
                  </span>
                ))}
              </div>
            </div>

            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" dataKey="pc1" name="PC1" unit="" stroke="#64748b" />
                  <YAxis type="number" dataKey="pc2" name="PC2" unit="" stroke="#64748b" />
                  <Tooltip
                    cursor={{ strokeDasharray: '3 3' }}
                    content={({ payload }) => {
                      if (!payload || !payload.length) return null;
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 border border-slate-700 p-2.5 rounded-lg text-xs font-mono">
                          <div><strong>Cluster {data.cluster}</strong> ({data.condition})</div>
                          <div className="text-slate-400">Temp: {data.temp}°C | Dist: {data.dist}cm</div>
                          <div className="text-slate-400">PC1: {data.pc1} | PC2: {data.pc2}</div>
                        </div>
                      );
                    }}
                  />
                  <Scatter name="Sensor Records" data={clustering.pca_projection_points || []}>
                    {(clustering.pca_projection_points || []).map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CLUSTER_COLORS[entry.cluster % CLUSTER_COLORS.length]}
                        opacity={0.8}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
