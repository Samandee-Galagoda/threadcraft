import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from './Modal';
import Swatch from './Swatch';
import { catalog } from '../api';

/**
 * The full fabric catalogue, in a dialog.
 *
 * Loaded from the API rather than hardcoded, so it always matches what the
 * wizard will actually offer — the swatch grid on the home page is a static
 * teaser, and the two would otherwise disagree the moment an admin adds a
 * fabric.
 */
export default function CatalogueModal({ onClose }) {
  const [materials, setMaterials] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    catalog
      .materials()
      .then((rows) => !cancelled && setMaterials(rows))
      .catch((err) => !cancelled && setError(err.message || 'Could not load the catalogue.'));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Modal
      title="Our fabrics"
      subtitle={materials ? `${materials.length} materials · priced per metre` : 'Loading…'}
      onClose={onClose}
    >
      {error && <p className="wizard-error">{error}</p>}
      {!materials && !error && <p className="form-label-hint">Fetching the catalogue…</p>}

      {materials?.map((material) => {
        // A colourway a customer cannot currently order shouldn't be offered as
        // if it were available.
        const inStock = (material.colors || []).filter((c) => Number(c.stock_metres) > 0);
        return (
          <div className="cat-row" key={material.id}>
            <Swatch material={material} className="cat-swatch" />
            <div className="cat-detail">
              <div className="cat-name">
                {material.name}
                <span className="cat-price">
                  LKR {Number(material.cost_per_metre).toLocaleString()}/m
                </span>
              </div>
              <div className="cat-colours">
                {inStock.length === 0 ? (
                  <span className="cat-none">Currently unavailable</span>
                ) : (
                  inStock.map((colour) => (
                    <span className="cat-colour" key={colour.id} title={colour.name}>
                      <span className="colour-dot" style={{ background: colour.hex_code }} />
                      {colour.name}
                      {Number(colour.surcharge) > 0 && (
                        <em>+{Number(colour.surcharge).toLocaleString()}</em>
                      )}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>
        );
      })}

      {materials && (
        <>
          <p className="form-label-hint" style={{ margin: '18px 0 14px' }}>
            Fabric is charged by the metre, and how much your garment needs depends on its size and
            cut — the wizard itemises it before you commit to anything.
          </p>
          <Link to="/design" className="btn-filled" onClick={onClose}>
            Start designing
          </Link>
        </>
      )}
    </Modal>
  );
}
