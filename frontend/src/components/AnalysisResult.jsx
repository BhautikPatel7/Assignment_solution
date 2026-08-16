import styles from './AnalysisResult.module.css';

const REGION_LABELS = {
  main_wall:     { label: 'Main Wall',     icon: '🏠', color: '#ef5050' },
  pillar:        { label: 'Pillar',        icon: '🏛️', color: '#5050ef' },
  balcony:       { label: 'Balcony',       icon: '🪟', color: '#f5c832' },
  roof:          { label: 'Roof',          icon: '🏗️', color: '#32c8c8' },
  boundary_wall: { label: 'Boundary Wall', icon: '🧱', color: '#c89632' },
  window:        { label: 'Window',        icon: '🪟', color: '#64c864' },
  door:          { label: 'Door',          icon: '🚪', color: '#ff8c00' },
};

const QUALITY_CONFIG = {
  good:       { label: 'Good',       cls: 'good'     },
  acceptable: { label: 'Acceptable', cls: 'acceptable' },
  poor:       { label: 'Poor',       cls: 'poor'     },
  unusable:   { label: 'Unusable',   cls: 'poor'     },
};

/* ── Success Result ── */
function SuccessPanel({ session, onProceedToSegment, isSegmenting }) {
  const { session_id, analysis } = session;
  const qCfg = QUALITY_CONFIG[analysis.image_quality] || { label: analysis.image_quality, cls: 'acceptable' };

  const editableRegions   = analysis.regions_present   || [];
  const protectedRegions  = analysis.protected_regions || [];
  const allRegions = [...editableRegions, ...protectedRegions];

  return (
    <div id="analysis-success" className={styles.panel}>
      {/* Status Header */}
      <div className={`${styles.statusBar} ${styles.statusBarSuccess}`}>
        <div className={styles.statusIcon}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <polyline points="9,12 11,14 15,10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className={styles.statusText}>
          <h3 className={styles.statusTitle}>Image Accepted</h3>
          <p className={styles.statusDesc}>Your house photo is ready for renovation planning</p>
        </div>
        <div className={`${styles.qualityBadge} ${styles[`quality_${qCfg.cls}`]}`}>
          {qCfg.label} Quality
        </div>
      </div>

      {/* Analysis Grid */}
      <div className={styles.grid}>
        {/* Session Info */}
        <div className={styles.metaCard}>
          <div className={styles.metaLabel}>Session ID</div>
          <code className={styles.sessionCode}>{session_id}</code>
        </div>

        {/* Floors */}
        <div className={styles.metaCard}>
          <div className={styles.metaLabel}>Floors Detected</div>
          <div className={styles.floorDisplay}>
            <span className={styles.floorNumber}>{analysis.floors ?? '—'}</span>
            <div className={styles.floorIcons}>
              {Array.from({ length: analysis.floors || 0 }).map((_, i) => (
                <svg key={i} width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
                </svg>
              ))}
            </div>
          </div>
        </div>

        {/* Confidence */}
        <div className={styles.metaCard}>
          <div className={styles.metaLabel}>AI Confidence</div>
          <div className={styles.confidenceWrap}>
            <span className={styles.confidenceNum}>
              {analysis.confidence ? `${(analysis.confidence * 100).toFixed(0)}%` : '—'}
            </span>
            <div className={styles.confidenceBar}>
              <div
                className={styles.confidenceFill}
                style={{ width: `${(analysis.confidence || 0) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Regions */}
      <div className={styles.section}>
        <h4 className={styles.sectionTitle}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
            <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
            <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
            <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
          </svg>
          Detected Regions ({allRegions.length})
        </h4>
        <div className={styles.regionGrid}>
          {allRegions.map((r) => {
            const cfg = REGION_LABELS[r] || { label: r, icon: '⬜', color: '#888' };
            const isProtected = protectedRegions.includes(r);
            return (
              <div key={r} className={`${styles.regionChip} ${isProtected ? styles.regionProtected : styles.regionEditable}`}>
                <span
                  className={styles.regionDot}
                  style={{ background: cfg.color }}
                />
                <span className={styles.regionLabel}>{cfg.label}</span>
                {isProtected && (
                  <span className={styles.lockBadge} title="Protected — won't be modified">
                    🔒
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Notes */}
      {analysis.notes && (
        <div className={styles.notesBox}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="12" cy="16" r="1" fill="currentColor"/>
          </svg>
          <p className={styles.notesText}>{analysis.notes}</p>
        </div>
      )}

      {/* Call to Action */}
      <div className={styles.cta}>
        <button
          id="proceed-to-segment-btn"
          className={styles.proceedBtn}
          onClick={onProceedToSegment}
          disabled={isSegmenting}
        >
          {isSegmenting ? 'Running AI Segmentation... (takes ~10s)' : 'Proceed to Segmentation'}
          {!isSegmenting && (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14m-7-7l7 7-7 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

/* ── Rejection Result ── */
function RejectionPanel({ rejected, onRetry }) {
  return (
    <div id="analysis-rejected" className={styles.panel}>
      {/* Status Header */}
      <div className={`${styles.statusBar} ${styles.statusBarReject}`}>
        <div className={styles.statusIconReject}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
            <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
        </div>
        <div className={styles.statusText}>
          <h3 className={styles.statusTitle}>Image Not Accepted</h3>
          <p className={styles.statusDesc}>This photo cannot be used for renovation analysis</p>
        </div>
        {rejected.image_quality && (
          <div className={`${styles.qualityBadge} ${styles.quality_poor}`}>
            {rejected.image_quality} Quality
          </div>
        )}
      </div>

      {/* Reason */}
      <div className={styles.reasonBox}>
        <div className={styles.reasonTitle}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" strokeWidth="2"/>
            <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="12" cy="17" r="1" fill="currentColor"/>
          </svg>
          Why was it rejected?
        </div>
        <p className={styles.reasonText}>{rejected.rejection_reason}</p>
      </div>

      {/* Suggestion */}
      {rejected.suggestion && (
        <div className={styles.suggestionBox}>
          <div className={styles.suggestionTitle}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <polyline points="9,12 11,14 15,10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            How to fix it
          </div>
          <p className={styles.suggestionText}>{rejected.suggestion}</p>
        </div>
      )}

      {/* Tips */}
      <div className={styles.tipsBox}>
        <div className={styles.tipsTitle}>📸 Tips for a good photo</div>
        <ul className={styles.tipsList}>
          <li>Front-facing exterior view of the house</li>
          <li>Clear, well-lit photo (daytime preferred)</li>
          <li>Building should fill most of the frame</li>
          <li>Avoid extreme angles, close-ups, or interior shots</li>
          <li>Minimal obstruction by trees, vehicles, or people</li>
        </ul>
      </div>

      {/* Retry */}
      <div className={styles.cta}>
        <button
          id="retry-upload-btn"
          className={styles.retryBtn}
          onClick={onRetry}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <polyline points="1,4 1,10 7,10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M3.51 15a9 9 0 102.13-9.36L1 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Try Another Photo
        </button>
      </div>
    </div>
  );
}

/* ── Main Export ── */
export default function AnalysisResult({ session, rejected, onRetry, onProceedToSegment, isSegmenting }) {
  if (session)  return <SuccessPanel  session={session} onProceedToSegment={onProceedToSegment} isSegmenting={isSegmenting} />;
  if (rejected) return <RejectionPanel rejected={rejected} onRetry={onRetry} />;
  return null;
}
