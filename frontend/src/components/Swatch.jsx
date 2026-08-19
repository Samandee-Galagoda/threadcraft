/**
 * A material swatch — the photograph where one exists, the CSS gradient where
 * it does not.
 *
 * Gradients told a customer the *colour* of a fabric but nothing about its
 * hand: chiffon and satin were two pale rectangles, which is no help at the one
 * step that asks what the garment should feel like. The gradient survives as
 * the fallback so a fabric an admin adds before they have a photograph still
 * renders, rather than showing a broken image.
 */
export default function Swatch({ material, className = 'mat-swatch', alt }) {
  if (material?.swatch_image_url) {
    return (
      <img
        className={className}
        src={material.swatch_image_url}
        alt={alt ?? `${material.name} fabric`}
        loading="lazy"
      />
    );
  }
  return (
    <div
      className={className}
      style={{ background: material?.swatch_css || 'var(--sand)' }}
      // Decorative: with no photograph there is nothing here a screen reader
      // could usefully describe beyond the name already beside it.
      aria-hidden="true"
    />
  );
}
