/**
 * Labelled body diagrams for the measurement guide.
 *
 * The *table* on that page is driven entirely by the catalogue API, so a
 * measurement field an admin adds appears in the guide with no code change.
 * The diagrams cannot be: a drawing of where to put the tape is artwork, not
 * data. They are keyed by cloth-type slug and by the letter the catalogue
 * assigns each field, so the two halves stay in step — if a garment has no
 * diagram the table still renders, and an unrecognised letter simply isn't
 * drawn rather than breaking the page.
 *
 * Every mark is a *span*, not a dot: the point of the page is showing where a
 * measurement starts and where it ends.
 */

// ── Shared silhouettes ──────────────────────────────────────────────────────
// Two figures cover all eight garments. Drawing eight separate bodies would
// mean eight chances for the proportions to disagree with each other.

function UpperBody({ hem = 300, skirt = null, sleeves = 'short' }) {
  return (
    <g>
      <ellipse cx="120" cy="38" rx="21" ry="27" className="bd-fill" />
      <rect x="112" y="63" width="16" height="13" rx="5" className="bd-fill" />
      {/* torso */}
      <path
        d={`M72 80 Q56 98 52 130 L48 190 Q46 230 50 258 L54 ${hem} L186 ${hem} L190 258 Q194 230 192 190 L188 130 Q184 98 168 80 Z`}
        className="bd-fill"
      />
      {sleeves === 'long' ? (
        <>
          <path d="M72 80 Q44 100 36 165 Q32 205 36 236" className="bd-fill" />
          <path d="M168 80 Q196 100 204 165 Q208 205 204 236" className="bd-fill" />
          <ellipse cx="36" cy="243" rx="7" ry="9" className="bd-fill" />
          <ellipse cx="204" cy="243" rx="7" ry="9" className="bd-fill" />
        </>
      ) : (
        <>
          <path d="M72 80 Q46 96 40 140 L54 146" className="bd-fill" />
          <path d="M168 80 Q194 96 200 140 L186 146" className="bd-fill" />
          <path d="M40 140 Q36 200 40 240" className="bd-line" />
          <path d="M200 140 Q204 200 200 240" className="bd-line" />
        </>
      )}
      {skirt}
    </g>
  );
}

function LowerBody({ children }) {
  return (
    <g>
      <rect x="62" y="14" width="116" height="22" rx="4" className="bd-fill" />
      {children}
    </g>
  );
}

// ── Mark helpers ────────────────────────────────────────────────────────────
// `girth`   — a circumference, drawn as a horizontal span across the body
// `span`    — a vertical length, drawn down one side
// `across`  — a horizontal width measured on the body itself (shoulder, hem)

const girth = (y, x1, x2, side = 'left') => ({ kind: 'girth', y, x1, x2, side });
const span = (x, y1, y2) => ({ kind: 'span', x, y1, y2 });
const across = (y, x1, x2, labelY) => ({ kind: 'across', y, x1, x2, labelY });

