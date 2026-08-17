import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ml } from '../../api';
import { useWizard } from '../../context/WizardContext';

/**
 * Step 4 surfaces both capabilities of the measurement model:
 *   - suggest  -> pre-fill the fields the customer hasn't measured
 *   - validate -> flag an entry that contradicts the rest of the profile
 *
 * Both are advisory. If the model is unavailable the step still works exactly
 * as a plain form, which is why every ML call here is wrapped and ignored on
 * failure.
 */
export default function StepMeasurements({ clothType, savedMeasurements }) {
  const { state, dispatch } = useWizard();
  const [suggesting, setSuggesting] = useState(false);
  const [suggested, setSuggested] = useState({});
  const [warnings, setWarnings] = useState([]);
  const [mlNote, setMlNote] = useState(null);
  const [sizeEstimate, setSizeEstimate] = useState(null);
  const sizeRequestRef = useRef(0);

  // Memoised so the `?? []` fallback doesn't create a fresh array each render,
  // which would re-trigger the validation callback every time.
  const fields = useMemo(() => clothType?.measurement_fields ?? [], [clothType]);
  const { profile, measurements } = state;

  const profileComplete = profile.height && profile.weight && profile.sex !== '';

  // Prefill from the signed-in customer's saved profile, once, and only for
  // fields they haven't already typed into.
  useEffect(() => {
    if (!savedMeasurements) return;
    const values = {};
    for (const field of fields) {
      const saved = savedMeasurements[field.field_key];
      if (saved && !measurements[field.field_key]) values[field.field_key] = saved;
    }
    if (Object.keys(values).length) dispatch({ type: 'SET_MEASUREMENTS', values });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedMeasurements, clothType?.id]);

  async function handleSuggest() {
    if (!profileComplete) return;
    setSuggesting(true);
    setMlNote(null);
    try {
      const payload = {
        height: Number(profile.height),
        weight: Number(profile.weight),
        sex: Number(profile.sex),
        ...(profile.age ? { age: Number(profile.age) } : {}),
      };
      // Send anything already measured so the prediction conditions on it.
      for (const field of fields) {
        const value = measurements[field.field_key];
        if (value !== '' && value != null) payload[field.field_key] = Number(value);
      }

      const response = await ml.suggestMeasurements(payload);
      if (!response.available) {
        setMlNote('Measurement suggestions are not available on this deployment.');
        return;
      }

      const values = {};
      for (const field of fields) {
        const prediction = response.suggestions[field.field_key];
        const alreadyEntered = measurements[field.field_key];
        if (prediction && (alreadyEntered === '' || alreadyEntered == null)) {
          values[field.field_key] = prediction.predicted_cm;
        }
      }
      setSuggested(response.suggestions);
      if (Object.keys(values).length) dispatch({ type: 'SET_MEASUREMENTS', values });
      setMlNote(response.note);
    } catch {
      setMlNote('Could not reach the measurement service — please enter values manually.');
    } finally {
      setSuggesting(false);
    }
  }

  const runValidation = useCallback(async () => {
    if (!profileComplete) return;
    const payload = {
      height: Number(profile.height),
      weight: Number(profile.weight),
      sex: Number(profile.sex),
      ...(profile.age ? { age: Number(profile.age) } : {}),
    };
    let anyMeasurement = false;
    for (const field of fields) {
      const value = measurements[field.field_key];
      if (value !== '' && value != null) {
        payload[field.field_key] = Number(value);
        anyMeasurement = true;
      }
    }
    if (!anyMeasurement) {
      setWarnings([]);
      return;
    }
    try {
      const response = await ml.validateMeasurements(payload);
      setWarnings(response.available ? response.warnings : []);
    } catch {
      setWarnings([]);
    }
  }, [profile, measurements, fields, profileComplete]);

  // Debounced so we aren't calling the API on every keystroke.
  useEffect(() => {
    const timer = setTimeout(runValidation, 700);
    return () => clearTimeout(timer);
  }, [runValidation]);

  const runSizeEstimate = useCallback(async () => {
    if (!profileComplete) {
      setSizeEstimate(null);
      return;
    }
    const payload = {
      height: Number(profile.height),
      weight: Number(profile.weight),
      sex: Number(profile.sex),
      ...(profile.age ? { age: Number(profile.age) } : {}),
    };
    // Anything already measured is sent, so it's used instead of a prediction.
    for (const key of ['chest', 'waist', 'hip']) {
      const value = measurements[key];
      if (value !== '' && value != null) payload[key] = Number(value);
    }
    // A stale slow response must not overwrite a fresh one — the request is
    // re-fired on every profile and measurement change.
    const seq = ++sizeRequestRef.current;
    try {
      const response = await ml.sizeEstimate(payload);
      if (seq === sizeRequestRef.current) setSizeEstimate(response.available ? response : null);
    } catch {
      if (seq === sizeRequestRef.current) setSizeEstimate(null);
    }
  }, [profile, measurements, profileComplete]);

  useEffect(() => {
    const timer = setTimeout(runSizeEstimate, 700);
    return () => clearTimeout(timer);
  }, [runSizeEstimate]);

  const warningFor = (key) => warnings.find((w) => w.field === key);

  return (
    <div>
      <h1 className="step-title">Your Measurements</h1>
      <p className="step-sub">Step 4 of 6 · All values in centimetres</p>

      <div className="form-section">
        <span className="form-label">About you</span>
        <p className="form-label-hint" style={{ marginBottom: 12 }}>
          Give us these four and we can estimate the rest for you.
        </p>
        <div className="field-row">
          <div className="field">
            <label htmlFor="p-height">Height (cm)</label>
            <input
              id="p-height"
              type="number"
              value={profile.height}
              onChange={(e) => dispatch({ type: 'SET_PROFILE', values: { height: e.target.value } })}
            />
          </div>
          <div className="field">
            <label htmlFor="p-weight">Weight (kg)</label>
            <input
              id="p-weight"
              type="number"
              value={profile.weight}
              onChange={(e) => dispatch({ type: 'SET_PROFILE', values: { weight: e.target.value } })}
            />
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor="p-age">Age</label>
            <input
              id="p-age"
              type="number"
              value={profile.age}
              onChange={(e) => dispatch({ type: 'SET_PROFILE', values: { age: e.target.value } })}
            />
          </div>
          <div className="field">
            <label htmlFor="p-sex">Sizing basis</label>
            <select
              id="p-sex"
              value={profile.sex}
              onChange={(e) => dispatch({ type: 'SET_PROFILE', values: { sex: e.target.value } })}
            >
              <option value="">Select…</option>
              <option value="0">Women&apos;s</option>
              <option value="1">Men&apos;s</option>
            </select>
          </div>
        </div>

        <button
          type="button"
          className="btn-outline-sm"
          disabled={!profileComplete || suggesting}
          onClick={handleSuggest}
        >
          {suggesting ? 'Estimating…' : '✦ Estimate my measurements'}
        </button>
        {!profileComplete && (
          <p className="form-label-hint">
            Enter height, weight and sizing basis to enable estimates.
          </p>
        )}
        {mlNote && <p className="ai-note">{mlNote}</p>}
      </div>

      {/* Replaces the withdrawn size recommender. The trained model estimates
          chest/waist/hip; a UK chart turns those into a band. Both halves are
          monotonic in body size, so this cannot produce the inverted answers
          that got the previous model pulled. */}
      {sizeEstimate && (
        <div className="form-section">
          <div className="ai-hint">
            <strong>Off the rack you&apos;d be about a {sizeEstimate.size}</strong>
            {sizeEstimate.detail && <> — {sizeEstimate.detail}</>}
            <div className="size-basis">
              {['chest', 'waist', 'hip']
                .filter((key) => sizeEstimate.basis[key])
                .map((key) => {
                  const item = sizeEstimate.basis[key];
                  return (
                    <span key={key}>
                      {key} {item.value_cm} cm
                      {/* ± is shown only for predicted values, so the customer
                          can see which numbers came from a model. */}
                      {item.source === 'predicted' && item.confidence_cm
                        ? ` ±${item.confidence_cm}`
                        : ''}
                      {item.source === 'measured' ? ' (yours)' : ''}
                    </span>
                  );
                })}
            </div>
          </div>
          <p className="ai-note">{sizeEstimate.note}</p>
        </div>
      )}

      <div className="form-section">
        <span className="form-label">{clothType?.name} measurements</span>
        {fields.length === 0 && (
          <p className="form-label-hint">
            No measurement fields are configured for this garment yet.
          </p>
        )}

        {fields.map((field) => {
          const warning = warningFor(field.field_key);
          const estimate = suggested[field.field_key];
          return (
            <div className="meas-field" key={field.id}>
              <div className="meas-field-head">
                <label htmlFor={`m-${field.field_key}`}>
                  {field.letter && <span className="letter-badge">{field.letter}</span>}
                  {field.label}
                  {field.is_required && <span className="required">*</span>}
                </label>
                <span className="meas-range">
                  {Number(field.min_value)}–{Number(field.max_value)} {field.unit}
                </span>
              </div>
              <input
                id={`m-${field.field_key}`}
                type="number"
                step="0.1"
                min={Number(field.min_value)}
                max={Number(field.max_value)}
                className={warning ? 'has-warning' : ''}
                value={measurements[field.field_key] ?? ''}
                onChange={(e) =>
                  dispatch({ type: 'SET_MEASUREMENT', field: field.field_key, value: e.target.value })
                }
              />
              {estimate && (
                <div className="meas-estimate">
                  Estimated {estimate.predicted_cm} cm — edit if you&apos;ve measured
                </div>
              )}
              {warning && <div className="meas-warning">⚠ {warning.message}</div>}
              {field.instructions && <p className="meas-help">{field.instructions}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
