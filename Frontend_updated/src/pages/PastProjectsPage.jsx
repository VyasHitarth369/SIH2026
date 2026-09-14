import Trans from '../components/shared/Trans.jsx';
import { useLanguage } from '../context/LanguageContext';
import { useProblems } from '../context/ProblemsContext';
import { pastProjectsList } from '../data/mockData';

export default function PastProjectsPage() {
  const { t, lang } = useLanguage();
  const { problems } = useProblems();

  // Combine solved live problems and curated past completed projects
  const solvedProblems = problems.filter((p) => p.type === 'solved');

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{t.pastProjects}</h1>
          <p>{lang === 'hi' ? 'सफलतापूर्वक हल की गई समस्याएं एवं उनके संपूर्ण तकनीकी समाधान का विस्तृत विवरण' : 'Comprehensive details of resolved civic problems and their implemented technological solutions'}</p>
        </div>
      </div>

      <div className="stack">
        {/* Curated landmark past deployments */}
        {pastProjectsList.map((p) => (
          <div className="card" key={p.id || p.title}>
            <div className="problem-card__head">
              <span className="badge badge-teal">✅ {lang === 'hi' ? 'पूर्ण' : 'COMPLETED'}</span>
              <span className="badge badge-outline">{lang === 'hi' ? (p.clientHi || p.client) : p.client} · {p.year}</span>
            </div>

            <h3 className="problem-title">{lang === 'hi' ? (p.titleHi || p.title) : p.title}</h3>

            <div className="section-box section-box--muted" style={{ marginTop: 10 }}>
              <h4 style={{ margin: '0 0 6px 0' }}>🧩 {lang === 'hi' ? 'समस्या का पूर्ण विवरण (Problem Statement)' : 'Full Problem Statement'}</h4>
              <p className="problem-desc" style={{ margin: 0 }}>{lang === 'hi' ? (p.descHi || p.desc) : p.desc}</p>
              {p.location && (
                <div className="problem-meta" style={{ marginTop: 6 }}>
                  📍 <strong><Trans text="Location:" /></strong> {p.location}
                </div>
              )}
            </div>

            <div className="solution-block" style={{ marginTop: 12 }}>
              <h4 style={{ margin: '0 0 6px 0' }}>💡 {lang === 'hi' ? 'कार्यान्वित समाधान का पूर्ण विवरण (Solution Details)' : 'Implemented Solution Details'}</h4>
              <p style={{ margin: '0 0 8px 0' }}>{lang === 'hi' ? (p.solutionHi || p.solution) : p.solution}</p>
              {p.technologies?.length > 0 && (
                <div className="problem-meta">
                  🛠️ <strong><Trans text="Technologies:" /></strong> {p.technologies.join(', ')}
                </div>
              )}
            </div>

            <div className="credit-block" style={{ marginTop: 12 }}>
              <h4>{<Trans text="Impact:" />} {lang === 'hi' ? (p.impactHi || p.impact) : p.impact}</h4>
              {p.solvedBy && (
                <div className="credit-grid" style={{ marginTop: 8 }}>
                  <div><span className="credit-tag">👨‍🎓 <Trans text="Student" /></span>{p.solvedBy.student}</div>
                  <div><span className="credit-tag">🎓 <Trans text="University" /></span><Trans text={p.solvedBy.university} /></div>
                  <div><span className="credit-tag">🏢 <Trans text="Industry Partner" /></span><Trans text={p.solvedBy.industry} /></div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live solved problems on the platform */}
        {solvedProblems.map((p) => (
          <div className="card" key={p.id}>
            <div className="problem-card__head">
              <span className="badge badge-teal">✅ {t.solved.toUpperCase()}</span>
              <span className="badge badge-violet">ID: #CH-JH-{p.id}</span>
            </div>

            <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>

            <div className="section-box section-box--muted" style={{ marginTop: 10 }}>
              <h4 style={{ margin: '0 0 6px 0' }}>🧩 {lang === 'hi' ? 'समस्या का पूर्ण विवरण (Problem Statement)' : 'Full Problem Statement'}</h4>
              <p className="problem-desc" style={{ margin: 0 }}>{p.desc[lang] || p.desc.hi}</p>
              <div className="problem-meta" style={{ marginTop: 6 }}>
                📍 <strong><Trans text="Location:" /></strong> {p.loc} · 🏷️ <strong><Trans text="Domain:" /></strong> <Trans text={p.domain || p.category} />
              </div>
            </div>

            {p.solution && (
              <div className="solution-block" style={{ marginTop: 12 }}>
                <h4 style={{ margin: '0 0 6px 0' }}>💡 {lang === 'hi' ? 'कार्यान्वित समाधान का पूर्ण विवरण (Solution Details)' : 'Implemented Solution Details'}</h4>
                <p style={{ margin: '0 0 8px 0' }}>{p.solution[lang] || p.solution.hi}</p>
                {p.requiredTechnologies?.length > 0 && (
                  <div className="problem-meta">
                    🛠️ <strong><Trans text="Technologies:" /></strong> {p.requiredTechnologies.join(', ')}
                  </div>
                )}
              </div>
            )}

            {p.solvedBy && (
              <div className="credit-block" style={{ marginTop: 12 }}>
                <h4>{t.solvedByLabel}</h4>
                <div className="credit-grid" style={{ marginTop: 8 }}>
                  <div><span className="credit-tag">👨‍🎓 {t.studentLabel}</span>{p.solvedBy.student}</div>
                  <div><span className="credit-tag">🎓 {t.universityLabel}</span><Trans text={p.solvedBy.university} /></div>
                  <div><span className="credit-tag">🏢 {t.industryLabel}</span><Trans text={p.solvedBy.industry} /></div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