// ── Per-garment diagrams ────────────────────────────────────────────────────
// Letters match the catalogue exactly (see the seed's measurement fields).
const DIAGRAMS = {
  tshirt: {
    viewBox: '0 0 240 400',
    body: <UpperBody hem={318} sleeves="short" />,
    marks: {
      A: girth(132, 52, 188),
      B: across(72, 72, 168, 62),
      C: span(214, 80, 318),
      D: { kind: 'diagonal', x1: 72, y1: 82, x2: 44, y2: 143 },
    },
  },
  shirt: {
    viewBox: '0 0 240 400',
    body: (
      <UpperBody
        hem={330}
        sleeves="long"
        skirt={
          <>
            {/* collar and placket, so the collar/cuff marks have something to point at */}
            <path d="M100 76 L84 96 L120 110 L156 96 L140 76" className="bd-fill" />
            <line x1="120" y1="110" x2="120" y2="326" className="bd-dash" opacity=".35" />
          </>
        }
      />
    ),
    marks: {
      A: girth(134, 52, 188),
      B: across(72, 72, 168, 62),
      C: span(214, 80, 330),
      D: { kind: 'diagonal', x1: 168, y1: 82, x2: 204, y2: 238 },
      E: { kind: 'ellipse', cx: 120, cy: 72, rx: 21, ry: 8 },
      F: girth(243, 194, 214, 'right'),
    },
  },
  dress: {
    viewBox: '0 0 240 560',
    body: (
      <UpperBody
        hem={300}
        sleeves="short"
        skirt={<path d="M54 300 L34 502 L206 502 L186 300 Z" className="bd-fill" />}
      />
    ),
    marks: {
      A: girth(130, 52, 188),
      B: girth(190, 48, 192),
      C: girth(258, 50, 190),
      D: across(72, 72, 168, 62),
      E: span(222, 80, 502),
      F: { kind: 'diagonal', x1: 72, y1: 82, x2: 44, y2: 143 },
      G: span(120, 70, 96),
    },
  },
  kurta: {
    viewBox: '0 0 240 480',
    body: (
      <UpperBody
        hem={300}
        sleeves="long"
        skirt={
          <>
            <path d="M54 300 L48 420 L192 420 L186 300 Z" className="bd-fill" />
            {/* side slit, which is why a kurta reads longer than a shirt */}
            <line x1="50" y1="380" x2="50" y2="418" className="bd-dash" />
            <line x1="190" y1="380" x2="190" y2="418" className="bd-dash" />
          </>
        }
      />
    ),
    marks: {
      A: girth(132, 52, 188),
      B: across(72, 72, 168, 62),
      C: span(216, 80, 420),
      D: { kind: 'diagonal', x1: 168, y1: 82, x2: 204, y2: 238 },
    },
  },
  'saree-blouse': {
    viewBox: '0 0 240 300',
    body: (
      <g>
        <ellipse cx="120" cy="38" rx="21" ry="27" className="bd-fill" />
        <rect x="112" y="63" width="16" height="13" rx="5" className="bd-fill" />
        {/* cropped body — the defining feature of this garment */}
        <path d="M72 80 Q56 98 52 130 L52 178 L188 178 L188 130 Q184 98 168 80 Z" className="bd-fill" />
        <path d="M72 80 Q46 94 42 126 L56 132" className="bd-fill" />
        <path d="M168 80 Q194 94 198 126 L184 132" className="bd-fill" />
        <path d="M52 176 Q120 170 188 176" className="bd-line" />
        <line x1="52" y1="200" x2="188" y2="200" className="bd-dash" opacity=".3" />
      </g>
    ),
    marks: {
      A: girth(128, 52, 188),
      B: girth(174, 52, 188),
      C: across(72, 72, 168, 62),
      D: { kind: 'diagonal', x1: 168, y1: 82, x2: 198, y2: 128 },
    },
  },
  'salwar-kameez': {
    viewBox: '0 0 240 560',
    body: (
      <UpperBody
        hem={300}
        sleeves="long"
        skirt={
          <>
            {/* kameez over salwar, so both lengths have a body to sit against */}
            <path d="M54 300 L46 392 L194 392 L186 300 Z" className="bd-fill" />
            <path d="M60 392 L54 520 L110 520 L116 400 L124 400 L130 520 L186 520 L180 392 Z" className="bd-fill" />
            <path d="M46 390 Q120 384 194 390" className="bd-line" />
          </>
        }
      />
    ),
    marks: {
      A: girth(130, 52, 188),
      B: girth(190, 48, 192),
      C: girth(258, 50, 190),
      D: span(216, 80, 392),
      E: span(30, 300, 520),
    },
  },
  trousers: {
    viewBox: '0 0 240 560',
    body: (
      <LowerBody>
        <path
          d="M62 36 L56 124 L54 194 L48 510 L108 510 L116 254 L120 206 L124 254 L132 510 L192 510 L186 194 L184 124 L178 36 Z"
          className="bd-fill"
        />
        <path d="M56 124 Q120 140 184 124" className="bd-dash" opacity=".45" />
      </LowerBody>
    ),
    marks: {
      A: girth(25, 62, 178),
      B: girth(102, 55, 185),
      C: span(116, 150, 510),
      D: span(28, 14, 510),
      E: girth(176, 54, 116, 'left'),
      F: girth(300, 51, 116, 'left'),
      G: across(510, 48, 108, 528),
    },
  },
  skirt: {
    viewBox: '0 0 240 480',
    body: (
      <LowerBody>
        <path d="M62 36 L34 410 L206 410 L178 36 Z" className="bd-fill" />
        <path d="M52 200 Q120 190 188 200" className="bd-dash" opacity=".3" />
        <path d="M42 310 Q120 298 198 310" className="bd-dash" opacity=".25" />
      </LowerBody>
    ),
    marks: {
      A: girth(25, 62, 178),
      B: girth(108, 50, 190),
      C: span(222, 36, 410),
      D: across(410, 34, 206, 430),
    },
  },
};

