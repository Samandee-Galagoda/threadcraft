import { Link } from 'react-router-dom';
import Footer from '../components/Footer';
import Navbar from '../components/Navbar';

export default function NotFound() {
  return (
    <>
      <Navbar />
      <div className="success-page">
        <div className="success-eyebrow">404</div>
        <h1 className="success-title">
          This page isn&apos;t
          <br />
          <em>in our catalogue</em>
        </h1>
        <p className="success-sub">
          The page you were looking for doesn&apos;t exist or has moved.
        </p>
        <div className="success-actions">
          <Link to="/" className="btn-primary">
            Back to home
          </Link>
          <Link to="/design" className="btn-secondary">
            Start designing
          </Link>
        </div>
      </div>
      <Footer />
    </>
  );
}
