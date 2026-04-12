import { marketingContent } from '../content';

export default function TestimonialsSection() {
  const { testimonials } = marketingContent;

  return (
    <section id="testimonials" className="mkt-section">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-eyebrow">What people say</div>
          <h2 className="mkt-section-heading">
            Don't take our word for it.
          </h2>
          <p className="mkt-section-sub mkt-section-sub--center">
            From independent landlords to regional management firms — PropIQ is changing how the industry operates.
          </p>
        </div>

        <div className="mkt-testimonials__grid">
          {testimonials.map((t) => (
            <div key={t.author} className="mkt-testimonial-card">
              <div className="mkt-testimonial__stars">
                {'★★★★★'.split('').map((s, i) => <span key={i}>{s}</span>)}
              </div>
              <p className="mkt-testimonial__quote">"{t.quote}"</p>
              <div className="mkt-testimonial__author">
                <div className="mkt-testimonial__avatar">{t.avatar}</div>
                <div>
                  <div className="mkt-testimonial__name">{t.author}</div>
                  <div className="mkt-testimonial__role">{t.role} · {t.portfolio}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
