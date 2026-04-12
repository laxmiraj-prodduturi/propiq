import { marketingContent } from '../content';

export default function ProblemSection() {
  const { problem } = marketingContent;

  return (
    <section className="mkt-section">
      <div className="mkt-container">
        <div style={{ maxWidth: 560 }}>
          <div className="mkt-eyebrow">{problem.eyebrow}</div>
          <h2 className="mkt-section-heading">{problem.heading}</h2>
          <p className="mkt-section-sub">{problem.description}</p>
        </div>

        <div className="mkt-problem__grid">
          {problem.painPoints.map((point) => (
            <div key={point.title} className="mkt-problem-card">
              <div className="mkt-problem-card__icon">{point.icon}</div>
              <div className="mkt-problem-card__body">
                <div className="mkt-problem-card__title">{point.title}</div>
                <div className="mkt-problem-card__desc">{point.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
