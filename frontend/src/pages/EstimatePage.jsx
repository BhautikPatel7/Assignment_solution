import { useState, useEffect } from 'react';
import Header from '../components/Header';
import { estimateCost, BASE_URL } from '../api';
import styles from './EstimatePage.module.css';

export default function EstimatePage({ session, segData, vizData, estData, onClear }) {
  const [status, setStatus] = useState('done'); // since we got it from VisualizePage
  const [data, setData] = useState(estData?.data || null);
  const [error, setError] = useState('');
  const [houseHeight, setHouseHeight] = useState(20);

  // Fetch estimate
  const fetchEstimate = async (height) => {
    setStatus('loading');
    try {
      const res = await estimateCost(session.session_id, height);
      setData(res.data);
      setStatus('done');
    } catch (e) {
      setError(e.message);
      setStatus('error');
    }
  };

  const handleRecalculate = (e) => {
    e.preventDefault();
    if (houseHeight > 0) {
      fetchEstimate(houseHeight);
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  return (
    <div className={styles.page}>
      <Header sessionId={session?.session_id} onClearSession={onClear} />

      <main className={styles.main}>
        {/* Step Indicator */}
        <div className={styles.stepBar}>
          <StepDot n={1} label="Upload & Analyze" done />
          <div className={styles.stepLine} />
          <StepDot n={2} label="Segmentation" done />
          <div className={styles.stepLine} />
          <StepDot n={3} label="Materials" done />
          <div className={styles.stepLine} />
          <StepDot n={4} label="Visualize" done />
          <div className={styles.stepLine} />
          <StepDot n={5} label="Estimate" active />
        </div>

        <div className={styles.contentLayout}>
          
          {/* Header & Controls */}
          <div className={styles.headerRow}>
            <div>
              <h2 className={styles.pageTitle}>Project Cost Estimate</h2>
              <p className={styles.pageSubtitle}>
                Estimated quantities and costs based on real-world dimensions derived from your image.
              </p>
            </div>
            
            <form className={styles.scaleForm} onSubmit={handleRecalculate}>
              <div className={styles.scaleInputWrap}>
                <label>Estimated House Height</label>
                <div className={styles.inputGroup}>
                  <input 
                    type="number" 
                    step="0.5"
                    min="5"
                    value={houseHeight} 
                    onChange={(e) => setHouseHeight(parseFloat(e.target.value) || 0)} 
                    className={styles.numInput}
                  />
                  <span className={styles.unitSuffix}>ft</span>
                  <button type="submit" className={styles.recalcBtn} disabled={status === 'loading'}>
                    {status === 'loading' ? '↻...' : 'Recalculate'}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {status === 'error' && (
            <div className={styles.errorCard}>
              <span className={styles.errorIcon}>⚠️</span>
              <p>{error}</p>
              <button onClick={() => fetchEstimate(houseHeight)} className={styles.retryBtn}>Retry</button>
            </div>
          )}

          {status === 'loading' && !data && (
            <div className={styles.loadingState}>
              <div className={styles.spinner}></div>
              <p>Calculating quantities and rates...</p>
            </div>
          )}

          {data && (
            <div className={styles.estimateGrid}>
              
              {/* Left Column: Breakdown Table */}
              <div className={styles.tableCard}>
                <h3 className={styles.cardTitle}>Itemized Breakdown</h3>
                <div className={styles.tableWrap}>
                  <table className={styles.estimateTable}>
                    <thead>
                      <tr>
                        <th>Region</th>
                        <th>Material</th>
                        <th className={styles.numCol}>Qty</th>
                        <th className={styles.numCol}>Rate (Mat/Lab)</th>
                        <th className={styles.numCol}>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.breakdown.map((item, idx) => (
                        <tr key={idx}>
                          <td>
                            <span className={styles.tdRegion}>{item.region_name}</span>
                          </td>
                          <td>
                            <span className={styles.tdMat}>{item.material_name}</span>
                            {item.wastage_factor > 1 && (
                              <span className={styles.wastageBadge}>
                                +{Math.round((item.wastage_factor - 1) * 100)}% waste
                              </span>
                            )}
                          </td>
                          <td className={styles.numCol}>
                            {item.required_quantity} <span className={styles.tinyUnit}>{item.unit}</span>
                          </td>
                          <td className={styles.numCol}>
                            <div className={styles.rateStack}>
                              <span>{formatCurrency(item.material_rate)}</span>
                              <span className={styles.laborRate}>+{formatCurrency(item.labor_rate)}</span>
                            </div>
                          </td>
                          <td className={styles.numCol}>
                            <span className={styles.itemTotal}>{formatCurrency(item.total_cost)}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Right Column: Summary */}
              <div className={styles.summarySidebar}>
                <div className={styles.summaryCard}>
                  <h3 className={styles.cardTitle}>Project Total</h3>
                  
                  <div className={styles.summaryRows}>
                    <div className={styles.summaryRow}>
                      <span className={styles.sLabel}>Total Materials</span>
                      <span className={styles.sValue}>{formatCurrency(data.summary.total_material_cost)}</span>
                    </div>
                    <div className={styles.summaryRow}>
                      <span className={styles.sLabel}>Total Labor</span>
                      <span className={styles.sValue}>{formatCurrency(data.summary.total_labor_cost)}</span>
                    </div>
                    <div className={styles.divider}></div>
                    <div className={`${styles.summaryRow} ${styles.grandTotal}`}>
                      <span className={styles.sLabel}>Grand Total</span>
                      <span className={styles.sValue}>{formatCurrency(data.summary.grand_total)}</span>
                    </div>
                  </div>

                  <button 
                    className={styles.downloadReportBtn}
                    onClick={() => {
                      window.open(`${BASE_URL}/api/report/${session.session_id}`, '_blank');
                    }}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Download PDF Report
                  </button>
                  <p className={styles.disclaimer}>
                    * This is an AI-generated estimate based on image dimensions and standard local rates. Actual site conditions may vary.
                  </p>
                </div>
              </div>

            </div>
          )}
        </div>
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
