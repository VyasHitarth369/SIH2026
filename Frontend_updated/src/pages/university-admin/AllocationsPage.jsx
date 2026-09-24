import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import Countdown from '../../components/shared/Countdown';
import apiClient from '../../services/apiClient';

const statusLabel = {
  invited: 'Review Pending',
  recommended: 'Awaiting Allocation',
  accepted: 'Provisionally Accepted',
  selected: 'Allocated to Your University',
  not_selected: 'Not Selected (Higher Rank Assigned)',
  rejected: 'Declined by Institution',
  expired: 'Deadline Expired',
  project_created: 'Project Active / Faculty Assigned',
};

const statusClass = {
  invited: 'badge-amber',
  recommended: 'badge-amber',
  accepted: 'badge-teal',
  selected: 'badge-teal',
  not_selected: 'badge-gray',
  rejected: 'badge-coral',
  expired: 'badge-gray',
  project_created: 'badge-teal',
};

// Subtle professional rank styles per Part 3 specification
const rankBadgeStyle = {
  1: { background: '#fef3c7', border: '1px solid #f59e0b', color: '#92400e', fontWeight: 700 }, // Subtle Gold
  2: { background: '#f1f5f9', border: '1px solid #94a3b8', color: '#334155', fontWeight: 600 }, // Subtle Silver/Neutral
  3: { background: '#ffedd5', border: '1px solid #ea580c', color: '#9a3412', fontWeight: 600 }, // Subtle Bronze
  4: { background: '#f8fafc', border: '1px solid #cbd5e1', color: '#475569', fontWeight: 500 }, // Clean Neutral
  5: { background: '#f8fafc', border: '1px solid #cbd5e1', color: '#475569', fontWeight: 500 }, // Clean Neutral
};

