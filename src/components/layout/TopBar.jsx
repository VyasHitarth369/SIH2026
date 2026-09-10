import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';

export default function TopBar() {
  const { t, lang, setLang } = useLanguage();
  const { isAuthed, logout, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="topbar">
      <div className="topbar__logo">⚡ {t.brand}<span>{t.brandSuffix}</span></div>
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
        {isAuthed && (
          <>
            <button className="btn btn-light btn-sm" onClick={() => navigate('/profile')}>{user?.name || (lang === 'hi' ? 'मेरी प्रोफ़ाइल' : 'Profile')}</button>
            <button className="btn btn-light" onClick={handleLogout}>{t.logout}</button>
          </>
        )}
      </div>
    </header>
  );
}
