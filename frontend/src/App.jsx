import React, { useState } from 'react';
import { TwinNodeProvider } from './context/TwinNodeContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';

// SCADA Pages
import { OverviewPage } from './pages/OverviewPage';
import { NodeManagementPage } from './pages/NodeManagementPage';
import { TestBenchPage } from './pages/TestBenchPage';
import { SensorMonitoringPage } from './pages/SensorMonitoringPage';
import { FaultDetectionPage } from './pages/FaultDetectionPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { TestReportsPage } from './pages/TestReportsPage';

// Machine Learning Studio Pages
import { MLOverviewPage } from './pages/ml/MLOverviewPage';
import { DatasetManagerPage } from './pages/ml/DatasetManagerPage';
import { DataPreprocessingPage } from './pages/ml/DataPreprocessingPage';
import { EDAPage } from './pages/ml/EDAPage';
import { ModelTrainingPage } from './pages/ml/ModelTrainingPage';
import { ModelEvaluationPage } from './pages/ml/ModelEvaluationPage';
import { LivePredictionsPage } from './pages/ml/LivePredictionsPage';
import { ModelManagementPage } from './pages/ml/ModelManagementPage';
import { ExternalDatasetManagerPage } from './pages/ml/ExternalDatasetManagerPage';

export function App() {
  const [activeTab, setActiveTab] = useState('ml_overview');

  const renderContent = () => {
    switch (activeTab) {
      // ML Studio
      case 'ml_overview':
        return <MLOverviewPage onNavigate={setActiveTab} />;
      case 'ml_datasets':
        return <DatasetManagerPage onNavigate={setActiveTab} />;
      case 'ml_external_datasets':
        return <ExternalDatasetManagerPage onNavigate={setActiveTab} />;
      case 'ml_preprocessing':
        return <DataPreprocessingPage onNavigate={setActiveTab} />;
      case 'ml_eda':
        return <EDAPage onNavigate={setActiveTab} />;
      case 'ml_training':
        return <ModelTrainingPage onNavigate={setActiveTab} onTrainingComplete={() => setActiveTab('ml_evaluation')} />;
      case 'ml_evaluation':
        return <ModelEvaluationPage onNavigate={setActiveTab} />;
      case 'ml_predictions':
        return <LivePredictionsPage onNavigate={setActiveTab} />;
      case 'ml_management':
        return <ModelManagementPage onNavigate={setActiveTab} />;

      // SCADA Instrumentation
      case 'overview':
        return <OverviewPage />;
      case 'nodes':
        return <NodeManagementPage />;
      case 'testbench':
        return <TestBenchPage />;
      case 'sensors':
        return <SensorMonitoringPage />;
      case 'faults':
        return <FaultDetectionPage />;
      case 'analytics':
        return <AnalyticsPage />;
      case 'reports':
        return <TestReportsPage />;
      default:
        return <MLOverviewPage onNavigate={setActiveTab} />;
    }
  };

  return (
    <TwinNodeProvider>
      <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col font-sans">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
          <main className="flex-1 overflow-y-auto p-6 bg-radial-gradient">
            <div className="max-w-7xl mx-auto">
              {renderContent()}
            </div>
          </main>
        </div>
      </div>
    </TwinNodeProvider>
  );
}

export default App;
