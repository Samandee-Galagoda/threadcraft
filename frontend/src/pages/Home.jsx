import { useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import CatalogueModal from '../components/CatalogueModal';

export default function Home() {
  const [catalogueOpen, setCatalogueOpen] = useState(false);

  return (
    <>
      <div className="announce">FREE DELIVERY ON ORDERS OVER LKR 8,000 · 10-DAY DELIVERY GUARANTEE</div>
      <Navbar />

      {/* HERO */}
      <div className="hero">
        <div className="hero-img">
          <img src="/img/hero.jpg" alt="Sewing thread and needles" />
        </div>
        <div className="hero-content">
          <div className="hero-eyebrow">Your Design, Stitched to Perfection</div>
          <h1 className="hero-title">WEAR<br/>YOUR<br/>VISION</h1>
          <p className="hero-sub">Design your custom garment online.<br/>Preview it with AI. Delivered in 10 days.</p>
          <div style={{display:'flex',gap:'16px',flexWrap:'wrap'}}>
            <Link to="/design" className="btn-filled">Start designing</Link>
            <Link to="/how-it-works" className="btn-outline">How it works</Link>
          </div>
        </div>
      </div>

      <div className="sale-bar">Introducing AI Mockup Preview — See Your Design Before We Stitch It</div>

      {/* START YOUR ORDER */}
      <div className="order-cta">
        <h2>From Idea to Garment — In Six Steps</h2>
        <p>No tailor visits required. Design your custom clothing completely online and receive an AI-generated preview before we stitch a single thread.</p>
        <div className="steps-row">
          <div className="step-item"><div className="step-num">01</div><div className="step-label">Cloth Type</div><div className="step-desc">Select your garment</div></div>
          <div className="step-item"><div className="step-num">02</div><div className="step-label">Design</div><div className="step-desc">Tags, description & images</div></div>
          <div className="step-item"><div className="step-num">03</div><div className="step-label">Material</div><div className="step-desc">Fabric & colour</div></div>
          <div className="step-item"><div className="step-num">04</div><div className="step-label">Measure</div><div className="step-desc">Your exact body size</div></div>
          <div className="step-item"><div className="step-num">05</div><div className="step-label">Pricing</div><div className="step-desc">Full transparent breakdown</div></div>
          <div className="step-item"><div className="step-num">06</div><div className="step-label">AI Preview</div><div className="step-desc">See it. Confirm. Pay.</div></div>
        </div>
        <Link to="/design" className="btn-filled">Begin your order</Link>
      </div>

      {/* CLOTH TYPES */}
      <div className="section-header">
        <h2>What Would You Like to Create?</h2>
        <p>Choose your garment · We do the rest</p>
      </div>
      <div className="cloth-grid">
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-1">
            <img src="/img/tshirt.jpg" alt="T‑shirt" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>T‑shirt</h3><p>Casual wear</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-2">
            <img src="/img/shirt.jpg" alt="Shirt" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Shirt</h3><p>Formal · semi‑formal</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-3">
            <img src="/img/dress.jpg" alt="Dress" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Dress</h3><p>Full · midi · mini</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-4">
            <img src="/img/trouser.jpg" alt="Trousers" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Trousers</h3><p>Formal · casual</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-5">
            <img src="/img/kurta.jpg" alt="Kurta" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Kurta</h3><p>Traditional tunic</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-6">
            <img src="/img/saree-blouse.jpg" alt="Saree Blouse" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Saree Blouse</h3><p>Fitted blouse</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-7">
            <img src="/img/salwar-kameez.jpg" alt="Salwar Kameez" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Salwar Kameez</h3><p>Traditional suit</p></div>
        </Link>
        <Link to="/design" className="cloth-card">
          <div className="cloth-card-bg cloth-card-bg-8">
            <img src="/img/skirt.jpg" alt="Skirt" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div className="cloth-overlay"><h3>Skirt</h3><p>A‑line · straight</p></div>
        </Link>
      </div>

      {/* AI BANNER */}
      <div className="ai-banner">
        <div>
          <div className="ai-banner-label">★ AI Feature</div>
          <h2>See Your Design <em>Before</em> We Stitch It</h2>
          <p>Our AI mockup generator creates a photorealistic preview of your garment from your description and style choices. If you love it, we stitch it. Powered by Stable Diffusion XL.</p>
          <Link to="/design" className="btn-outline" style={{borderColor:'var(--taupe)',color:'var(--taupe)'}}>Try the designer</Link>
        </div>
        <div className="ai-mockup-placeholder">
          <svg viewBox="0 0 64 64"><rect x="8" y="8" width="48" height="48" rx="4" strokeWidth="1.5"/><circle cx="22" cy="26" r="5" strokeWidth="1.5"/><path d="M8 44l12-12 10 10 8-10 18 12" strokeWidth="1.5" fill="none"/></svg>
          <p>AI-generated mockup preview</p>
          <div style={{fontSize:'10px',letterSpacing:'.15em',color:'#6b5040',textTransform:'uppercase'}}>Your design will appear here</div>
        </div>
      </div>

      {/* MATERIALS */}
      <div className="materials">
        <div className="section-header" style={{padding:'0 0 36px'}}>
          <h2>Premium Fabrics</h2>
          <p>Select from our curated material collection</p>
        </div>
        <div className="mat-grid">
          <div className="mat-item"><div className="mat-swatch" style={{background:'#f5ede0'}}></div><div className="mat-name">Cotton</div></div>
          <div className="mat-item"><div className="mat-swatch" style={{background:'#e8ddd0'}}></div><div className="mat-name">Linen</div></div>
          <div className="mat-item"><div className="mat-swatch" style={{background:'linear-gradient(135deg,#e8ddf0,#d4c8e8)'}}></div><div className="mat-name">Silk</div></div>
          <div className="mat-item"><div className="mat-swatch" style={{background:'linear-gradient(135deg,#f0ece8,#e4dcd4)'}}></div><div className="mat-name">Chiffon</div></div>
          <div className="mat-item"><div className="mat-swatch" style={{background:'linear-gradient(135deg,#dce8f0,#c8d8e8)'}}></div><div className="mat-name">Satin</div></div>
          <div className="mat-item"><div className="mat-swatch" style={{background:'linear-gradient(135deg,#d8e0d8,#c4d0c4)'}}></div><div className="mat-name">Denim</div></div>
          <div className="mat-item"><div className="mat-swatch" style={{background:'linear-gradient(135deg,#f0e4e8,#e4d0d4)'}}></div><div className="mat-name">Velvet</div></div>
        </div>
        <div style={{textAlign:'center'}}><button type="button" className="btn-outline" onClick={() => setCatalogueOpen(true)}>View full catalogue</button></div>
      </div>

      <Footer />
      {catalogueOpen && <CatalogueModal onClose={() => setCatalogueOpen(false)} />}
    </>
  );
}
