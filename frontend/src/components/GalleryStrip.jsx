import { mediaUrl } from '../api';

/**
 * AI previews, shown to visitors who have not designed anything yet.
 *
 * A customer's design is captioned with the garment, fabric and colour actually
 * ordered; a preview shipped with the site (see lib/gallerySamples) says so, so
 * the two are never mistaken for each other.
 */

export default function GalleryStrip({ items }) {
  return (
    <div className="gallery-grid">
      {items.map((item, index) => (
        <figure className="gallery-tile" key={`${item.image_url}-${index}`}>
          <img
            src={item.sample ? item.image_url : mediaUrl(item.image_url)}
            alt={`AI preview of a ${item.cloth_type ?? 'garment'}`}
            loading="lazy"
          />
          <figcaption>
            <span className="gallery-garment">{item.cloth_type ?? 'Custom garment'}</span>
            <span className="gallery-detail">
              {[item.material, item.colour].filter(Boolean).join(' · ') || 'AI preview'}
            </span>
          </figcaption>
          <span className="gallery-tag">{item.sample ? 'Sample preview' : 'Customer design'}</span>
        </figure>
      ))}
    </div>
  );
}
