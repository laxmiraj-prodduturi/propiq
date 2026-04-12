import { marketingContent } from '../content';

export default function ComparisonSection() {
  const { differentiators, brand } = marketingContent;

  return (
    <section className="mkt-section">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">Why switch</div>
          <h2 className="mkt-section-heading">{differentiators.heading}</h2>
          <p className="mkt-section-sub mkt-section-sub--center">
            Traditional software makes you do the work. PropIQ does the work with you.
          </p>
        </div>

        <div className="mkt-comparison__table">
          <div className="mkt-comparison__header">
            <div className="mkt-comparison__col-head" style={{ gridColumn: 1 }}>Area</div>
            <div className="mkt-comparison__col-head">Traditional Software</div>
            <div className="mkt-comparison__col-head mkt-comparison__col-head--propiq">
              <span>✦</span> {brand.name}
            </div>
          </div>

          {differentiators.comparison.map((row, i) => (
            <div key={i} className="mkt-comparison__row">
              <div className="mkt-comparison__cell" style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {['Workflow', 'Reporting', 'Intelligence', 'Control', 'Experience', 'Timing'][i]}
              </div>
              <div className="mkt-comparison__cell">
                <span className="mkt-comparison__x">✕</span>
                {row.traditional}
              </div>
              <div className="mkt-comparison__cell mkt-comparison__cell--propiq">
                <span className="mkt-comparison__check">✓</span>
                {row.propiq}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
