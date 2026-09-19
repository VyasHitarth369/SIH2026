import { useState, useEffect } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import Milestones from '../../components/shared/Milestones.jsx';
import { apiClient } from '../../services/apiClient';

export default function MyProjectsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const [backendProjects, setBackendProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all | ongoing | completed

  const userEmail = user?.email || '';
  const userName = user?.name || user?.full_name || '';
  const userStudentId = user?.stakeholder?.student_id || user?.profile?.studentId || '';
  const userUni =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    user?.profile?.studentUniversity ||
    user?.university ||
    '';

  useEffect(() => {
    let isMounted = true;
    async function loadMyProjects() {
      try {
        setLoading(true);
        // Authoritative membership query on backend
        const res = await apiClient.get('/projects?my_projects=true');
        if (isMounted && res && res.success && Array.isArray(res.data)) {
          setBackendProjects(res.data);
        }
      } catch (err) {
        console.warn('Could not fetch enrolled student projects from backend:', err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadMyProjects();
    return () => {
      isMounted = false;
    };
  }, []);

  // Adapt backend project records
  const adaptedBackend = backendProjects.map((p) => {
    const isCompleted = p.status === 'deployed' || p.status === 'solved' || p.status === 'completed';
    return {
      id: p.project_id || p.id,
      project_id: p.project_id,
      title: { en: p.title || p.project_title || '', hi: p.title || p.project_title || '' },
      desc: { en: p.description || '', hi: p.description || '' },
      loc: p.location || `${p.city || ''}, ${p.district || ''}`.replace(/^,\s*|,\s*$/g, '') || 'Jharkhand, India',
      domain: p.domain || 'Innovation & Technology',
      faculty: p.faculty_name ? { name: p.faculty_name, email: p.faculty_email } : null,
      industryName: p.industry_name || null,
      students: (p.student_participants || p.student_names || []).map((s) => (typeof s === 'string' ? { name: s } : s)),
      requiredTechnologies: Array.isArray(p.skills_required)
        ? p.skills_required
        : typeof p.skills_required === 'string' && p.skills_required.includes(',')
        ? p.skills_required.split(',').map((s) => s.trim())
        : [p.skills_required || 'Applied Engineering'].filter(Boolean),
      status: p.status || 'active',
      isCompleted,
      allocation: { allocatedTo: p.university_name || userUni, status: 'allocated' },
    };
  });

  // Also match any context problems where the logged-in student is explicitly listed in `students`
  const contextEnrolled = problems.filter((p) => {
    const students = p.students || [];
    return students.some((s) => {
      const matchEmail = userEmail && s.email && s.email.toLowerCase() === userEmail.toLowerCase();
      const matchName = userName && s.name && s.name.toLowerCase() === userName.toLowerCase();
      const matchId = userStudentId && (s.student_id === userStudentId || s.id === userStudentId);
      return matchEmail || matchName || matchId;
    });
  }).map((p) => ({
    ...p,
    isCompleted: p.type === 'solved' || p.status === 'solved' || p.status === 'completed' || p.status === 'deployed',
    industryName: p.suggestedIndustries?.[0] || p.industry_name || null,
  }));

  const existingIds = new Set(adaptedBackend.map((p) => String(p.id)));
  const allMyProjects = [
    ...adaptedBackend,
    ...contextEnrolled.filter((p) => !existingIds.has(String(p.id))),
  ];

  const filtered = allMyProjects.filter((p) => {
    if (filter === 'ongoing') return !p.isCompleted;
    if (filter === 'completed') return p.isCompleted;
    return true;
  });

  const ongoingCount = allMyProjects.filter((p) => !p.isCompleted).length;
  const completedCount = allMyProjects.filter((p) => p.isCompleted).length;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>
            <Trans text="My Project" />
          </h1>
          <p>
            {lang === 'hi'
              ? 'वे परियोजनाएं और समस्याएं जिनमें आप एक आधिकारिक टीम सदस्य के रूप में कार्यरत हैं'
              : 'Projects and problem statements where you are an officially assigned team member'}
          </p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px', marginBottom: 16 }}>
        <div className="filter-tabs">
          <div className={`filter-tab${filter === 'all' ? ' active' : ''}`} onClick={() => setFilter('all')}>
            <Trans text="All Projects" /> ({allMyProjects.length})
          </div>
          <div className={`filter-tab${filter === 'ongoing' ? ' active' : ''}`} onClick={() => setFilter('ongoing')}>
            <Trans text="Ongoing Work" /> ({ongoingCount})
          </div>
          <div className={`filter-tab${filter === 'completed' ? ' active' : ''}`} onClick={() => setFilter('completed')}>
            <Trans text="Solved & Completed Work" /> ({completedCount})
          </div>
        </div>
      </div>

      {loading && allMyProjects.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <p className="problem-desc"><Trans text="Loading your project memberships..." /></p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <p className="problem-desc">
            {filter === 'ongoing'
              ? (lang === 'hi' ? 'कोई सक्रिय कार्य प्रगति पर नहीं है।' : 'No ongoing projects at this time.')
              : filter === 'completed'
              ? (lang === 'hi' ? 'अभी तक कोई परियोजना पूर्ण या हल नहीं हुई है।' : 'No completed/solved projects yet.')
              : (lang === 'hi' ? 'आप अभी किसी भी परियोजना टीम में सदस्य के रूप में नामांकित नहीं हैं।' : 'You are not assigned as a team member on any project yet.')}
          </p>
        </div>
      ) : (
        filtered.map((p) => {
          const studentNames = (p.students || []).map((s) => s.name || s).filter(Boolean);
          const facultyName = p.faculty?.name || p.faculty_name;
          const industryName = p.industryName || p.industry_name;

          return (
            <div className="card" key={p.id}>
              <div className="problem-card__head">
                <span className={`badge ${p.isCompleted ? 'badge-teal' : 'badge-blue'}`}>
                  {p.isCompleted ? (lang === 'hi' ? '✅ पूर्ण / हल' : '✅ Solved / Completed') : (lang === 'hi' ? '⚙️ प्रगति पर' : '⚙️ Ongoing / In Progress')}
                </span>
                <span className="badge badge-gray">
                  🏫 {p.allocation?.allocatedTo || userUni || 'University'}
                </span>
                <span className="badge badge-violet">
                  ID: #{String(p.id).startsWith('PRJ-') ? p.id : `PRJ-JH-${p.id}`}
                </span>
              </div>

              <h3 className="problem-title">{p.title[lang] || p.title.en || p.title.hi}</h3>
              <p className="problem-desc">{p.desc[lang] || p.desc.en || p.desc.hi}</p>

              <div className="problem-meta" style={{ marginTop: 8 }}>
                📍 <strong><Trans text="Location:" /></strong> {p.loc}
              </div>

              {p.requiredTechnologies?.length > 0 && (
                <div className="skills-block" style={{ marginTop: 10 }}>
                  <div className="skills-block__label">
                    🛠️ <strong><Trans text="Skills Required:" /></strong>
                  </div>
                  <div className="skills-chips" style={{ marginTop: 4 }}>
                    {p.requiredTechnologies.map((skill, idx) => (
                      <span className="skill-chip" key={idx}>{skill}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="section-box section-box--muted" style={{ marginTop: 14 }}>
                <div className="problem-meta">
                  👨‍🏫 <strong><Trans text="Faculty Mentoring:" /></strong>{' '}
                  {facultyName ? (
                    <strong>{facultyName}</strong>
                  ) : (
                    <span style={{ color: 'var(--amber)' }}><Trans text="Not yet allocated" /></span>
                  )}
                </div>

                <div className="problem-meta" style={{ marginTop: 6 }}>
                  🏢 <strong><Trans text="Industry Name:" /></strong>{' '}
                  {industryName ? (
                    <strong>{industryName}</strong>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </div>

                <div className="problem-meta" style={{ marginTop: 6 }}>
                  👨‍🎓 <strong><Trans text="Student Names Working on It:" /></strong>{' '}
                  {studentNames.length > 0 ? (
                    <span>
                      {studentNames.map((name, i) => {
                        const isCurrent = userName && name.toLowerCase().includes(userName.toLowerCase());
                        return (
                          <span key={i}>
                            {i > 0 && ', '}
                            <strong>{name}</strong>
                            {isCurrent && <span className="badge badge-teal" style={{ marginLeft: 4, padding: '2px 6px', fontSize: 11 }}><Trans text="You" /></span>}
                          </span>
                        );
                      })}
                    </span>
                  ) : (
                    <span><strong>{userName || 'Enrolled Student'}</strong> <span className="badge badge-teal"><Trans text="You" /></span></span>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <Milestones problem={p} isCitizen={false} />
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
