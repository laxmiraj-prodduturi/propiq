import { Link } from 'react-router-dom';
import { marketingContent } from '../content';

export default function HeroSection() {
  const { hero } = marketingContent;

  return (
    <section className="mkt-hero">
      <div className="mkt-hero__bg">
        <div className="mkt-hero__grid" />
        <div className="mkt-hero__orb mkt-hero__orb--1" />
        <div className="mkt-hero__orb mkt-hero__orb--2" />
        <div className="mkt-hero__orb mkt-hero__orb--3" />
      </div>

      <div className="mkt-container">
        <div className="mkt-hero__content">
          <div className="mkt-eyebrow">{hero.eyebrow}</div>

          <h1 className="mkt-hero__headline">
            {hero.headline}<br />
            <span className="mkt-accent--brand">{hero.headlineAccent}</span>
          </h1>

          <p className="mkt-hero__sub">{hero.subheadline}</p>

          <div className="mkt-hero__actions">
            <Link to="/login" className="mkt-btn mkt-btn--primary mkt-btn--lg">
              {hero.cta.primary}
              <span>→</span>
            </Link>
            <button
              className="mkt-btn mkt-btn--ghost mkt-btn--lg"
              onClick={() => document.querySelector('#features')?.scrollIntoView({ behavior: 'smooth' })}
            >
              {hero.cta.secondary}
            </button>
          </div>

          <div className="mkt-hero__trusted">
            <div className="mkt-hero__trusted-dots">
              {['SK', 'MT', 'JL', 'NR', 'DC'].map((initials) => (
                <div key={initials} className="mkt-hero__trusted-dot">{initials}</div>
              ))}
            </div>
            {hero.trustedBy}
          </div>

          <div className="mkt-hero__preview">
            <div className="mkt-hero__window">
              <div className="mkt-hero__window-bar">
                <div className="mkt-hero__dot mkt-hero__dot--red" />
                <div className="mkt-hero__dot mkt-hero__dot--yellow" />
                <div className="mkt-hero__dot mkt-hero__dot--green" />
                <div className="mkt-hero__window-title">PropIQ AI Copilot</div>
              </div>
              <div className="mkt-hero__chat">
                <div className="mkt-chat-bubble mkt-chat-bubble--user">
                  What does my lease say about subletting?
                </div>
                <div className="mkt-chat-bubble mkt-chat-bubble--ai">
                  Based on your lease at 2454 Ronald McNair Way, <strong>subletting is not permitted</strong> without prior written consent from the property manager (Section 8.2). Violations may result in lease termination with 30 days notice.
                  <div>
                    <span className="mkt-chat-bubble__cite">📄 Lease §8.2 — Subletting</span>
                  </div>
                </div>
                <div className="mkt-chat-bubble mkt-chat-bubble--user">
                  I have a leaking pipe in the kitchen — it's pretty bad.
                </div>
                <div className="mkt-chat-bubble mkt-chat-bubble--ai">
                  Got it — classified as <strong>High urgency</strong>. I've created work order #WO-2841 and notified your property manager. A licensed plumber will contact you within 4 hours. I'll keep you updated on status changes.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
