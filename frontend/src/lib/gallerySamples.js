/**
 * AI previews shipped with the frontend, and the helper that pads the live
 * gallery with them.
 *
 * Not decoration: mockups written by the local storage backend live on the
 * instance's disk, and the API withholds any whose file has gone (see
 * storage.media_exists), so a freshly deployed site can legitimately have
 * nothing to show. These are genuine outputs of this project's own generator,
 * exported from the mockup cache at 720px — not stock photography — and they
 * are tagged so a visitor can tell them from a real customer order.
 */

// Captions are the real order each image was generated for, checked against
// the mockup cache — not invented. Three, because the strip shows three: the
// cache also held two more burgundy shirts, which would only ever have been
// bytes nobody downloads.
export const SAMPLE_MOCKUPS = [
  { image_url: '/img/gallery/mockup-04.jpg', cloth_type: 'Dress', material: 'Cotton', colour: 'Ivory' },
  { image_url: '/img/gallery/mockup-05.jpg', cloth_type: 'Trousers', material: 'Linen', colour: 'Deep Blue' },
  { image_url: '/img/gallery/mockup-02.jpg', cloth_type: 'Shirt', material: 'Cotton', colour: 'Burgundy' },
].map((item) => ({ ...item, sample: true }));

/** Real designs first, then samples, up to `count` tiles. */
export function withSamples(items, count) {
  const filled = [...items];
  for (const sample of SAMPLE_MOCKUPS) {
    if (filled.length >= count) break;
    filled.push(sample);
  }
  return filled.slice(0, count);
}
