import { Link } from 'react-router-dom';
import { marketingContent } from '../content';

export default function CTASection() {
  const { cta } = marketingContent;

  return (
    <section className="mkt-section mkt-cta">
      <div className="mkt-cta__bg" />
      <div className="mkt-container">
        <div className="mkt-cta__content">
          <div className="mkt-eyebrow" style={{ margin: '0 auto 20px' }}>{cta.eyebrow}</div>
          <h2 className="mkt-cta__heading">
            <span className="mkt-accent--brand">{cta.heading}</span>
          </h2>
          <p className="mkt-cta__sub">{cta.description}</p>
          <div className="mkt-cta__actions">
            <Link to="/login" className="mkt-btn mkt-btn--primary mkt-btn--lg">
              {cta.primary} →
            </Link>
            <button className="mkt-btn mkt-btn--ghost mkt-btn--lg">
              {cta.secondary}
            </button>
          </div>
          <p className="mkt-cta__note">No credit card required · 14-day free trial · Cancel anytime</p>
        </div>
      </div>
    </section>
  );
}
