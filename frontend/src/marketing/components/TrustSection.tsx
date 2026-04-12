import { marketingContent } from '../content';

export default function TrustSection() {
  const { trust } = marketingContent;

  return (
    <section id="trust" className="mkt-section mkt-section--alt">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">{trust.eyebrow}</div>
          <h2 className="mkt-section-heading">{trust.heading}</h2>
          <p className="mkt-section-sub mkt-section-sub--center">
            Property management involves sensitive data — financial records, personal information, legal documents.
            PropIQ is built to handle it with the care it deserves.
          </p>
        </div>

        <div className="mkt-trust__grid">
          {trust.points.map((point) => (
            <div key={point.title} className="mkt-trust-card">
              <span className="mkt-trust-card__icon">{point.icon}</span>
              <div className="mkt-trust-card__title">{point.title}</div>
              <div className="mkt-trust-card__desc">{point.description}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
