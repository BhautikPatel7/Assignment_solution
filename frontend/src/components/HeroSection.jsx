import styles from './HeroSection.module.css';

const features = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2"/>
        <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
    title: 'AI Image Validation',
    desc: 'Gemini Vision checks if your photo is a clear, exterior house view before processing.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
        <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
        <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
        <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
      </svg>
    ),
    title: 'Region Segmentation',
    desc: 'Automatically identifies walls, roofs, balconies, pillars, doors and windows.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
        <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
      </svg>
    ),
    title: 'Material Estimation',
    desc: 'Calculates material quantities and cost estimates for your renovation project.',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
        <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
    title: 'Detailed Report',
    desc: 'Get a full renovation report with visualizations, material list, and cost breakdown.',
  },
];

export default function HeroSection() {
  return (
    <section className={styles.hero}>
      <div className={styles.badge}>
        <span className={styles.badgeDot} />
        Powered by Gemini Vision AI
      </div>

      <h1 className={styles.headline}>
        Transform Your Home's
        <span className={styles.gradient}> Exterior</span>
        <br />with AI Precision
      </h1>

      <p className={styles.sub}>
        Upload a photo of your house exterior. Our AI instantly validates the image,
        analyzes architecture, segments regions, and generates a detailed renovation
        material estimate — all in seconds.
      </p>

      {/* Pipeline Steps */}
      <div className={styles.pipeline}>
        {['Upload Photo', 'AI Validates', 'Segments Regions', 'Estimates Cost'].map((step, i) => (
          <div key={step} className={styles.pipelineItem}>
            <div className={styles.pipelineNum}>{i + 1}</div>
            <span className={styles.pipelineLabel}>{step}</span>
            {i < 3 && <div className={styles.pipelineArrow}>→</div>}
          </div>
        ))}
      </div>

      {/* Feature Cards */}
      <div className={styles.features}>
        {features.map((f) => (
          <div key={f.title} className={styles.featureCard}>
            <div className={styles.featureIcon}>{f.icon}</div>
            <div>
              <h3 className={styles.featureTitle}>{f.title}</h3>
              <p className={styles.featureDesc}>{f.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
