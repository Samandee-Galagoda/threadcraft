import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import StepCloth from '../components/wizard/StepCloth';
import StepDesign from '../components/wizard/StepDesign';
import StepMaterial from '../components/wizard/StepMaterial';
import StepMeasurements from '../components/wizard/StepMeasurements';
import StepMockup from '../components/wizard/StepMockup';
import StepPricing from '../components/wizard/StepPricing';
import { catalog, dashboard, mockup as mockupApi, orders, pricing } from '../api';
import { useAuth } from '../context/AuthContext';
import { resetWizard, useWizard } from '../context/WizardContext';
import { TOTAL_STEPS, highestUnlockedStep, isStepComplete } from '../lib/wizardReducer';

const STEP_LABELS = ['Cloth', 'Design', 'Material', 'Measure', 'Pricing', 'AI Preview'];

export default function DesignWizard() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { state, dispatch } = useWizard();

  const [clothTypes, setClothTypes] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [catalogError, setCatalogError] = useState(null);
  const [catalogLoading, setCatalogLoading] = useState(true);

  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState(null);

  const [generating, setGenerating] = useState(false);
  const [mockupError, setMockupError] = useState(null);

  const [savedMeasurements, setSavedMeasurements] = useState(null);
  const [placing, setPlacing] = useState(false);
  const [placeError, setPlaceError] = useState(null);
  const [guestEmail, setGuestEmail] = useState('');

  const clothType = useMemo(
    () => clothTypes.find((c) => c.id === state.clothTypeId) ?? null,
    [clothTypes, state.clothTypeId],
  );
  const material = useMemo(
    () => materials.find((m) => m.id === state.materialId) ?? null,
    [materials, state.materialId],
  );
  const colour = useMemo(
    () => material?.colors?.find((c) => c.id === state.materialColorId) ?? null,
    [material, state.materialColorId],
  );

  // ── Catalogue ───────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [types, mats] = await Promise.all([catalog.clothTypes(), catalog.materials()]);
        if (cancelled) return;
        setClothTypes(types);
        setMaterials(mats);
      } catch (err) {
        if (!cancelled) setCatalogError(err.message || 'Could not load the catalogue.');
      } finally {
        if (!cancelled) setCatalogLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Prefill measurements for a signed-in customer.
  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    dashboard
      .load()
      .then((data) => {
        if (!cancelled && data.measurements) setSavedMeasurements(data.measurements);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  // ── Live pricing ────────────────────────────────────────────────────────
  const quoteDeps = JSON.stringify({
    c: state.clothTypeId,
    m: state.materialId,
    col: state.materialColorId,
    o: state.designOptionIds,
    meas: state.measurements,
  });

  useEffect(() => {
    if (!state.clothTypeId || !state.materialId) {
      // Clearing a stale quote when the selection becomes incomplete. This is a
      // synchronous setState, but it converges immediately rather than cascading.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQuote(null);
      return undefined;
    }
    const controller = new AbortController();
    // Debounced: measurements change on every keystroke, and each one would
    // otherwise fire a pricing request.
    const timer = setTimeout(async () => {
      setQuoteLoading(true);
      setQuoteError(null);
      try {
        const measurements = {};
        for (const [key, value] of Object.entries(state.measurements)) {
          if (value !== '' && value != null) measurements[key] = Number(value);
        }
        const result = await pricing.quote(
          {
            cloth_type_id: state.clothTypeId,
            material_id: state.materialId,
            material_color_id: state.materialColorId,
            design_option_ids: state.designOptionIds,
            measurements,
          },
          { signal: controller.signal },
        );
        setQuote(result);
      } catch (err) {
        if (err.name !== 'AbortError') setQuoteError(err.message || 'Could not calculate a price.');
      } finally {
        setQuoteLoading(false);
      }
    }, 400);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quoteDeps]);

  // ── AI mockup ───────────────────────────────────────────────────────────
  const generateMockup = useCallback(
    async (useCache = true) => {
      if (!state.clothTypeId || !state.materialId) return;
      setGenerating(true);
      setMockupError(null);
      try {
        const result = await mockupApi.generate({
          cloth_type_id: state.clothTypeId,
          material_id: state.materialId,
          material_color_id: state.materialColorId,
          design_option_ids: state.designOptionIds,
          custom_description: state.customDescription,
          use_cache: useCache,
        });
        dispatch({ type: 'SET_MOCKUP', mockup: result });
      } catch (err) {
        setMockupError(err.message || 'Preview generation failed.');
      } finally {
        setGenerating(false);
      }
    },
    [state.clothTypeId, state.materialId, state.materialColorId, state.designOptionIds, state.customDescription, dispatch],
  );

  // Generate once on entering step 6, if we don't already have one.
  const requestedRef = useRef(false);
  useEffect(() => {
    if (state.step !== TOTAL_STEPS) {
      requestedRef.current = false;
      return;
    }
    if (state.mockup || generating || requestedRef.current) return;
    // Fetch-on-enter. The ref guard stops this re-firing while the request is
    // in flight; the resulting state lands asynchronously.
    requestedRef.current = true;
    generateMockup(true);
  }, [state.step, state.mockup, generating, generateMockup]);

  // ── Navigation ──────────────────────────────────────────────────────────
  const unlocked = highestUnlockedStep(state);
  const canAdvance = isStepComplete(state, state.step);

  function goToStep(step) {
    if (step > unlocked) return;
    dispatch({ type: 'SET_STEP', step });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function placeOrder() {
    setPlaceError(null);
    if (!isAuthenticated && !guestEmail) {
      setPlaceError('Please enter an email address so we can send your confirmation.');
      return;
    }
    setPlacing(true);
    try {
      const measurements = {};
      for (const [key, value] of Object.entries(state.measurements)) {
        if (value !== '' && value != null) measurements[key] = Number(value);
      }
      const order = await orders.create({
        cloth_type_id: state.clothTypeId,
        material_id: state.materialId,
        material_color_id: state.materialColorId,
        design_option_ids: state.designOptionIds,
        measurements,
        custom_description: state.customDescription,
        draft_id: state.draftId,
        mockup_url: state.mockup?.image_url ?? null,
        mockup_prompt: state.mockup?.prompt ?? null,
        mockup_model: state.mockup?.model_id ?? null,
        ...(isAuthenticated ? {} : { guest_email: guestEmail }),
      });
      resetWizard();
      navigate(`/success?order=${encodeURIComponent(order.order_number)}`);
    } catch (err) {
      setPlaceError(err.message || 'Could not place the order.');
    } finally {
      setPlacing(false);
    }
  }

  return (
    <>
      <Navbar backLink />

      <div className="progress-wrap">
        <div className="progress-steps">
          {STEP_LABELS.map((label, index) => {
            const step = index + 1;
            const isDone = state.step > step;
            const isActive = state.step === step;
            const isLocked = step > unlocked;
            return (
              <button
                type="button"
                key={label}
                disabled={isLocked}
                className={`prog-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''} ${
                  isLocked ? 'locked' : ''
                }`}
                onClick={() => goToStep(step)}
              >
                <div className="prog-num">{isDone ? '✓' : step}</div>
                <div className="prog-label">{label}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="wizard">
        <div className="wizard-main">
          {state.step === 1 && (
            <StepCloth clothTypes={clothTypes} loading={catalogLoading} error={catalogError} />
          )}
          {state.step === 2 && (
            <StepDesign
              clothType={clothType}
              onSuggestClothType={(id) => {
                const match = clothTypes.find((c) => c.id === id);
                if (match) {
                  dispatch({ type: 'SELECT_CLOTH_TYPE', id: match.id, slug: match.slug });
                }
              }}
            />
          )}
          {state.step === 3 && (
            <StepMaterial materials={materials} loading={catalogLoading} error={catalogError} />
          )}
          {state.step === 4 && (
            <StepMeasurements clothType={clothType} savedMeasurements={savedMeasurements} />
          )}
          {state.step === 5 && (
            <StepPricing quote={quote} loading={quoteLoading} error={quoteError} />
          )}
          {state.step === 6 && (
            <StepMockup
              clothType={clothType}
              material={material}
              colour={colour}
              generating={generating}
              error={mockupError}
              onRegenerate={() => generateMockup(false)}
            />
          )}
        </div>

        <aside className="wizard-sidebar">
          <h3 className="sidebar-title">Your Order</h3>
          <p className="sidebar-sub">Summary so far</p>

          <div className="order-summary">
            <div className="summary-row">
              <span className="summary-key">Garment</span>
              <span className="summary-val">{clothType?.name ?? 'Not selected'}</span>
            </div>
            <div className="summary-row">
              <span className="summary-key">Material</span>
              <span className="summary-val">{material?.name ?? 'Not selected'}</span>
            </div>
            <div className="summary-row">
              <span className="summary-key">Colour</span>
              <span className="summary-val">{colour?.name ?? '—'}</span>
            </div>
            <div className="summary-row">
              <span className="summary-key">Details</span>
              <span className="summary-val">
                {state.designOptionIds.length
                  ? `${state.designOptionIds.length} selected`
                  : 'None'}
              </span>
            </div>
          </div>

          <div className="price-preview">
            <h4>Estimated price</h4>
            {quote ? (
              <>
                <div className="price-row">
                  <span>Base</span>
                  <span>LKR {Number(quote.base).toLocaleString()}</span>
                </div>
                <div className="price-row">
                  <span>Stitching</span>
                  <span>LKR {Number(quote.stitching).toLocaleString()}</span>
                </div>
                <div className="price-row">
                  <span>Material</span>
                  <span>LKR {Number(quote.material).toLocaleString()}</span>
                </div>
                <div className="price-row">
                  <span>Delivery</span>
                  <span>
                    {Number(quote.delivery) === 0
                      ? 'Free'
                      : `LKR ${Number(quote.delivery).toLocaleString()}`}
                  </span>
                </div>
                <div className="price-total">
                  <span>Total</span>
                  <span>LKR {Number(quote.total).toLocaleString()}</span>
                </div>
              </>
            ) : (
              <p className="price-pending">
                {quoteLoading ? 'Calculating…' : 'Choose a garment and fabric'}
              </p>
            )}
          </div>

          {state.step < TOTAL_STEPS ? (
            <button
              type="button"
              className="btn-next"
              disabled={!canAdvance}
              onClick={() => goToStep(state.step + 1)}
            >
              Next — {STEP_LABELS[state.step]} →
            </button>
          ) : (
            <>
              {!isAuthenticated && (
                <div className="field" style={{ marginBottom: 12 }}>
                  <label htmlFor="guest-email">Email for your confirmation</label>
                  <input
                    id="guest-email"
                    type="email"
                    value={guestEmail}
                    placeholder="you@example.com"
                    onChange={(e) => setGuestEmail(e.target.value)}
                  />
                </div>
              )}
              <button
                type="button"
                className="btn-confirm"
                disabled={placing || generating || !quote}
                onClick={placeOrder}
              >
                {placing
                  ? 'Placing your order…'
                  : `✓ Confirm — LKR ${Number(quote?.total ?? 0).toLocaleString()}`}
              </button>
            </>
          )}

          {placeError && <div className="field-error">{placeError}</div>}

          {state.step > 1 && (
            <button type="button" className="btn-back" onClick={() => goToStep(state.step - 1)}>
              ← Back
            </button>
          )}
        </aside>
      </div>
    </>
  );
}
