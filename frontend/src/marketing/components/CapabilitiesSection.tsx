import { marketingContent } from '../content';

export default function CapabilitiesSection() {
  const { capabilities } = marketingContent;

  return (
    <section id="features" className="mkt-section">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">Core capabilities</div>
          <h2 className="mkt-section-heading">
            Everything your operation needs.{' '}
            <span className="mkt-accent">Nothing it doesn't.</span>
          </h2>
          <p className="mkt-section-sub mkt-section-sub--center">
            Specialized AI agents for every workflow — grounded in your data, controlled by your team.
          </p>
        </div>

        <div className="mkt-capabilities__grid">
          {capabilities.map((cap) => (
            <div key={cap.id} className="mkt-cap-card">
              <div className="mkt-cap-card__header">
                <div className="mkt-cap-card__icon">{cap.icon}</div>
                <div className="mkt-cap-card__tag">{cap.tag}</div>
              </div>
              <div className="mkt-cap-card__title">{cap.title}</div>
              <div className="mkt-cap-card__desc">{cap.description}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
