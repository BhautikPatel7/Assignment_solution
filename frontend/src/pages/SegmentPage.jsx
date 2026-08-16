import { useState, useEffect } from 'react';
import Header from '../components/Header';
import SegmentViewer from '../components/SegmentViewer';
import SegmentLoading from '../components/SegmentLoading';
import { segmentImage } from '../api';
import styles from './SegmentPage.module.css';

export default function SegmentPage({ session, segData, onSegmentDone, onClear }) {
  const [isLoading, setIsLoading] = useState(!segData);
  const [data, setData]           = useState(segData);   // holds M2 result once done
  const [error, setError]         = useState('');
  const [elapsed, setElapsed]     = useState(0);         // live elapsed timer (seconds)

  // Auto-run segmentation on mount if no cached result
  useEffect(() => {
    if (segData) return; // already have results

    let startTime = Date.now();
    const tick = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    segmentImage(session.session_id)
      .then((res) => {
        clearInterval(tick);
        setData(res);
        onSegmentDone(res);
        setIsLoading(false);
      })
      .catch((err) => {
        clearInterval(tick);
        setError(err.message || 'Segmentation failed.');
        setIsLoading(false);
      });

    return () => clearInterval(tick);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={styles.page}>
      <Header sessionId={session?.session_id} onClearSession={onClear} />

      <main className={styles.main}>
        {/* Step Indicator */}
        <div className={styles.stepBar}>
          <StepIndicator step={1} label="Upload &amp; Analyze" done />
          <div className={styles.stepLine} />
          <StepIndicator step={2} label="Segmentation" active={isLoading} done={!isLoading && !!data} />
          <div className={`${styles.stepLine} ${styles.stepLineDim}`} />
          <StepIndicator step={3} label="Materials" dim />
          <div className={`${styles.stepLine} ${styles.stepLineDim}`} />
          <StepIndicator step={4} label="Visualize" dim />
        </div>

        {/* Loading State */}
        {isLoading && <SegmentLoading elapsed={elapsed} />}

        {/* Error State */}
        {error && !isLoading && (
          <div className={styles.errorCard}>
            <div className={styles.errorIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="12" cy="16" r="1" fill="currentColor"/>
              </svg>
            </div>
            <div>
              <h3 className={styles.errorTitle}>Segmentation Failed</h3>
              <p className={styles.errorMsg}>{error}</p>
            </div>
            <button className={styles.retryBtn} onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        )}

        {/* Result State */}
        {data && !isLoading && (
          <SegmentViewer
            session={session}
            data={data}
            onContinue={() => alert('Module 3 — Material Selection coming next!')}
          />
        )}
      </main>
    </div>
  );
}

function StepIndicator({ step, label, done, active, dim }) {
  return (
    <div className={`${styles.step} ${done ? styles.stepDone : ''} ${active ? styles.stepActive : ''} ${dim ? styles.stepDim : ''}`}>
      <div className={styles.stepNum}>
        {done ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <polyline points="20,6 9,17 4,12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        ) : step}
      </div>
      <span className={styles.stepLabel} dangerouslySetInnerHTML={{ __html: label }} />
    </div>
  );
}
