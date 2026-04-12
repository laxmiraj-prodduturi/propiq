import { Link } from 'react-router-dom';
import { marketingContent } from '../content';

export default function PricingSection() {
  const { pricing } = marketingContent;

  return (
    <section id="pricing" className="mkt-section mkt-section--alt">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">Pricing</div>
          <h2 className="mkt-section-heading">Simple pricing. Real value.</h2>
          <p className="mkt-section-sub mkt-section-sub--center">
            Start free. No credit card required. Upgrade when you're ready to scale.
          </p>
        </div>

        <div className="mkt-pricing__grid">
          {pricing.map((tier) => (
            <div
              key={tier.tier}
              className={`mkt-pricing-card${tier.highlighted ? ' mkt-pricing-card--highlighted' : ''}`}
            >
              {'badge' in tier && tier.badge && (
                <div className="mkt-pricing__badge">{tier.badge}</div>
              )}

              <div className="mkt-pricing__tier">{tier.tier}</div>

              <div className="mkt-pricing__price">
                <span className="mkt-pricing__amount">{tier.price}</span>
                {tier.period && <span className="mkt-pricing__period">{tier.period}</span>}
              </div>

              <div className="mkt-pricing__desc">{tier.description}</div>
              <div className="mkt-pricing__units">📦 {tier.units}</div>

              <div className="mkt-pricing__divider" />

              <ul className="mkt-pricing__features">
                {tier.features.map((f) => (
                  <li key={f} className="mkt-pricing__feature">
                    <span className="mkt-pricing__feature-check">✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                to="/login"
                className={`mkt-btn ${tier.highlighted ? 'mkt-btn--primary' : 'mkt-btn--outline'}`}
                style={{ width: '100%', justifyContent: 'center' }}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
