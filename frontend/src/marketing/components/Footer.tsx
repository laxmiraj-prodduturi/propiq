import { Link } from 'react-router-dom';
import { marketingContent } from '../content';

export default function Footer() {
  const { footer, brand } = marketingContent;

  const handleAnchor = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith('#')) {
      e.preventDefault();
      document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className="mkt-footer">
      <div className="mkt-container">
        <div className="mkt-footer__main">
          <div className="mkt-footer__brand">
            <div className="mkt-footer__logo">{brand.name}</div>
            <p className="mkt-footer__tagline">{footer.tagline}</p>
          </div>

          {footer.columns.map((col) => (
            <div key={col.heading}>
              <div className="mkt-footer__col-heading">{col.heading}</div>
              <ul className="mkt-footer__links">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="mkt-footer__link"
                      onClick={(e) => handleAnchor(e, link.href)}
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mkt-footer__bottom">
          <p className="mkt-footer__copy">{footer.copyright}</p>
          <ul className="mkt-footer__legal">
            {footer.legal.map((item) => (
              <li key={item.label}>
                <Link to={item.href} className="mkt-footer__legal-link">{item.label}</Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}
