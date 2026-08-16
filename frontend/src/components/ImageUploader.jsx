import { useState, useRef, useCallback } from 'react';
import styles from './ImageUploader.module.css';

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const MAX_SIZE_MB = 20;

export default function ImageUploader({ onSubmit, isLoading, analysisComplete }) {
  const [dragOver, setDragOver]     = useState(false);
  const [preview,  setPreview]      = useState(null);
  const [file,     setFile]         = useState(null);
  const [error,    setError]        = useState('');
  const inputRef = useRef(null);

  const validateFile = (f) => {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      return 'Please upload a JPG, PNG, or WebP image.';
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File size must be under ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFile = useCallback((f) => {
    setError('');
    const err = validateFile(f);
    if (err) { setError(err); return; }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const onInputChange = (e) => {
    const f = e.target.files[0];
    if (f) handleFile(f);
  };

  const handleRemove = () => {
    setFile(null);
    setPreview(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleAnalyze = () => {
    if (file) onSubmit(file);
  };

  return (
    <div className={styles.wrapper}>
      {/* Drop Zone */}
      {!preview ? (
        <div
          id="upload-dropzone"
          className={`${styles.dropzone} ${dragOver ? styles.dragOver : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
          aria-label="Upload image drop zone"
        >
          <input
            ref={inputRef}
            id="image-file-input"
            type="file"
            accept="image/jpeg,image/jpg,image/png,image/webp"
            className={styles.hiddenInput}
            onChange={onInputChange}
            aria-label="Select image file"
          />

          <div className={styles.dzIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <polyline points="17,8 12,3 7,8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>

          <p className={styles.dzTitle}>
            {dragOver ? 'Drop your image here' : 'Drop your house photo here'}
          </p>
          <p className={styles.dzSub}>or <span className={styles.browse}>browse files</span></p>
          <p className={styles.dzHint}>Supports JPG, PNG, WebP · Max {MAX_SIZE_MB}MB</p>
          <p className={styles.dzHint2}>
            ✓ Exterior view &nbsp;·&nbsp; ✓ Front-facing &nbsp;·&nbsp; ✓ Well-lit
          </p>
        </div>
      ) : (
        /* Preview Card */
        <div className={styles.previewCard}>
          <div className={styles.previewImageWrap}>
            <img
              src={preview}
              alt="Selected house"
              className={styles.previewImage}
            />
            <button
              id="remove-image-btn"
              className={styles.removeBtn}
              onClick={handleRemove}
              aria-label="Remove image"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </button>
          </div>

          <div className={styles.previewMeta}>
            <div className={styles.metaRow}>
              <div className={styles.fileIcon}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" strokeWidth="2"/>
                  <path d="M14 2v6h6" stroke="currentColor" strokeWidth="2"/>
                </svg>
              </div>
              <div>
                <p className={styles.fileName}>{file.name}</p>
                <p className={styles.fileSize}>{(file.size / 1024).toFixed(0)} KB · {file.type.split('/')[1].toUpperCase()}</p>
              </div>
            </div>

            <div className={styles.readyBadge}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <polyline points="20,6 9,17 4,12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Ready
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div id="upload-error" className={styles.error} role="alert">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="12" cy="16" r="1" fill="currentColor"/>
          </svg>
          {error}
        </div>
      )}

      {/* Action Button */}
      <button
        id="analyze-btn"
        className={`${styles.analyzeBtn} ${(!file || isLoading || analysisComplete) ? styles.disabled : ''}`}
        onClick={handleAnalyze}
        disabled={!file || isLoading || analysisComplete}
      >
        {isLoading ? (
          <>
            <span className={styles.spinner} />
            Analyzing with Gemini…
          </>
        ) : analysisComplete ? (
          <>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <polyline points="9,12 11,14 15,10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Analysis Complete
          </>
        ) : (
          <>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
              <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Analyze House Image
          </>
        )}
      </button>

      {file && !isLoading && (
        <p className={styles.hint}>
          AI will validate your image and extract architectural details
        </p>
      )}
    </div>
  );
}
