import { useState } from 'react';
import Header from '../components/Header';
import HeroSection from '../components/HeroSection';
import ImageUploader from '../components/ImageUploader';
import AnalysisResult from '../components/AnalysisResult';
import { analyzeImage } from '../api';
import styles from './UploadPage.module.css';

export default function UploadPage({ session, onAnalyzeDone, onProceedToSegment, onClear }) {
  const [rejected, setRejected] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError]   = useState('');

  const handleAnalyze = async (file) => {
    setIsLoading(true);
    setApiError('');
    setRejected(null);

    try {
      const data = await analyzeImage(file);

      if (data.status === 'success') {
        onAnalyzeDone({ session_id: data.session_id, analysis: data.analysis });
      } else {
        setRejected({
          rejection_reason: data.rejection_reason,
          suggestion:       data.suggestion,
          image_quality:    data.image_quality,
        });
      }
    } catch (err) {
      setApiError(err.message || 'Something went wrong. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    onClear();
  };

  return (
    <div className={styles.page}>
      <Header sessionId={session?.session_id} onClearSession={onClear} />

      <main className={styles.main}>
        {/* Hero — hide once we have a result */}
        {!session && !rejected && <HeroSection />}

        {/* Upload Card */}
        <section className={styles.uploadSection}>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardIcon}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="17,8 12,3 7,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <div>
                <h2 className={styles.cardTitle}>Upload House Photo</h2>
                <p className={styles.cardSub}>Module 1 — AI Image Validation &amp; Analysis</p>
              </div>
            </div>

            <ImageUploader
              onSubmit={handleAnalyze}
              isLoading={isLoading}
              analysisComplete={!!session}
            />

            {/* API Error */}
            {apiError && (
              <div id="api-error" className={styles.apiError} role="alert">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                  <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <circle cx="12" cy="16" r="1" fill="currentColor"/>
                </svg>
                <span>{apiError}</span>
              </div>
            )}
          </div>
        </section>

        {/* Result Panel */}
        {(session || rejected) && (
          <section className={styles.resultSection}>
            <AnalysisResult
              session={session}
              rejected={rejected}
              onRetry={handleRetry}
              onProceedToSegment={onProceedToSegment}
            />
          </section>
        )}
      </main>
    </div>
  );
}
