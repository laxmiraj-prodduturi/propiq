import { useState } from 'react';
import { marketingContent } from '../content';

export default function PersonasSection() {
  const { personas } = marketingContent;
  const [activeId, setActiveId] = useState<string>(personas[0].id);
  const active = personas.find((p) => p.id === activeId)!;

  return (
    <section id="personas" className="mkt-section mkt-section--alt">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">Built for everyone</div>
          <h2 className="mkt-section-heading">One platform. Three personas. Zero compromises.</h2>
          <p className="mkt-section-sub mkt-section-sub--center">
            PropIQ adapts its interface and intelligence to each role — owners see what owners need,
            managers see what managers need, tenants get a simple experience that actually works.
          </p>
        </div>

        <div className="mkt-personas__tabs">
          {personas.map((p) => (
            <button
              key={p.id}
              className={`mkt-personas__tab${activeId === p.id ? ' mkt-personas__tab--active' : ''}`}
              onClick={() => setActiveId(p.id)}
            >
              <span>{p.icon}</span>
              {p.label}
            </button>
          ))}
        </div>

        <div className="mkt-personas__panel">
          <div>
            <div className="mkt-personas__sub">{active.label}</div>
            <h3 className="mkt-personas__heading">{active.heading}</h3>
            <p className="mkt-personas__desc">{active.description}</p>
            <ul className="mkt-personas__benefits">
              {active.benefits.map((b) => (
                <li key={b} className="mkt-personas__benefit">
                  <span className="mkt-personas__check">✓</span>
                  {b}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="mkt-personas__quote-card">
              <div className="mkt-personas__quote-mark">"</div>
              <p className="mkt-personas__quote-text">{active.quote}</p>
              <div className="mkt-personas__quote-author">— {active.quoteAuthor}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
