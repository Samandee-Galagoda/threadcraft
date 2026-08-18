import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <>
      <footer>
        <div className="footer-brand">
          <h3>THREADCRAFT</h3>
          <p>Sri Lanka's first AI-powered custom clothing platform. Designed online, stitched with care, delivered to your door.</p>
        </div>
        <div className="footer-col">
          <h4>Design</h4>
          <ul>
            <li>Start designing</li><li>Cloth types</li><li>Materials</li><li>How it works</li>
          </ul>
        </div>
        <div className="footer-col">
          <h4>Orders</h4>
          <ul>
            <li>Track my order</li><li>Order history</li><li>Delivery info</li><li>Returns policy</li>
          </ul>
        </div>
        <div className="footer-col">
          <h4>Company</h4>
          <ul>
            <li><Link to="/about">About us</Link></li><li>Contact</li><li>Privacy policy</li><li>Terms of service</li>
          </ul>
        </div>
      </footer>
      <div className="footer-bottom">© 2026 ThreadCraft · Custom Clothing · Sri Lanka · All rights reserved</div>
    </>
  );
}
