import { Outlet, NavLink, useNavigate, useSearchParams } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import { VidySetuMark } from '../shared/VidySetuLogo.jsx';
import Trans from '../shared/Trans.jsx';

export default function DemoDashboardLayout() {
  const { t, lang, setLang } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'add-problem';

  const handleLogout = () => {
    showToast(
      lang === 'hi'
        ? 'डेमो सत्र रीसेट हुआ।'
        : 'Demo session reset. No authentication required.'
    );
    navigate('/demo/problem-solutions');
  };

  const handleProfileClick = () => {
    navigate('/demo/problem-solutions?tab=profile');
  };

  const displayName = lang === 'hi' ? 'नागरिक उपयोगकर्ता' : 'Citizen User';

  return (
    <div className="app-shell">
      {/* TopBar matching VidySetu production visual design - zero authentication required */}
      <header className="topbar">
        <div
          className="topbar__logo"
          style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
          onClick={() => navigate('/demo/problem-solutions')}
        >
          <VidySetuMark size={24} />
          <span>{t.brand}<span>{t.brandSuffix}</span></span>
        </div>
        <div className="topbar__actions">
          <div className="lang-toggle" role="group" aria-label={t.langLabel}>
            <button
              type="button"
              className={`lang-toggle__btn${lang === 'en' ? ' lang-toggle__btn--active' : ''}`}
              aria-pressed={lang === 'en'}
              onClick={() => setLang('en')}
            >
              English
            </button>
            <button
              type="button"
              className={`lang-toggle__btn${lang === 'hi' ? ' lang-toggle__btn--active' : ''}`}
              aria-pressed={lang === 'hi'}
              onClick={() => setLang('hi')}
            >
              हिंदी
            </button>
          </div>
          <button
            type="button"
            className="btn btn-light btn-sm"
            onClick={handleProfileClick}
            title={lang === 'hi' ? 'प्रोफ़ाइल देखें' : 'View Profile'}
          >
            👤 {displayName}
          </button>
          <button
            type="button"
            className="btn btn-light"
            onClick={handleLogout}
          >
            {t.logout || (lang === 'hi' ? 'लॉग आउट' : 'Logout')}
          </button>
        </div>
      </header>

      {/* Main Layout Container with Dark Left Sidebar */}
      <div className="dashboard-layout">
        <aside className="sidebar">
          <div>
            <div className="sidebar__project">{<Trans text="⚡ SIH26043" />}</div>
            <div className="sidebar__role-badge">
              {lang === 'hi' ? 'नागरिक पोर्टल' : 'Citizen Portal'}
            </div>
            <nav className="sidebar__nav">
              <NavLink
                to="/demo/problem-solutions?tab=problems"
                className={`sidebar__link${currentTab === 'problems' ? ' is-active' : ''}`}
              >
                {lang === 'hi' ? '🔎 मेरी समस्याएं' : '🔎 My Problems'}
              </NavLink>
              <NavLink
                to="/demo/problem-solutions?tab=all-problems"
                className={`sidebar__link${currentTab === 'all-problems' ? ' is-active' : ''}`}
              >
                {lang === 'hi' ? '🌐 सभी समस्याएं' : '🌐 All Problems'}
              </NavLink>
              <NavLink
                to="/demo/problem-solutions"
                className={`sidebar__link${currentTab === 'add-problem' ? ' is-active' : ''}`}
              >
                {lang === 'hi' ? '➕ नई समस्या दर्ज करें' : '➕ Submit New Problem'}
              </NavLink>
              <NavLink
                to="/demo/problem-solutions?tab=profile"
                className={`sidebar__link${currentTab === 'profile' ? ' is-active' : ''}`}
              >
                {lang === 'hi' ? '👤 मेरी प्रोफ़ाइल' : '👤 Profile'}
              </NavLink>
            </nav>
          </div>
          <div className="sidebar__footer">{<Trans text="VidySetu v2.0 · Jharkhand" />}</div>
        </aside>

        <main className="dashboard-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
