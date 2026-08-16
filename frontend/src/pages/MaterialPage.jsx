import { useState, useEffect, useCallback, useRef } from 'react';
import Header from '../components/Header';
import { MATERIAL_CATALOG, isPaint, textureUrl } from '../constants/materials';
import { compositeImage } from '../api';
import styles from './MaterialPage.module.css';

const EDITABLE_REGIONS = ['main_wall', 'pillar', 'balcony', 'boundary_wall'];

export default function MaterialPage({ session, segData, onMaterialsDone, onClear }) {
  // Active region in the picker
  const [activeRegion, setActiveRegion]   = useState('main_wall');
  // Tab: 'paint' | 'texture'
  const [activeTab, setActiveTab]         = useState('paint');
  // selections: { region_id: { type, value } }
  const [selections, setSelections]       = useState({});
  // Preview image (base64)
  const [previewImg, setPreviewImg]       = useState(segData?.original_image || null);
  const [compositing, setCompositing]     = useState(false);
  const [compositeErr, setCompositeErr]   = useState('');

  // Debounce composite calls
  const debounceRef = useRef(null);

  // Which regions actually exist in this session's segmentation?
  const availableRegions = EDITABLE_REGIONS.filter(rid =>
    segData?.detected_regions?.includes(rid) ||
    segData?.regions?.some(r => r.region_id === rid)
  );

  // Fallback — show all if no region list
  const regionList = availableRegions.length > 0 ? availableRegions : EDITABLE_REGIONS;

  // Auto-select first available tab for active region
  useEffect(() => {
    const cat = MATERIAL_CATALOG[activeRegion];
    if (!cat) return;
    if (cat.paints.length === 0) setActiveTab('texture');
    else setActiveTab('paint');
  }, [activeRegion]);

  /* ── Trigger composite on selection change ── */
  const triggerComposite = useCallback((newSelections) => {
    if (Object.keys(newSelections).length === 0) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setCompositing(true);
      setCompositeErr('');
      try {
        const res = await compositeImage(session.session_id, newSelections);
        setPreviewImg(res.composite_image);
      } catch (e) {
        setCompositeErr(e.message);
      } finally {
        setCompositing(false);
      }
    }, 300);
  }, [session.session_id]);

  /* ── Handle material pick ── */
  function selectMaterial(type, value) {
    const next = {
      ...selections,
      [activeRegion]: { type, value },
    };
    setSelections(next);
    triggerComposite(next);
  }

  /* ── Clear selection for one region ── */
  function clearRegion(rid) {
    const next = { ...selections };
    delete next[rid];
    setSelections(next);
    // If no selections left, show original image
    if (Object.keys(next).length === 0) {
      setPreviewImg(segData?.original_image || null);
    } else {
      triggerComposite(next);
    }
  }

  /* ── Reset ALL selections → back to original image ── */
  function handleReset() {
    clearTimeout(debounceRef.current);
    setSelections({});
    setPreviewImg(segData?.original_image || null);
    setCompositeErr('');
  }

  /* ── Active selection for current region ── */
  const currentSel = selections[activeRegion];
  const cat        = MATERIAL_CATALOG[activeRegion] || { paints: [], textures: [] };

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
          <StepDot n={3} label="Materials" active />
          <div className={`${styles.stepLine} ${styles.stepLineDim}`} />
          <StepDot n={4} label="Visualize" dim />
        </div>

        {/* ── Main layout ── */}
        <div className={styles.layout}>

          {/* ── Left: Preview image ── */}
          <div className={styles.previewPanel}>
            <div className={styles.previewHeader}>
              <span className={styles.previewLabel}>Live Preview</span>
              <div className={styles.previewHeaderRight}>
                {compositing && (
                  <span className={styles.compositing}>
                    <span className={styles.spinnerSm} /> Applying…
                  </span>
                )}
                {Object.keys(selections).length > 0 && (
                  <button
                    id="reset-to-original-btn"
                    className={styles.resetBtn}
                    onClick={handleReset}
                    title="Remove all material selections and restore original image"
                  >
                    ↺ Reset to Original
                  </button>
                )}
              </div>
            </div>

            <div className={styles.previewWrap}>
              {previewImg ? (
                <img
                  id="material-preview-img"
                  src={`data:image/png;base64,${previewImg}`}
                  alt="Material preview"
                  className={`${styles.previewImg} ${compositing ? styles.previewDimmed : ''}`}
                />
              ) : (
                <div className={styles.previewPlaceholder}>Loading…</div>
              )}
            </div>

            {compositeErr && (
              <div className={styles.previewErr}>⚠ {compositeErr}</div>
            )}

            {/* Region highlight strip below image */}
            <div className={styles.regionStrip}>
              {regionList.map(rid => {
                const c   = MATERIAL_CATALOG[rid];
                const sel = selections[rid];
                return (
                  <button
                    key={rid}
                    id={`region-tab-${rid}`}
                    className={`${styles.regionTab} ${activeRegion === rid ? styles.regionTabActive : ''}`}
                    onClick={() => setActiveRegion(rid)}
                  >
                    <span className={styles.regionTabIcon}>{c?.icon}</span>
                    <span className={styles.regionTabLabel}>{c?.label}</span>
                    {sel && (
                      <span
                        className={styles.regionTabSwatch}
                        style={
                          isPaint(sel.value)
                            ? { background: sel.value }
                            : { background: 'linear-gradient(135deg, #6366f1, #06b6d4)' }
                        }
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Right: Material picker ── */}
          <div className={styles.pickerPanel}>

            {/* Region header */}
            <div className={styles.pickerHeader}>
              <span className={styles.pickerRegionIcon}>{cat.icon}</span>
              <div>
                <h2 className={styles.pickerTitle}>{cat.label}</h2>
                <p className={styles.pickerSub}>Choose paint or texture</p>
              </div>
              {currentSel && (
                <div className={styles.selectedBadge}>
                  {isPaint(currentSel.value) ? '🎨 Paint' : '🪨 Texture'}
                </div>
              )}
            </div>

            {/* Tabs */}
            <div className={styles.tabs}>
              {cat.paints.length > 0 && (
                <button
                  id="tab-paint-btn"
                  className={`${styles.tab} ${activeTab === 'paint' ? styles.tabActive : ''}`}
                  onClick={() => setActiveTab('paint')}
                >
                  🎨 Paint Colors
                </button>
              )}
              {cat.textures.length > 0 && (
                <button
                  id="tab-texture-btn"
                  className={`${styles.tab} ${activeTab === 'texture' ? styles.tabActive : ''}`}
                  onClick={() => setActiveTab('texture')}
                >
                  🪨 Textures & Tiles
                </button>
              )}
            </div>

            {/* Paint swatches */}
            {activeTab === 'paint' && (
              <div className={styles.swatchGrid}>
                {cat.paints.map(p => (
                  <button
                    key={p.id}
                    id={`paint-${p.id}`}
                    className={`${styles.swatchCard} ${currentSel?.value === p.hex ? styles.swatchActive : ''}`}
                    onClick={() => selectMaterial('paint', p.hex)}
                    title={p.name}
                  >
                    <div className={styles.swatchColor} style={{ background: p.hex }} />
                    <span className={styles.swatchName}>{p.name}</span>
                    <span className={styles.swatchRate}>₹{p.rate_per_sqft}/sqft</span>
                    {currentSel?.value === p.hex && (
                      <span className={styles.swatchCheck}>✓</span>
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* Texture cards */}
            {activeTab === 'texture' && (
              <div className={styles.textureGrid}>
                {cat.textures.map(t => (
                  <button
                    key={t.id}
                    id={`texture-${t.id}`}
                    className={`${styles.textureCard} ${currentSel?.value === t.file ? styles.textureActive : ''}`}
                    onClick={() => selectMaterial('texture', t.file)}
                  >
                    <div className={styles.textureImgWrap}>
                      <img
                        src={textureUrl(t.file)}
                        alt={t.name}
                        className={styles.textureImg}
                        onError={e => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                      <div className={styles.texturePlaceholder} style={{ display: 'none' }}>
                        🪨
                      </div>
                    </div>
                    <div className={styles.textureInfo}>
                      <span className={styles.textureName}>{t.name}</span>
                      <span className={styles.textureRate}>
                        ₹{t.material_rate + t.labor_rate}/sqft
                        <span className={styles.textureRateSub}> incl. labor</span>
                      </span>
                    </div>
                    {currentSel?.value === t.file && (
                      <span className={styles.textureCheck}>✓</span>
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* Selection summary */}
            <div className={styles.summary}>
              <h4 className={styles.summaryTitle}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Selected Materials
              </h4>
              <div className={styles.summaryList}>
                {regionList.map(rid => {
                  const sel = selections[rid];
                  const c   = MATERIAL_CATALOG[rid];
                  return (
                    <div key={rid} className={styles.summaryRow}>
                      <span className={styles.summaryIcon}>{c?.icon}</span>
                      <span className={styles.summaryRegion}>{c?.label}</span>
                      {sel ? (
                        <>
                          <span className={styles.summaryVal}>
                            {isPaint(sel.value) ? (
                              <>
                                <span className={styles.summaryDot} style={{ background: sel.value }} />
                                {c?.paints.find(p => p.hex === sel.value)?.name || 'Paint'}
                              </>
                            ) : (
                              <>🪨 {c?.textures.find(t => t.file === sel.value)?.name || 'Texture'}</>
                            )}
                          </span>
                          <button
                            className={styles.clearRegionBtn}
                            onClick={() => clearRegion(rid)}
                            title={`Remove ${c?.label} selection`}
                          >✕</button>
                        </>
                      ) : (
                        <span className={styles.summaryNone}>Not selected</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Proceed CTA */}
            <div className={styles.cta}>
              <button
                id="proceed-to-visualize-btn"
                className={styles.ctaBtn}
                onClick={() => onMaterialsDone(selections)}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Generate AI Visualization
                <span className={styles.ctaBadge}>Module 4 →</span>
              </button>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}

function StepDot({ n, label, done, active, dim }) {
  return (
    <div className={`${styles.step} ${done ? styles.stepDone : ''} ${active ? styles.stepActive : ''} ${dim ? styles.stepDim : ''}`}>
      <div className={styles.stepNum}>
        {done ? <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><polyline points="20,6 9,17 4,12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg> : n}
      </div>
      <span className={styles.stepLabel}>{label}</span>
    </div>
  );
}
