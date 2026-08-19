import { useState } from 'react';

/**
 * Checkout details, shown after the customer confirms the AI preview.
 *
 * **Card details never leave the browser.** In production Stripe Checkout
 * collects them on its own hosted page, so this form's card fields exist only
 * for the simulated mode the project runs in without a Stripe key — they drive
 * the demo and are discarded on submit. They are deliberately not part of the
 * payload sent to our API: an API that has never seen a card number cannot log
 * one, store one, or leak one, and no amount of care downstream is as reliable
 * as never receiving it.
 */

const LUHN_MIN = 13;

/** Luhn check — catches a mistyped digit before it becomes a failed payment. */
function luhnValid(number) {
  const digits = number.replace(/\D/g, '');
  if (digits.length < LUHN_MIN) return false;
  let sum = 0;
  let double = false;
  for (let i = digits.length - 1; i >= 0; i -= 1) {
    let d = Number(digits[i]);
    if (double) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
    double = !double;
  }
  return sum % 10 === 0;
}

function expiryValid(value) {
  const match = /^(\d{2})\s*\/\s*(\d{2})$/.exec(value.trim());
  if (!match) return false;
  const month = Number(match[1]);
  if (month < 1 || month > 12) return false;
  const now = new Date();
  const year = 2000 + Number(match[2]);
  // Valid through the last day of the stated month.
  return new Date(year, month, 1) > now;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
// Sri Lankan numbers are 10 digits locally (0xx xxx xxxx) or +94 followed by 9.
const PHONE_RE = /^(?:\+?94|0)?\d{9,10}$/;

export default function CheckoutForm({
  total,
  currency,
  accountEmail,
  simulated,
  busy,
  error,
  onBack,
  onSubmit,
}) {
  const [form, setForm] = useState({
    customer_name: '',
    email: accountEmail ?? '',
    customer_phone: '',
    delivery_address: '',
    delivery_city: '',
    delivery_postcode: '',
  });
  const [card, setCard] = useState({ number: '', expiry: '', cvc: '', name: '' });
  const [touched, setTouched] = useState(false);

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const setCardField = (key) => (event) => setCard({ ...card, [key]: event.target.value });

  const problems = {
    customer_name: form.customer_name.trim().length < 2 && 'Please give the name for the parcel.',
    email: !EMAIL_RE.test(form.email.trim()) && 'That does not look like an email address.',
    customer_phone:
      !PHONE_RE.test(form.customer_phone.replace(/[\s-]/g, '')) &&
      'Please give a phone number we can reach you on.',
    delivery_address:
      form.delivery_address.trim().length < 6 && 'Please give the delivery address.',
    delivery_city: form.delivery_city.trim().length < 2 && 'Please give the city or town.',
    number: !luhnValid(card.number) && 'Check the card number.',
    expiry: !expiryValid(card.expiry) && 'Expiry must be MM/YY and in the future.',
    cvc: !/^\d{3,4}$/.test(card.cvc) && 'CVC is the 3 or 4 digits on the back.',
  };
  const valid = !Object.values(problems).some(Boolean);
  const show = (key) => touched && problems[key];

  function submit(event) {
    event.preventDefault();
    setTouched(true);
    if (!valid) return;
    // Only the delivery details are handed up. `card` stays in this component
    // and dies with it.
    onSubmit({
      ...form,
      email: form.email.trim(),
      customer_phone: form.customer_phone.replace(/[\s-]/g, ''),
    });
  }

  return (
    <form className="checkout-form" onSubmit={submit}>
      <div className="checkout-head">
        <h2>Delivery &amp; payment</h2>
        <p>
          Last step — where the garment goes and how you&apos;d like to pay.
          <strong>
            {' '}
            {currency} {Number(total).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </strong>
        </p>
      </div>

      {error && <div className="wizard-error">{error}</div>}

      <div className="checkout-section">
        <span className="form-label">Your details</span>
        <div className="field-row">
          <div className="field">
            <label htmlFor="co-name">Full name</label>
            <input
              id="co-name"
              value={form.customer_name}
              onChange={set('customer_name')}
              autoComplete="name"
            />
            {show('customer_name') && <p className="field-error">{problems.customer_name}</p>}
          </div>
          <div className="field">
            <label htmlFor="co-phone">Phone number</label>
            <input
              id="co-phone"
              value={form.customer_phone}
              onChange={set('customer_phone')}
              placeholder="077 123 4567"
              autoComplete="tel"
            />
            {show('customer_phone') && <p className="field-error">{problems.customer_phone}</p>}
          </div>
        </div>
        <div className="field">
          <label htmlFor="co-email">Email</label>
          <input
            id="co-email"
            type="email"
            value={form.email}
            onChange={set('email')}
            autoComplete="email"
          />
          <p className="form-label-hint">
            Your receipt, the design preview and every status update are sent here.
          </p>
          {show('email') && <p className="field-error">{problems.email}</p>}
        </div>
      </div>

      <div className="checkout-section">
        <span className="form-label">Delivery address</span>
        <div className="field">
          <label htmlFor="co-address">Street address</label>
          <input
            id="co-address"
            value={form.delivery_address}
            onChange={set('delivery_address')}
            autoComplete="street-address"
          />
          {show('delivery_address') && <p className="field-error">{problems.delivery_address}</p>}
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor="co-city">City / town</label>
            <input
              id="co-city"
              value={form.delivery_city}
              onChange={set('delivery_city')}
              autoComplete="address-level2"
            />
            {show('delivery_city') && <p className="field-error">{problems.delivery_city}</p>}
          </div>
          <div className="field">
            <label htmlFor="co-postcode">Postcode</label>
            <input
              id="co-postcode"
              value={form.delivery_postcode}
              onChange={set('delivery_postcode')}
              autoComplete="postal-code"
            />
          </div>
        </div>
      </div>

      <div className="checkout-section">
        <span className="form-label">Card</span>
        <div className="field">
          <label htmlFor="co-cardname">Name on card</label>
          <input
            id="co-cardname"
            value={card.name}
            onChange={setCardField('name')}
            autoComplete="cc-name"
          />
        </div>
        <div className="field">
          <label htmlFor="co-cardnumber">Card number</label>
          <input
            id="co-cardnumber"
            inputMode="numeric"
            value={card.number}
            onChange={setCardField('number')}
            placeholder="4242 4242 4242 4242"
            autoComplete="cc-number"
          />
          {show('number') && <p className="field-error">{problems.number}</p>}
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor="co-expiry">Expiry</label>
            <input
              id="co-expiry"
              value={card.expiry}
              onChange={setCardField('expiry')}
              placeholder="MM/YY"
              autoComplete="cc-exp"
            />
            {show('expiry') && <p className="field-error">{problems.expiry}</p>}
          </div>
          <div className="field">
            <label htmlFor="co-cvc">CVC</label>
            <input
              id="co-cvc"
              inputMode="numeric"
              value={card.cvc}
              onChange={setCardField('cvc')}
              placeholder="123"
              autoComplete="cc-csc"
            />
            {show('cvc') && <p className="field-error">{problems.cvc}</p>}
          </div>
        </div>
        <p className="checkout-secure">
          {simulated
            ? 'Demonstration mode — no charge is made and these card details are never sent anywhere. Try 4242 4242 4242 4242.'
            : 'Card details are handled by Stripe on their own secure page and never reach our servers.'}
        </p>
      </div>

      <div className="checkout-actions">
        <button type="button" className="btn-outline" onClick={onBack} disabled={busy}>
          ← Back to preview
        </button>
        <button type="submit" className="btn-filled" disabled={busy}>
          {busy
            ? 'Placing your order…'
            : `Pay ${currency} ${Number(total).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
        </button>
      </div>
    </form>
  );
}
