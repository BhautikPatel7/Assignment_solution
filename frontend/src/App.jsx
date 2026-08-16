import { useState } from 'react';
import UploadPage from './pages/UploadPage';
import SegmentPage from './pages/SegmentPage';

/**
 * App.jsx — E2M root component
 *
 * App-level state holds the active session so it can be passed
 * between Module pages without a router library.
 *
 * step:
 *  'upload'  → Module 1 — Upload + Analyze
 *  'segment' → Module 2 — Segmentation
 */
export default function App() {
  const [step, setStep]       = useState('upload');
  const [session, setSession] = useState(null); // { session_id, analysis }
  const [segData, setSegData] = useState(null); // full M2 response

  const handleAnalyzeDone = (sessionObj) => {
    setSession(sessionObj);
  };

  const handleProceedToSegment = () => {
    setStep('segment');
  };

  const handleSegmentDone = (data) => {
    setSegData(data);
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
        onSegmentDone={handleSegmentDone}
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
