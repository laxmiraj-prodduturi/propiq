import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { marketingContent } from '../content';

export default function MarketingNav() {
  const [scrolled, setScrolled] = useState(false);
  const { brand, nav } = marketingContent;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleAnchor = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith('#')) {
      e.preventDefault();
      document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <nav className={`mkt-nav${scrolled ? ' mkt-nav--scrolled' : ''}`}>
      <div className="mkt-nav__inner">
        <a href="#" className="mkt-nav__logo">{brand.name}</a>

        <ul className="mkt-nav__links">
          {nav.links.map((link) => (
            <li key={link.label}>
              <a
                href={link.href}
                className="mkt-nav__link"
                onClick={(e) => handleAnchor(e, link.href)}
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="mkt-nav__actions">
          <Link to={nav.login.href} className="mkt-nav__signin">
            {nav.login.label}
          </Link>
          <Link to={nav.cta.href} className="mkt-btn mkt-btn--primary">
            {nav.cta.label}
          </Link>
        </div>
      </div>
    </nav>
  );
}
