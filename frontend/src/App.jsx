import { useState } from 'react';
import UploadPage    from './pages/UploadPage';
import SegmentPage   from './pages/SegmentPage';
import MaterialPage  from './pages/MaterialPage';
import VisualizePage from './pages/VisualizePage';

import EstimatePage  from './pages/EstimatePage';

/**
 * App.jsx — E2M root component
 *
 * step:
 *  'upload'    → Module 1 — Upload + Analyze
 *  'segment'   → Module 2 — Segmentation + Brush Correction
 *  'materials' → Module 3 — Material Selection
 *  'visualize' → Module 4 — AI Visualization
 *  'estimate'  → Module 5 — Cost Estimation
 */
export default function App() {
  const [step,      setStep]      = useState('upload');
  const [session,   setSession]   = useState(null);
  const [segData,   setSegData]   = useState(null);
  const [matData,   setMatData]   = useState(null);
  const [vizData,   setVizData]   = useState(null);
  const [estData,   setEstData]   = useState(null);

  const handleAnalyzeDone        = (s)    => setSession(s);
  
  const handleProceedToSegment   = (data) => { 
    setSegData(data); 
    setStep('segment'); 
  };
  
  const handleProceedToMaterials = ()     => {
    setStep('materials'); 
  };
  
  const handleProceedToVisualize = (viz)  => { 
    setVizData(viz);
    setStep('visualize'); 
  };
  
  const handleProceedToEstimate  = (est)  => { 
    setEstData(est);
    setStep('estimate'); 
  };

  const handleClear = () => {
    sessionStorage.clear();
    localStorage.removeItem('e2m_session');
    window.location.reload();
  };

  if (step === 'segment') {
    return (
      <SegmentPage
        session={session}
        segData={segData}
        onProceedToMaterials={handleProceedToMaterials}
        onClear={handleClear}
      />
    );
  }

  if (step === 'materials') {
    return (
      <MaterialPage
        session={session}
        segData={segData}
        onProceedToVisualize={handleProceedToVisualize}
        onClear={handleClear}
      />
    );
  }

  if (step === 'visualize') {
    return (
      <VisualizePage
        session={session}
        segData={segData}
        vizData={vizData}
        onProceedToEstimate={handleProceedToEstimate}
        onClear={handleClear}
      />
    );
  }

  if (step === 'estimate') {
    return (
      <EstimatePage
        session={session}
        segData={segData}
        vizData={vizData}
        estData={estData}
        onClear={handleClear}
      />
    );
  }

  return (
    <UploadPage
      session={session}
      onAnalyzeDone={handleAnalyzeDone}
      onProceedToSegment={handleProceedToSegment}
      onClear={handleClear}
    />
  );
}

