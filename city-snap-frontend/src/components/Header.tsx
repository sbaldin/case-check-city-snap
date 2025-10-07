import { NavLink } from 'react-router-dom';

const NAV_ACTIVE_CLASS = 'text-primary fw-semibold';

const Header = () => (
  <header className="bg-white shadow-sm">
    <nav className="container d-flex justify-content-between align-items-center py-3">
      <NavLink to="/" className="mb-0 fw-bold navbar-brand text-decoration-none">
        CitySnap
      </NavLink>
      <div className="d-flex align-items-center gap-3">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `text-decoration-none nav-link px-0 ${isActive ? NAV_ACTIVE_CLASS : 'text-black'}`
          }
          end
        >
          Поиск
        </NavLink>
        <NavLink
          to="/building"
          className={({ isActive }) =>
            `text-decoration-none nav-link px-0 ${isActive ? NAV_ACTIVE_CLASS : 'text-black'}`
          }
        >
          Результат
        </NavLink>
        <a
          href="https://docs.google.com/document/d/1GfL4O149lIRNPgLiRS-NwLaaWsizv5HgNkYWnIEMNQU/edit?pli=1&tab=t.0"
          className="text-black text-decoration-none"
          target="_blank"
          rel="noreferrer"
        >
          О сервисе
        </a>
      </div>
    </nav>
  </header>
);

export default Header;
