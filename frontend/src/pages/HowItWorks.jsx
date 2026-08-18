import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

/**
 * The six wizard steps, explained properly.
 *
 * The home page lists them as six words; this is where each one is actually
 * described. Kept as static copy rather than driven off the catalogue: it
 * explains the *process*, which doesn't change when a garment is added, and
 * making it dynamic would mean the marketing page breaking whenever the API is
 * cold.
 */
const STEPS = [
  {
    num: '01',
    title: 'Cloth type',
    image: '/img/tshirt.jpg',
    alt: 'Folded garments on a rail',
    lead: 'Pick what you want made.',
    body: 'Eight garments to begin with — t-shirt, shirt, dress, trousers, kurta, saree blouse, salwar kameez and skirt. Each one carries its own measurements, its own design options and its own fabric requirement, so choosing here shapes every step that follows.',
    detail: 'New garments are added by our team without touching the site, so the list grows.',
  },
  {
    num: '02',
    title: 'Design',
    image: '/img/step-design.jpg',
    alt: 'Garment sketches pinned beside fabric samples',
    lead: 'Tell us how it should look.',
    body: 'Choose fit, neckline, sleeve and pattern from the options that suit your garment. Add a description in your own words, and upload reference photos if you have a picture in mind — a screenshot, a photo of something you already own, anything.',
    detail: 'Upload a reference photo and we will suggest the garment type from it.',
  },
  {
    num: '03',
    title: 'Material',
    image: '/img/step-material.jpg',
    alt: 'Fabric swatches pinned to a board',
    lead: 'Choose the cloth and the colour.',
    body: 'Cotton, linen, silk, chiffon, satin, denim and velvet, each in several colourways. Prices are per metre and shown as you choose, so a fabric that costs more tells you so before you pick it rather than at checkout.',
    detail: 'Anything out of stock is disabled rather than quietly failing later.',
  },
  {
    num: '04',
    title: 'Measure',
    image: '/img/measurement-guide.jpg',
    alt: 'A measuring tape',
    lead: 'Your measurements, not a size.',
    body: 'Enter the measurements your chosen garment needs — the wizard asks only for those. Our measurement guide shows exactly where to put the tape for each one, and if a number looks inconsistent with the rest we will flag it before it becomes a badly cut garment.',
    detail: 'Only know your height and weight? We can estimate the rest as a starting point.',
  },
  {
    num: '05',
    title: 'Pricing',
    image: '/img/step-pricing.jpg',
    alt: 'Fabric swatches laid out with a tablet',
    lead: 'The full breakdown, before you commit.',
    body: 'Base price, stitching, every design option that carries a premium, the exact metres of cloth your measurements require, and delivery. Itemised, updating as you change your mind, and calculated on our side so the figure you agree to is the figure you pay.',
    detail: 'Delivery is free over LKR 8,000.',
  },
  {
    num: '06',
    title: 'AI preview',
    image: '/img/step-preview.jpg',
    alt: 'Fabric samples beside sketches in an atelier',
    lead: 'See it before it is sewn.',
    body: 'Your choices are turned into a description and rendered as an image, so you get a sense of the finished garment before anyone cuts cloth. Confirm, pay, and we begin — or go back and change something first.',
    detail: 'The preview is an impression, not a photograph of the finished garment.',
  },
];

export default function HowItWorks() {
  return (
    <>
      <div className="announce">
        FREE DELIVERY ON ORDERS OVER LKR 8,000 · 10-DAY DELIVERY GUARANTEE
      </div>
      <Navbar />

      <div className="page-header">
        <div className="page-header-eyebrow">How it works</div>
        <h1>Six steps</h1>
        <div className="page-header-rule">
          <span>design to door in ten days</span>
        </div>
        <p>
          Everything happens online until the moment a tailor picks up the cloth. Here is what each
          step actually asks of you, and what we do with it.
        </p>
      </div>

      {STEPS.map((step, index) => (
        <section className={`hiw-row ${index % 2 ? 'reverse' : ''}`} key={step.num}>
          <div className="hiw-row-img">
            <img src={step.image} alt={step.alt} loading="lazy" />
          </div>
          <div className="hiw-row-copy">
            <div className="hiw-row-num">{step.num}</div>
            <h2>{step.title}</h2>
            <p className="hiw-row-lead">{step.lead}</p>
            <p>{step.body}</p>
            <p className="hiw-row-detail">{step.detail}</p>
          </div>
        </section>
      ))}

      <div className="order-cta">
        <h2>After you confirm</h2>
        <p>
          Your order moves through five tracked stages, and you can follow it at any time from your
          order number — no need to ask us where it is.
        </p>
        <div className="steps-row">
          {[
            ['Received', 'We have your order and your measurements'],
            ['Fabric cut', 'Your cloth is cut to your numbers'],
            ['Stitching', 'The garment is being made'],
            ['QC check', 'Checked against your measurements'],
            ['Dispatched', 'On its way to you'],
          ].map(([label, desc]) => (
            <div className="step-item" key={label}>
              <div className="step-label">{label}</div>
              <div className="step-desc">{desc}</div>
            </div>
          ))}
        </div>
        <Link to="/design" className="btn-filled">
          Start designing
        </Link>
      </div>

      <Footer />
    </>
  );
}
