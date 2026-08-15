import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';

export default function DesignWizard() {
  const [step, setStep] = useState(1);
  const navigate = useNavigate();

  const [order, setOrder] = useState({
    clothType: '',
    fit: 'Slim fit',
    neckline: 'Round neck',
    sleeve: 'Short sleeve',
    pattern: 'Plain / solid',
    desc: '',
    material: '',
    color: '',
    measurements: { chest: '', waist: '', hip: '', length: '' }
  });

  const nextStep = () => setStep(s => Math.min(s + 1, 6));
  const prevStep = () => setStep(s => Math.max(s - 1, 1));

  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    // Placeholder AI-generation delay: replaced by a real POST /api/mockup call in a later PR.
    if (step === 6) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setGenerating(true);
      setTimeout(() => {
        setGenerating(false);
      }, 3000);
    }
  }, [step]);

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
    }, 3000);
  };

  const handleConfirm = () => {
    navigate('/success');
  };

  return (
    <>
      <Navbar backLink={true} />
      
      <div className="progress-wrap">
        <div className="progress-steps">
          <div className={`prog-step ${step > 1 ? 'done' : step === 1 ? 'active' : ''}`} onClick={() => setStep(1)}><div className="prog-num">{step > 1 ? '✓' : '1'}</div><div className="prog-label">Cloth</div></div>
          <div className={`prog-step ${step > 2 ? 'done' : step === 2 ? 'active' : ''}`} onClick={() => setStep(2)}><div className="prog-num">{step > 2 ? '✓' : '2'}</div><div className="prog-label">Design</div></div>
          <div className={`prog-step ${step > 3 ? 'done' : step === 3 ? 'active' : ''}`} onClick={() => setStep(3)}><div className="prog-num">{step > 3 ? '✓' : '3'}</div><div className="prog-label">Material</div></div>
          <div className={`prog-step ${step > 4 ? 'done' : step === 4 ? 'active' : ''}`} onClick={() => setStep(4)}><div className="prog-num">{step > 4 ? '✓' : '4'}</div><div className="prog-label">Measure</div></div>
          <div className={`prog-step ${step > 5 ? 'done' : step === 5 ? 'active' : ''}`} onClick={() => setStep(5)}><div className="prog-num">{step > 5 ? '✓' : '5'}</div><div className="prog-label">Pricing</div></div>
          <div className={`prog-step ${step === 6 ? 'active' : ''}`} onClick={() => setStep(6)}><div className="prog-num">6</div><div className="prog-label">AI Preview</div></div>
        </div>
      </div>

      <div className="wizard">
        <div className="wizard-main">
          {step === 1 && (
            <div>
              <h1 className="step-title">Choose Your Garment</h1>
              <p className="step-sub">Step 1 of 6 · What would you like to create?</p>
              
              <div className="cloth-select-grid">
                {['T-shirt', 'Shirt', 'Dress', 'Trousers', 'Kurta', 'Saree Blouse', 'Salwar Kameez', 'Skirt'].map(c => (
                  <div key={c} className={`cloth-option ${order.clothType === c ? 'selected' : ''}`} onClick={() => setOrder({...order, clothType: c})}>
                    <svg viewBox="0 0 60 60"><path d="M15 10L8 16v10h8v24h28V26h8V16l-7-6-7 5-7-5-7 5z" strokeWidth="1.5"/></svg>
                    <h4>{c}</h4>
                    <p>Select</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h1 className="step-title">Describe Your Design</h1>
              <p className="step-sub">Step 2 of 6 · {order.clothType || 'Garment'} selected</p>

              <div className="form-section">
                <span className="form-label">Fit style</span>
                <div className="tags-wrap">
                  {['Slim fit', 'Regular fit', 'Oversized', 'Fitted', 'Flowy'].map(t => (
                    <button key={t} className={`tag-btn ${order.fit === t ? 'active' : ''}`} onClick={() => setOrder({...order, fit: t})}>{t}</button>
                  ))}
                </div>
              </div>
              <div className="form-section">
                <span className="form-label">Neckline</span>
                <div className="tags-wrap">
                  {['V-neck', 'Round neck', 'Square neck', 'Off-shoulder', 'Collar', 'Halter'].map(t => (
                    <button key={t} className={`tag-btn ${order.neckline === t ? 'active' : ''}`} onClick={() => setOrder({...order, neckline: t})}>{t}</button>
                  ))}
                </div>
              </div>
              <div className="form-section">
                <span className="form-label">Sleeve type</span>
                <div className="tags-wrap">
                  {['Sleeveless', 'Short sleeve', '3/4 sleeve', 'Long sleeve', 'Puffed sleeve', 'Bell sleeve'].map(t => (
                    <button key={t} className={`tag-btn ${order.sleeve === t ? 'active' : ''}`} onClick={() => setOrder({...order, sleeve: t})}>{t}</button>
                  ))}
                </div>
              </div>
              <div className="form-section">
                <span className="form-label">Pattern & details</span>
                <div className="tags-wrap">
                  {['Plain / solid', 'Floral', 'Striped', 'Embroidered', 'Lace trim', 'Pockets', 'Front buttons', 'Side zip'].map(t => (
                    <button key={t} className={`tag-btn ${order.pattern === t ? 'active' : ''}`} onClick={() => setOrder({...order, pattern: t})}>{t}</button>
                  ))}
                </div>
              </div>

              <div className="form-section">
                <span className="form-label">Describe your design <span style={{color:'var(--taupe)',fontWeight:300,textTransform:'none',fontSize:'11px'}}>(optional)</span></span>
                <textarea placeholder="e.g. I want a midi dress..." value={order.desc} onChange={e => setOrder({...order, desc: e.target.value})}></textarea>
              </div>

              <div className="form-section">
                <span className="form-label">Reference images <span style={{color:'var(--taupe)',fontWeight:300,textTransform:'none',fontSize:'11px'}}>(optional)</span></span>
                <div className="upload-zone">
                  <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 8v8M8 12h8" strokeLinecap="round"/></svg>
                  <p>Drag & drop or click to upload</p>
                  <small>JPG, PNG or WEBP · Max 5 MB each · Up to 3 images</small>
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h1 className="step-title">Choose Your Material</h1>
              <p className="step-sub">Step 3 of 6 · Fabric & Colour</p>
              
              <div className="mat-grid" style={{marginBottom: '40px'}}>
                {[
                  {name: 'Cotton', bg: '#f5ede0'},
                  {name: 'Linen', bg: '#e8ddd0'},
                  {name: 'Silk', bg: 'linear-gradient(135deg,#e8ddf0,#d4c8e8)'},
                  {name: 'Chiffon', bg: 'linear-gradient(135deg,#f0ece8,#e4dcd4)'},
                  {name: 'Satin', bg: 'linear-gradient(135deg,#dce8f0,#c8d8e8)'},
                  {name: 'Denim', bg: 'linear-gradient(135deg,#d8e0d8,#c4d0c4)'},
                  {name: 'Velvet', bg: 'linear-gradient(135deg,#f0e4e8,#e4d0d4)'}
                ].map(m => (
                  <div key={m.name} className={`mat-item ${order.material === m.name ? 'selected' : ''}`} onClick={() => setOrder({...order, material: m.name})}>
                    <div className="mat-swatch" style={{background: m.bg}}></div>
                    <div className="mat-name">{m.name}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <h1 className="step-title">Your Measurements</h1>
              <p className="step-sub">Step 4 of 6 · Provide your exact body size</p>
              
              <div className="field-row">
                <div className="field">
                  <label>Chest (cm)</label>
                  <input type="number" value={order.measurements.chest} onChange={e => setOrder({...order, measurements: {...order.measurements, chest: e.target.value}})} />
                </div>
                <div className="field">
                  <label>Waist (cm)</label>
                  <input type="number" value={order.measurements.waist} onChange={e => setOrder({...order, measurements: {...order.measurements, waist: e.target.value}})} />
                </div>
              </div>
              <div className="field-row">
                <div className="field">
                  <label>Hip (cm)</label>
                  <input type="number" value={order.measurements.hip} onChange={e => setOrder({...order, measurements: {...order.measurements, hip: e.target.value}})} />
                </div>
                <div className="field">
                  <label>Total Length (cm)</label>
                  <input type="number" value={order.measurements.length} onChange={e => setOrder({...order, measurements: {...order.measurements, length: e.target.value}})} />
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div>
              <h1 className="step-title">Pricing Breakdown</h1>
              <p className="step-sub">Step 5 of 6 · Full transparent breakdown</p>
              
              <div className="price-block">
                <h4>Estimated Cost</h4>
                <div className="pr"><span>Base price ({order.clothType || 'Garment'})</span><span>LKR 2,200</span></div>
                <div className="pr"><span>Stitching complexity</span><span>LKR 350</span></div>
                <div className="pr"><span>Material ({order.material || 'TBC'})</span><span>LKR 6,210</span></div>
                <div className="pr"><span>Delivery</span><span>LKR 350</span></div>
                <div className="pr-total"><span className="k">Total</span><span className="v">LKR 9,110</span></div>
              </div>
            </div>
          )}

          {step === 6 && (
            <div>
              <h1 className="step-title">Your AI Mockup Preview</h1>
              <p className="step-sub">Step 6 of 6 · Generated from your design inputs</p>

              <div className="ai-preview-box">
                <div className="ai-label">★ AI Generated Preview</div>
                {generating ? (
                  <div className="ai-loading">
                    <div className="spinner"></div>
                    <div className="loading-text">Generating your mockup…</div>
                    <div className="loading-sub">Stable Diffusion XL · ~20 seconds</div>
                  </div>
                ) : (
                  <>
                    <svg viewBox="0 0 64 64" style={{opacity: 1, stroke: 'var(--brown)', width: '120px', height: '120px'}}><rect x="8" y="8" width="48" height="48" rx="4" strokeWidth="1.5"/><circle cx="22" cy="26" r="5" strokeWidth="1.5"/><path d="M8 44l12-12 10 10 8-10 18 12" strokeWidth="1.5" fill="none"/></svg>
                    <h3 style={{color: 'var(--dark)'}}>Mockup Ready!</h3>
                    <p>Your {order.clothType || 'Garment'} design</p>
                  </>
                )}
              </div>

              {!generating && <button className="regen-btn" onClick={handleGenerate}>↺ Regenerate preview</button>}

              <div className="design-recap">
                <div className="recap-title">Design recap — what we used to generate your preview</div>
                <div className="recap-grid">
                  <div className="recap-item"><div className="k">Garment</div><div className="v">{order.clothType || 'TBC'}</div></div>
                  <div className="recap-item"><div className="k">Material</div><div className="v">{order.material || 'TBC'}</div></div>
                  <div className="recap-item"><div className="k">Fit</div><div className="v">{order.fit}</div></div>
                  <div className="recap-item"><div className="k">Neckline</div><div className="v">{order.neckline}</div></div>
                  <div className="recap-item"><div className="k">Sleeve</div><div className="v">{order.sleeve}</div></div>
                  <div className="recap-item"><div className="k">Details</div><div className="v">{order.pattern}</div></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* SIDEBAR */}
        <div className="wizard-sidebar">
          <h3 className="sidebar-title">Your Order</h3>
          <p className="sidebar-sub">Summary so far</p>

          <div className="order-summary">
            <div className="summary-row"><span className="summary-key">Garment</span><span className="summary-val">{order.clothType || 'Not selected'}</span></div>
            <div className="summary-row"><span className="summary-key">Fit</span><span className="summary-val">{order.fit}</span></div>
            <div className="summary-row"><span className="summary-key">Neckline</span><span className="summary-val">{order.neckline}</span></div>
            <div className="summary-row"><span className="summary-key">Sleeve</span><span className="summary-val">{order.sleeve}</span></div>
            <div className="summary-row"><span className="summary-key">Material</span><span className="summary-val" style={{color: order.material ? 'var(--dark)' : 'var(--taupe)'}}>{order.material || 'Not selected'}</span></div>
          </div>

          <div className="price-preview">
            <h4>Estimated Price</h4>
            <div className="price-row"><span>Base price</span><span>LKR 2,200</span></div>
            <div className="price-row"><span>Stitching</span><span>LKR 350</span></div>
            <div className="price-row" style={{color:'#6b5040'}}><span>Material</span><span>{order.material ? 'LKR 6,210' : '—'}</span></div>
            <div className="price-row" style={{color:'#6b5040'}}><span>Delivery</span><span>LKR 350</span></div>
            <div className="price-total"><span>Total</span><span>{order.material ? 'LKR 9,110' : 'From LKR 2,900'}</span></div>
          </div>

          {step < 6 ? (
            <button className="btn-next" onClick={nextStep} disabled={step === 1 && !order.clothType}>
              Next — Step {step + 1} →
            </button>
          ) : (
            <button className="btn-confirm" onClick={handleConfirm} disabled={generating}>
              ✓ Confirm & Pay — LKR 9,110
            </button>
          )}

          {step > 1 && (
            <button className="btn-back" onClick={prevStep}>← Back</button>
          )}

          {step === 6 && (
            <div className="trust-badges">
              <div className="trust-item"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Secure payment via Stripe</div>
              <div className="trust-item"><svg viewBox="0 0 24 24"><rect x="1" y="3" width="22" height="18" rx="2"/><path d="M1 9h22"/></svg> Your card details are never stored</div>
              <div className="trust-item"><svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg> Delivery within 10 days, guaranteed</div>
            </div>
          )}

          {step < 5 && (
            <div className="measurements-hint">
              <p><strong>Good to know:</strong> Follow the steps to design your dream outfit online. Our AI will preview it for you.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
