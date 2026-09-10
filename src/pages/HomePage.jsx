import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth, ROLES } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import TopBar from '../components/layout/TopBar';
import RoleFields, { validateRoleFields, normalizeRoleFields } from '../components/auth/RoleFields';
import Trans from '../components/shared/Trans.jsx';

const ROLE_HOME = {
  citizen: '/citizen/problems',
  student: '/student/projects',
  faculty: '/faculty/projects',
  'university-admin': '/university-admin/dashboard',
  government: '/government/dashboard',
  industry: '/industry-employee/dashboard',
};

export default function HomePage() {
  const { t, lang } = useLanguage();
  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [authMode, setAuthMode] = useState('login');
  const [name, setName] = useState('Rahul Sharma');
  const [city, setCity] = useState('Ranchi, Jharkhand');
  const [email, setEmail] = useState('citizen@samadhan.gov.in');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('citizen');
  const [roleValues, setRoleValues] = useState({});

  const setRoleValue = (key, value) => setRoleValues((prev) => ({ ...prev, [key]: value }));

  const handleRoleChange = (newRole) => {
    setRole(newRole);
    setRoleValues({});
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Section 7: password and stakeholder role are mandatory; login must
    // never succeed with a missing password.
    if (!email.trim()) {
      showToast(t.fillEmail);
      return;
    }
    if (!password.trim()) {
      showToast(t.fillPassword);
      return;
    }
    if (!role) {
      showToast(t.selectRole);
      return;
    }

    // Section 16: registration requires role-specific fields to be filled in.
    if (authMode === 'signup') {
      const missing = validateRoleFields(role, roleValues, lang);
      if (missing.length > 0) {
        showToast(`${t.fillRequiredFieldsPrefix}${missing.join(', ')}`);
        return;
      }
    }

    let session;
    try {
      session = login({
        name,
        email: email.trim(),
        password,
        role,
        profile: { city, ...normalizeRoleFields(role, roleValues) },
      });
    } catch (err) {
      showToast(<Trans text={err.message} />);
      return;
    }

    navigate(ROLE_HOME[session.role] || '/');
  };

  return (
    <div className="app-shell">
      <TopBar />

      <section className="hero">
        <h1>{t.heroTitle}</h1>
        <p>{t.heroSub}</p>
        <div className="hero__stats">
          <div className="hero-stat"><div className="hero-stat__num">1,240+</div><div className="hero-stat__label">{t.stat1}</div></div>
          <div className="hero-stat"><div className="hero-stat__num">450+</div><div className="hero-stat__label">{t.stat2}</div></div>
          <div className="hero-stat"><div className="hero-stat__num">85+</div><div className="hero-stat__label">{t.stat3}</div></div>
        </div>
      </section>

      <div className="auth-container">
        <div className="auth-tabs">
          <div className={`auth-tab${authMode === 'login' ? ' is-active' : ''}`} onClick={() => setAuthMode('login')}>{t.loginTab}</div>
          <div className={`auth-tab${authMode === 'signup' ? ' is-active' : ''}`} onClick={() => setAuthMode('signup')}>{t.signupTab}</div>
        </div>

        <h2 className="auth-heading">{authMode === 'login' ? t.loginHeading : t.signupHeading}</h2>
        <p className="auth-sub">{t.loginSub}</p>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>{t.lblRegRole} *</label>
            {/* Section 8: no emojis/icons next to stakeholder options on this page — plain text only. */}
            <select value={role} onChange={(e) => handleRoleChange(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>{t[r.labelKey] || r.label}</option>
              ))}
            </select>
          </div>

          {authMode === 'signup' && (
            <>
              <div className="field">
                <label>{t.lblRegName}</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              {role === 'citizen' && (
                <div className="field">
                  <label>{t.lblRegCity}</label>
                  <input type="text" value={city} onChange={(e) => setCity(e.target.value)} />
                </div>
              )}
              <RoleFields role={role} values={roleValues} onChange={setRoleValue} />
            </>
          )}

          <div className="field">
            <label>{t.lblRegEmail} *</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>

          <div className="field">
            <label>{t.lblRegPass} *</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••" required />
          </div>

          <button type="submit" className="btn btn-primary btn-block">{t.btnLoginSubmit}</button>
        </form>
      </div>
    </div>
  );
}
