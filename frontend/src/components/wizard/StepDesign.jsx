import { useState } from 'react';
import { ml, uploads, mediaUrl } from '../../api';
import { useWizard } from '../../context/WizardContext';

const MAX_IMAGES = 3;
const MAX_BYTES = 5 * 1024 * 1024;

export default function StepDesign({ clothType, onSuggestClothType }) {
  const { state, dispatch } = useWizard();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [classification, setClassification] = useState(null);
  const [classifierNote, setClassifierNote] = useState(null);

  const groups = clothType?.option_groups ?? [];

  async function handleFiles(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = ''; // allow re-selecting the same file
    if (!files.length) return;

    setUploadError(null);
    const remaining = MAX_IMAGES - state.referenceImages.length;
    if (remaining <= 0) {
      setUploadError(`You can upload at most ${MAX_IMAGES} reference images.`);
      return;
    }

    setUploading(true);
    const uploaded = [...state.referenceImages];
    try {
      for (const file of files.slice(0, remaining)) {
        if (file.size > MAX_BYTES) {
          setUploadError(`"${file.name}" is larger than 5 MB.`);
          continue;
        }
        const result = await uploads.reference(state.draftId, file);
        uploaded.push(result);

        // Ask the classifier what it thinks the garment is — purely a
        // suggestion, and only offered for the first image.
        if (uploaded.length === 1) {
          try {
            // Stored unconditionally, including `available: false`. Previously
            // an unavailable classifier rendered nothing at all, so the deployed
            // site looked like the feature was broken rather than switched off —
            // the opposite of StepMeasurements, which says so via .ai-note.
            setClassification(await ml.classifyGarment(file));
          } catch {
            // Advisory only; an upload must never fail because of it.
            setClassifierNote('Could not reach the garment recogniser — carry on, it is optional.');
          }
        }
      }
      dispatch({ type: 'SET_REFERENCE_IMAGES', images: uploaded });
    } catch (err) {
      setUploadError(err.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  }

  async function removeImage(image) {
    try {
      await uploads.remove(image.id);
    } catch {
      // Already gone server-side is fine — drop it from the UI regardless.
    }
    dispatch({
      type: 'SET_REFERENCE_IMAGES',
      images: state.referenceImages.filter((i) => i.id !== image.id),
    });
  }

  return (
    <div>
      <h1 className="step-title">Describe Your Design</h1>
      <p className="step-sub">
        Step 2 of 6 · {clothType?.name ?? 'Garment'} selected
      </p>

      {groups.map((group) => {
        const groupOptionIds = group.options.map((o) => o.id);
        return (
          <div className="form-section" key={group.id}>
            <span className="form-label">{group.label}</span>
            <div className="tags-wrap">
              {group.options.map((option) => (
                <button
                  type="button"
                  key={option.id}
                  className={`tag-btn ${state.designOptionIds.includes(option.id) ? 'active' : ''}`}
                  onClick={() =>
                    dispatch({ type: 'TOGGLE_OPTION', id: option.id, groupOptionIds })
                  }
                >
                  {option.label}
                  {Number(option.stitching_premium) > 0 && (
                    <span className="tag-premium">
                      +{Number(option.stitching_premium).toLocaleString()}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        );
      })}

      <div className="form-section">
        <span className="form-label">
          Describe your design <span className="form-label-hint">(optional)</span>
        </span>
        <textarea
          placeholder="e.g. a midi dress with a fitted bodice and a soft flared skirt…"
          value={state.customDescription}
          maxLength={500}
          onChange={(e) => dispatch({ type: 'SET_DESCRIPTION', value: e.target.value })}
        />
        <div className="char-count">{state.customDescription.length} / 500</div>
      </div>

      <div className="form-section">
        <span className="form-label">
          Reference images <span className="form-label-hint">(optional · up to {MAX_IMAGES})</span>
        </span>

        <label className="upload-zone" htmlFor="reference-upload">
          <svg viewBox="0 0 24 24">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M12 8v8M8 12h8" strokeLinecap="round" />
          </svg>
          <p>{uploading ? 'Uploading…' : 'Click to upload a reference photo'}</p>
          <small>JPG, PNG or WEBP · max 5 MB each</small>
          <input
            id="reference-upload"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            hidden
            disabled={uploading || state.referenceImages.length >= MAX_IMAGES}
            onChange={handleFiles}
          />
        </label>

        {uploadError && <div className="field-error">{uploadError}</div>}

        {state.referenceImages.length > 0 && (
          <div className="reference-grid">
            {state.referenceImages.map((image) => (
              <div className="reference-thumb" key={image.id}>
                <img src={mediaUrl(image.url)} alt="Design reference" />
                <button type="button" onClick={() => removeImage(image)} aria-label="Remove">
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {classification?.available && classification.predictions?.length > 0 && (
          <div className="ai-hint">
            <strong>AI suggestion</strong> — that looks like{' '}
            <em>{classification.predictions[0].label}</em>{' '}
            ({Math.round(classification.predictions[0].score * 100)}% confidence).
            {classification.matched_cloth_type_id &&
              classification.matched_cloth_type_id !== state.clothTypeId && (
                <button
                  type="button"
                  className="link-btn"
                  onClick={() => onSuggestClothType?.(classification.matched_cloth_type_id)}
                >
                  Switch to this garment type
                </button>
              )}
          </div>
        )}

        {/* Say why nothing was suggested. The model needs ~1.15 GB and the free
            deployment has 512 MB, so on the hosted site this is the normal
            state — and an unexplained blank reads as a bug. */}
        {classification && !classification.available && (
          <p className="ai-note">{classification.note}</p>
        )}
        {classifierNote && <p className="ai-note">{classifierNote}</p>}
      </div>
    </div>
  );
}
