import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';

export default function UniversityProblemsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all'); // all | my | others | solved

  const myUniversity = user?.profile?.university || 'BIT Mesra, Ranchi';

  // All problems allocated to this university
  const universityProblems = problems.filter(
    (p) => p.allocation?.allocatedTo && (!myUniversity || p.allocation.allocatedTo === myUniversity)
  );

  const filtered = universityProblems.filter((p) => {
    const isMine = p.faculty?.email === user?.email;
    if (filter === 'my') return isMine;
    if (filter === 'others') return !isMine;
    if (filter === 'solved') return p.type === 'solved';
    return true;
  });

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{lang === 'hi' ? '🏫 विश्वविद्यालय की सभी समस्याएं' : '🏫 All University Allotted Problems'}</h1>
          <p>{lang === 'hi' ? `${myUniversity} को आवंटित सभी समस्याएं (भले ही आप उन पर कार्य न कर रहे हों)` : `All problem statements allotted to ${myUniversity} (including problems assigned to other faculty)`}</p>
        </div>
        <button className="btn btn-light" onClick={() => navigate('/faculty/projects')}>
          {lang === 'hi' ? '📁 मेरे प्रोजेक्ट्स देखें' : '📁 View My Projects'} →
        </button>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div className={`filter-tab${filter === 'all' ? ' active' : ''}`} onClick={() => setFilter('all')}>
            <Trans text="All" /> ({universityProblems.length})
          </div>
          <div className={`filter-tab${filter === 'my' ? ' active' : ''}`} onClick={() => setFilter('my')}>
            {lang === 'hi' ? 'मेरे आवंटित प्रोजेक्ट' : 'Assigned to Me'}
          </div>
          <div className={`filter-tab${filter === 'others' ? ' active' : ''}`} onClick={() => setFilter('others')}>
            {lang === 'hi' ? 'अन्य फैकल्टी के प्रोजेक्ट' : 'Other Faculty Projects'}
          </div>
          <div className={`filter-tab${filter === 'solved' ? ' active' : ''}`} onClick={() => setFilter('solved')}>
            <Trans text="Solved" />
          </div>
        </div>
      </div>

      {filtered.map((p) => {
        const isMine = p.faculty?.email === user?.email;
        const studentsCount = p.students?.length || 0;

        return (
          <div className="card" key={p.id}>
            <div className="problem-card__head">
              <span className={`badge ${isMine ? 'badge-blue' : 'badge-gray'}`}>
                {isMine
                  ? (lang === 'hi' ? '✓ आपको आवंटित' : 'Allotted to You')
                  : (lang === 'hi' ? 'विश्वविद्यालय प्रोजेक्ट' : 'University Project')}
              </span>
              {p.type === 'solved' && <span className="badge badge-teal"><Trans text="Solved" /></span>}
              <span className="badge badge-violet">ID: #CH-JH-{p.id}</span>
            </div>

            <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
            <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>

            <div className="problem-meta">
              📍 <strong><Trans text="Location:" /></strong> {p.loc} · 🏷️ <strong><Trans text="Domain:" /></strong> <Trans text={p.domain || p.category} />
            </div>
            {p.requiredTechnologies?.length > 0 && (
              <div className="problem-meta">
                💡 <strong><Trans text="Required Technologies:" /></strong> {p.requiredTechnologies.join(', ')}
              </div>
            )}
            {p.suggestedIndustries?.length > 0 && (
              <div className="problem-meta">
                🏢 <strong><Trans text="Suggested Industries:" /></strong> {p.suggestedIndustries.join(', ')}
              </div>
            )}

            <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
              <div className="problem-meta">
                👨‍🏫 <strong><Trans text="Assigned Faculties" />:</strong>{' '}
                {p.faculty?.name ? (
                  <span>
                    <strong>{p.faculty.name}</strong> ({p.faculty.email}){' '}
                    {isMine && <span className="badge badge-blue">{lang === 'hi' ? 'आप' : 'You'}</span>}
                  </span>
                ) : (
                  <span style={{ color: 'var(--amber)' }}><Trans text="Not yet allocated" /></span>
                )}
              </div>

              <div className="problem-meta" style={{ marginTop: 6 }}>
                👨‍🎓 <strong><Trans text="Students Working:" /></strong> <strong>{studentsCount}</strong>{' '}
                {p.students?.length > 0 && (
                  <span>({p.students.map((s) => s.name).join(', ')})</span>
                )}
              </div>
            </div>

            {p.solution && (
              <div className="solution-block" style={{ marginTop: 10 }}>
                <h4><Trans text="Proposed Solution" /></h4>
                <p>{p.solution[lang] || p.solution.hi}</p>
              </div>
            )}

            {isMine && (
              <div className="proposal-card__actions" style={{ marginTop: 12 }}>
                <button className="btn btn-primary btn-sm" onClick={() => navigate(`/faculty/students/${p.id}`)}>
                  {lang === 'hi' ? 'छात्रों की टीम प्रबंधित करें →' : 'Manage Student Team →'}
                </button>
              </div>
            )}
          </div>
        );
      })}

      {filtered.length === 0 && (
        <div className="card">
          <Trans text="No problems allocated to your university yet." />
        </div>
      )}
    </div>
  );
}
