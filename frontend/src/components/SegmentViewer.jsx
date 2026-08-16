import { useState } from 'react';
import styles from './SegmentViewer.module.css';

const REGION_META = {
  main_wall:     { label: 'Main Wall',     color: [255, 80,  80 ] },
  pillar:        { label: 'Pillar',        color: [80,  80,  255] },
  balcony:       { label: 'Balcony',       color: [255, 200, 50 ] },
  roof:          { label: 'Roof',          color: [50,  200, 200] },
  boundary_wall: { label: 'Boundary Wall', color: [200, 150, 50 ] },
  window:        { label: 'Window',        color: [100, 200, 100] },
  door:          { label: 'Door',          color: [255, 140, 0  ] },
};

function rgbCss([r, g, b]) {
  return `rgb(${r},${g},${b})`;
}

function rgbAlpha([r, g, b], a) {
  return `rgba(${r},${g},${b},${a})`;
}

export default function SegmentViewer({ session, data, onContinue }) {
  const [showOverlay, setShowOverlay] = useState(true);
  const [activeRegion, setActiveRegion] = useState(null);

  const { regions = [], overlay_image, detected_regions = [], protected_regions = [], elapsed_seconds } = data;

  // Sort regions by coverage descending
  const sorted = [...regions].sort((a, b) => b.coverage_pct - a.coverage_pct);

  return (
    <div className={styles.wrap}>
      {/* Header bar */}
      <div className={styles.topBar}>
        <div className={styles.topLeft}>
          <div className={styles.successBadge}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <polyline points="9,12 11,14 15,10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Segmentation Complete
          </div>
          <span className={styles.statChip}>{detected_regions.length} regions detected</span>
          {elapsed_seconds && (
            <span className={styles.statChip}>
              ⏱ {elapsed_seconds < 60
                ? `${elapsed_seconds.toFixed(1)}s`
                : `${(elapsed_seconds/60).toFixed(1)}min`}
            </span>
          )}
          <span className={styles.statChip}>GPU: {data.device_used || 'cpu'}</span>
        </div>

        {/* Overlay toggle */}
        <button
          id="toggle-overlay-btn"
          className={`${styles.toggleBtn} ${showOverlay ? styles.toggleActive : ''}`}
          onClick={() => setShowOverlay(v => !v)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2"/>
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/>
          </svg>
          {showOverlay ? 'Hide Overlay' : 'Show Overlay'}
        </button>
      </div>

      {/* Image panel — full width */}
      <div className={styles.imagePanel}>
        <div className={styles.imageWrap}>
          {overlay_image ? (
            <img
              id="segment-overlay-img"
              src={`data:image/png;base64,${overlay_image}`}
              alt="Segmentation overlay"
              className={`${styles.overlayImg} ${!showOverlay ? styles.overlayHidden : ''}`}
            />
          ) : (
            <div className={styles.noImage}>No overlay available</div>
          )}

          {/* Hover highlight for active region */}
          {activeRegion && (() => {
            const r = regions.find(r => r.region_id === activeRegion);
            const meta = REGION_META[activeRegion];
            if (!r || !r.bounding_box || !meta) return null;
            const [x1, y1, x2, y2] = r.bounding_box;
            const iw = data.image_width  || 1;
            const ih = data.image_height || 1;
            return (
              <div
                className={styles.regionHighlight}
                style={{
                  left:   `${(x1/iw)*100}%`,
                  top:    `${(y1/ih)*100}%`,
                  width:  `${((x2-x1)/iw)*100}%`,
                  height: `${((y2-y1)/ih)*100}%`,
                  borderColor: rgbCss(meta.color),
                  background:  rgbAlpha(meta.color, 0.12),
                }}
              >
                <span className={styles.hlLabel} style={{ background: rgbCss(meta.color) }}>
                  {meta.label}
                </span>
              </div>
            );
          })()}
        </div>
      </div>

      {/* Horizontal regions strip — below the image */}
      <div className={styles.regionsPanel}>
        <div className={styles.regionsPanelHeader}>
          <h3 className={styles.sidebarTitle}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Detected Regions
          </h3>
          <div className={styles.summaryChips}>
            <span className={styles.statChip}>{data.image_width} × {data.image_height}px</span>
            <span className={styles.statChip}>{detected_regions.length} editable</span>
            <span className={styles.statChip}>{protected_regions.length} protected</span>
          </div>
          {/* CTA inline */}
          <button id="proceed-to-materials-btn" className={styles.ctaBtn} onClick={onContinue}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Select Materials
            <span className={styles.ctaBadge}>Module 3 →</span>
          </button>
        </div>

        {/* Horizontal scroll row */}
        <div className={styles.regionRow}>
          {sorted.map((r) => {
            const meta        = REGION_META[r.region_id] || { label: r.region_id, color: [128,128,128] };
            const isProtected = r.is_protected;
            const isActive    = activeRegion === r.region_id;
            const color       = r.color_rgb || meta.color;

            return (
              <div
                key={r.region_id}
                id={`region-${r.region_id}`}
                className={`${styles.regionCard} ${isActive ? styles.regionCardActive : ''}`}
                onMouseEnter={() => setActiveRegion(r.region_id)}
                onMouseLeave={() => setActiveRegion(null)}
                style={isActive ? { borderColor: rgbCss(color), background: rgbAlpha(color, 0.07) } : {}}
              >
                <div className={styles.rcHeader}>
                  <div className={styles.rcDot} style={{ background: rgbCss(color) }} />
                  <span className={styles.rcLabel}>{meta.label}</span>
                  {isProtected && (
                    <span className={styles.rcProtect} title="Protected — windows and doors are never modified">🔒</span>
                  )}
                </div>

                <div className={styles.rcStats}>
                  <div className={styles.rcStat}>
                    <span className={styles.rcStatLabel}>Coverage</span>
                    <span className={styles.rcStatValue}>{r.coverage_pct?.toFixed(1)}%</span>
                  </div>
                  <div className={styles.rcStat}>
                    <span className={styles.rcStatLabel}>Pixels</span>
                    <span className={styles.rcStatValue}>{r.pixel_count?.toLocaleString()}</span>
                  </div>
                </div>

                <div className={styles.rcBar}>
                  <div
                    className={styles.rcBarFill}
                    style={{ width: `${Math.min(100, r.coverage_pct || 0)}%`, background: rgbCss(color) }}
                  />
                </div>

                {isProtected && (
                  <p className={styles.rcProtectNote}>Protected — won't be modified</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
