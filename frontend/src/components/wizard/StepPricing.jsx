export default function StepPricing({ quote, loading, error }) {
  if (loading) return <div className="wizard-loading">Calculating your price…</div>;
  if (error) return <div className="wizard-error">{error}</div>;
  if (!quote) {
    return <div className="wizard-error">Choose a garment and fabric to see pricing.</div>;
  }

  const byCategory = (category) => quote.lines.filter((l) => l.category === category);

  return (
    <div>
      <h1 className="step-title">Pricing Breakdown</h1>
      <p className="step-sub">Step 5 of 6 · Every line itemised, nothing hidden</p>

      <div className="price-block">
        <h4>Estimated cost</h4>

        {['base', 'stitching', 'material', 'delivery'].map((category) => {
          const lines = byCategory(category);
          if (!lines.length) return null;
          return lines.map((line, index) => (
            <div className="pr" key={`${category}-${index}`}>
              <span>{line.label}</span>
              <span>LKR {Number(line.amount).toLocaleString()}</span>
            </div>
          ));
        })}

        <div className="pr-total">
          <span className="k">Total</span>
          <span className="v">LKR {Number(quote.total).toLocaleString()}</span>
        </div>
      </div>

      <div className="price-explainer">
        <h4>How this is calculated</h4>
        <ul>
          <li>
            <strong>Base price</strong> — set per garment type in the admin catalogue.
          </li>
          <li>
            <strong>Stitching</strong> — a base cost plus a premium for each design detail that
            takes extra work.
          </li>
          <li>
            <strong>Material</strong> — {Number(quote.fabric_metres)} m of fabric at its
            cost-per-metre. The metreage scales with your measurements, so a larger garment uses
            (and costs) proportionally more.
          </li>
          <li>
            <strong>Delivery</strong> — a flat fee, waived above the free-delivery threshold.
          </li>
        </ul>
        <p className="price-note">
          This total is recalculated on the server when you place the order, so what you see here
          is what you pay.
        </p>
      </div>
    </div>
  );
}
