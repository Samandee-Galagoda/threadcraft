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
 * Furthest step the current state actually justifies — used to stop someone
 * deep-linking to step 5 with no garment chosen.
 */
export function highestUnlockedStep(state) {
  if (!state.clothTypeId) return 1;
  if (!state.materialId) return 3;
  return TOTAL_STEPS;
}

export function isStepComplete(state, step) {
  switch (step) {
    case 1:
      return Boolean(state.clothTypeId);
    case 2:
      return true; // design tags are all optional
    case 3:
      return Boolean(state.materialId);
    case 4:
      return Object.values(state.measurements).some((v) => v !== '' && v != null);
    default:
      return true;
  }
}
