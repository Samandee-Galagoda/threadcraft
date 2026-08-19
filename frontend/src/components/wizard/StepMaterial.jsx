import { useWizard } from '../../context/WizardContext';
import Swatch from '../Swatch';

export default function StepMaterial({ materials, loading, error }) {
  const { state, dispatch } = useWizard();

  if (loading) return <div className="wizard-loading">Loading fabrics…</div>;
  if (error) return <div className="wizard-error">{error}</div>;

  const selected = materials.find((m) => m.id === state.materialId);

  return (
    <div>
      <h1 className="step-title">Choose Your Material</h1>
      <p className="step-sub">Step 3 of 6 · Fabric &amp; colour, with live stock</p>

      <div className="mat-grid">
        {materials.map((material) => {
          const outOfStock = Number(material.stock_metres) <= 0;
          return (
            <button
              type="button"
              key={material.id}
              disabled={outOfStock}
              className={`mat-item ${state.materialId === material.id ? 'selected' : ''} ${
                outOfStock ? 'disabled' : ''
              }`}
              onClick={() =>
                dispatch({
                  type: 'SELECT_MATERIAL',
                  id: material.id,
                  colorId: material.colors?.[0]?.id ?? null,
                })
              }
            >
              <Swatch material={material} />
              <div className="mat-name">{material.name}</div>
              <div className="mat-price">
                LKR {Number(material.cost_per_metre).toLocaleString()}/m
              </div>
              {outOfStock ? (
                <div className="mat-stock out">Out of stock</div>
              ) : material.is_low_stock ? (
                <div className="mat-stock low">
                  Only {Number(material.stock_metres).toFixed(1)} m left
                </div>
              ) : (
                <div className="mat-stock ok">In stock</div>
              )}
            </button>
          );
        })}
      </div>

      {selected?.colors?.length > 0 && (
        <div className="form-section" style={{ marginTop: 36 }}>
          <span className="form-label">{selected.name} — colour</span>
          <div className="colour-grid">
            {selected.colors.map((colour) => (
              <button
                type="button"
                key={colour.id}
                className={`colour-swatch ${
                  state.materialColorId === colour.id ? 'selected' : ''
                }`}
                onClick={() => dispatch({ type: 'SELECT_COLOR', id: colour.id })}
                title={colour.name}
              >
                <span style={{ background: colour.hex_code }} />
                <em>{colour.name}</em>
                {Number(colour.surcharge) > 0 && (
                  <small>+{Number(colour.surcharge).toLocaleString()}</small>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
