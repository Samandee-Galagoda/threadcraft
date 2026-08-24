/**
 * Wizard state. Pure reducer — no API calls, no storage access, no randomness,
 * so it can be unit-tested directly.
 */

// Bumped whenever the shape changes, so a stale sessionStorage payload from an
// older build is discarded rather than crashing the wizard.
export const WIZARD_STATE_VERSION = 2;
export const STORAGE_KEY = 'tc_wizard_v2';
export const TOTAL_STEPS = 6;

export function createInitialState(draftId) {
  return {
    version: WIZARD_STATE_VERSION,
    draftId,
    step: 1,
    maxStepReached: 1,
    clothTypeId: null,
    clothTypeSlug: null,
    designOptionIds: [],
    customDescription: '',
    referenceImages: [],
    materialId: null,
    materialColorId: null,
    measurements: {},
    profile: { height: '', weight: '', age: '', sex: '' },
    mockup: null,
  };
}

export function wizardReducer(state, action) {
  switch (action.type) {
    case 'SET_STEP': {
      const step = Math.min(Math.max(1, action.step), TOTAL_STEPS);
      return { ...state, step, maxStepReached: Math.max(state.maxStepReached, step) };
    }

    case 'SELECT_CLOTH_TYPE':
      // Changing garment invalidates design options and measurements, because
      // both are defined per cloth type. Leaving them would silently carry a
      // dress's measurements onto a pair of trousers.
      return {
        ...state,
        clothTypeId: action.id,
        clothTypeSlug: action.slug,
        designOptionIds: [],
        measurements: {},
        mockup: null,
      };

    case 'TOGGLE_OPTION': {
      // One selection per group: drop any other option from the same group.
      const withoutGroup = state.designOptionIds.filter(
        (id) => !action.groupOptionIds.includes(id),
      );
      const isAlreadySelected = state.designOptionIds.includes(action.id);
      return {
        ...state,
        designOptionIds: isAlreadySelected ? withoutGroup : [...withoutGroup, action.id],
        mockup: null,
      };
    }

    case 'SET_DESCRIPTION':
      return { ...state, customDescription: action.value.slice(0, 500), mockup: null };

    case 'SET_REFERENCE_IMAGES':
      return { ...state, referenceImages: action.images };

    case 'SELECT_MATERIAL':
      return { ...state, materialId: action.id, materialColorId: action.colorId ?? null, mockup: null };

    case 'SELECT_COLOR':
      return { ...state, materialColorId: action.id, mockup: null };

    case 'SET_MEASUREMENT': {
      const value = action.value === '' ? '' : Number(action.value);
      return { ...state, measurements: { ...state.measurements, [action.field]: value } };
    }

    case 'SET_MEASUREMENTS':
      return { ...state, measurements: { ...state.measurements, ...action.values } };

    case 'SET_PROFILE':
      return { ...state, profile: { ...state.profile, ...action.values } };

    case 'SET_MOCKUP':
      return { ...state, mockup: action.mockup };

    case 'RESET':
      return createInitialState(action.draftId);

    default:
      return state;
  }
}

/** Rehydrate from a persisted payload, discarding anything from an older shape. */
export function hydrate(raw, fallbackDraftId) {
  if (!raw) return createInitialState(fallbackDraftId);
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (parsed?.version !== WIZARD_STATE_VERSION) {
      return createInitialState(fallbackDraftId);
    }
    return { ...createInitialState(fallbackDraftId), ...parsed };
  } catch {
    return createInitialState(fallbackDraftId);
  }
}

/**
 * Every reason step N is not finished yet, phrased for the customer.
 *
 * `context` carries the catalogue detail the wizard state doesn't hold — the
 * garment's option groups and measurement fields — because the state stores
 * only ids. It is optional: with no context the garment-specific rules are
 * skipped rather than reported as failures, so the wizard is never blocked by
 * a catalogue that hasn't loaded yet.
 */
export function stepProblems(state, step, context = {}) {
  const { clothType, material } = context;
  const problems = [];

  switch (step) {
    case 1:
      if (!state.clothTypeId) {
        problems.push('Choose the garment you would like made before continuing.');
      }
      return problems;

    case 2: {
      // One selection per option group. Each group is a distinct decision the
      // tailor has to make (neckline, sleeve, length), so "some tag somewhere"
      // isn't enough to cut from.
      for (const group of clothType?.option_groups ?? []) {
        const ids = group.options?.map((option) => option.id) ?? [];
        if (!ids.some((id) => state.designOptionIds.includes(id))) {
          problems.push(`Choose an option for “${group.label}”.`);
        }
      }
      if (!state.customDescription.trim()) {
        problems.push('Describe your design in your own words — the AI preview is built from it.');
      }
      return problems;
    }

    case 3:
      if (!state.materialId) {
        problems.push('Choose the fabric your garment is cut from.');
      } else if (material?.colors?.length && !state.materialColorId) {
        problems.push(`Choose a colour for ${material.name}.`);
      }
      return problems;

    case 4: {
      const fields = clothType?.measurement_fields;
      if (!fields) {
        // Catalogue not loaded — fall back to the loose check rather than
        // inventing field names we don't have.
        if (!Object.values(state.measurements).some(isFilled)) {
          problems.push('Enter your measurements before continuing.');
        }
        return problems;
      }

      const missing = fields.filter((field) => !isFilled(state.measurements[field.field_key]));
      if (missing.length) {
        problems.push(
          missing.length === fields.length
            ? `Enter all ${fields.length} measurements — none have been filled in yet.`
            : `Every measurement is needed. Still missing: ${missing
                .map((field) => field.label)
                .join(', ')}.`,
        );
      }

      for (const field of fields) {
        const value = Number(state.measurements[field.field_key]);
        if (missing.includes(field) || Number.isNaN(value)) continue;
        if (value < Number(field.min_value) || value > Number(field.max_value)) {
          problems.push(
            `${field.label} must be between ${Number(field.min_value)} and ` +
              `${Number(field.max_value)} ${field.unit}.`,
          );
        }
      }
      return problems;
    }

    default:
      return problems;
  }
}

function isFilled(value) {
  return value !== '' && value != null && !Number.isNaN(Number(value));
}

export function isStepComplete(state, step, context) {
  return stepProblems(state, step, context).length === 0;
}

/**
 * Furthest step the current state actually justifies — the first one that isn't
 * finished. Stops someone deep-linking to step 5, or clicking ahead on the
 * progress bar, with half a design.
 */
export function highestUnlockedStep(state, context) {
  for (let step = 1; step < TOTAL_STEPS; step += 1) {
    if (!isStepComplete(state, step, context)) return step;
  }
  return TOTAL_STEPS;
}
