/**
 * MaskBrushCanvas.jsx
 *
 * Brush-correction tool for a single segmentation region mask.
 *
 * Props:
 *   sessionId   {string}   — session UUID
 *   regionId    {string}   — e.g. "main_wall"
 *   regionLabel {string}   — e.g. "Main Wall"
 *   colorRgb    {number[]} — [R, G, B]  display colour
 *   maskB64     {string}   — base64 PNG of the current mask (grayscale)
 *   originalB64 {string}   — base64 PNG of the original house image (used as bg)
 *   imageWidth  {number}
 *   imageHeight {number}
 *   onSave      {function} — called with { overlay_image, coverage_pct, pixel_count, ... }
 *   onCancel    {function}
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import { updateMask } from '../api';
import styles from './MaskBrushCanvas.module.css';

const TOOLS = { PAINT: 'paint', ERASE: 'erase' };

export default function MaskBrushCanvas({
  sessionId,
  regionId,
  regionLabel,
  colorRgb = [255, 80, 80],
  maskB64,
  originalB64,
  imageWidth,
  imageHeight,
  onSave,
  onCancel,
}) {
  /* ── Refs ─────────────────────────────── */
  const wrapRef    = useRef(null);   // container div (for sizing)
  const bgRef      = useRef(null);   // original image canvas (read-only)
  const maskRef    = useRef(null);   // mask canvas (boolean: white/black)
  const drawRef    = useRef(null);   // composite display canvas (user sees this)
  const isDrawing  = useRef(false);
  const lastPos    = useRef(null);

  /* ── State ────────────────────────────── */
  const [tool,       setTool]       = useState(TOOLS.PAINT);
  const [brushSize,  setBrushSize]  = useState(30);
  const [opacity,    setOpacity]    = useState(0.6);
  const [saving,     setSaving]     = useState(false);
  const [saveError,  setSaveError]  = useState('');
  const [undoStack,  setUndoStack]  = useState([]);   // ImageData snapshots
  const [scale,      setScale]      = useState(1);    // display scale factor

  /* ── Colour string helpers ────────────── */
  const fillColor  = `rgba(${colorRgb.join(',')},${opacity})`;
  const eraseColor = 'rgba(0,0,0,1)';  // on mask canvas, black = erased

  /* ── Compute display scale ────────────── */
  useEffect(() => {
    if (!wrapRef.current) return;
    const obs = new ResizeObserver(() => {
      const w = wrapRef.current.clientWidth;
      setScale(w / imageWidth);
    });
    obs.observe(wrapRef.current);
    return () => obs.disconnect();
  }, [imageWidth]);

  /* ── Load background + existing mask ─── */
  useEffect(() => {
    const bg   = bgRef.current;
    const mask = maskRef.current;
    if (!bg || !mask) return;

    const bgCtx   = bg.getContext('2d');
    const maskCtx = mask.getContext('2d');

    // 1. Draw original image as background
    const origImg = new Image();
    origImg.onload = () => bgCtx.drawImage(origImg, 0, 0, imageWidth, imageHeight);
    origImg.src = `data:image/png;base64,${originalB64}`;

    // 2. Load existing mask (grayscale)
    const maskImg = new Image();
    maskImg.onload = () => {
      maskCtx.drawImage(maskImg, 0, 0, imageWidth, imageHeight);
      // Snapshot for undo
      setUndoStack([maskCtx.getImageData(0, 0, imageWidth, imageHeight)]);
      compositeDisplay();
    };
    maskImg.src = `data:image/png;base64,${maskB64}`;
  }, [maskB64, originalB64, imageWidth, imageHeight]); // eslint-disable-line

  /* ── Composite: blend original + mask overlay → display canvas ── */
  const compositeDisplay = useCallback(() => {
    const draw   = drawRef.current;
    const bg     = bgRef.current;
    const mask   = maskRef.current;
    if (!draw || !bg || !mask) return;

    const ctx     = draw.getContext('2d');
    const maskCtx = mask.getContext('2d');

    // Draw original
    ctx.clearRect(0, 0, imageWidth, imageHeight);
    ctx.drawImage(bg, 0, 0);

    // Overlay mask as semi-transparent color
    const maskData = maskCtx.getImageData(0, 0, imageWidth, imageHeight);
    const [r, g, b] = colorRgb;
    const overlayData = ctx.createImageData(imageWidth, imageHeight);

    for (let i = 0; i < maskData.data.length; i += 4) {
      const isMasked = maskData.data[i] > 127; // white pixel = masked
      overlayData.data[i]   = isMasked ? r : 0;
      overlayData.data[i+1] = isMasked ? g : 0;
      overlayData.data[i+2] = isMasked ? b : 0;
      overlayData.data[i+3] = isMasked ? Math.round(opacity * 180) : 0;
    }

    // Draw the overlay on top of the original
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width  = imageWidth;
    tempCanvas.height = imageHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.putImageData(overlayData, 0, 0);
    ctx.drawImage(tempCanvas, 0, 0);
  }, [colorRgb, imageWidth, imageHeight, opacity]);

  // Re-composite when opacity changes
  useEffect(() => { compositeDisplay(); }, [opacity, compositeDisplay]);

  /* ── Pointer helpers ──────────────────── */
  function getCanvasPos(e) {
    const canvas = drawRef.current;
    const rect   = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: Math.round((clientX - rect.left) / scale),
      y: Math.round((clientY - rect.top)  / scale),
    };
  }

  function drawStroke(from, to) {
    const maskCtx = maskRef.current.getContext('2d');

    maskCtx.globalCompositeOperation = tool === TOOLS.ERASE
      ? 'destination-out'
      : 'source-over';
    maskCtx.strokeStyle  = tool === TOOLS.ERASE ? eraseColor : '#ffffff';
    maskCtx.lineWidth    = brushSize;
    maskCtx.lineCap      = 'round';
    maskCtx.lineJoin     = 'round';

    maskCtx.beginPath();
    maskCtx.moveTo(from.x, from.y);
    maskCtx.lineTo(to.x,   to.y);
    maskCtx.stroke();

    // Reset composite op
    maskCtx.globalCompositeOperation = 'source-over';
    compositeDisplay();
  }

  /* ── Mouse / Touch events ─────────────── */
  function onPointerDown(e) {
    e.preventDefault();
    isDrawing.current = true;
    lastPos.current   = getCanvasPos(e);

    // Push undo snapshot
    const maskCtx = maskRef.current.getContext('2d');
    setUndoStack(prev => [
      ...prev.slice(-19),   // keep max 20 snapshots
      maskCtx.getImageData(0, 0, imageWidth, imageHeight),
    ]);

    // Paint a dot on click
    drawStroke(lastPos.current, lastPos.current);
  }

  function onPointerMove(e) {
    e.preventDefault();
    if (!isDrawing.current) return;
    const pos = getCanvasPos(e);
    drawStroke(lastPos.current, pos);
    lastPos.current = pos;
  }

  function onPointerUp() {
    isDrawing.current = false;
  }

  /* ── Undo ─────────────────────────────── */
  function handleUndo() {
    if (undoStack.length < 2) return;
    const prev    = undoStack[undoStack.length - 2];
    const maskCtx = maskRef.current.getContext('2d');
    maskCtx.putImageData(prev, 0, 0);
    setUndoStack(s => s.slice(0, -1));
    compositeDisplay();
  }

  /* ── Clear entire mask ────────────────── */
  function handleClear() {
    const maskCtx = maskRef.current.getContext('2d');
    setUndoStack(prev => [...prev, maskCtx.getImageData(0, 0, imageWidth, imageHeight)]);
    maskCtx.clearRect(0, 0, imageWidth, imageHeight);
    compositeDisplay();
  }

  /* ── Fill entire mask ─────────────────── */
  function handleFill() {
    const maskCtx = maskRef.current.getContext('2d');
    setUndoStack(prev => [...prev, maskCtx.getImageData(0, 0, imageWidth, imageHeight)]);
    maskCtx.fillStyle = '#ffffff';
    maskCtx.fillRect(0, 0, imageWidth, imageHeight);
    compositeDisplay();
  }

  /* ── Save corrected mask ──────────────── */
  async function handleSave() {
    setSaving(true);
    setSaveError('');
    try {
      // Export mask canvas as grayscale PNG → base64
      const maskCanvas  = maskRef.current;

      // Convert to proper grayscale: threshold the mask channel
      const maskCtx     = maskCanvas.getContext('2d');
      const rawData     = maskCtx.getImageData(0, 0, imageWidth, imageHeight);
      const grayCanvas  = document.createElement('canvas');
      grayCanvas.width  = imageWidth;
      grayCanvas.height = imageHeight;
      const gCtx        = grayCanvas.getContext('2d');
      const grayData    = gCtx.createImageData(imageWidth, imageHeight);

      for (let i = 0; i < rawData.data.length; i += 4) {
        // A pixel is part of the mask only if:
        //   alpha > 127  → it is visible (not erased with destination-out)
        //   R     > 127  → it is white  (painted, not black background)
        // Using OR would flag every opaque black pixel as masked → 100% coverage bug
        const isMasked         = rawData.data[i+3] > 127 && rawData.data[i] > 127;
        const val              = isMasked ? 255 : 0;
        grayData.data[i]       = val;
        grayData.data[i+1]     = val;
        grayData.data[i+2]     = val;
        grayData.data[i+3]     = 255;
      }
      gCtx.putImageData(grayData, 0, 0);

      // Export to base64
      const dataUrl  = grayCanvas.toDataURL('image/png');
      const b64      = dataUrl.split(',')[1];

      const result = await updateMask(sessionId, regionId, b64);
      onSave(result);
    } catch (err) {
      setSaveError(err.message || 'Failed to save mask.');
    } finally {
      setSaving(false);
    }
  }

  /* ── Brush cursor preview ─────────────── */
  const cursorStyle = `url("data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='${brushSize*scale}' height='${brushSize*scale}'>`+
    `<circle cx='${(brushSize*scale)/2}' cy='${(brushSize*scale)/2}' r='${(brushSize*scale)/2-1}' `+
    `fill='none' stroke='white' stroke-width='2' opacity='0.8'/></svg>`
  )}") ${Math.round(brushSize*scale/2)} ${Math.round(brushSize*scale/2)}, crosshair`;

  /* ── Render ───────────────────────────── */
  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>

        {/* ── Header ── */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <div
              className={styles.regionDot}
              style={{ background: `rgb(${colorRgb.join(',')})` }}
            />
            <div>
              <h2 className={styles.title}>Correct Region: {regionLabel}</h2>
              <p className={styles.subtitle}>
                Paint&nbsp;<span className={styles.paintHint}>white&nbsp;=&nbsp;add</span>&nbsp;·&nbsp;
                Erase&nbsp;<span className={styles.eraseHint}>black&nbsp;=&nbsp;remove</span>
              </p>
            </div>
          </div>
          <button id="mask-cancel-btn" className={styles.closeBtn} onClick={onCancel}>✕</button>
        </div>

        {/* ── Toolbar ── */}
        <div className={styles.toolbar}>

          {/* Tool toggle */}
          <div className={styles.toolGroup}>
            <button
              id="tool-paint-btn"
              className={`${styles.toolBtn} ${tool === TOOLS.PAINT ? styles.toolActive : ''}`}
              onClick={() => setTool(TOOLS.PAINT)}
              title="Paint (add to mask)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 19l7-7 3 3-7 7-3-3z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 2l7.586 7.586" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="11" cy="11" r="2" stroke="currentColor" strokeWidth="2"/>
              </svg>
              Paint
            </button>
            <button
              id="tool-erase-btn"
              className={`${styles.toolBtn} ${tool === TOOLS.ERASE ? styles.toolActiveErase : ''}`}
              onClick={() => setTool(TOOLS.ERASE)}
              title="Erase (remove from mask)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M20 20H7L3 16l10-10 7 7-1.5 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M6.5 17.5l5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              Erase
            </button>
          </div>

          {/* Brush size */}
          <div className={styles.sliderGroup}>
            <label className={styles.sliderLabel}>
              Brush
              <span className={styles.sliderVal}>{brushSize}px</span>
            </label>
            <input
              id="brush-size-slider"
              type="range" min={5} max={120} step={5}
              value={brushSize}
              onChange={e => setBrushSize(Number(e.target.value))}
              className={styles.slider}
            />
          </div>

          {/* Overlay opacity */}
          <div className={styles.sliderGroup}>
            <label className={styles.sliderLabel}>
              Opacity
              <span className={styles.sliderVal}>{Math.round(opacity * 100)}%</span>
            </label>
            <input
              id="opacity-slider"
              type="range" min={0.1} max={1} step={0.05}
              value={opacity}
              onChange={e => setOpacity(Number(e.target.value))}
              className={styles.slider}
            />
          </div>

          {/* Action buttons */}
          <div className={styles.actionGroup}>
            <button
              id="undo-btn"
              className={styles.actionBtn}
              onClick={handleUndo}
              disabled={undoStack.length < 2}
              title="Undo last stroke (Ctrl+Z)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <polyline points="1,4 1,10 7,10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M3.51 15a9 9 0 102.13-9.36L1 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Undo
            </button>
            <button
              id="fill-mask-btn"
              className={styles.actionBtn}
              onClick={handleFill}
              title="Fill entire image with this region"
            >
              Fill All
            </button>
            <button
              id="clear-mask-btn"
              className={`${styles.actionBtn} ${styles.actionDanger}`}
              onClick={handleClear}
              title="Clear all mask pixels"
            >
              Clear
            </button>
          </div>
        </div>

        {/* ── Canvas area ── */}
        <div className={styles.canvasWrap} ref={wrapRef}>
          {/* Hidden canvases at full image resolution */}
          <canvas
            ref={bgRef}
            width={imageWidth}
            height={imageHeight}
            style={{ display: 'none' }}
          />
          <canvas
            ref={maskRef}
            width={imageWidth}
            height={imageHeight}
            style={{ display: 'none' }}
          />

          {/* Visible drawing canvas — scaled to fit container */}
          <canvas
            ref={drawRef}
            id="brush-canvas"
            width={imageWidth}
            height={imageHeight}
            className={styles.drawCanvas}
            style={{ cursor: cursorStyle }}
            onMouseDown={onPointerDown}
            onMouseMove={onPointerMove}
            onMouseUp={onPointerUp}
            onMouseLeave={onPointerUp}
            onTouchStart={onPointerDown}
            onTouchMove={onPointerMove}
            onTouchEnd={onPointerUp}
          />

          {/* Brush-size cursor indicator overlay */}
          <div
            className={styles.brushHint}
            style={{
              width:  brushSize * scale,
              height: brushSize * scale,
              borderColor: tool === TOOLS.ERASE ? '#ef4444' : `rgb(${colorRgb.join(',')})`,
            }}
          />
        </div>

        {/* ── Legend ── */}
        <div className={styles.legend}>
          <div className={styles.legendItem}>
            <div className={styles.legendSwatch} style={{ background: `rgba(${colorRgb.join(',')},0.7)` }} />
            Selected region (this mask)
          </div>
          <div className={styles.legendItem}>
            <div className={styles.legendSwatch} style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)' }} />
            Rest of image
          </div>
        </div>

        {/* ── Footer / Save ── */}
        <div className={styles.footer}>
          {saveError && (
            <div className={styles.saveError}>⚠ {saveError}</div>
          )}
          <div className={styles.footerBtns}>
            <button
              id="mask-cancel-footer-btn"
              className={styles.cancelBtn}
              onClick={onCancel}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              id="mask-save-btn"
              className={styles.saveBtn}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? (
                <>
                  <span className={styles.spinner} />
                  Saving…
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                    <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
                    <polyline points="17,21 17,13 7,13 7,21" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
                    <polyline points="7,3 7,8 15,8" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
                  </svg>
                  Save Correction
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
