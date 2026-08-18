import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

/**
 * Deliberately short. The storefront already explains the six-step process and
 * the AI preview on the home page, so repeating either here would just be a
 * second, staler copy to keep in sync.
 *
 * Photography is from Pexels, whose licence allows commercial use and
 * modification with no attribution required. Credited in docs/assets/CREDITS.md
 * anyway, because "not required" is not the same as "not worth doing".
 */
export default function About() {
  return (
    <>
      <div className="announce">FREE DELIVERY ON ORDERS OVER LKR 8,000 · 10-DAY DELIVERY GUARANTEE</div>
      <Navbar />

      <div className="page-header">
        <div className="page-header-eyebrow">About ThreadCraft</div>
        <h1>Made for one</h1>
        <div className="page-header-rule">
          <span>est. Colombo</span>
        </div>
        <p>
          Sri Lanka sews for the world. We thought it was time it sewed for you — one garment, cut
          to your measurements, designed by you online.
        </p>
      </div>

      {/* Same split as the home hero, so the two pages read as one site. */}
      <div className="hero" style={{ minHeight: 'auto' }}>
        <div className="hero-img">
          <img src="/img/about-atelier.jpg" alt="A tailor cutting cloth in a workshop" />
        </div>
        <div className="hero-content">
          <div className="hero-eyebrow">Why we exist</div>
          <h2
            style={{
              fontFamily: 'var(--serif)',
              fontSize: 38,
              fontWeight: 300,
              lineHeight: 1.2,
              marginBottom: 18,
            }}
          >
            Ready-to-wear fits
            <br />
            <em style={{ color: 'var(--brown)' }}>almost</em> nobody
          </h2>
          <p className="hero-sub">
            Off the rack assumes one set of proportions and hopes you match it. A tailor doesn&apos;t
            assume anything — they measure. ThreadCraft puts that on the internet: choose the
            garment, the cloth and the details, tell us your measurements, and see an AI preview
            before a single stitch is sewn.
          </p>
          <Link to="/design" className="btn-filled">
            Design yours
          </Link>
        </div>
      </div>

      <div className="sale-bar">Every garment cut to order · Nothing made until you confirm it</div>

      <div className="order-cta">
        <h2>How we work</h2>
        <p>
          Three commitments, and we would rather be judged on them than on adjectives.
        </p>
        <div className="steps-row">
          <div className="step-item">
            <div className="step-num">01</div>
            <div className="step-label">Your measurements</div>
            <div className="step-desc">
              Not a size. Save them once and every future order uses them.
            </div>
          </div>
          <div className="step-item">
            <div className="step-num">02</div>
            <div className="step-label">Priced in the open</div>
            <div className="step-desc">
              Cloth, stitching and delivery itemised before you commit — no estimate that changes.
            </div>
          </div>
          <div className="step-item">
            <div className="step-num">03</div>
            <div className="step-label">Seen before sewn</div>
            <div className="step-desc">
              An AI preview of your design, so nothing is cut on a guess.
            </div>
          </div>
        </div>
      </div>

      <div className="about-split">
        <figure className="about-figure">
          <img src="/img/about-measure.jpg" alt="A measuring tape draped over a dress form" />
          <figcaption>Measured, not sized</figcaption>
        </figure>
        <figure className="about-figure">
          <img src="/img/about-tailor.jpg" alt="A tailor at work among rolls of fabric" />
          <figcaption>Sewn by people, here</figcaption>
        </figure>
      </div>

      <div className="ai-banner">
        <div>
          <div className="ai-banner-label">★ The workshop</div>
          <h2>
            Local tailors,
            <br />
            <em>global standards</em>
          </h2>
          <p>
            Every ThreadCraft order is made by tailors in Sri Lanka and tracked through five stages
            — received, cut, stitched, checked, dispatched — so you always know where your garment
            is.
          </p>
          <Link
            to="/design"
            className="btn-outline"
            style={{ borderColor: 'var(--taupe)', color: 'var(--taupe)' }}
          >
            Start your order
          </Link>
        </div>
        <div className="ai-mockup-placeholder">
          <div className="about-stats">
            <div>
              <strong>10</strong>
              <span>days, design to door</span>
            </div>
            <div>
              <strong>8</strong>
              <span>garment types</span>
            </div>
            <div>
              <strong>5</strong>
              <span>tracked stages</span>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </>
  );
}
