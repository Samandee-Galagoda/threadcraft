# Model 3 — Measurement Predictor & Validator

Predicts a customer's full set of garment measurements from the few they've actually taken, and
flags entries that contradict the rest of their profile.

## Run order

| # | Notebook | Kaggle accelerator | Internet | Roughly |
|---|---|---|---|---|
| 1 | `01_data_cleaning.ipynb` | **None (CPU)** | On | 1–2 minutes |
| 2 | `02_train.ipynb` | **None (CPU)** | On | 5–8 minutes |

No GPU needed for either. Both need the `HF_TOKEN` Kaggle Secret attached and `HF_USERNAME` set.

## Why this model exists

The proposal names this as an explicit ThreadCraft limitation:

> *"Measurement accuracy: The platform relies on self-reported customer measurements. Inaccurate
> measurements will affect the fit of the final garment."*

This model attacks that limitation directly, giving two product capabilities from the same
trained regressors:

| Capability | In the product |
|---|---|
| **Predict** | Wizard Step 4 pre-fills editable suggestions instead of blank boxes |
| **Validate** | A typo or unit mix-up is caught before it reaches the tailor |

## Dataset — ANSUR II

**6,068 people × 93 measurements**, from the 2012 Anthropometric Survey of US Army Personnel,
published by the Penn State OPEN Design Lab.

```
https://tools.openlab.psu.edu/publicData/ANSUR_II_MALE_Public.csv    (4,082 rows)
https://tools.openlab.psu.edu/publicData/ANSUR_II_FEMALE_Public.csv  (1,986 rows)
```

**Licence: US Government work, cleared for unlimited public release.** No attribution
requirement, no non-commercial clause, no gating, no login — the cleanest licence of any dataset
in this project.

Its columns map almost 1:1 onto ThreadCraft's `measurement_fields` table: chest, waist, hip,
shoulder, sleeve, collar, inseam, outseam, thigh, calf, cuff, ankle, total_length.

### Three data traps this notebook handles

1. **Use `https://`, not `http://`.** The `http` URLs now silently serve an unrelated HTML page —
   you get a 200 and a file that isn't data. The notebook asserts on row count to catch it.
2. **The files are `latin-1` encoded**, not UTF-8 — default `pd.read_csv` raises.
3. **The male file's ID column is `subjectid`; the female file's is `SubjectId`.** Concatenating
   without harmonising case silently produces two half-empty columns.

Plus the units, which are the easiest thing to get wrong: **all lengths are millimetres**, and
**`weightkg` is actually kg × 10** (its mean is ~855, i.e. 85.5 kg). The notebook converts once
and then asserts every field lands in a plausible human range — a factor-of-10 error would
otherwise train fine and then suggest a 10 cm sleeve.

## Measured results — this has actually been run

Accuracy depends on how much the customer supplied, so it's reported per scenario:

| Scenario | Mean R² | Mean MAE |
|---|---|---|
| A: height + weight + age + sex only | 0.818 | 1.62 cm |
| B: + chest & waist | 0.819 | 1.33 cm |
| C: + chest, waist, hip, shoulder | 0.826 | 1.21 cm |

Per-field R² at scenario A: `total_length` 0.983, `outseam` 0.898, `chest` 0.881, `collar` 0.873,
`hip` 0.873, `waist` 0.859, `sleeve` 0.840, `thigh` 0.840, `inseam` 0.815, `cuff` 0.793,
`shoulder` 0.754, `calf` 0.677, **`ankle` 0.551** (the weakest — say so rather than quoting only
the mean).

> Note `total_length` maps to cervicale height, which is near-perfectly correlated with stature —
> and stature is an input. Its 0.983 is close to trivial and shouldn't be presented as a headline.

### The masking design, and the evidence for it

A real customer supplies an **arbitrary subset** of measurements. Training on complete rows and
serving mostly-missing input is a train/serve mismatch, so each regressor is trained on randomly
masked copies of the data instead.

Tested against the simpler base-features-only alternative at the hardest scenario — the one that
alternative was built for — **masking won on 13/13 targets** (mean +0.016 R²), and additionally
improves as the customer supplies more. `design_comparison.csv` records this.

### Validator threshold tuning

Flagging threshold is a residual percentile, tuned on evidence rather than picked:

| Percentile | False positives | Catches 10% error | Catches 20% error | Catches 2× error |
|---|---|---|---|---|
| 90 | 14.3% | 89.3% | 99.8% | 100% |
| 95 | 7.9% | 84.3% | 99.7% | 100% |
| 97.5 | 4.5% | 78.1% | 99.4% | 100% |
| **99 (default)** | **2.1%** | **69.3%** | **98.6%** | **100%** |
| 99.5 | 1.2% | 62.6% | 98.1% | 100% |

The 99th percentile is the default: nagging 14% of customers whose bodies are simply unusual
would be worse than missing some small errors, and gross errors — the ones that actually ruin a
garment — are caught essentially always.

Verified behaviour on a 170 cm / 68 kg profile:

```
realistic profile        -> 0 warnings
waist mistyped as 176    -> flagged (expected ~83 cm)
sleeve entered as 32 in  -> flagged (expected ~84 cm)
```

## Limitations — lead with these

- **The training population is US Army personnel.** Younger, fitter and more athletic than a
  general civilian population, so predictions will be systematically off for older, sedentary or
  higher-BMI customers.
- **Body proportions vary between populations.** ThreadCraft serves a Sri Lankan market; ANSUR II
  is a US sample. Predictions are a **starting point the customer edits**, never a substitute for
  measuring. This is the single most important caveat.
- Sex is the binary recorded in ANSUR II — a limitation of the source data.
- ANSUR II has **no bust circumference and no knee circumference**, so those ThreadCraft fields
  can't be predicted. `chest` is the nearest analogue to bust, `calf` the nearest lower-leg
  circumference.
- `shoulder` maps to biacromial breadth and `inseam` to crotch height — close analogues of the
  tailoring measurements, not identical definitions. Expect a small systematic offset versus a
  tailor's own tape.

## Citation

> Gordon, C. C. et al. (2014). *2012 Anthropometric Survey of U.S. Army Personnel: Methods and
> Summary Statistics.* NATICK/TR-15/007.
