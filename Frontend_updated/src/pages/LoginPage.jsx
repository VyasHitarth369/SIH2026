import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import Trans, { useTranslate } from '../components/shared/Trans.jsx';
import { VidySetuMark } from '../components/shared/VidySetuLogo.jsx';
import { supabase } from '../services/supabaseClient';
import { jharkhandCities } from '../data/locations';
import { STUDENT_APPROVED_UNIVERSITIES } from '../data/orgData';
import '../styles/auth.css';

const ROLE_HOME = {
  citizen: '/citizen/problems',
  student: '/student/projects',
  faculty: '/faculty/projects',
  university_admin: '/university-admin/dashboard',
  'university-admin': '/university-admin/dashboard',
  government: '/government/dashboard',
  industry_employee: '/industry-employee/dashboard',
  industry: '/industry-employee/dashboard',
};

const JHARKHAND_DISTRICTS = [
  'Ranchi', 'Dhanbad', 'East Singhbhum', 'Hazaribagh', 'Bokaro',
  'Deoghar', 'Giridih', 'Ramgarh', 'Palamu', 'Chatra',
  'Gumla', 'Simdega', 'Khunti', 'Lohardaga', 'Latehar',
  'Saraikela-Kharsawan', 'Jamtara', 'Godda', 'Sahibganj',
  'Pakur', 'Koderma', 'Garhwa', 'West Singhbhum',
];

const UNIVERSITIES = [
  'Vishwakarma Government Engineering College (VGEC)',
  'Gujarat Technological University (GTU)',
  'Indian Institute of Technology (IIT)',
  'National Institute of Technology (NIT)',
  'Other University',
];

const COMPANIES = [
  'Tata Consultancy Services (TCS)',
  'Infosys',
  'Wipro',
  'HCLTech',
  'Accenture',
  'Other Company',
];

const DOMAINS = [
  'Web Development',
  'App Development',
  'AI / ML',
  'Data Science',
  'Cyber Security',
  'IoT',
  'Cloud Computing',
  'Robotics',
  'Other',
];

