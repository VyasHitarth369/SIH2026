import { useEffect, useState } from 'react';
import Trans from '../components/shared/Trans.jsx';
import { useLanguage } from '../context/LanguageContext';
import { useProblems } from '../context/ProblemsContext';
import { projectService } from '../services/projectService';

export default function PastProjectsPage() {
  const { t, lang } = useLanguage();
  const { problems } = useProblems();

  const [completedProjects, setCompletedProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function loadCompletedProjects() {
      try {
        setLoading(true);
        const data = await projectService.fetchProjects({ status: 'completed' });
        if (mounted) {
          const rawList = Array.isArray(data) ? data : (data?.data || []);
          const completedList = rawList.filter(
            (p) => ['completed', 'deployed', 'solved'].includes(p.status) || p.current_milestone === 'Solution Deployed' || p.is_deployed
          );
          setCompletedProjects(completedList);
        }
      } catch (err) {
        if (mounted) {
          setFetchError(err.message || 'Failed to load completed projects');
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadCompletedProjects();
    return () => { mounted = false; };
  }, []);

  // Solved live problems on the platform
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
        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
            <span className="spinner" style={{ display: 'inline-block', marginRight: 10 }} />
            <span>{lang === 'hi' ? 'पूर्ण परियोजनाएं लोड हो रही हैं...' : 'Loading completed projects...'}</span>
          </div>
        )}

        {!loading && fetchError && (
          <div className="card" style={{ borderLeft: '4px solid #f59e0b', backgroundColor: '#fffbeb', padding: '16px' }}>
            <p style={{ margin: 0, color: '#92400e' }}>
              {lang === 'hi' ? 'परियोजना डेटा लोड करने में असमर्थ।' : 'Unable to load completed projects from database at this time.'}
            </p>
          </div>
        )}

        {!loading && !fetchError && completedProjects.length === 0 && (
          <div className="card empty-state" style={{ textAlign: 'center', padding: '32px' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📂</div>
            <p className="problem-desc">
              {lang === 'hi' ? 'कोई पूर्ण परियोजना दर्ज नहीं है।' : 'No completed projects recorded yet in the database.'}
            </p>
          </div>
        )}

        {/* Live database completed projects */}
        {!loading && completedProjects.map((p) => (
          <div className="card" key={p.project_id || p.id}>
            <div className="problem-card__head">
              <span className="badge badge-teal">✅ {lang === 'hi' ? 'पूर्ण' : 'COMPLETED'}</span>
              <span className="badge badge-outline">{p.project_id}</span>
            </div>

            <h3 className="problem-title">{p.project_title || p.title}</h3>

            {p.challenge_title && (
              <div className="section-box section-box--muted" style={{ marginTop: 10 }}>
                <h4 style={{ margin: '0 0 6px 0' }}>🧩 {lang === 'hi' ? 'हल की गई समस्या (Solved Challenge)' : 'Solved Challenge Problem Statement'}</h4>
                <div style={{ fontWeight: 600, color: '#1e3a8a', marginBottom: 4 }}>{p.challenge_title}</div>
                {p.challenge_description && <p className="problem-desc" style={{ margin: 0 }}>{p.challenge_description}</p>}
              </div>
            )}

            <div className="solution-block" style={{ marginTop: 12 }}>
              <h4 style={{ margin: '0 0 6px 0' }}>💡 {lang === 'hi' ? 'कार्यान्वित तकनीकी समाधान (Implemented Solution)' : 'Implemented Solution Details'}</h4>
              <p style={{ margin: '0 0 8px 0' }}>{p.description || (lang === 'hi' ? 'सफलतापूर्वक सत्यापित और तैनात तकनीकी समाधान।' : 'Verified and deployed technological solution.')}</p>
              {p.evidence_url && (
                <div className="problem-meta" style={{ marginTop: 6 }}>
                  🔗 <strong>{lang === 'hi' ? 'सत्यापित साक्ष्य:' : 'Milestone Evidence:'}</strong>{' '}
                  <a href={p.evidence_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>
                    {p.evidence_url}
                  </a>
                </div>
              )}
            </div>

            {(p.university_name || p.industry_name) && (
              <div className="credit-block" style={{ marginTop: 12 }}>
                <div className="credit-grid" style={{ marginTop: 8 }}>
                  {p.university_name && (
                    <div><span className="credit-tag">🎓 <Trans text="University" /></span><Trans text={p.university_name} /></div>
                  )}
                  {p.industry_name && (
                    <div><span className="credit-tag">🏢 <Trans text="Industry Partner" /></span><Trans text={p.industry_name} /></div>
                  )}
                </div>
              </div>
            )}
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
