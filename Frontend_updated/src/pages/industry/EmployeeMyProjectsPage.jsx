import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { matchingService } from '../../services/matchingService';

export default function EmployeeMyProjectsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMyProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await matchingService.listMyIndustryProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not load my projects:', err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMyProjects();
  }, [fetchMyProjects]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="My Mentorship Projects" /></h1>
          <p>
            {lang === 'hi'
              ? 'वे सभी सहयोगी प्रोजेक्ट्स जहां आप आधिकारिक उद्योग मेंटर (Industry Mentor) के रूप में नियुक्त हैं।'
              : 'All collaborative projects where you are assigned as the official Industry Mentor.'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
          <p><Trans text="Loading your mentored projects..." /></p>
        </div>
      )}

      {error && !loading && (
        <div className="card" style={{ padding: '16px', background: '#fef2f2', border: '1px solid #f87171', color: '#991b1b' }}>
          <p><strong>Error:</strong> {error}</p>
          <button className="btn btn-sm btn-outline" onClick={fetchMyProjects} style={{ marginTop: 8 }}>
            <Trans text="Retry" />
          </button>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {projects.map((p) => {
            const stuNames = p.student_names || p.student_participants || [];

            return (
              <div className="card" key={p.project_id}>
                <div className="problem-card__head" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge-teal" style={{ fontWeight: 600 }}>
                    ⭐ <Trans text="Official Industry Mentor" />
                  </span>
                  <span className="badge badge-blue">
                    📁 {p.project_id}
                  </span>
                  <span className="badge badge-violet">
                    {p.status || 'Active'}
                  </span>
                  {p.current_milestone && (
                    <span className="badge badge-amber">
                      🚩 {p.current_milestone}
                    </span>
                  )}
                </div>

                <h3 className="problem-title" style={{ marginTop: 8 }}>
                  {p.title || p.project_title}
                </h3>

                {p.challenge_title && p.challenge_title !== p.title && (
                  <p className="problem-meta" style={{ marginTop: 2 }}>
                    🎯 <Trans text="Linked Problem:" /> <strong>{p.challenge_title}</strong>
                  </p>
                )}

                <p className="problem-desc" style={{ marginTop: 8 }}>
                  {p.description || 'No description provided.'}
                </p>

                <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        🏫 <Trans text="Partner University:" />
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {p.university_name || 'Partner University'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        👨‍🏫 <Trans text="Faculty Mentor:" />
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {p.faculty_name || 'Faculty Advisor'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        📍 <Trans text="Location:" />
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {p.location || p.city || 'Jharkhand'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        👨‍🎓 <Trans text="Student Team:" />
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {stuNames.length > 0 ? (
                          stuNames.join(', ')
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            <Trans text="Team in formation / Pending selection" />
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="card empty-state" style={{ padding: '40px 20px', textAlign: 'center' }}>
          <span className="empty-state__icon" style={{ fontSize: 48 }}>📁</span>
          <h3 style={{ marginTop: 12 }}><Trans text="No Mentorship Projects Assigned Yet" /></h3>
          <p style={{ maxWidth: 500, margin: '8px auto', color: 'var(--text-muted)' }}>
            {lang === 'hi'
              ? 'वर्तमान में आपको किसी भी प्रोजेक्ट के लिए उद्योग मेंटर के रूप में नियुक्त नहीं किया गया है। नए अवसरों को देखने और अपनी रुचि व्यक्त करने के लिए "सक्रिय सहयोग" देखें।'
              : 'You are not assigned as an Industry Mentor on any project yet. Browse Active Collaborations to view open projects and express your interest.'}
          </p>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/industry-employee/collaboration')}
            style={{ marginTop: 16 }}
          >
            🔍 <Trans text="Explore Active Collaborations" />
          </button>
        </div>
      )}
    </div>
  );
}
