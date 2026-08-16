import { useState, useEffect, useRef, useCallback } from 'react';
import Header from '../components/Header';
import { MATERIAL_CATALOG, isPaint } from '../constants/materials';
import { visualizeImage } from '../api';
import styles from './VisualizePage.module.css';

const LOADING_STEPS = [
  { icon: '🔍', text: 'Analyzing house architecture with Gemini Vision…' },
  { icon: '🎨', text: 'Building material visualization prompt…' },
  { icon: '🤖', text: 'AI is rendering your renovation…' },
  { icon: '✨', text: 'Applying photorealistic finish…' },
  { icon: '🏠', text: 'Almost done…' },
];

export default function VisualizePage({ session, segData, vizData, onProceedToEstimate, onClear }) {
  const [status, setStatus]         = useState('done');
  const [vizImg, setVizImg]         = useState(vizData?.visualization_image || null);
  const [promptUsed, setPromptUsed] = useState('');
  const [error, setError]           = useState('');
  const [loadStep, setLoadStep]     = useState(0);
  const [sliderPos, setSliderPos]   = useState(50);
  const [isEstimating, setIsEstimating] = useState(false);
  const [apiError, setApiError]     = useState('');
  const isDragging                  = useRef(false);
  const sliderRef                   = useRef(null);

  // ── Before/After drag slider ───────────────────────────────
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    isDragging.current = true;
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging.current || !sliderRef.current) return;
    const rect = sliderRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const pct = Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100));
    setSliderPos(pct);
  }, []);

  const handleMouseUp = useCallback(() => { isDragging.current = false; }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleMouseMove);
    window.addEventListener('touchend', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleMouseMove);
      window.removeEventListener('touchend', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const handleProceedClick = async () => {
    setIsEstimating(true);
    setApiError('');
    try {
      const { estimateCost } = await import('../api');
      const res = await estimateCost(session.session_id);
      onProceedToEstimate(res);
    } catch (e) {
      setApiError(e.message || 'Failed to estimate costs.');
    } finally {
      setIsEstimating(false);
    }
  };

  // Original image from segData
  const originalImg = segData?.original_image || null;

  return (
    <div className={styles.page}>
      <Header sessionId={session?.session_id} onClearSession={onClear} />

      <main className={styles.main}>

        {/* Step bar */}
        <div className={styles.stepBar}>
          <StepDot n={1} label="Upload & Analyze" done />
          <div className={styles.stepLine} />
          <StepDot n={2} label="Segmentation" done />
          <div className={styles.stepLine} />
          <StepDot n={3} label="Materials" done />
          <div className={styles.stepLine} />
          <StepDot n={4} label="Visualize" active={status === 'loading'} done={status === 'done'} />
          <div className={`${styles.stepLine} ${status === 'done' ? '' : styles.stepLineDim}`} />
          <StepDot n={5} label="Estimate" dim={status !== 'done'} />
        </div>

        {/* ── Loading state ── */}
        {status === 'loading' && (
          <div className={styles.loadingCard}>
            <div className={styles.loadingOrb}>
              <div className={styles.orbRing1} />
              <div className={styles.orbRing2} />
              <div className={styles.orbRing3} />
              <span className={styles.orbIcon}>🏠</span>
            </div>
            <h2 className={styles.loadingTitle}>Generating AI Visualization</h2>
            <p className={styles.loadingSubtitle}>
              This takes 20–40 seconds. Our AI is rendering your renovation photorealistically.
            </p>
            <div className={styles.loadingSteps}>
              {LOADING_STEPS.map((step, i) => (
                <div
                  key={i}
                  className={`${styles.loadingStep} ${i === loadStep ? styles.loadingStepActive : ''} ${i < loadStep ? styles.loadingStepDone : ''}`}
                >
                  <span className={styles.loadingStepIcon}>{i < loadStep ? '✓' : step.icon}</span>
                  <span className={styles.loadingStepText}>{step.text}</span>
                </div>
              ))}
            </div>
            <div className={styles.loadingBar}>
              <div
                className={styles.loadingBarFill}
                style={{ width: `${((loadStep + 1) / LOADING_STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* ── Error state ── */}
        {status === 'error' && (
          <div className={styles.errorCard}>
            <span className={styles.errorIcon}>⚠️</span>
            <h2>Visualization Failed</h2>
            <p className={styles.errorMsg}>{error}</p>
            <button className={styles.retryBtn} onClick={() => window.location.reload()}>Retry Module</button>
          </div>
        )}

        {/* ── Done state (Before/After Slider) ── */}
        {status === 'done' && (
          <div className={styles.resultLayout}>

            {/* ── Left: Before/After comparison ── */}
            <div className={styles.comparePanel}>
              <div className={styles.comparePanelHeader}>
                <span className={styles.compareLabel}>Before / After Comparison</span>
                <span className={styles.compareTip}>↔ Drag the slider</span>
              </div>

              {/* Comparison slider */}
              <div
                id="before-after-slider"
                className={styles.compareWrap}
                ref={sliderRef}
                onMouseDown={handleMouseDown}
                onTouchStart={handleMouseDown}
              >
                {/* After (AI visualization) — full width behind */}
                {vizImg && (
                  <img
                    src={`data:image/png;base64,${vizImg}`}
                    alt="AI Visualization"
                    className={styles.compareImgAfter}
                    draggable={false}
                  />
                )}

                {/* Before (original) — clipped to slider position */}
                {originalImg && (
                  <div
                    className={styles.compareImgBeforeWrap}
                    style={{ width: `${sliderPos}%` }}
                  >
                    <img
                      src={`data:image/png;base64,${originalImg}`}
                      alt="Original"
                      className={styles.compareImgBefore}
                      draggable={false}
                    />
                  </div>
                )}

                {/* Slider handle */}
                <div
                  className={styles.sliderHandle}
                  style={{ left: `${sliderPos}%` }}
                  onMouseDown={handleMouseDown}
                  onTouchStart={handleMouseDown}
                >
                  <div className={styles.sliderLine} />
                  <div className={styles.sliderKnob}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M8 5l-5 7 5 7M16 5l5 7-5 7" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                </div>

                {/* Labels */}
                <span className={styles.labelBefore}>Original</span>
                <span className={styles.labelAfter}>AI Render</span>
              </div>

              {/* Download buttons */}
              <div className={styles.downloadRow}>
                {originalImg && (
                  <a
                    href={`data:image/png;base64,${originalImg}`}
                    download="original_house.png"
                    className={styles.dlLink}
                  >
                    Download Original
                  </a>
                )}
                {vizImg && (
                  <a
                    href={`data:image/png;base64,${vizImg}`}
                    download="visualized_house.png"
                    className={`${styles.dlLink} ${styles.dlLinkPrimary}`}
                  >
                    Download Render
                  </a>
                )}
              </div>
            </div>

            {/* ── Right: Meta info ── */}
            <div className={styles.metaPanel}>
              
              <div className={styles.materialSummaryCard}>
                <h3 className={styles.cardTitle}>Applied Materials</h3>
                <div className={styles.materialList}>
                  {Object.entries(vizData?.selections || {}).map(([rid, sel]) => {
                    const label = rid.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return (
                      <div key={rid} className={styles.materialItem}>
                        <div className={styles.matRegion}>{label}</div>
                        <div className={styles.matValue}>
                          {isPaint(sel.value) ? (
                            <><span className={styles.colorDot} style={{ background: sel.value }}></span> Paint</>
                          ) : (
                            <>🪨 Texture</>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className={styles.ctaCard}>
                <h3 className={styles.cardTitle}>Next Step</h3>
                <p className={styles.cardDesc}>
                  Now that you've visualized your new exterior, generate a detailed cost estimate based on real-world measurements derived from this image.
                </p>
                {apiError && <div style={{ color: '#fca5a5', marginBottom: 10, fontSize: 13 }}>{apiError}</div>}
                <button 
                  className={styles.ctaBtn} 
                  onClick={handleProceedClick}
                  disabled={isEstimating}
                >
                  {isEstimating ? 'Calculating Estimate...' : 'Proceed to Cost Estimation'}
                  {!isEstimating && (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StepDot({ n, label, done, active, dim }) {
  return (
    <div className={`${styles.step} ${done ? styles.stepDone : ''} ${active ? styles.stepActive : ''} ${dim ? styles.stepDim : ''}`}>
      <div className={styles.stepNum}>
        {done
          ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><polyline points="20,6 9,17 4,12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          : n}
      </div>
      <span className={styles.stepLabel}>{label}</span>
    </div>
  );
}
