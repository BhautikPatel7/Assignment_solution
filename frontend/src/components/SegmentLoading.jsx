import styles from './SegmentLoading.module.css';

const PHASES = [
  { seconds: 0,   label: 'Loading AI models…',                       icon: '⚙️' },
  { seconds: 10,  label: 'Phase 1 — SegFormer sliding window pass',   icon: '🔍' },
  { seconds: 60,  label: 'Analyzing wall, window, door, pillar…',     icon: '🏠' },
  { seconds: 120, label: 'Phase 2 — YOLO-World detecting regions…',   icon: '🎯' },
  { seconds: 180, label: 'SAM2 refining masks…',                      icon: '✂️' },
  { seconds: 220, label: 'Phase 3 — Post-processing & cleanup…',      icon: '🧹' },
  { seconds: 240, label: 'Almost done — finalizing results…',         icon: '⏳' },
];

function formatTime(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function SegmentLoading({ elapsed }) {
  // Find the current phase
  const current = [...PHASES].reverse().find(p => elapsed >= p.seconds) || PHASES[0];

  // Estimated total: 270s = 4.5 min
  const TOTAL_EST = 270;
  const pct = Math.min(95, Math.round((elapsed / TOTAL_EST) * 100));

  return (
    <div className={styles.wrap}>
      {/* Central spinner */}
      <div className={styles.spinnerRing}>
        <div className={styles.spinnerInner}>
          <span className={styles.phaseIcon}>{current.icon}</span>
        </div>
        <svg className={styles.spinnerSvg} viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="44" className={styles.trackCircle} />
          <circle
            cx="50" cy="50" r="44"
            className={styles.progressCircle}
            strokeDasharray={`${pct * 2.765} 276.5`}
          />
        </svg>
      </div>

      <h2 className={styles.title}>Segmenting Your House</h2>
      <p className={styles.phase}>{current.label}</p>

      {/* Linear progress bar */}
      <div className={styles.barWrap}>
        <div className={styles.bar}>
          <div className={styles.barFill} style={{ width: `${pct}%` }} />
          <div className={styles.barShimmer} />
        </div>
        <div className={styles.barLabels}>
          <span className={styles.elapsed}>⏱ {formatTime(elapsed)}</span>
          <span className={styles.pct}>{pct}%</span>
          <span className={styles.est}>~4–5 min total</span>
        </div>
      </div>

      {/* Phase timeline */}
      <div className={styles.timeline}>
        {PHASES.map((p) => {
          const isDone   = elapsed > p.seconds + 10;
          const isActive = elapsed >= p.seconds && !isDone;
          return (
            <div
              key={p.seconds}
              className={`${styles.timelineItem}
                ${isDone   ? styles.timelineDone   : ''}
                ${isActive ? styles.timelineActive : ''}
              `}
            >
              <div className={styles.timelineDot} />
              <span className={styles.timelineLabel}>{p.label}</span>
              {isDone && (
                <svg className={styles.timelineCheck} width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <polyline points="20,6 9,17 4,12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                </svg>
              )}
            </div>
          );
        })}
      </div>

      <p className={styles.note}>
        Using SegFormer-b4 + YOLO-World + SAM2 — this runs on CPU so it takes a few minutes.
        <br />Please keep this tab open.
      </p>
    </div>
  );
}
