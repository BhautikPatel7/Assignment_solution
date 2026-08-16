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

export default function VisualizePage({ session, segData, matData, onVisualizeDone, onClear }) {
  const [status, setStatus]         = useState('loading'); // 'loading' | 'done' | 'error'
  const [vizImg, setVizImg]         = useState(null);      // base64
  const [promptUsed, setPromptUsed] = useState('');
  const [error, setError]           = useState('');
  const [loadStep, setLoadStep]     = useState(0);
  const [sliderPos, setSliderPos]   = useState(50);        // before/after slider %
  const isDragging                  = useRef(false);
  const sliderRef                   = useRef(null);
  const stepTimer                   = useRef(null);

  // Cycle through loading steps
  useEffect(() => {
    if (status !== 'loading') return;
    stepTimer.current = setInterval(() => {
      setLoadStep(s => (s + 1) % LOADING_STEPS.length);
    }, 4000);
    return () => clearInterval(stepTimer.current);
  }, [status]);

  // Trigger visualization on mount
  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const res = await visualizeImage(session.session_id);
        if (cancelled) return;
        setVizImg(res.visualization_image);
        setPromptUsed(res.prompt_used || '');
        setStatus('done');
        clearInterval(stepTimer.current);
      } catch (e) {
        if (cancelled) return;
        setError(e.message);
        setStatus('error');
        clearInterval(stepTimer.current);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [session.session_id]);

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
          <StepDot n={4} label="Visualize" active />
          <div className={`${styles.stepLine} ${styles.stepLineDim}`} />
          <StepDot n={5} label="Estimate" dim />
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
            <h3 className={styles.errorTitle}>Visualization Failed</h3>
            <p className={styles.errorMsg}>{error}</p>
            <button className={styles.retryBtn} onClick={() => window.location.reload()}>
              ↺ Try Again
            </button>
          </div>
        )}

        {/* ── Done state ── */}
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
                    className={styles.downloadBtn}
                  >
                    ⬇ Original
                  </a>
                )}
                {vizImg && (
                  <a
                    href={`data:image/png;base64,${vizImg}`}
                    download="renovation_visualization.png"
                    className={`${styles.downloadBtn} ${styles.downloadBtnPrimary}`}
                  >
                    ⬇ Download Visualization
                  </a>
                )}
              </div>
            </div>

            {/* ── Right: Info panel ── */}
            <div className={styles.infoPanel}>

              {/* Materials applied */}
              <div className={styles.infoCard}>
                <h4 className={styles.infoTitle}>
                  <span>🎨</span> Materials Applied
                </h4>
                <div className={styles.materialList}>
                  {Object.entries(matData || {}).map(([rid, sel]) => {
                    const cat = MATERIAL_CATALOG[rid];
                    if (!cat) return null;
                    const isColor = isPaint(sel.value);
                    const matName = isColor
                      ? cat.paints.find(p => p.hex === sel.value)?.name || 'Paint'
                      : cat.textures.find(t => t.file === sel.value)?.name || 'Texture';
                    return (
                      <div key={rid} className={styles.materialRow}>
                        <span className={styles.materialIcon}>{cat.icon}</span>
                        <div className={styles.materialInfo}>
                          <span className={styles.materialRegion}>{cat.label}</span>
                          <span className={styles.materialName}>
                            {isColor && (
                              <span className={styles.colorDot} style={{ background: sel.value }} />
                            )}
                            {matName}
                          </span>
                        </div>
                        <span className={`${styles.materialType} ${isColor ? styles.typeColor : styles.typeTexture}`}>
                          {isColor ? 'Paint' : 'Texture'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* AI Prompt */}
              {promptUsed && (
                <div className={styles.infoCard}>
                  <h4 className={styles.infoTitle}>
                    <span>🤖</span> AI Prompt Used
                  </h4>
                  <p className={styles.promptText}>{promptUsed}</p>
                </div>
              )}

              {/* Proceed CTA */}
              <div className={styles.cta}>
                <button
                  id="proceed-to-estimate-btn"
                  className={styles.ctaBtn}
                  onClick={() => onVisualizeDone({ visualization_image: vizImg, prompt: promptUsed })}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Proceed to Cost Estimation
                  <span className={styles.ctaBadge}>Module 5 →</span>
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