/** One measurement drawn on the figure. */
function Mark({ letter, mark, active, onSelect }) {
  const cls = `bd-mark ${active ? 'active' : ''}`;
  const badge = (x, y) => (
    <g className="bd-badge" onClick={() => onSelect(letter)}>
      <circle cx={x} cy={y} r="10" />
      <text x={x} y={y + 4} textAnchor="middle">
        {letter}
      </text>
    </g>
  );

  if (mark.kind === 'girth') {
    const bx = mark.side === 'right' ? mark.x2 + 18 : mark.x1 - 18;
    return (
      <g className={cls}>
        <line x1={mark.x1} y1={mark.y} x2={mark.x2} y2={mark.y} className="bd-guide" />
        <line x1={mark.x1} y1={mark.y - 5} x2={mark.x1} y2={mark.y + 5} className="bd-tick" />
        <line x1={mark.x2} y1={mark.y - 5} x2={mark.x2} y2={mark.y + 5} className="bd-tick" />
        {badge(bx, mark.y)}
      </g>
    );
  }
  if (mark.kind === 'span') {
    return (
      <g className={cls}>
        <line x1={mark.x} y1={mark.y1} x2={mark.x} y2={mark.y2} className="bd-guide" />
        <line x1={mark.x - 5} y1={mark.y1} x2={mark.x + 5} y2={mark.y1} className="bd-tick" />
        <line x1={mark.x - 5} y1={mark.y2} x2={mark.x + 5} y2={mark.y2} className="bd-tick" />
        {badge(mark.x, (mark.y1 + mark.y2) / 2)}
      </g>
    );
  }
  if (mark.kind === 'across') {
    return (
      <g className={cls}>
        <line x1={mark.x1} y1={mark.y} x2={mark.x2} y2={mark.y} className="bd-guide" />
        <line x1={mark.x1} y1={mark.y - 5} x2={mark.x1} y2={mark.y + 5} className="bd-tick" />
        <line x1={mark.x2} y1={mark.y - 5} x2={mark.x2} y2={mark.y + 5} className="bd-tick" />
        {badge((mark.x1 + mark.x2) / 2, mark.labelY)}
      </g>
    );
  }
  if (mark.kind === 'diagonal') {
    return (
      <g className={cls}>
        <line x1={mark.x1} y1={mark.y1} x2={mark.x2} y2={mark.y2} className="bd-guide" />
        {badge(mark.x2 + (mark.x2 < 120 ? -16 : 16), mark.y2)}
      </g>
    );
  }
  if (mark.kind === 'ellipse') {
    return (
      <g className={cls}>
        <ellipse cx={mark.cx} cy={mark.cy} rx={mark.rx} ry={mark.ry} className="bd-guide" fill="none" />
        {badge(mark.cx + mark.rx + 18, mark.cy)}
      </g>
    );
  }
  return null;
}

export default function BodyDiagram({ slug, fields, activeLetter, onSelect }) {
  const diagram = DIAGRAMS[slug];
  if (!diagram) return null;

  return (
    <svg className="body-diagram" viewBox={diagram.viewBox} role="img"
         aria-label="Diagram showing where each measurement is taken">
      {diagram.body}
      {/* Only letters the catalogue actually defines are drawn, so removing a
          field from a garment removes its mark rather than leaving it orphaned. */}
      {fields
        .filter((field) => diagram.marks[field.letter])
        .map((field) => (
          <Mark
            key={field.letter}
            letter={field.letter}
            mark={diagram.marks[field.letter]}
            active={activeLetter === field.letter}
            onSelect={onSelect}
          />
        ))}
    </svg>
  );
}
