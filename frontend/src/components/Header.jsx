import styles from './Header.module.css';

export default function Header({ sessionId, onClearSession }) {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
            <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <span className={styles.logoText}>E2M</span>
          <span className={styles.logoBadge}>AI</span>
        </div>
      </div>

      <nav className={styles.nav}>
        {sessionId && (
          <div className={styles.sessionBadge}>
            <span className={styles.sessionDot} />
            <span className={styles.sessionLabel}>Session active</span>
            <code className={styles.sessionId}>{sessionId.slice(0, 8)}…</code>
          </div>
        )}
        {sessionId && (
          <button
            id="clear-session-btn"
            className={styles.clearBtn}
            onClick={onClearSession}
            title="Clear session and start fresh"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Clear Session
          </button>
        )}
      </nav>
    </header>
  );
}
