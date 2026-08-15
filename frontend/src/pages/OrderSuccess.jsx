import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';

export default function OrderSuccess() {
  const navigate = useNavigate();

  return (
    <>
      <Navbar secure={true} />
      <div className="success-page">
        <div className="success-icon">
          <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div className="success-eyebrow">Order Confirmed</div>
        <h1 className="success-title">Your garment is<br/><em style={{fontStyle:'italic', color:'var(--brown)'}}>on its way</em></h1>
        <p className="success-sub">Thank you for your order. We have sent a confirmation email to <strong>samandee@email.com</strong> with your AI mockup image and full order details. Our team will begin stitching within 24 hours.</p>

        <div className="success-mockup">
          <svg viewBox="0 0 64 64"><rect x="8" y="8" width="48" height="48" rx="4" strokeWidth="1.5"/><circle cx="22" cy="26" r="5" strokeWidth="1.5"/><path d="M8 44l12-12 10 10 8-10 18 12" strokeWidth="1.5" fill="none"/></svg>
          <div className="success-mockup-label">Your AI mockup — also in your email</div>
        </div>

        <div className="order-num">Order #TC-2026-00142</div>

        <div className="timeline-strip">
          <div className="tl-item active"><div className="tl-dot"></div><div className="tl-label">Received</div></div>
          <div className="tl-item"><div className="tl-dot"></div><div className="tl-label">Fabric cut</div></div>
          <div className="tl-item"><div className="tl-dot"></div><div className="tl-label">Stitching</div></div>
          <div className="tl-item"><div className="tl-dot"></div><div className="tl-label">QC check</div></div>
          <div className="tl-item"><div className="tl-dot"></div><div className="tl-label">Dispatched</div></div>
        </div>

        <div className="success-actions">
          <button className="btn-primary">Track my order</button>
          <button className="btn-secondary" onClick={() => navigate('/design')}>Design another</button>
        </div>
      </div>
    </>
  );
}
