import Trans from '../shared/Trans.jsx';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { getNavItems, getRoleBadge } from './navConfig';

export default function Sidebar() {
  const { user } = useAuth();
  const { t, lang } = useLanguage();
  const items = getNavItems(user, t, lang);

  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar__project">{<Trans text="⚡ SIH26043" />}</div>
        <div className="sidebar__role-badge">{getRoleBadge(user, t, lang)}</div>
        <nav className="sidebar__nav">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar__link${isActive ? ' is-active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="sidebar__footer">{<Trans text="VidySetu v2.0 · Jharkhand" />}</div>
    </aside>
  );
}
