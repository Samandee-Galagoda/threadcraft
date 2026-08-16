import { mediaUrl } from '../../api';
import { useWizard } from '../../context/WizardContext';

export default function StepMockup({ clothType, material, colour, generating, error, onRegenerate }) {
  const { state } = useWizard();
  const { mockup } = state;

  const selectedOptionLabels = (clothType?.option_groups ?? [])
    .flatMap((group) => group.options)
    .filter((option) => state.designOptionIds.includes(option.id))
    .map((option) => option.label);

  return (
    <div>
      <h1 className="step-title">Your AI Mockup Preview</h1>
      <p className="step-sub">Step 6 of 6 · Generated from your design choices</p>

      <div className="ai-preview-box">
        <div className="ai-label">★ AI Generated Preview</div>

        {generating ? (
          <div className="ai-loading">
            <div className="spinner" />
            <div className="loading-text">Generating your mockup…</div>
            <div className="loading-sub">This usually takes a few seconds</div>
          </div>
        ) : error ? (
          <div className="ai-loading">
            <div className="loading-text">Couldn&apos;t generate a preview</div>
            <div className="loading-sub">{error}</div>
          </div>
        ) : mockup ? (
          <img src={mediaUrl(mockup.image_url)} alt="AI generated garment preview" className="ai-image" />
        ) : (
          <div className="ai-loading">
            <div className="loading-text">Ready to generate</div>
          </div>
        )}
      </div>

      {mockup && !generating && (
        <>
          <p className="ai-disclaimer">{mockup.disclaimer}</p>

          {mockup.is_fallback && (
            <p className="ai-note">
              The image service is unavailable right now, so this is a placeholder. Your order is
              unaffected — you can still review your design and place it below.
            </p>
          )}

          <button type="button" className="regen-btn" onClick={onRegenerate}>
            ↺ Regenerate preview
          </button>

          <details className="prompt-details">
            <summary>See the prompt this was generated from</summary>
            <p className="prompt-text">{mockup.prompt}</p>
            <p className="prompt-meta">
              Model: <code>{mockup.model_id}</code>
              {mockup.cached ? ' · served from cache' : ` · ${mockup.latency_ms} ms`}
            </p>
          </details>
        </>
      )}

      <div className="design-recap">
        <div className="recap-title">Design recap — what we used to generate your preview</div>
        <div className="recap-grid">
          <div className="recap-item">
            <div className="k">Garment</div>
            <div className="v">{clothType?.name ?? '—'}</div>
          </div>
          <div className="recap-item">
            <div className="k">Material</div>
            <div className="v">{material?.name ?? '—'}</div>
          </div>
          <div className="recap-item">
            <div className="k">Colour</div>
            <div className="v">{colour?.name ?? '—'}</div>
          </div>
          {selectedOptionLabels.map((label) => (
            <div className="recap-item" key={label}>
              <div className="k">Detail</div>
              <div className="v">{label}</div>
            </div>
          ))}
        </div>
        {state.customDescription && (
          <p className="recap-description">“{state.customDescription}”</p>
        )}
      </div>
    </div>
  );
}
