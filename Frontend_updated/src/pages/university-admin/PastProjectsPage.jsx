import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import apiClient from '../../services/apiClient';
import Milestones from '../../components/shared/Milestones.jsx';

export default function UniversityPastProjectsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedMilestones, setExpandedMilestones] = useState(null);

  const myUniversity =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    'University Administration';

  const fetchPastProjects = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch projects with approved_only=true, backend authoritatively scopes to authenticated university
      const res = await apiClient.get('/projects', { approved_only: true });
      if (res && res.data && Array.isArray(res.data)) {
        // Filter strictly to completed/solved/deployed projects (Stage 7)
        const completed = res.data.filter((p) =>
          p.is_deployed ||
          p.status === 'deployed' ||
          p.status === 'solved' ||
          p.status === 'completed' ||
          p.current_milestone === 'Solution Deployed'
        );
        setProjects(completed);
      } else {
        setProjects([]);
      }
    } catch (err) {
      console.warn('Could not fetch past projects:', err.message);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPastProjects();
  }, [fetchPastProjects]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Past Projects" /></h1>
          <p>
            {lang === 'hi'
              ? `${myUniversity} द्वारा सफलतापूर्वक पूर्ण एवं तैनात की गई वास्तविक परियोजनाएं।`
              : `Completed and successfully deployed civic innovation projects mentored by ${myUniversity}.`}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: '24px', textAlign: 'center' }}>
          <p>{lang === 'hi' ? 'पूर्व परियोजनाएं लोड हो रही हैं...' : 'Loading past projects from server...'}</p>
        </div>
      )}

      {!loading && projects.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {projects.map((p) => {
            const skills = Array.isArray(p.skills_required)
              ? p.skills_required
              : typeof p.skills_required === 'string'
              ? p.skills_required.split(',').map((s) => s.trim()).filter(Boolean)
              : [];

            const studentsList = Array.isArray(p.students) ? p.students : [];
            const facultyMentors = Array.isArray(p.faculty_mentors) && p.faculty_mentors.length > 0
              ? p.faculty_mentors
              : [{ faculty_name: p.faculty_name, email: p.faculty_email, role: 'Primary Faculty Mentor' }];

            return (
              <div className="card" key={p.project_id}>
                <div className="problem-card__head">
                  <span className="badge badge-teal">
                    ✅ <Trans text="Solution Deployed (Stage 7/7)" />
                  </span>
                  <span className="badge badge-violet">
                    ID: #{p.project_id}
                  </span>
                  <span className="badge badge-outline">
                    🏫 {p.university_name || myUniversity}
                  </span>
                </div>

                <h3 className="problem-title">{p.title}</h3>
                <p className="problem-desc">{p.description}</p>

                <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        📍 <Trans text="Location:" />
                      </div>
                      <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {p.location || 'Jharkhand, India'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        🏢 <Trans text="Industry Partner:" />
                      </div>
                      <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {p.industry_name || '—'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        👨‍💼 <Trans text="Industry Mentor:" />
                      </div>
                      <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {p.industry_employee_name || p.industry_mentor_name || '—'}
                      </div>
                    </div>
                  </div>

                  {skills.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>
                        🛠️ <Trans text="Skills Required:" />
                      </div>
                      <div className="skills-chips">
                        {skills.map((sk, idx) => (
                          <span className="skill-chip" key={`${sk}-${idx}`}>{sk}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>
                      👨‍🏫 <Trans text="Faculty Mentors:" />
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {facultyMentors.map((fac, idx) => (
                        <div
                          key={fac.faculty_id || idx}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '4px 10px',
                            background: '#f1f5f9',
                            borderRadius: 6,
                            fontSize: 12.5,
                          }}
                        >
                          <strong>{fac.faculty_name}</strong>
                          {fac.email && <span style={{ color: 'var(--text-muted)' }}>({fac.email})</span>}
                          {fac.role && <span className="badge badge-outline" style={{ fontSize: 10 }}>{fac.role}</span>}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>
                      👨‍🎓 <Trans text="Student Team Members:" />
                    </div>
                    {studentsList.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {studentsList.map((stu, idx) => (
                          <div
                            key={stu.student_id || idx}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 6,
                              padding: '4px 10px',
                              background: '#ecfdf5',
                              border: '1px solid #a7f3d0',
                              borderRadius: 6,
                              fontSize: 12.5,
                              color: '#065f46',
                            }}
                          >
                            <span>🎓</span>
                            <strong>{stu.name || stu.student_name || stu}</strong>
                            {stu.role && <span style={{ color: '#047857', fontSize: 11 }}>({stu.role})</span>}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                        <Trans text="No student records associated." />
                      </div>
                    )}
                  </div>
                </div>

                <div className="proposal-card__actions" style={{ marginTop: 14 }}>
                  <button
                    className="btn btn-light btn-sm"
                    onClick={() => setExpandedMilestones(expandedMilestones === p.project_id ? null : p.project_id)}
                  >
                    {expandedMilestones === p.project_id ? <Trans text="Hide Milestones" /> : <Trans text="View Milestones Timeline" />}
                  </button>
                </div>

                {expandedMilestones === p.project_id && (
                  <div style={{ marginTop: 14 }}>
                    <Milestones project={p} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && projects.length === 0 && (
        <div className="card empty-state">
          <span className="empty-state__icon">📁</span>
          <h3><Trans text="No Past Projects" /></h3>
          <p>
            {lang === 'hi'
              ? 'वर्तमान में आपके विश्वविद्यालय से संबद्ध कोई पूर्ण परियोजना उपलब्ध नहीं है।'
              : 'No completed or solved projects found for your university at this time.'}
          </p>
        </div>
      )}
    </div>
  );
}
