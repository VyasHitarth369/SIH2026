import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { matchingService } from '../../services/matchingService';

function parseList(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val.filter(Boolean);
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) return parsed.filter(Boolean);
    } catch {
      // not json
    }
    return val
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

export default function CollaborationPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState({});

  // Interest Modal / Input state
  const [interestModalOpen, setInterestModalOpen] = useState(false);
  const [targetProject, setTargetProject] = useState(null);
  const [interestMessage, setInterestMessage] = useState('');

  const isManager = Boolean(
    user?.is_spoc ||
    user?.approval_authority ||
    user?.stakeholder?.approval_authority
  );

  const currentEmployeeId = user?.stakeholder?.employee_id;

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await matchingService.listEligibleProjectsForEmployee();
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not load eligible projects:', err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const openInterestModal = (proj) => {
    setTargetProject(proj);
    setInterestMessage('');
    setInterestModalOpen(true);
  };

  const handleExpressInterest = async () => {
    const pid = targetProject?.project_id;
    if (!pid) return;

    try {
      setSubmitting((prev) => ({ ...prev, [pid]: true }));
      await matchingService.expressEmployeeInterest(pid, interestMessage.trim());
      showToast(<Trans text="Interest expressed successfully! Pending Manager review." />);
      setInterestModalOpen(false);
      setTargetProject(null);
      await fetchProjects();
    } catch (err) {
      showToast(<Trans text={`Failed to express interest: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [pid]: false }));
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Active Industry Collaborations" /></h1>
          <p>
            {lang === 'hi'
              ? 'आपकी कंपनी के साथ साझेदार सक्रिय कॉर्पोरेट इनोवेशन प्रोजेक्ट्स।'
              : 'Active corporate innovation projects partnered with your organization.'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
          <p><Trans text="Loading active collaboration projects..." /></p>
        </div>
      )}

      {error && !loading && (
        <div className="card" style={{ padding: '16px', background: '#fef2f2', border: '1px solid #f87171', color: '#991b1b' }}>
          <p><strong>Error:</strong> {error}</p>
          <button className="btn btn-sm btn-outline" onClick={fetchProjects} style={{ marginTop: 8 }}>
            <Trans text="Retry" />
          </button>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {projects.map((p) => {
            const ch = p.challenge || {};
            const analysis = p.ai_analysis || {};
            const skills = parseList(analysis.skills_required || ch.expected_solution);
            const techs = parseList(analysis.technologies_suggested);
            const myInterest = p.my_interest;
            const assignedMentor = p.assigned_mentor;
            const isAssignedToMe = assignedMentor?.employee_id === currentEmployeeId;
            const isBusy = submitting[p.project_id];

            return (
              <div className="card" key={p.project_id}>
                <div className="gov-card__head" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge-blue">
                    📁 {p.project_id}
                  </span>
                  <span className="badge badge-teal">
                    {p.status || 'Active'}
                  </span>
                  {assignedMentor ? (
                    <span className="badge badge-violet" style={{ fontWeight: 600 }}>
                      ⭐ <Trans text="Industry Mentor Assigned" />
                    </span>
                  ) : (
                    <span className="badge badge-amber">
                      ⏳ <Trans text="Open for Mentorship" />
                    </span>
                  )}
                </div>

                <h3 className="problem-title" style={{ marginTop: 8 }}>
                  {p.project_title || ch.title || 'Collaborative Project'}
                </h3>

                {ch.title && ch.title !== p.project_title && (
                  <p className="problem-meta" style={{ marginTop: 2 }}>
                    🎯 <Trans text="Linked Problem:" /> <strong>{ch.title}</strong>
                  </p>
                )}

                <p className="problem-desc" style={{ marginTop: 8 }}>
                  {p.description || ch.description || 'No description provided.'}
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
                        {ch.city || ch.location || 'Jharkhand'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                        🏢 <Trans text="Official Industry Mentor:" />
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                        {assignedMentor ? (
                          <span>⭐ {assignedMentor.employee_name} ({assignedMentor.designation || 'Mentor'})</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            <Trans text="Pending selection by Industry Manager" />
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Skills & Technologies */}
                {(skills.length > 0 || techs.length > 0) && (
                  <div className="skills-block" style={{ marginTop: 12 }}>
                    <div className="skills-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {skills.map((s, i) => (
                        <span className="skill-chip" key={`s-${i}`} style={{ background: '#e0f2fe', color: '#0369a1', padding: '3px 8px', borderRadius: 4, fontSize: 12 }}>
                          • {s}
                        </span>
                      ))}
                      {techs.map((t, i) => (
                        <span className="skill-chip" key={`t-${i}`} style={{ background: '#f3e8ff', color: '#6b21a8', padding: '3px 8px', borderRadius: 4, fontSize: 12 }}>
                          ⚙️ {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* EMPLOYEE INTEREST SECTION (FOR REGULAR EMPLOYEES) */}
                {!isManager && (
                  <div style={{ marginTop: 16, borderTop: '1px solid #e2e8f0', paddingTop: 12 }}>
                    {isAssignedToMe ? (
                      <div style={{ padding: '10px 14px', background: '#ecfdf5', border: '1px solid #86efac', borderRadius: 6 }}>
                        <strong style={{ color: '#065f46' }}>
                          ⭐ <Trans text="You are the Official Industry Mentor for this Project!" />
                        </strong>
                      </div>
                    ) : myInterest ? (
                      <div style={{ padding: '10px 14px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 6 }}>
                        <div style={{ fontWeight: 600, color: '#15803d' }}>
                          ✅ <Trans text="Interest Expressed" /> ({myInterest.status})
                        </div>
                        {myInterest.message && (
                          <div style={{ fontSize: '0.85rem', color: '#166534', marginTop: 2, fontStyle: 'italic' }}>
                            “{myInterest.message}”
                          </div>
                        )}
                      </div>
                    ) : !assignedMentor ? (
                      <div>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={isBusy}
                          onClick={() => openInterestModal(p)}
                          style={{ padding: '8px 18px', fontWeight: 600 }}
                        >
                          <Trans text="[I AM INTERESTED]" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="card empty-state" style={{ padding: '40px 20px', textAlign: 'center' }}>
          <span className="empty-state__icon" style={{ fontSize: 48 }}>🔗</span>
          <h3 style={{ marginTop: 12 }}><Trans text="No Active Collaborations" /></h3>
          <p style={{ color: 'var(--text-muted)' }}>
            <Trans text="No active collaborative innovation projects currently partnered with your organization." />
          </p>
        </div>
      )}

      {/* EXPRESS INTEREST MODAL */}
      {interestModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div className="card" style={{ maxWidth: 500, width: '90%', padding: 24 }}>
            <h3 style={{ marginTop: 0 }}>
              <Trans text="Express Interest in Project Mentorship" />
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              {lang === 'hi'
                ? 'इस प्रोजेक्ट के लिए अपनी विशेषज्ञता, तकनीकी कौशल एवं उपलब्धता का विवरण साझा करें:'
                : 'Describe your expertise, technical capabilities, or availability to mentor this project:'}
            </p>

            <textarea
              rows={4}
              value={interestMessage}
              onChange={(e) => setInterestMessage(e.target.value)}
              placeholder={
                lang === 'hi'
                  ? 'उदा. मुझे IoT सेंसर नेटवर्क्स एवं एम्बेडेड सिस्टम्स में 5 वर्षों का अनुभव है...'
                  : 'e.g. I have 5 years experience in IoT sensor deployments and software architecture...'
              }
              style={{
                width: '100%',
                padding: 10,
                borderRadius: 4,
                border: '1px solid #d1d5db',
                fontFamily: 'inherit',
                fontSize: '0.95rem',
                marginTop: 8,
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setInterestModalOpen(false)}
              >
                <Trans text="Cancel" />
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleExpressInterest}
                disabled={submitting[targetProject?.project_id]}
              >
                {submitting[targetProject?.project_id] ? (
                  <Trans text="Submitting..." />
                ) : (
                  <Trans text="Submit Interest" />
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
