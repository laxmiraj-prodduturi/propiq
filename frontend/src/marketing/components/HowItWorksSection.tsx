import { marketingContent } from '../content';

export default function HowItWorksSection() {
  const { howItWorks } = marketingContent;

  return (
    <section id="how-it-works" className="mkt-section mkt-section--alt">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">{howItWorks.eyebrow}</div>
          <h2 className="mkt-section-heading">{howItWorks.heading}</h2>
          <p className="mkt-section-sub mkt-section-sub--center">{howItWorks.description}</p>
        </div>

        <div className="mkt-how__steps">
          {howItWorks.steps.map((step) => (
            <div key={step.step} className="mkt-how__step">
              <div className="mkt-how__number">{step.step}</div>
              <div className="mkt-how__body">
                <div className="mkt-how__title">{step.title}</div>
                <div className="mkt-how__desc">{step.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
