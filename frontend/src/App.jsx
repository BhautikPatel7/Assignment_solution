import { useState } from 'react';
import UploadPage    from './pages/UploadPage';
import SegmentPage   from './pages/SegmentPage';
import MaterialPage  from './pages/MaterialPage';
import VisualizePage from './pages/VisualizePage';

/**
 * App.jsx — E2M root component
 *
 * step:
 *  'upload'    → Module 1 — Upload + Analyze
 *  'segment'   → Module 2 — Segmentation + Brush Correction
 *  'materials' → Module 3 — Material Selection
 *  'visualize' → Module 4 — AI Visualization
 */
export default function App() {
  const [step,      setStep]      = useState('upload');
  const [session,   setSession]   = useState(null);
  const [segData,   setSegData]   = useState(null);
  const [matData,   setMatData]   = useState(null);
  const [vizData,   setVizData]   = useState(null);

  const handleAnalyzeDone        = (s)    => setSession(s);
  const handleProceedToSegment   = ()     => setStep('segment');
  const handleSegmentDone        = (data) => setSegData(data);
  const handleProceedToMaterials = ()     => setStep('materials');
  const handleMaterialsDone      = (sel)  => { setMatData(sel); setStep('visualize'); };
  const handleVisualizeDone      = (viz)  => { setVizData(viz); setStep('estimate'); };

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
        onSegmentDone={handleSegmentDone}
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
        onMaterialsDone={handleMaterialsDone}
        onClear={handleClear}
      />
    );
  }

  if (step === 'visualize') {
    return (
      <VisualizePage
        session={session}
        segData={segData}
        matData={matData}
        onVisualizeDone={handleVisualizeDone}
        onClear={handleClear}
      />
    );
  }

  if (step === 'estimate') {
    // Placeholder — Module 5 coming next
    return (
      <div style={{ color: '#f1f5f9', padding: 40, fontFamily: 'Inter,sans-serif' }}>
        <h2>Module 5 — Cost Estimation (coming next)</h2>
        <button onClick={handleClear} style={{ marginTop: 20, padding: '8px 20px', cursor: 'pointer' }}>
          Start Over
        </button>
      </div>
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

