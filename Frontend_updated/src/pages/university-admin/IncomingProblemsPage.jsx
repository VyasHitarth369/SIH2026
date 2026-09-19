import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import Countdown from '../../components/shared/Countdown';
import apiClient from '../../services/apiClient';

const statusLabel = {
  invited: 'New / Pending Review',
  recommended: 'New / Recommended',
  accepted: 'Approved / Pending Faculty Allocation',
  selected: 'Allocated / Project Created',
  not_selected: 'Not Selected',
  rejected: 'Rejected',
  expired: 'Deadline Expired',
  project_created: 'Faculty Assigned / Project Active',
};

const statusClass = {
  invited: 'badge-amber',
  recommended: 'badge-blue',
  accepted: 'badge-teal',
  selected: 'badge-teal',
  not_selected: 'badge-gray',
  rejected: 'badge-coral',
  expired: 'badge-gray',
  project_created: 'badge-teal',
};

export default function IncomingProblemsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [liveInvitations, setLiveInvitations] = useState([]);
  const [loadingLive, setLoadingLive] = useState(false);
  const [submitting, setSubmitting] = useState({});

  // Faculty state
  const [facultyRoster, setFacultyRoster] = useState([]);
  const [selectedFaculty, setSelectedFaculty] = useState({}); // { [challengeId]: [facultyObj, ...] }
  const [facultyPickerVal, setFacultyPickerVal] = useState({}); // { [challengeId]: facultyId }

  // Rejection modal state
  const [rejectingItem, setRejectingItem] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [rejectingLoading, setRejectingLoading] = useState(false);

  // In-session approval state tracking
  const [approvedState, setApprovedState] = useState({});

  const uniId =
    user?.stakeholder?.university_id ||
    user?.profile?.university_id ||
    'U001';

  const myUniversity =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    'Birla Institute of Technology (BIT Mesra)';

  // 1. Fetch invitations authoritatively
  const fetchLive = useCallback(async () => {
    try {
      setLoadingLive(true);
      const res = await apiClient.get(`/challenges/universities/${uniId}/invitations`);
      const data = res?.data || [];
      setLiveInvitations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not fetch university invitations:', err.message);
    } finally {
      setLoadingLive(false);
    }
  }, [uniId]);

  // 2. Fetch authoritative faculty list for this university
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
    fetchLive();
    fetchFaculty();
  }, [fetchLive, fetchFaculty]);

  // Handle Approve action (Part 5 & 6)
  const handleApprove = async (item) => {
    const cid = item.challenge_id;
    try {
      setSubmitting((prev) => ({ ...prev, [cid]: true }));
      await apiClient.post(`/challenges/${cid}/universities/approve`, {});
      setApprovedState((prev) => ({ ...prev, [cid]: true }));
      showToast(
        <Trans text="Problem statement approved. Please select faculty mentors below." />
      );
      await fetchLive();
    } catch (err) {
      showToast(<Trans text={`Approval failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [cid]: false }));
    }
  };

  // Open Rejection Modal (Part 9)
  const openRejectModal = (item) => {
    setRejectingItem(item);
    setRejectionReason('');
  };

  // Submit Rejection (Part 9 & 10)
  const submitRejection = async () => {
    if (!rejectionReason.trim()) {
      showToast(<Trans text="Please provide a valid reason for rejection." />);
      return;
    }
    const cid = rejectingItem.challenge_id;
    try {
      setRejectingLoading(true);
      await apiClient.post(`/challenges/${cid}/universities/reject`, {
        reason: rejectionReason.trim(),
      });
      showToast(<Trans text="Problem statement rejected. Feedback recorded for government and submitter." />);
      setRejectingItem(null);
      setRejectionReason('');
      await fetchLive();
    } catch (err) {
      showToast(<Trans text={`Rejection failed: ${err.message}`} />);
    } finally {
      setRejectingLoading(false);
    }
  };

  // Faculty selection handlers (Part 7 & 8)
  const addFacultyMentor = (cid) => {
    const chosenId = facultyPickerVal[cid];
    if (!chosenId) return;
    const facObj = facultyRoster.find((f) => f.faculty_id === chosenId);
    if (!facObj) return;

    const currentList = selectedFaculty[cid] || [];
    // Duplicate prevention (Part 8)
    if (currentList.some((f) => f.faculty_id === chosenId)) {
      showToast(<Trans text="Faculty member is already selected." />);
      return;
    }

    setSelectedFaculty((prev) => ({
      ...prev,
      [cid]: [...currentList, facObj],
    }));
    setFacultyPickerVal((prev) => ({ ...prev, [cid]: '' }));
  };

  const removeFacultyMentor = (cid, fid) => {
    setSelectedFaculty((prev) => ({
      ...prev,
      [cid]: (prev[cid] || []).filter((f) => f.faculty_id !== fid),
    }));
  };

  const handleConfirmFaculty = async (item) => {
    const cid = item.challenge_id;
    const mentors = selectedFaculty[cid] || [];
    if (mentors.length === 0) {
      showToast(<Trans text="Please select at least one faculty mentor." />);
      return;
    }

    try {
      setSubmitting((prev) => ({ ...prev, [cid]: true }));
      const facultyIds = mentors.map((m) => m.faculty_id);
      const res = await apiClient.post(`/challenges/${cid}/universities/assign-faculty`, {
        faculty_ids: facultyIds,
      });

      showToast(
        <Trans text="Faculty assigned successfully. Collaborative project created and Top-5 Industry matching initiated." />
      );
      setApprovedState((prev) => ({ ...prev, [cid]: false }));
      setSelectedFaculty((prev) => ({ ...prev, [cid]: [] }));
      await fetchLive();
    } catch (err) {
      showToast(<Trans text={`Faculty assignment failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [cid]: false }));
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="New Problems" /></h1>
          <p>
            {lang === 'hi'
              ? `${myUniversity} को अग्रेषित नई समस्याएं। समीक्षा करें, स्वीकार या अस्वीकार करें, एवं फैकल्टी मेंटर्स आवंटित करें।`
              : `Newly routed problem statements assigned to ${myUniversity}. Review, approve/reject, and allocate faculty mentors.`}
          </p>
        </div>
      </div>

      {loadingLive && (
        <div className="card" style={{ padding: '24px', textAlign: 'center' }}>
          <p>{lang === 'hi' ? 'समस्याएं लोड हो रही हैं...' : 'Loading newly routed problems from server...'}</p>
        </div>
      )}

      {!loadingLive && liveInvitations.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {liveInvitations.map((inv) => {
            const ch = inv.challenge || {};
            const analysis = inv.ai_analysis || {};
            const status = inv.status;
            const cid = inv.challenge_id;
            const deadlineMs = inv.response_deadline ? new Date(inv.response_deadline).getTime() : null;
            const isBusy = submitting[cid];
            const isApproved = approvedState[cid] || status === 'accepted' || status === 'selected';

            const skillsList = [
              ...(analysis.required_skills || analysis.skills_required || []),
              ...(analysis.required_technologies || analysis.technologies_suggested || []),
            ];

            const currentMentors = selectedFaculty[cid] || [];
            const availableFaculty = facultyRoster.filter(
              (f) => !currentMentors.some((m) => m.faculty_id === f.faculty_id)
            );

            return (
              <div className="card" key={inv.match_id || cid}>
                <div className="problem-card__head">
                  <span className={`badge ${statusClass[status] || 'badge-blue'}`}>
                    {statusLabel[status] || status}
                  </span>
                  <span className="badge badge-blue">
                    🎯 <Trans text="Priority Rank:" /> #{inv.rank}
                  </span>
                  <span className="badge badge-teal">
                    ✨ <Trans text="Match Score:" /> {Number(inv.match_score).toFixed(1)}%
                  </span>
                  <span className="badge badge-violet">
                    ID: #{ch.challenge_id || cid}
                  </span>
                </div>

                <h3 className="problem-title">{ch.title || `Challenge #${cid}`}</h3>
                <p className="problem-desc">{ch.description || 'No description provided.'}</p>

                <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
                    <div>
                      📍 <strong><Trans text="Location:" /></strong> {ch.city || 'Jharkhand'}, {ch.district || ch.city || 'Jharkhand'}
                    </div>
                    <div>
                      🎯 <strong><Trans text="Scope:" /></strong> {ch.impact_scope || 'Area Specific'}
                    </div>
                    <div>
                      👤 <strong><Trans text="Submitter:" /></strong> {ch.submitted_by || 'Citizen Submitter'}
                    </div>
                    <div>
                      🏷️ <strong><Trans text="Category:" /></strong> {analysis.category || 'General Civic'}
                    </div>
                  </div>

                  {inv.match_reason && (
                    <div style={{ marginTop: 8, color: '#4b5563', fontStyle: 'italic', fontSize: 13 }}>
                      💡 <strong><Trans text="Match Rationale:" /></strong> {inv.match_reason}
                    </div>
                  )}

                  {skillsList.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>
                        🛠️ <Trans text="Required Skills & Technologies:" />
                      </div>
                      <div className="skills-chips">
                        {skillsList.map((skill, idx) => (
                          <span className="skill-chip" key={`${skill}-${idx}`}>{skill}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {deadlineMs && status === 'invited' && (
                  <div style={{ margin: '12px 0' }}>
                    <span style={{ fontWeight: 600, marginRight: 8 }}>
                      ⏳ {lang === 'hi' ? 'स्वीकार करने की समय सीमा:' : 'Response Window:'}
                    </span>
                    <Countdown deadlineAt={deadlineMs} />
                  </div>
                )}

                {/* Approve / Reject Actions (Part 5) */}
                {status === 'invited' && !isApproved && (
                  <div className="proposal-card__actions" style={{ marginTop: 16 }}>
                    <button
                      className="btn btn-success btn-sm"
                      disabled={isBusy}
                      onClick={() => handleApprove(inv)}
                    >
                      {isBusy ? <Trans text="Processing..." /> : `✓ ${lang === 'hi' ? 'स्वीकार करें' : 'Approve'}`}
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      disabled={isBusy}
                      onClick={() => openRejectModal(inv)}
                    >
                      {isBusy ? <Trans text="Processing..." /> : `✕ ${lang === 'hi' ? 'अस्वीकार करें' : 'Reject'}`}
                    </button>
                  </div>
                )}

                {/* Faculty Mentor Assignment Section (Part 6, 7 & 8) */}
                {isApproved && status !== 'rejected' && (
                  <div
                    style={{
                      marginTop: 16,
                      padding: 16,
                      background: '#f8fafc',
                      border: '1px solid #cbd5e1',
                      borderRadius: 8,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                      <h4 style={{ margin: 0, color: '#0f172a' }}>
                        👨‍🏫 <Trans text="Assign Faculty Mentors" />
                      </h4>
                      <span className="badge badge-teal">
                        <Trans text="Multiple Selection Allowed" />
                      </span>
                    </div>

                    <p style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>
                      {lang === 'hi'
                        ? 'इस अनुमोदित समस्या के मार्गदर्शन हेतु अपने विश्वविद्यालय के एक या अधिक फैकल्टी मेंटर्स चुनें।'
                        : 'Select one or more faculty mentors from your university to guide this project.'}
                    </p>

                    {/* Selected Faculty List */}
                    {currentMentors.length > 0 && (
                      <div style={{ marginBottom: 14 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>
                          <Trans text="Selected Faculty Mentors:" />
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                          {currentMentors.map((m, idx) => (
                            <div
                              key={m.faculty_id}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 6,
                                padding: '5px 12px',
                                background: '#ecfdf5',
                                border: '1px solid #6ee7b7',
                                borderRadius: 6,
                                fontSize: 13,
                                color: '#065f46',
                              }}
                            >
                              <span>{idx === 0 ? '⭐' : '👨‍🏫'}</span>
                              <strong>{m.faculty_id}</strong> — {m.faculty_name}
                              <button
                                type="button"
                                onClick={() => removeFacultyMentor(cid, m.faculty_id)}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  color: '#dc2626',
                                  cursor: 'pointer',
                                  fontWeight: 'bold',
                                  marginLeft: 4,
                                }}
                                title="Remove"
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Faculty Picker Controls */}
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <select
                        value={facultyPickerVal[cid] || ''}
                        onChange={(e) => setFacultyPickerVal((prev) => ({ ...prev, [cid]: e.target.value }))}
                        style={{
                          padding: '8px 12px',
                          borderRadius: 6,
                          border: '1px solid #cbd5e1',
                          flex: '1 1 300px',
                          fontSize: 13,
                          background: '#fff',
                        }}
                      >
                        <option value="">
                          {lang === 'hi' ? '-- फैकल्टी चुनें (आईडी एवं नाम) --' : '-- Select Faculty (ID & Name) --'}
                        </option>
                        {availableFaculty.map((f) => (
                          <option key={f.faculty_id} value={f.faculty_id}>
                            {f.faculty_id} — {f.faculty_name} ({f.department})
                          </option>
                        ))}
                      </select>

                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        disabled={!facultyPickerVal[cid]}
                        onClick={() => addFacultyMentor(cid)}
                      >
                        + <Trans text="Add Mentor" />
                      </button>

                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={isBusy || currentMentors.length === 0}
                        onClick={() => handleConfirmFaculty(inv)}
                      >
                        {isBusy ? <Trans text="Processing..." /> : <Trans text="Confirm Faculty Assignment" />}
                      </button>
                    </div>
                  </div>
                )}

                {/* Display rejection note if rejected */}
                {status === 'rejected' && (
                  <div style={{ marginTop: 12, padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, color: '#991b1b' }}>
                    <strong>✕ <Trans text="Rejected:" /></strong>{' '}
                    {inv.response_note || (lang === 'hi' ? 'विश्वविद्यालय प्रशासन द्वारा अस्वीकृत।' : 'Declined by university administration.')}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loadingLive && liveInvitations.length === 0 && (
        <div className="card empty-state">
          <span className="empty-state__icon">📭</span>
          <h3><Trans text="No New Problems" /></h3>
          <p>
            {lang === 'hi'
              ? 'वर्तमान में आपके विश्वविद्यालय को कोई नई समस्या अग्रेषित नहीं की गई है।'
              : 'No new problem statements are currently routed to your university.'}
          </p>
        </div>
      )}

      {/* Rejection Reason Modal (Part 9) */}
      {rejectingItem && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-head">
              <h3>✕ <Trans text="Reject Problem Statement" /></h3>
              <button
                type="button"
                className="modal-close"
                onClick={() => setRejectingItem(null)}
                disabled={rejectingLoading}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p style={{ fontSize: 13.5, color: '#475569', marginBottom: 12 }}>
                <strong><Trans text="Problem:" /></strong> {rejectingItem.challenge?.title || `Challenge #${rejectingItem.challenge_id}`}
              </p>

              <div className="field">
                <label style={{ fontWeight: 600, color: '#1e293b' }}>
                  <Trans text="Reason for Rejection (Mandatory):" />
                </label>
                <textarea
                  rows={4}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder={
                    lang === 'hi'
                      ? 'कृपया अस्वीकृति का कारण स्पष्ट रूप से लिखें (उदा. प्रयोगशाला सुविधाओं की कमी, वर्तमान अनुसंधान क्षेत्र से बाहर, आदि)...'
                      : 'Please specify the clear reason for declining this problem (e.g. lack of specialized lab infrastructure, outside current department research scope, etc.)...'
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13.5 }}
                />
                <small style={{ color: '#64748b' }}>
                  {lang === 'hi'
                    ? 'यह कारण सरकारी अधिकारी एवं मूल समस्या प्रेषक को भेजा जाएगा।'
                    : 'This feedback will be routed to the Government officer and the original submitter.'}
                </small>
              </div>
            </div>

            <div className="modal-foot">
              <button
                type="button"
                className="btn btn-light btn-sm"
                onClick={() => setRejectingItem(null)}
                disabled={rejectingLoading}
              >
                <Trans text="Cancel" />
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={submitRejection}
                disabled={rejectingLoading || !rejectionReason.trim()}
              >
                {rejectingLoading ? <Trans text="Submitting..." /> : <Trans text="Confirm Rejection" />}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
