import { useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const MEASUREMENT_DATA = {
  dress: {
    title: "DRESS — 7 MEASUREMENTS",
    measurements: [
      { letter: "A", name: "Bust", desc: "Wrap the tape around the fullest part of your chest, under your arms and across your shoulder blades. Keep the tape horizontal all the way around. Wear your regular everyday bra — not a sports bra or push-up.", range: "65–145", min: 65, max: 145 },
      { letter: "B", name: "Waist", desc: "Measure around your natural waist — the narrowest part of your torso, approximately 2–4 cm above your belly button. Breathe out normally before measuring. Do not suck in.", range: "50–130", min: 50, max: 130 },
      { letter: "C", name: "Hip", desc: "Measure around the fullest part of your hips and seat, approximately 18–23 cm below your natural waist. Stand with feet together. Keep the tape horizontal and level all the way around.", range: "70–155", min: 70, max: 155 },
      { letter: "D", name: "Shoulder width", desc: "Measure straight across the back from the tip of your right shoulder bone to the tip of your left shoulder bone. The end point is the small bony protrusion at the very edge of each shoulder.", range: "28–60", min: 28, max: 60 },
      { letter: "E", name: "Total dress length", desc: "Measure from the highest point of your shoulder (near your neck) straight down your body to where you want the hem to fall. Stand without shoes. Mini ≈ 80 cm · Midi ≈ 105 cm · Maxi ≈ 140 cm.", range: "40–165", min: 40, max: 165 },
      { letter: "F", name: "Sleeve length", desc: "Measure from the shoulder seam point along the outside of your arm to where you want the sleeve to end. Enter 0 for sleeveless. Short sleeve ≈ 18–25 cm. Long sleeve ≈ 58–66 cm.", range: "0–72", min: 0, max: 72 },
      { letter: "G", name: "Neckline depth", desc: "Measure from the highest shoulder point straight down to the lowest point of the neckline opening. Round neck ≈ 5 cm. V-neck ≈ 12–16 cm. Deep V ≈ 18–22 cm.", range: "4–22", min: 4, max: 22 }
    ]
  },
  tshirt: {
    title: "T-SHIRT — 4 MEASUREMENTS",
    measurements: [
      { letter: "A", name: "Chest circumference", desc: "Wrap tape around the fullest part of your chest, under your arms. Keep the tape horizontal all the way around. Slip two fingers underneath to ensure it is not too tight.", range: "60–140", min: 60, max: 140 },
      { letter: "B", name: "Shoulder width", desc: "Measure from shoulder bone tip to tip across the back. Ask someone to help — this is difficult to measure on yourself. The point is the small bony protrusion at the very edge of each shoulder.", range: "28–60", min: 28, max: 60 },
      { letter: "C", name: "Body length", desc: "From the highest shoulder point (near the neck) straight down to where you want the hem. For a regular t-shirt this is typically at the hip — approximately 65–75 cm from the shoulder.", range: "50–90", min: 50, max: 90 },
      { letter: "D", name: "Sleeve length", desc: "From the shoulder seam point along the outside of your arm to where the sleeve ends. Short sleeve ≈ 18–25 cm. Long sleeve ≈ 58–68 cm. Enter 0 for sleeveless/tank top style.", range: "0–70", min: 0, max: 70 }
    ]
  },
  shirt: {
    title: "SHIRT — 6 MEASUREMENTS",
    measurements: [
      { letter: "A", name: "Chest circumference", desc: "Around the fullest part of your chest, tape horizontal under the arms and across the shoulder blades. Add 4 cm ease for regular fit — we do this automatically based on your fit tag selection.", range: "70–150", min: 70, max: 150 },
      { letter: "B", name: "Shoulder width", desc: "Across the back from shoulder bone tip to tip. This is the most critical shirt measurement — if the shoulder seam does not sit at your shoulder edge, nothing else will fit correctly.", range: "32–62", min: 32, max: 62 },
      { letter: "C", name: "Shirt length", desc: "High point of shoulder at back of neck to where the hem falls. For a tucked shirt add 12–15 cm to ensure enough fabric stays tucked when you move or reach upward.", range: "60–95", min: 60, max: 95 },
      { letter: "D", name: "Sleeve length", desc: "Shoulder seam to wrist bone with your arm slightly bent at 90 degrees. Always measure with the elbow bent — a straight arm will give a measurement that is too short.", range: "15–72", min: 15, max: 72 },
      { letter: "E", name: "Collar circumference", desc: "Around the base of your neck where the collar sits. Slide one finger between the tape and your neck — a collar that fits at rest will feel tight all day if it has no ease.", range: "30–52", min: 30, max: 52 },
      { letter: "F", name: "Cuff circumference", desc: "Around your wrist bone. For French cuffs add 2 cm for cufflinks. Your cuff should button comfortably — not so loose it slides around, and not so tight it leaves marks.", range: "18–32", min: 18, max: 32 }
    ]
  },
  skirt: {
    title: "SKIRT — 4 MEASUREMENTS",
    measurements: [
      { letter: "A", name: "Waist circumference", desc: "Measure around your body at the exact point where the waistband will sit. For high-waist this is your natural waist. For mid-rise measure 4–5 cm lower. Decide first, then measure at that point.", range: "50–130", min: 50, max: 130 },
      { letter: "B", name: "Hip circumference", desc: "Around the fullest part of your hips and seat, approximately 18–23 cm below your natural waist. Stand with feet together. This is especially important for A-line and pencil skirts.", range: "70–155", min: 70, max: 155 },
      { letter: "C", name: "Skirt length", desc: "From the top of the waistband straight down to where you want the hem. Stand without shoes. Mini ≈ 40 cm · Knee ≈ 57 cm · Midi ≈ 80 cm · Maxi ≈ 110 cm.", range: "25–120", min: 25, max: 120 },
      { letter: "D", name: "Hem circumference", desc: "For pencil and straight-cut skirts only — measure around your hips at the level where the hem will sit. Take a normal stride and ensure it is wide enough. For A-line/circle skirts enter 0.", range: "60–300", min: 0, max: 300 }
    ]
  },
  trousers: {
    title: "TROUSERS — 7 MEASUREMENTS",
    measurements: [
      { letter: "A", name: "Waist circumference", desc: "Measure where the waistband will sit — high waist at natural waist, mid-rise 4 cm lower, low-rise 8 cm lower. Measure at that exact point, not at the natural waist for all styles.", range: "50–135", min: 50, max: 135 },
      { letter: "B", name: "Hip circumference", desc: "Around the fullest part of your hips and seat, approximately 18–23 cm below your natural waist. This is the most critical trouser measurement — too small and you cannot pull them on.", range: "70–160", min: 70, max: 160 },
      { letter: "C", name: "Inseam length", desc: "From the crotch seam along the inside of the leg to your ankle bone. Easiest measured on a well-fitting pair of trousers you own — measure the inside seam from crotch point to hem.", range: "50–100", min: 50, max: 100 },
      { letter: "D", name: "Outseam length", desc: "From the top of the waistband down the outside of the leg to the hem. This includes the waistband and is always longer than the inseam. Outseam = inseam + rise.", range: "80–130", min: 80, max: 130 },
      { letter: "E", name: "Thigh circumference", desc: "Around the fullest part of your upper thigh, approximately 3 cm below the crotch. Keep the tape snug but not compressing. For slim fit add 4–6 cm ease — applied automatically.", range: "40–100", min: 40, max: 100 },
      { letter: "F", name: "Knee circumference", desc: "Around the knee cap, taken with the leg slightly bent. For very slim trousers, ensure this measurement allows enough room to walk and sit comfortably.", range: "30–60", min: 30, max: 60 },
      { letter: "G", name: "Leg opening", desc: "Around the hem. For slim trousers ≈ 32–36 cm, straight ≈ 38–44 cm, wide leg ≈ 50+ cm. Ensure the opening is wide enough to fit your foot through.", range: "25–60", min: 25, max: 60 }
    ]
  }
};

const TABS = [
  { id: 'dress', label: 'Dress' },
  { id: 'tshirt', label: 'T-shirt' },
  { id: 'shirt', label: 'Shirt' },
  { id: 'blouse', label: 'Blouse' },
  { id: 'skirt', label: 'Skirt' },
  { id: 'trousers', label: 'Trousers' },
  { id: 'kurta', label: 'Kurta' },
  { id: 'saree', label: 'Saree Blouse' },
  { id: 'salwar', label: 'Salwar Kameez' },
];

export default function MeasurementGuide() {
  const [activeTab, setActiveTab] = useState('dress');
  const [activeRow, setActiveRow] = useState('A');

  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
    setActiveRow('A'); // Reset active row when changing tabs
  };

  const data = MEASUREMENT_DATA[activeTab];

  return (
    <>
      <Navbar />

      {/* PAGE HEADER */}
      <div className="page-header">
        <div className="page-header-eyebrow">Step 4 of 6 — Custom Clothing</div>
        <h1>Measurement Guide</h1>
        <div className="page-header-rule"><span>✦</span></div>
        <p>Accurate measurements ensure a perfect fit. Use a soft measuring tape and stand naturally. All measurements are in centimetres. Select your garment type below to see the required measurements.</p>
      </div>

      {/* TIPS STRIP */}
      <div className="tips-strip">
        <div className="tip-item">
          <svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <span>Wear light undergarments only — no bulky layers</span>
        </div>
        <div className="tip-item">
          <svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <span>Ask someone to help — self-measuring reduces accuracy</span>
        </div>
        <div className="tip-item">
          <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>
          <span>Keep tape snug — not tight, not loose</span>
        </div>
        <div className="tip-item">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span>Stand straight and relaxed — do not hold breath</span>
        </div>
        <div className="tip-item">
          <svg viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          <span>All measurements in centimetres (cm)</span>
        </div>
      </div>

      {/* CLOTH TYPE TABS */}
      <div className="cloth-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`ctab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => handleTabClick(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* PANEL WRAPPER */}
      <div className="panel active">
        {data ? (
          <div className="chart-wrap">
            {/* BODY FIGURE */}
            <div className="figure-col">
              <div className="figure-title">Measurement Chart</div>
              <div className="figure-date">{data.title}</div>
              
              <div className="img-crop-container">
                <img src="/img/measurement-guide.jpg" className="body-img" alt="Body Diagram" />
              </div>

              <div style={{marginTop: '20px', padding: '14px 16px', border: '.5px solid var(--sand)', background: 'var(--warm)'}}>
                <div style={{fontSize: '9px', letterSpacing: '.2em', textTransform: 'uppercase', color: 'var(--taupe)', marginBottom: '8px'}}>How to use this guide</div>
                <p style={{fontSize: '11px', color: 'var(--text)', lineHeight: 1.7}}>Click any row in the table to highlight its description. Enter your measurements in the Value column — they save automatically to your account.</p>
              </div>
            </div>

            {/* MEASUREMENT TABLE */}
            <div>
              <table className="meas-table">
                <thead>
                  <tr>
                    <th className="td-letter">#</th>
                    <th>Measurement &amp; how to take it</th>
                    <th className="td-range">Range</th>
                    <th className="td-input" style={{textAlign: 'center'}}>Value (cm)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.measurements.map((meas) => (
                    <tr
                      key={meas.letter}
                      className={activeRow === meas.letter ? 'active-row' : ''}
                      onClick={() => setActiveRow(meas.letter)}
                    >
                      <td className="td-letter">
                        <div className="letter-badge">{meas.letter}</div>
                      </td>
                      <td className="td-label">
                        <strong>{meas.name}</strong>
                        <span>{meas.desc}</span>
                      </td>
                      <td className="td-range">
                        <span className="range-val">{meas.range}</span>
                        <span className="range-unit">cm</span>
                      </td>
                      <td className="td-input">
                        <input type="number" placeholder="—" min={meas.min} max={meas.max} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="sig-box">
                <div className="sig-label">Customer signature</div>
                <div className="sig-line"></div>
              </div>
              <div className="notes-box">
                <div className="notes-label">Notes</div>
                <div className="notes-lines">
                  <div></div>
                  <div></div>
                  <div></div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{textAlign: 'center', padding: '100px 0', color: 'var(--taupe)'}}>
            Measurements for this garment type are coming soon.
          </div>
        )}
      </div>

      <Footer />
    </>
  );
}