export default function LoginPage({ defaultMode = 'login' }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login, signup, homePath } = useAuth();
  const { lang, setLang } = useLanguage();
  const { showToast } = useToast();
  const t = useTranslate();

  const [mode, setMode] = useState(
    location.pathname === '/signup' || defaultMode === 'signup' ? 'signup' : 'login'
  );

  // If already logged in, redirect to authoritative portal
  useEffect(() => {
    if (user) {
      navigate(homePath || '/');
    }
  }, [user, homePath, navigate]);

  useEffect(() => {
    if (location.pathname === '/signup' || defaultMode === 'signup') {
      setMode('signup');
    } else if (location.pathname === '/login' || defaultMode === 'login') {
      setMode('login');
    }
  }, [location.pathname, defaultMode]);

  // General fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [city, setCity] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Role Selection (Signup metadata only - never authoritative authorization)
  const [selectedRole, setSelectedRole] = useState('citizen');

  // Role-specific fields state
  const [roleFields, setRoleFields] = useState({
    district: '',
    authorityId: '',
    governmentDept: '',
    governmentDesignation: '',
    university: '',
    universityDesignation: '',
    studentUniversity: '',
    studentDepartment: '',
    studentId: '',
    studentDomain: '',
    studentSkill: '',
    linkedinId: '',
    githubId: '',
    facultyUniversity: '',
    facultyId: '',
    researchArea: '',
    facultyExpertise: '',
    companyName: '',
    companyEmail: '',
    employeeId: '',
    industryDesignation: '',
    industryDomain: '',
    industryExpertise: '',
  });

  // Forgot password modal
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitting, setForgotSubmitting] = useState(false);

  const handleRoleFieldChange = (field, value) => {
    setRoleFields((prev) => ({ ...prev, [field]: value }));
  };

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setRoleFields({
      district: '',
      authorityId: '',
      governmentDept: '',
      governmentDesignation: '',
      university: '',
      universityDesignation: '',
      studentUniversity: '',
      studentDepartment: '',
      studentId: '',
      studentDomain: '',
      studentSkill: '',
      linkedinId: '',
      githubId: '',
      facultyUniversity: '',
      facultyId: '',
      researchArea: '',
      facultyExpertise: '',
      companyName: '',
      companyEmail: '',
      employeeId: '',
      industryDesignation: '',
      industryDomain: '',
      industryExpertise: '',
    });
  };

  // Password Strength Calculation
  const getPasswordStrength = () => {
    if (!password) return { level: 0, text: '', lines: ['#E2E8F0', '#E2E8F0', '#E2E8F0'] };
    if (password.length < 6) {
      return {
        level: 1,
        text: t('Weak password'),
        lines: ['#DC2626', '#E2E8F0', '#E2E8F0'],
      };
    }
    if (password.length < 10) {
      return {
        level: 2,
        text: t('Moderate password'),
        lines: ['#B45309', '#B45309', '#E2E8F0'],
      };
    }
    return {
      level: 3,
      text: t('Strong password'),
      lines: ['#15803D', '#15803D', '#15803D'],
    };
  };

  const strength = getPasswordStrength();

  const handleModeChange = (newMode) => {
    setMode(newMode);
    if (newMode === 'login' && location.pathname === '/signup') {
      navigate('/login', { replace: true });
    } else if (newMode === 'signup' && location.pathname === '/login') {
      navigate('/signup', { replace: true });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!email.trim()) {
      showToast(t('Please enter your email address.'));
      return;
    }
    if (!password.trim()) {
      showToast(t('Please enter your password.'));
      return;
    }

    setSubmitting(true);

    if (mode === 'login') {
      try {
        const session = await login({
          email: email.trim(),
          password,
        });
        showToast(t('Login successful'));
        navigate(ROLE_HOME[session.role] || homePath || '/');
      } catch (err) {
        showToast(err.message || t('Login failed'));
      } finally {
        setSubmitting(false);
      }
      return;
    }

    // SIGNUP MODE
    if (!city || !city.trim()) {
      showToast(t('Please select your city.'));
      setSubmitting(false);
      return;
    }

    if (password !== confirmPassword) {
      showToast(t('Passwords do not match.'));
      setSubmitting(false);
      return;
    }

    if (!agreedToTerms) {
      showToast(t('Please accept the Terms of Use and Privacy Policy.'));
      setSubmitting(false);
      return;
    }

    // Validate role-specific required fields
    if (selectedRole === 'government') {
      if (!roleFields.authorityId.trim() || !roleFields.governmentDept.trim() || !roleFields.governmentDesignation.trim()) {
        showToast(t('Please fill in Authority ID, Department, and Designation.'));
        setSubmitting(false);
        return;
      }
    } else if (selectedRole === 'university_admin') {
      if (!roleFields.university || !roleFields.universityDesignation.trim()) {
        showToast(t('Please select a University and enter Designation.'));
        setSubmitting(false);
        return;
      }
    } else if (selectedRole === 'student') {
      if (!roleFields.studentUniversity || !STUDENT_APPROVED_UNIVERSITIES.includes(roleFields.studentUniversity)) {
        showToast(t('Please select an approved university.'));
        setSubmitting(false);
        return;
      }
      if (!roleFields.studentDepartment.trim() || !roleFields.studentId.trim() || !roleFields.studentDomain) {
        showToast(t('Please fill in University, Department, Student ID, and Domain.'));
        setSubmitting(false);
        return;
      }
    } else if (selectedRole === 'faculty') {
      if (!roleFields.facultyUniversity || !roleFields.facultyId.trim() || !roleFields.researchArea.trim() || !roleFields.facultyExpertise.trim()) {
        showToast(t('Please fill in University, Faculty ID, Research Area, and Expertise.'));
        setSubmitting(false);
        return;
      }
    } else if (selectedRole === 'industry_employee') {
      if (!roleFields.companyName || !roleFields.companyEmail.trim() || !roleFields.employeeId.trim() || !roleFields.industryDesignation.trim() || !roleFields.industryDomain) {
        showToast(t('Please fill in Company, Company Email, Employee ID, Designation, and Domain.'));
        setSubmitting(false);
        return;
      }
    }

    let profilePayload = { city: city.trim() };
    if (selectedRole === 'citizen') {
      profilePayload.district = roleFields.district || '';
    } else if (selectedRole === 'government') {
      profilePayload.authorityId = roleFields.authorityId.trim();
      profilePayload.department = roleFields.governmentDept.trim();
      profilePayload.designation = roleFields.governmentDesignation.trim();
    } else if (selectedRole === 'university_admin') {
      profilePayload.university = roleFields.university;
      profilePayload.designation = roleFields.universityDesignation.trim();
    } else if (selectedRole === 'student') {
      profilePayload.university = roleFields.studentUniversity;
      profilePayload.department = roleFields.studentDepartment.trim();
      profilePayload.studentId = roleFields.studentId.trim();
      profilePayload.domain = roleFields.studentDomain;
      if (roleFields.studentSkill) profilePayload.skills = roleFields.studentSkill;
      if (roleFields.linkedinId) profilePayload.linkedinId = roleFields.linkedinId.trim();
      if (roleFields.githubId) profilePayload.githubId = roleFields.githubId.trim();
    } else if (selectedRole === 'faculty') {
      profilePayload.university = roleFields.facultyUniversity;
      profilePayload.facultyId = roleFields.facultyId.trim();
      profilePayload.researchArea = roleFields.researchArea.trim();
      profilePayload.expertise = roleFields.facultyExpertise.trim();
    } else if (selectedRole === 'industry_employee') {
      profilePayload.company = roleFields.companyName;
      profilePayload.companyName = roleFields.companyName;
      profilePayload.companyEmail = roleFields.companyEmail.trim();
      profilePayload.employeeId = roleFields.employeeId.trim();
      profilePayload.designation = roleFields.industryDesignation.trim();
      profilePayload.domain = roleFields.industryDomain;
      if (roleFields.industryExpertise) profilePayload.expertise = roleFields.industryExpertise.trim();
    }

    try {
      const res = await signup({
        name: fullName.trim(),
        email: email.trim(),
        password,
        role: selectedRole,
        city: city.trim(),
        profile: profilePayload,
      });

      if (res.needsEmailConfirmation) {
        showToast(t('Account created! Please check your email to verify your account before logging in.'));
        setMode('login');
      } else {
        showToast(t('Account created successfully'));
        navigate(ROLE_HOME[res.user?.role] || homePath || '/');
      }
    } catch (err) {
      showToast(err.message || t('Signup failed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!forgotEmail.trim()) {
      showToast(t('Please enter your email address.'));
      return;
    }
    setForgotSubmitting(true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(forgotEmail.trim(), {
        redirectTo: window.location.origin + '/login',
      });
      if (error) {
        showToast(error.message);
      } else {
        showToast(t('Password reset link sent! Check your inbox.'));
        setShowForgotModal(false);
        setForgotEmail('');
      }
    } catch (err) {
      showToast(err.message || t('Could not send reset link'));
    } finally {
      setForgotSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      {/* =====================================================
           TOP GOVERNMENT BAR
      ====================================================== */}
      <div className="gov-bar">
        <div className="gov-bar-inner">
          <div className="gov-left">
            <div className="gov-emblem">IND</div>
            <span><Trans text="Government & Civic Services Portal" /></span>
          </div>

          <div className="gov-right">
            <span><Trans text="Accessibility" /></span>
            <span><Trans text="Help & Support" /></span>
          </div>
        </div>
      </div>

      {/* =====================================================
           HEADER
      ====================================================== */}
      <header className="header">
        <div className="header-inner">
          <div className="brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <VidySetuMark size={36} />
            <div>
              <div className="brand-name">
                <span style={{ color: '#0E387A' }}>Vidy</span><span style={{ color: '#059669' }}>Setu</span>
              </div>
              <div className="brand-subtitle">
                <Trans text="Civic Problem Resolution Platform" />
              </div>
            </div>
          </div>

          <div className="header-right">
            <select
              className="language-select"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              aria-label={t("Select Language")}
            >
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
            </select>

            <button className="home-link" onClick={() => navigate('/')}>
              <Trans text="← Back to Home" />
            </button>
          </div>
        </div>
      </header>

      {/* =====================================================
           MAIN AUTH SECTION
      ====================================================== */}
      <main className="main">
        <div className="auth-wrapper">
          {/* LEFT INFORMATION PANEL */}
          <section className="info-panel">
            <div className="info-content">
              <div className="info-badge">
                <span className="live-dot"></span>
                <Trans text="SECURE CIVIC ACCESS" />
              </div>

              <h1>
                <Trans text="One platform." />
                <br />
                <span><Trans text="Many possibilities." /></span>
              </h1>

              <p className="info-description">
                <Trans text="Access VidySetu to report civic problems, track resolutions, collaborate on solutions and connect communities with institutions." />
              </p>

              {/* ECOSYSTEM FLOW */}
              <div className="ecosystem-mini">
                <div className="ecosystem-title"><Trans text="VidySetu Ecosystem" /></div>
                <div className="ecosystem-flow">
                  <div className="ecosystem-item">👤 <Trans text="Citizen" /></div>
                  <div className="ecosystem-arrow">→</div>
                  <div className="ecosystem-item">🏛️ <Trans text="University" /></div>
                  <div className="ecosystem-arrow">→</div>
                  <div className="ecosystem-item">🎓 <Trans text="Student" /></div>
                  <div className="ecosystem-arrow">→</div>
                  <div className="ecosystem-item">🏭 <Trans text="Industry" /></div>
                  <div className="ecosystem-arrow">→</div>
                  <div className="ecosystem-item">🏢 <Trans text="Government" /></div>
                </div>
              </div>
            </div>

            {/* SECURITY BOX */}
            <div className="security-box">
              <div className="security-item">
                <div className="security-icon">🔒</div>
                <span><Trans text="Secure authentication" /></span>
              </div>

              <div className="security-item">
                <div className="security-icon">✓</div>
                <span><Trans text="Role-based portal access" /></span>
              </div>

              <div className="security-item">
                <div className="security-icon">🌐</div>
                <span><Trans text="Multilingual civic platform" /></span>
              </div>
            </div>
          </section>

          {/* RIGHT AUTH FORM PANEL */}
          <section className="auth-panel">
            <div className="auth-heading">
              <h2>{mode === 'signup' ? <Trans text="Create your account" /> : <Trans text="Welcome back" />}</h2>
              <p>
                {mode === 'signup'
                  ? <Trans text="Register to join the VidySetu civic ecosystem." />
                  : <Trans text="Sign in to access your VidySetu portal." />}
              </p>
            </div>

            {/* LOGIN / SIGNUP TABS */}
            <div className="tabs">
              <button
                type="button"
                className={`tab ${mode === 'login' ? 'active' : ''}`}
                onClick={() => handleModeChange('login')}
              >
                <Trans text="Log In" />
              </button>

              <button
                type="button"
                className={`tab ${mode === 'signup' ? 'active' : ''}`}
                onClick={() => handleModeChange('signup')}
              >
                <Trans text="Sign Up" />
              </button>
            </div>

            {/* ROLE SELECTION (SIGN UP ONLY) */}
            {mode === 'signup' && (
              <div id="roleSelection">
                <label className="form-label"><Trans text="Select Portal Role" /></label>
                <div className="role-grid">
                  <div
                    className={`role-card ${selectedRole === 'citizen' ? 'active' : ''}`}
                    onClick={() => handleRoleSelect('citizen')}
                  >
                    <div className="role-icon">👤</div>
                    <div className="role-name"><Trans text="Citizen" /></div>
                  </div>

                  <div
                    className={`role-card ${selectedRole === 'government' ? 'active' : ''}`}
                    onClick={() => handleRoleSelect('government')}
                  >
                    <div className="role-icon">🏛️</div>
                    <div className="role-name"><Trans text="Government" /></div>
                  </div>

                  <div
                    className={`role-card ${selectedRole === 'university_admin' ? 'active' : ''}`}
                    onClick={() => handleRoleSelect('university_admin')}
                  >
                    <div className="role-icon">🏫</div>
                    <div className="role-name"><Trans text="University" /></div>
                  </div>

                  <div
                    className={`role-card ${selectedRole === 'student' ? 'active' : ''}`}
                    onClick={() => handleRoleSelect('student')}
                  >
                    <div className="role-icon">🎓</div>
                    <div className="role-name"><Trans text="Student" /></div>
                  </div>

                  <div
                    className={`role-card ${selectedRole === 'faculty' ? 'active' : ''}`}
                    onClick={() => handleRoleSelect('faculty')}
                  >
                    <div className="role-icon">👨‍🏫</div>
                    <div className="role-name"><Trans text="Faculty" /></div>
                  </div>

                  <div
                    className={`role-card ${selectedRole === 'industry_employee' ? 'active' : ''}`}
                    onClick={() => handleRoleSelect('industry_employee')}
                  >
                    <div className="role-icon">🏭</div>
                    <div className="role-name"><Trans text="Industry" /></div>
                  </div>
                </div>
              </div>
            )}

            {/* FORM */}
            <form onSubmit={handleSubmit}>
              {/* FULL NAME (SIGN UP ONLY) */}
              {mode === 'signup' && (
                <div className="form-group">
                  <label className="form-label"><Trans text="Full Name" /></label>
                  <div className="input-wrapper">
                    <span className="input-icon">👤</span>
                    <input
                      className="form-input with-icon"
                      type="text"
                      placeholder={t("Enter your full name")}
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                    />
                  </div>
                </div>
              )}

              {/* EMAIL */}
              <div className="form-group">
                <label className="form-label"><Trans text="Email Address" /></label>
                <div className="input-wrapper">
                  <span className="input-icon">✉</span>
                  <input
                    className="form-input with-icon"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* ROLE-SPECIFIC SIGNUP FIELDS */}
              {mode === 'signup' && (
                <>
                  {/* MANDATORY CITY FOR ALL SIGNUPS */}
                  <div className="form-group">
                    <label className="form-label"><Trans text="City *" /></label>
                    <div className="input-wrapper">
                      <span className="input-icon">📍</span>
                      <select
                        className="form-select with-icon"
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        required
                      >
                        <option value="">{t("Select your city…")}</option>
                        {jharkhandCities.map((c) => (
                          <option key={c.value} value={c.value}>
                            {c.en} ({c.hi})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {/* CITIZEN */}
                  {selectedRole === 'citizen' && (
                    <div className="form-group">
                      <label className="form-label"><Trans text="District" /></label>
                      <select
                        className="form-select"
                        value={roleFields.district}
                        onChange={(e) => handleRoleFieldChange('district', e.target.value)}
                      >
                        <option value="">{t("Select District")}</option>
                        {JHARKHAND_DISTRICTS.map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* GOVERNMENT */}
                  {selectedRole === 'government' && (
                    <>
                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="Authority ID *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter Authority ID")}
                            value={roleFields.authorityId}
                            onChange={(e) => handleRoleFieldChange('authorityId', e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="Government Department *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter government department")}
                            value={roleFields.governmentDept}
                            onChange={(e) => handleRoleFieldChange('governmentDept', e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="form-label"><Trans text="Designation *" /></label>
                        <input
                          className="form-input"
                          type="text"
                          placeholder={t("Enter designation")}
                          value={roleFields.governmentDesignation}
                          onChange={(e) => handleRoleFieldChange('governmentDesignation', e.target.value)}
                          required
                        />
                      </div>
                    </>
                  )}

                  {/* UNIVERSITY */}
                  {selectedRole === 'university_admin' && (
                    <>
                      <div className="form-group">
                        <label className="form-label"><Trans text="Select University *" /></label>
                        <select
                          className="form-select"
                          value={roleFields.university}
                          onChange={(e) => handleRoleFieldChange('university', e.target.value)}
                          required
                        >
                          <option value="">{t("Select University")}</option>
                          {UNIVERSITIES.map((u) => (
                            <option key={u} value={u}>{u}</option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label"><Trans text="Designation *" /></label>
                        <input
                          className="form-input"
                          type="text"
                          placeholder={t("Enter designation")}
                          value={roleFields.universityDesignation}
                          onChange={(e) => handleRoleFieldChange('universityDesignation', e.target.value)}
                          required
                        />
                      </div>
                    </>
                  )}

                  {/* STUDENT */}
                  {selectedRole === 'student' && (
                    <>
                      <div className="form-group">
                        <label className="form-label"><Trans text="Select University *" /></label>
                        <select
                          className="form-select"
                          value={roleFields.studentUniversity}
                          onChange={(e) => handleRoleFieldChange('studentUniversity', e.target.value)}
                          required
                        >
                          <option value="">{t("Select University")}</option>
                          {STUDENT_APPROVED_UNIVERSITIES.map((u) => (
                            <option key={u} value={u}>{u}</option>
                          ))}
                        </select>
                      </div>

                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="University Department *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("e.g. Computer Engineering")}
                            value={roleFields.studentDepartment}
                            onChange={(e) => handleRoleFieldChange('studentDepartment', e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="Student ID *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter Student ID")}
                            value={roleFields.studentId}
                            onChange={(e) => handleRoleFieldChange('studentId', e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="Domain *" /></label>
                          <select
                            className="form-select"
                            value={roleFields.studentDomain}
                            onChange={(e) => handleRoleFieldChange('studentDomain', e.target.value)}
                            required
                          >
                            <option value="">{t("Select Domain")}</option>
                            {DOMAINS.map((d) => (
                              <option key={d} value={d}>{t(d)}</option>
                            ))}
                          </select>
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="Skill" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("e.g. React, Python, SQL")}
                            value={roleFields.studentSkill}
                            onChange={(e) => handleRoleFieldChange('studentSkill', e.target.value)}
                          />
                        </div>
                      </div>

                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="LinkedIn ID" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter LinkedIn ID / profile")}
                            value={roleFields.linkedinId}
                            onChange={(e) => handleRoleFieldChange('linkedinId', e.target.value)}
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="GitHub ID" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter GitHub ID / profile")}
                            value={roleFields.githubId}
                            onChange={(e) => handleRoleFieldChange('githubId', e.target.value)}
                          />
                        </div>
                      </div>
                    </>
                  )}

                  {/* FACULTY */}
                  {selectedRole === 'faculty' && (
                    <>
                      <div className="form-group">
                        <label className="form-label"><Trans text="Select University *" /></label>
                        <select
                          className="form-select"
                          value={roleFields.facultyUniversity}
                          onChange={(e) => handleRoleFieldChange('facultyUniversity', e.target.value)}
                          required
                        >
                          <option value="">{t("Select University")}</option>
                          {UNIVERSITIES.map((u) => (
                            <option key={u} value={u}>{u}</option>
                          ))}
                        </select>
                      </div>

                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="Faculty ID *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter Faculty ID")}
                            value={roleFields.facultyId}
                            onChange={(e) => handleRoleFieldChange('facultyId', e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="Research Area *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter research area")}
                            value={roleFields.researchArea}
                            onChange={(e) => handleRoleFieldChange('researchArea', e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="form-label"><Trans text="Expertise *" /></label>
                        <input
                          className="form-input"
                          type="text"
                          placeholder={t("Enter area of expertise")}
                          value={roleFields.facultyExpertise}
                          onChange={(e) => handleRoleFieldChange('facultyExpertise', e.target.value)}
                          required
                        />
                      </div>
                    </>
                  )}

                  {/* INDUSTRY */}
                  {selectedRole === 'industry_employee' && (
                    <>
                      <div className="form-group">
                        <label className="form-label"><Trans text="Company Name *" /></label>
                        <select
                          className="form-select"
                          value={roleFields.companyName}
                          onChange={(e) => handleRoleFieldChange('companyName', e.target.value)}
                          required
                        >
                          <option value="">{t("Select Company")}</option>
                          {COMPANIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </div>

                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="Company Email *" /></label>
                          <input
                            className="form-input"
                            type="email"
                            placeholder="company@example.com"
                            value={roleFields.companyEmail}
                            onChange={(e) => handleRoleFieldChange('companyEmail', e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="Employee ID *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter Employee ID")}
                            value={roleFields.employeeId}
                            onChange={(e) => handleRoleFieldChange('employeeId', e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      <div className="two-column">
                        <div className="form-group">
                          <label className="form-label"><Trans text="Designation *" /></label>
                          <input
                            className="form-input"
                            type="text"
                            placeholder={t("Enter designation")}
                            value={roleFields.industryDesignation}
                            onChange={(e) => handleRoleFieldChange('industryDesignation', e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label"><Trans text="Domain *" /></label>
                          <select
                            className="form-select"
                            value={roleFields.industryDomain}
                            onChange={(e) => handleRoleFieldChange('industryDomain', e.target.value)}
                            required
                          >
                            <option value="">{t("Select Domain")}</option>
                            {DOMAINS.map((d) => (
                              <option key={d} value={d}>{d}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="form-label"><Trans text="Expertise" /></label>
                        <input
                          className="form-input"
                          type="text"
                          placeholder={t("Enter area of expertise")}
                          value={roleFields.industryExpertise}
                          onChange={(e) => handleRoleFieldChange('industryExpertise', e.target.value)}
                        />
                      </div>
                    </>
                  )}
                </>
              )}

              {/* PASSWORD */}
              <div className="form-group">
                <label className="form-label"><Trans text="Password" /></label>
                <div className="input-wrapper">
                  <span className="input-icon">🔒</span>
                  <input
                    className="form-input with-icon"
                    type={showPassword ? 'text' : 'password'}
                    placeholder={t("Enter your password")}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <Trans text="Hide" /> : <Trans text="Show" />}
                  </button>
                </div>

                {/* PASSWORD STRENGTH (SIGNUP ONLY) */}
                {mode === 'signup' && (
                  <>
                    <div className="password-strength">
                      {strength.lines.map((color, idx) => (
                        <span
                          key={idx}
                          className="strength-line"
                          style={{ background: color }}
                        ></span>
                      ))}
                    </div>
                    {strength.text && (
                      <div className="strength-text">{strength.text}</div>
                    )}
                  </>
                )}
              </div>

              {/* CONFIRM PASSWORD (SIGNUP ONLY) */}
              {mode === 'signup' && (
                <div className="form-group">
                  <label className="form-label"><Trans text="Confirm Password" /></label>
                  <input
                    className="form-input"
                    type="password"
                    placeholder={t("Re-enter password")}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                </div>
              )}

              {/* LOGIN OPTIONS */}
              {mode === 'login' && (
                <div className="form-options">
                  <label className="remember">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    <Trans text="Remember me" />
                  </label>

                  <button
                    type="button"
                    className="forgot"
                    onClick={() => setShowForgotModal(true)}
                  >
                    <Trans text="Forgot password?" />
                  </button>
                </div>
              )}

              {/* TERMS (SIGNUP ONLY) */}
              {mode === 'signup' && (
                <label className="terms">
                  <input
                    type="checkbox"
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                    required
                  />
                  <span>
                    <Trans text="I agree to the" /> <a href="#terms" onClick={(e) => e.preventDefault()}><Trans text="Terms of Use" /></a> <Trans text="and" />{' '}
                    <a href="#privacy" onClick={(e) => e.preventDefault()}><Trans text="Privacy Policy" /></a> <Trans text="of VidySetu." />
                  </span>
                </label>
              )}

              {/* SUBMIT BUTTON */}
              <button
                type="submit"
                className="submit-btn"
                disabled={submitting}
              >
                {submitting
                  ? <Trans text="Please wait..." />
                  : mode === 'signup'
                  ? <Trans text="Create Account →" />
                  : <Trans text="Continue to Portal →" />}
              </button>
            </form>

            {/* DIVIDER & NOTICE */}
            <div className="divider"><Trans text="CIVIC PLATFORM ACCESS" /></div>

            <div className="demo-box">
              <strong><Trans text="Official Civic Tech Initiative" /></strong>
              &nbsp; • &nbsp;
              <Trans text="Role-based verification enforced by backend database." />
            </div>
          </section>
        </div>
      </main>

      {/* =====================================================
           FORGOT PASSWORD MODAL
      ====================================================== */}
      {showForgotModal && (
        <div className="forgot-modal-overlay" onClick={() => setShowForgotModal(false)}>
          <div className="forgot-modal" onClick={(e) => e.stopPropagation()}>
            <h3><Trans text="Reset Password" /></h3>
            <p>
              <Trans text="Enter your registered email address and we'll send you a link to reset your password." />
            </p>
            <form onSubmit={handleForgotPassword}>
              <div className="form-group">
                <label className="form-label"><Trans text="Registered Email" /></label>
                <input
                  className="form-input"
                  type="email"
                  placeholder="name@example.com"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  required
                />
              </div>

              <div className="forgot-modal-actions">
                <button
                  type="button"
                  className="home-link"
                  onClick={() => setShowForgotModal(false)}
                >
                  <Trans text="Cancel" />
                </button>
                <button
                  type="submit"
                  className="submit-btn"
                  style={{ width: 'auto', padding: '0 20px', height: '38px' }}
                  disabled={forgotSubmitting}
                >
                  {forgotSubmitting ? <Trans text="Sending..." /> : <Trans text="Send Reset Link" />}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
