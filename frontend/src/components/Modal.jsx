import { useEffect } from 'react';

/**
 * Generic dialog, used by both the admin panel and the storefront.
 *
 * It started as the admin's Reprice/Colours editor — those were inline, which
 * pushed the whole material list around every time one opened, moving the row
 * you were editing out from under the cursor. Nothing about it is
 * admin-specific, so it lives here rather than under components/admin.
 */
export default function Modal({ title, subtitle, onClose, children }) {
  // Escape closes, matching every other dialog the customer side uses.
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
      {/* Stop propagation so a click inside the card doesn't dismiss it. */}
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>{title}</h3>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
