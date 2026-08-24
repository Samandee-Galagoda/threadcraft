import { useEffect, useRef } from 'react';

/**
 * Small dialog listing why the customer can't move on yet.
 *
 * Deliberately a popup rather than only inline text: the Next button lives in
 * the sidebar, often a screen away from the field that's empty, so an inline
 * message under that field can be scrolled out of sight at the moment it
 * matters. The inline messages stay too — this is the nudge, they are the
 * reference.
 */
export default function ValidationPopup({ title, problems, onClose }) {
  const okRef = useRef(null);

  useEffect(() => {
    okRef.current?.focus();
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="vpop-backdrop" role="presentation" onClick={onClose}>
      <div
        className="vpop-card"
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="vpop-head">
          <span className="vpop-icon" aria-hidden="true">
            !
          </span>
          <h4>{title}</h4>
        </div>

        {problems.length === 1 ? (
          <p className="vpop-single">{problems[0]}</p>
        ) : (
          <ul className="vpop-list">
            {problems.map((problem, index) => (
              // Index-keyed: two option groups can share a label, and so a message.
              <li key={index}>{problem}</li>
            ))}
          </ul>
        )}

        <button type="button" className="vpop-ok" ref={okRef} onClick={onClose}>
          Got it
        </button>
      </div>
    </div>
  );
}
