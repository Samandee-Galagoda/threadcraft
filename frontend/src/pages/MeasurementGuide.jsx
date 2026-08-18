import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import BodyDiagram from '../components/BodyDiagram';
import { catalog } from '../api';

const TIPS = [
  ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'Wear light undergarments only — no bulky layers'],
  [
    'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
    'Ask someone to help — self-measuring reduces accuracy',
  ],
  ['M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18', 'Keep the tape snug — not tight, not loose'],
  ['M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 6v6l4 2', 'Stand straight and relaxed — do not hold your breath'],
  ['M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6', 'All measurements in centimetres'],
];

/**
 * The guide is driven by the catalogue, not by a copy of it.
 *
 * Every garment, its measurement fields, their letters, ranges and instructions
 * all come from the API — the same rows the wizard asks for and the same ones an
 * admin edits. A hardcoded copy would be wrong the first time a field changed,
 * and the previous version had already drifted: it listed a "Blouse" the shop
 * does not sell, and four of its nine tabs had no content at all.
 *
 * There are no inputs here. This page explains how to measure; the wizard is
 * where measurements are entered, and your account is where they are saved.
 */
export default function MeasurementGuide() {
  const [clothTypes, setClothTypes] = useState([]);
  const [activeSlug, setActiveSlug] = useState(null);
  const [activeLetter, setActiveLetter] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    catalog
      .clothTypes()
      .then((types) => {
        if (cancelled) return;
        setClothTypes(types);
        setActiveSlug(types[0]?.slug ?? null);
        setActiveLetter(types[0]?.measurement_fields?.[0]?.letter ?? null);
      })
      .catch((err) => !cancelled && setError(err.message || 'Could not load the guide.'));
    return () => {
      cancelled = true;
    };
  }, []);

  const active = useMemo(
    () => clothTypes.find((type) => type.slug === activeSlug) ?? null,
    [clothTypes, activeSlug],
  );
  const fields = active?.measurement_fields ?? [];

  function selectGarment(type) {
    setActiveSlug(type.slug);
    setActiveLetter(type.measurement_fields?.[0]?.letter ?? null);
  }

  return (
    <>
      <Navbar backLink />

      <div className="page-header">
        <div className="page-header-eyebrow">Custom clothing</div>
        <h1>Measurement Guide</h1>
        <div className="page-header-rule">
          <span>where the tape goes</span>
        </div>
        <p>
          Accurate measurements are the whole difference between made-to-measure and merely
          expensive. Use a soft tape, stand naturally, and pick your garment below — each one shows
          exactly which measurements it needs and where each starts and ends.
        </p>
      </div>

      <div className="tips-strip">
        {TIPS.map(([path, text]) => (
          <div className="tip-item" key={text}>
            <svg viewBox="0 0 24 24" strokeWidth="1.4" fill="none" strokeLinecap="round">
              <path d={path} />
            </svg>
            <span>{text}</span>
          </div>
        ))}
      </div>

      {error && <div className="wizard-error" style={{ margin: 32 }}>{error}</div>}

      <div className="cloth-tabs">
        {clothTypes.map((type) => (
          <button
            type="button"
            key={type.slug}
            className={`ctab ${type.slug === activeSlug ? 'active' : ''}`}
            onClick={() => selectGarment(type)}
          >
            {type.name}
          </button>
        ))}
      </div>

      {active && (
        <div className="panel active">
          <div className="chart-wrap">
            <div className="figure-col">
              <div className="figure-title">{active.name}</div>
              <div className="figure-date">
                {fields.length} measurement{fields.length === 1 ? '' : 's'}
              </div>

              <BodyDiagram
                slug={active.slug}
                fields={fields}
                activeLetter={activeLetter}
                onSelect={setActiveLetter}
              />

              <div className="figure-note">
                <div className="figure-note-label">How to use this guide</div>
                <p>
                  Each letter on the figure marks where a measurement begins and ends. Click a
                  letter — or a row in the table — to highlight the pair.
                </p>
              </div>
            </div>

            <div>
              <table className="meas-table">
                <thead>
                  <tr>
                    <th className="td-letter">#</th>
                    <th>Measurement &amp; how to take it</th>
                    <th className="td-range">Typical range</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map((field) => (
                    <tr
                      key={field.field_key}
                      className={field.letter === activeLetter ? 'active-row' : ''}
                      onClick={() => setActiveLetter(field.letter)}
                    >
                      <td className="td-letter">
                        <div className="letter-badge">{field.letter}</div>
                      </td>
                      <td className="td-label">
                        <strong>{field.label}</strong>
                        <span>{field.instructions}</span>
                      </td>
                      <td className="td-range">
                        <span className="range-val">
                          {Number(field.min_value)}–{Number(field.max_value)}
                        </span>
                        <span className="range-unit">{field.unit}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="table-footer">
                Nothing to fill in here — this page is the reference. You enter your measurements at{' '}
                <strong>Step 4</strong> of the design wizard, and once saved to your account every
                future order pre-fills from them.
              </div>

              <div className="guide-actions">
                <Link to="/design" className="btn-filled">
                  Start designing
                </Link>
                <Link to="/dashboard/measurements" className="btn-outline">
                  My saved measurements
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </>
  );
}
