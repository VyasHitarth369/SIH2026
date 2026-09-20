import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import Trans, { useTranslate } from '../components/shared/Trans.jsx';
import { VidySetuMark } from '../components/shared/VidySetuLogo.jsx';
import '../styles/home.css';

export default function HomePage() {
  const navigate = useNavigate();
  const { lang, setLang } = useLanguage();
  const t = useTranslate();

  const handleLanguageChange = (e) => {
    setLang(e.target.value);
  };

  const scrollToSection = (e, id) => {
    e.preventDefault();
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="landing-page">
      {/* =====================================================
           TOP GOVERNMENT BAR
      ====================================================== */}
      <div className="gov-bar">
        <div className="landing-container gov-bar-inner">
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
           NAVBAR
      ====================================================== */}
      <nav className="navbar">
        <div className="landing-container nav-inner">
          <a
            href="#home"
            className="brand"
            onClick={(e) => scrollToSection(e, 'home')}
          >
            <VidySetuMark size={38} />
            <div>
              <div className="brand-name">
                <span style={{ color: '#0E387A' }}>Vidy</span><span style={{ color: '#059669' }}>Setu</span>
              </div>
              <div className="brand-subtitle">
                <Trans text="Civic Problem Resolution Platform" />
              </div>
            </div>
          </a>

          <div className="nav-links">
            <a href="#home" onClick={(e) => scrollToSection(e, 'home')}>
              <Trans text="Home" />
            </a>
            <a href="#how" onClick={(e) => scrollToSection(e, 'how')}>
              <Trans text="How It Works" />
            </a>
            <a href="#categories" onClick={(e) => scrollToSection(e, 'categories')}>
              <Trans text="Problems" />
            </a>
            <a href="#ecosystem" onClick={(e) => scrollToSection(e, 'ecosystem')}>
              <Trans text="Ecosystem" />
            </a>
          </div>

          <div className="nav-actions">
            <select
              className="language-select"
              value={lang}
              onChange={handleLanguageChange}
              aria-label={t("Select Language")}
            >
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
            </select>

            <button
              className="login-btn"
              onClick={() => navigate('/login')}
            >
              <Trans text="Log In" />
            </button>
          </div>
        </div>
      </nav>

      {/* =====================================================
           HERO
      ====================================================== */}
      <section className="hero" id="home">
        <div className="landing-container hero-inner">
          <div className="hero-content">
            <div className="hero-badge">
              <span className="status-dot"></span>
              <Trans text="Building Better Communities Together" />
            </div>

            <h1>
              <Trans text="Report a Problem." />
              <br />
              <span><Trans text="Find a Solution." /></span>
            </h1>

            <p className="hero-description">
              <Trans text="VidySetu connects citizens, government, universities, students and industry to identify real civic problems and turn them into measurable solutions." />
            </p>

            <div className="hero-actions">
              <button
                className="primary-btn"
                onClick={() => navigate('/login')}
              >
                <Trans text="+ Report a Problem" />
              </button>

              <button
                className="secondary-btn"
                onClick={() => navigate('/login')}
              >
                <Trans text="Track a Problem" />
              </button>
            </div>

            <div className="hero-note">
              <span>✓ <Trans text="Multilingual Access" /></span>
              <span>✓ <Trans text="Transparent Tracking" /></span>
              <span>✓ <Trans text="Community Driven" /></span>
            </div>
          </div>

          {/* Dashboard Visual */}
          <div className="hero-visual">
            <div className="dashboard-card">
              <div className="dashboard-header">
                <div className="dashboard-title"><Trans text="Civic Issue Overview" /></div>
                <div className="live-status">● <Trans text="PLATFORM OVERVIEW" /></div>
              </div>

              <div className="map-area">
                <div className="map-outline"></div>
                <div className="map-pin pin-1"></div>
                <div className="map-pin pin-2"></div>
                <div className="map-pin pin-3"></div>
                <div className="map-pin pin-4"></div>
                <div className="map-label"><Trans text="Jharkhand • Civic Issues" /></div>
              </div>

              <div className="dashboard-stats">
                <div className="mini-stat">
                  <div className="mini-stat-number">1,248</div>
                  <div className="mini-stat-label"><Trans text="Problems Reported" /></div>
                </div>

                <div className="mini-stat">
                  <div className="mini-stat-number">736</div>
                  <div className="mini-stat-label"><Trans text="Resolved" /></div>
                </div>

                <div className="mini-stat">
                  <div className="mini-stat-number">42</div>
                  <div className="mini-stat-label"><Trans text="Active Projects" /></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
           STATISTICS
      ====================================================== */}
      <section className="trust-bar">
        <div className="landing-container trust-inner">
          <div className="trust-item">
            <div className="trust-number">1,248+</div>
            <div className="trust-label"><Trans text="Problems Reported" /></div>
          </div>

          <div className="trust-item">
            <div className="trust-number">736+</div>
            <div className="trust-label"><Trans text="Solutions Delivered" /></div>
          </div>

          <div className="trust-item">
            <div className="trust-number">50+</div>
            <div className="trust-label"><Trans text="Institution Partners" /></div>
          </div>

          <div className="trust-item">
            <div className="trust-number">24</div>
            <div className="trust-label"><Trans text="Districts Covered" /></div>
          </div>
        </div>
      </section>

      {/* =====================================================
           PROBLEM CATEGORIES (Informational Only)
      ====================================================== */}
      <section className="section" id="categories">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-label"><Trans text="Civic Problems" /></div>
            <h2 className="section-title"><Trans text="What would you like to report?" /></h2>
            <p className="section-description">
              <Trans text="Help identify problems around you. Your report can become the starting point for a real solution." />
            </p>
          </div>

          <div className="category-grid">
            <div className="category-card">
              <div className="category-icon">🛣️</div>
              <h3><Trans text="Roads & Transport" /></h3>
              <p>
                <Trans text="Damaged roads, traffic issues, street connectivity and public transport." />
              </p>
            </div>

            <div className="category-card">
              <div className="category-icon">💧</div>
              <h3><Trans text="Water & Sanitation" /></h3>
              <p>
                <Trans text="Water supply, drainage, sanitation and waste management concerns." />
              </p>
            </div>

            <div className="category-card">
              <div className="category-icon">⚡</div>
              <h3><Trans text="Electricity" /></h3>
              <p>
                <Trans text="Street lighting, power infrastructure and electricity-related civic issues." />
              </p>
            </div>

            <div className="category-card">
              <div className="category-icon">🏛️</div>
              <h3><Trans text="Public Services" /></h3>
              <p>
                <Trans text="Problems related to public facilities, administration and civic services." />
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
           HOW IT WORKS
      ====================================================== */}
      <section className="section process-section" id="how">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-label"><Trans text="Simple Process" /></div>
            <h2 className="section-title"><Trans text="From Problem to Impact" /></h2>
            <p className="section-description">
              <Trans text="VidySetu creates a structured pathway from citizen-reported problems to innovative solutions." />
            </p>
          </div>

          <div className="process-grid">
            <div className="process-card">
              <div className="process-number">1</div>
              <h3><Trans text="Report" /></h3>
              <p><Trans text="Citizen submits a civic problem using text, image or voice." /></p>
            </div>

            <div className="process-card">
              <div className="process-number">2</div>
              <h3><Trans text="Validate" /></h3>
              <p>
                <Trans text="AI-assisted validation checks quality, relevance and existing solutions." />
              </p>
            </div>

            <div className="process-card">
              <div className="process-number">3</div>
              <h3><Trans text="Connect" /></h3>
              <p>
                <Trans text="Relevant universities and institutions receive suitable problem statements." />
              </p>
            </div>

            <div className="process-card">
              <div className="process-number">4</div>
              <h3><Trans text="Innovate" /></h3>
              <p>
                <Trans text="Students and faculty develop practical solution proposals." />
              </p>
            </div>

            <div className="process-card">
              <div className="process-number">5</div>
              <h3><Trans text="Impact" /></h3>
              <p>
                <Trans text="Industry and government help transform promising ideas into real outcomes." />
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
           ECOSYSTEM
      ====================================================== */}
      <section className="section ecosystem" id="ecosystem">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-label"><Trans text="Connected Ecosystem" /></div>
            <h2 className="section-title"><Trans text="One Platform. Multiple Stakeholders." /></h2>
            <p className="section-description">
              <Trans text="Bringing the right people together around real-world problems." />
            </p>
          </div>

          <div className="ecosystem-box">
            <div className="ecosystem-flow">
              <div className="flow-item">👤 <Trans text="Citizen" /></div>
              <div className="arrow">→</div>
              <div className="flow-item">🏛️ <Trans text="University" /></div>
              <div className="arrow">→</div>
              <div className="flow-item">🎓 <Trans text="Student" /></div>
              <div className="arrow">→</div>
              <div className="flow-item">🏭 <Trans text="Industry" /></div>
              <div className="arrow">→</div>
              <div className="flow-item">🏢 <Trans text="Government" /></div>
              <div className="arrow">→</div>
              <div className="flow-item">✓ <Trans text="Impact" /></div>
            </div>

            <div className="ecosystem-caption">
              <Trans text="Citizen → University → Student → Industry → Government → Impact" />
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
           CTA
      ====================================================== */}
      <section className="cta-section">
        <div className="landing-container">
          <div className="cta-box">
            <div className="cta-content">
              <h2><Trans text="Have a problem in your community?" /></h2>
              <p><Trans text="Your observation could become someone's next solution." /></p>
            </div>

            <button
              className="cta-button"
              onClick={() => navigate('/login')}
            >
              <Trans text="Report a Problem →" />
            </button>
          </div>
        </div>
      </section>

      {/* =====================================================
           FOOTER
      ====================================================== */}
      <footer>
        <div className="landing-container">
          <div className="footer-grid">
            <div>
              <div className="footer-brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <VidySetuMark size={28} />
                <span>
                  <span style={{ color: '#0E387A' }}>Vidy</span><span style={{ color: '#059669' }}>Setu</span>
                </span>
              </div>
              <p className="footer-description">
                <Trans text="A civic problem resolution platform connecting communities, institutions and innovators to create meaningful local impact." />
              </p>
            </div>

            <div className="footer-column">
              <h4><Trans text="Platform" /></h4>
              <a href="#home" onClick={(e) => scrollToSection(e, 'home')}>
                <Trans text="Home" />
              </a>
              <a href="#how" onClick={(e) => scrollToSection(e, 'how')}>
                <Trans text="How It Works" />
              </a>
              <a href="#categories" onClick={() => navigate('/login')}>
                <Trans text="Report Problem" />
              </a>
              <a href="#ecosystem" onClick={(e) => scrollToSection(e, 'ecosystem')}>
                <Trans text="Ecosystem" />
              </a>
            </div>

            <div className="footer-column">
              <h4><Trans text="Stakeholders" /></h4>
              <a onClick={() => navigate('/login')}><Trans text="Citizens" /></a>
              <a onClick={() => navigate('/login')}><Trans text="Government" /></a>
              <a onClick={() => navigate('/login')}><Trans text="Universities" /></a>
              <a onClick={() => navigate('/login')}><Trans text="Industry" /></a>
            </div>

            <div className="footer-column">
              <h4><Trans text="Support" /></h4>
              <a href="#home" onClick={(e) => scrollToSection(e, 'home')}>
                <Trans text="Help Centre" />
              </a>
              <a href="#home" onClick={(e) => scrollToSection(e, 'home')}>
                <Trans text="Accessibility" />
              </a>
              <a href="#home" onClick={(e) => scrollToSection(e, 'home')}>
                <Trans text="Privacy Policy" />
              </a>
              <a href="#home" onClick={(e) => scrollToSection(e, 'home')}>
                <Trans text="Terms of Use" />
              </a>
            </div>
          </div>

          <div className="footer-bottom">
            <span><Trans text="© 2026 VidySetu. Learn. Solve. Build a Smarter India." /></span>
            <span><Trans text="Designed for citizen-centric problem solving." /></span>
          </div>
        </div>
      </footer>
    </div>
  );
}
