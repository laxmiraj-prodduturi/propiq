import { marketingContent } from '../content';

export default function StatsSection() {
  const { stats } = marketingContent;

  return (
    <section className="mkt-stats">
      <div className="mkt-container">
        <div className="mkt-stats__grid">
          {stats.map((stat) => (
            <div key={stat.label} className="mkt-stat">
              <div className="mkt-stat__value">{stat.value}</div>
              <div className="mkt-stat__label">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
