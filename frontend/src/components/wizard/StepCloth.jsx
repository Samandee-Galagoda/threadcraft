import { useWizard } from '../../context/WizardContext';

export default function StepCloth({ clothTypes, loading, error }) {
  const { state, dispatch } = useWizard();

  if (loading) return <div className="wizard-loading">Loading garment catalogue…</div>;
  if (error) return <div className="wizard-error">{error}</div>;
  if (!clothTypes.length) {
    return <div className="wizard-error">No garment types are configured yet.</div>;
  }

  return (
    <div>
      <h1 className="step-title">Choose Your Garment</h1>
      <p className="step-sub">Step 1 of 6 · What would you like to create?</p>

      <div className="cloth-select-grid">
        {clothTypes.map((type) => (
          <button
            type="button"
            key={type.id}
            className={`cloth-option ${state.clothTypeId === type.id ? 'selected' : ''}`}
            onClick={() => dispatch({ type: 'SELECT_CLOTH_TYPE', id: type.id, slug: type.slug })}
          >
            {type.image_url ? (
              <img src={type.image_url} alt="" className="cloth-option-img" />
            ) : (
              <svg viewBox="0 0 60 60">
                <path d="M15 10L8 16v10h8v24h28V26h8V16l-7-6-7 5-7-5-7 5z" strokeWidth="1.5" />
              </svg>
            )}
            <h4>{type.name}</h4>
            <p>from LKR {Number(type.base_price).toLocaleString()}</p>
          </button>
        ))}
      </div>

      <p className="step-footnote">
        Garment types are managed in the admin catalogue — this list comes straight from the
        database, so new categories appear here without a code change.
      </p>
    </div>
  );
}