export default function AllocationsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [allocations, setAllocations] = useState([]);
  const [facultyRoster, setFacultyRoster] = useState([]);
  const [loading, setLoading] = useState(true);
  const [allocating, setAllocating] = useState({});
  const [facultyChoice, setFacultyChoice] = useState({});

  const uniId =
    user?.stakeholder?.university_id ||
    user?.profile?.university_id ||
    'U001';

  const myUniversity =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    'Birla Institute of Technology (BIT Mesra)';

  // 1. Authoritative fetch of university invitations & Top-5 allocations from backend
  const fetchAllocations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get(`/challenges/universities/${uniId}/invitations`);
      const data = res?.data || [];
      setAllocations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not fetch university allocations:', err.message);
    } finally {
      setLoading(false);
    }
  }, [uniId]);

  // 2. Authoritative fetch of university faculty directory from backend
  const fetchFaculty = useCallback(async () => {
    try {
      const res = await apiClient.get('/projects/university/faculty');
      if (res?.data && Array.isArray(res.data)) {
        setFacultyRoster(res.data);
      }
    } catch (err) {
      console.warn('Could not fetch university faculty:', err.message);
    }
  }, []);

  useEffect(() => {
    fetchAllocations();
    fetchFaculty();
  }, [fetchAllocations, fetchFaculty]);

  // Handle Faculty Allocation submission
  const handleAllocateFaculty = async (cid) => {
    const fid = facultyChoice[cid];
    if (!fid) {
      showToast(lang === 'hi' ? 'कृपया पहले एक फैकल्टी सदस्य चुनें।' : 'Please select a faculty member first.');
      return;
    }

    try {
      setAllocating((prev) => ({ ...prev, [cid]: true }));
      await apiClient.post(`/challenges/${cid}/universities/assign-faculty`, {
        faculty_ids: [fid],
      });
      showToast(lang === 'hi' ? 'फैकल्टी सफलतापूर्वक आवंटित। परियोजना सक्रिय हो गई है।' : 'Faculty successfully allocated. Collaborative project is now active.');
      setFacultyChoice((prev) => ({ ...prev, [cid]: '' }));
      await fetchAllocations();
    } catch (err) {
      showToast(lang === 'hi' ? `आवंटन विफल: ${err.message}` : `Faculty allocation failed: ${err.message}`);
    } finally {
      setAllocating((prev) => ({ ...prev, [cid]: false }));
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Allocation Monitoring" /></h1>
          <p>
            {lang === 'hi'
              ? `एआई-रैंक शीर्ष 5 विश्वविद्यालय आवंटन स्थिति ट्रैक करें और ${myUniversity} के लिए स्वीकृत समस्याओं को फैकल्टी को आवंटित करें।`
              : `Track AI-ranked Top 5 university allocation status and allocate approved problems to faculty for ${myUniversity}.`}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: '24px', textAlign: 'center' }}>
          <p>{lang === 'hi' ? 'आवंटन डेटा लोड हो रहा है...' : 'Loading university allocations from database...'}</p>
        </div>
      )}

      {!loading && allocations.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {allocations.map((inv) => {
            const ch = inv.challenge || {};
            const cid = inv.challenge_id;
            const myStatus = inv.status;
            const allMatches = Array.isArray(inv.all_matches) && inv.all_matches.length > 0
              ? inv.all_matches
              : [inv];
            const project = inv.project;
            const wonAllocation = myStatus === 'selected' || myStatus === 'project_created' || Boolean(project);
            const isApproved = myStatus === 'accepted' || wonAllocation;
            const deadlineAt = inv.response_deadline ? new Date(inv.response_deadline).getTime() : null;

            return (
              <div className="card" key={cid}>
                <div className="gov-card__head">
                  <span className="badge badge-violet">ID: #{cid}</span>
                  <span className={`badge ${statusClass[myStatus] || 'badge-blue'}`}>
                    <Trans text={statusLabel[myStatus] || myStatus} />
                  </span>
                  <span className={`badge ${isApproved ? 'badge-teal' : myStatus === 'rejected' ? 'badge-coral' : 'badge-amber'}`}>
                    <Trans text="Our Status:" /> <Trans text={myStatus} />
                  </span>
                </div>

                <h3 className="problem-title" style={{ marginTop: 8 }}>
                  {ch.title || (lang === 'hi' ? 'समस्या विवरण' : 'Problem Statement')}
                </h3>

                {ch.description && (
                  <p style={{ color: 'var(--text-muted)', fontSize: 13.5, margin: '6px 0 14px' }}>
                    {ch.description}
                  </p>
                )}

                {/* TOP 5 ALLOCATION QUEUE WITH SUBTLE PROFESSIONAL RANK DIFFERENTIATION */}
                <div style={{ marginTop: 12, marginBottom: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    🏛️ {lang === 'hi' ? 'एआई-रैंक शीर्ष 5 विश्वविद्यालय आवंटन कतार' : 'AI-Ranked Top 5 University Allocation Queue'} ({allMatches.length} {lang === 'hi' ? 'संस्थान' : 'Institutions'})
                  </div>

                  <div className="allocation-track" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {allMatches.map((m, idx) => {
                      const rankNum = m.rank || idx + 1;
                      const isMe = m.university_id === uniId || (m.university_name && m.university_name.includes(myUniversity));
                      const rankStyle = rankBadgeStyle[rankNum] || rankBadgeStyle[5];
                      const mStatus = m.status || 'recommended';

                      return (
                        <div
                          className="allocation-track__row"
                          key={m.match_id || m.university_id || idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '8px 12px',
                            borderRadius: 6,
                            background: isMe ? '#f0fdf4' : '#ffffff',
                            border: isMe ? '1px solid #86efac' : '1px solid #e2e8f0',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span
                              style={{
                                padding: '3px 8px',
                                borderRadius: 4,
                                fontSize: 12,
                                ...rankStyle,
                              }}
                            >
                              Rank #{rankNum}
                            </span>
                            <span style={{ fontSize: 13.5, fontWeight: isMe ? 700 : 500, color: isMe ? '#166534' : '#1e293b' }}>
                              {m.university_name || m.university_id}
                              {isMe && (
                                <span style={{ marginLeft: 6, fontSize: 11.5, color: '#059669', fontWeight: 600 }}>
                                  ({lang === 'hi' ? 'आपका विश्वविद्यालय' : 'You'})
                                </span>
                              )}
                            </span>
                            {m.match_score && (
                              <span style={{ fontSize: 11, color: '#64748b' }}>
                                ({Number(m.match_score).toFixed(1)}% match)
                              </span>
                            )}
                          </div>

                          <span className={`badge ${statusClass[mStatus] || 'badge-gray'}`} style={{ textTransform: 'capitalize' }}>
                            <Trans text={mStatus} />
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* DEADLINE COUNTDOWN IF PENDING */}
                {deadlineAt && ['invited', 'recommended', 'accepted'].includes(myStatus) && !project && (
                  <div className="allocation-track__row" style={{ marginTop: 8, padding: '8px 12px', background: '#f8fafc', borderRadius: 6 }}>
                    <span style={{ fontSize: 12.5, color: '#475569' }}>
                      {lang === 'hi' ? 'स्वीकार/अस्वीकार करने की समय सीमा:' : 'Response Deadline for Allocation:'}
                    </span>
                    <Countdown deadlineAt={deadlineAt} />
                  </div>
                )}

                {/* FACULTY ALLOCATION SECTION (WHEN WON / SELECTED OR ACCEPTED) */}
                {isApproved && !project?.faculty_id && (
                  <div className="decision-box" style={{ marginTop: 14, padding: 14, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}>
                    <div className="field" style={{ marginBottom: 10 }}>
                      <label style={{ fontWeight: 600, fontSize: 13 }}>
                        👨‍🏫 <Trans text="Allocate Faculty Guide / Mentor to Project" />
                      </label>
                      <select
                        value={facultyChoice[cid] || ''}
                        onChange={(e) => setFacultyChoice((prev) => ({ ...prev, [cid]: e.target.value }))}
                        disabled={allocating[cid]}
                        style={{ marginTop: 4 }}
                      >
                        <option value="">{lang === 'hi' ? 'फैकल्टी चुनें…' : 'Select faculty member…'}</option>
                        {facultyRoster.map((f) => (
                          <option key={f.faculty_id} value={f.faculty_id}>
                            {f.faculty_name} — {f.department} ({f.expertise || f.designation || 'Guide'})
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      className="btn btn-success btn-block"
                      onClick={() => handleAllocateFaculty(cid)}
                      disabled={allocating[cid]}
                    >
                      {allocating[cid] ? (
                        <Trans text="Allocating Faculty..." />
                      ) : (
                        <Trans text="Allocate Faculty & Create Project" />
                      )}
                    </button>
                  </div>
                )}

                {/* DISPLAY ASSIGNED FACULTY ONCE ALLOCATED */}
                {project && project.faculty_id && (
                  <div className="problem-meta" style={{ marginTop: 10, padding: '8px 12px', background: '#f0fdf4', borderRadius: 6, border: '1px solid #bbf7d0' }}>
                    <span style={{ fontSize: 13 }}>
                      👨‍🏫 <strong><Trans text="Allocated Faculty Guide:" /></strong> {project.faculty_name || project.faculty_id}
                      {project.faculty_email && <span style={{ color: '#64748b' }}> ({project.faculty_email})</span>}
                    </span>
                    <span className="badge badge-teal" style={{ marginLeft: 12 }}>
                      📁 Project: {project.project_id}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && allocations.length === 0 && (
        <div className="card empty-state" style={{ padding: 32, textAlign: 'center' }}>
          <span className="empty-state__icon" style={{ fontSize: 36 }}>🏛️</span>
          <h3><Trans text="No Allocations Available" /></h3>
          <p style={{ color: 'var(--text-muted)' }}>
            {lang === 'hi'
              ? 'वर्तमान में आपके विश्वविद्यालय के लिए कोई आवंटित समस्या नहीं है। कृपया "नई समस्याएं" पृष्ठ पर समीक्षा करें।'
              : 'No allocated problems found for your university yet. Please review incoming challenges on the New Problems page.'}
          </p>
        </div>
      )}
    </div>
  );
}
