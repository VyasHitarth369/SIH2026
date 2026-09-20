import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { matchingService } from '../../services/matchingService';

const statusClass = {
  invited: 'badge-amber',
  recommended: 'badge-blue',
  accepted: 'badge-teal',
  rejected: 'badge-coral',
};

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

export default function ProposalsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [liveInvitations, setLiveInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(true);
  const [submitting, setSubmitting] = useState({});
  const [selectedEmployees, setSelectedEmployees] = useState({}); // { [projectId]: interestId }

  // Reject Modal State
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectError, setRejectError] = useState('');

  const isManager = Boolean(
    user?.is_spoc ||
    user?.approval_authority ||
    user?.stakeholder?.approval_authority
  );

  const industryId =
    user?.stakeholder?.industry_id ||
    user?.profile?.industry_id ||
    null;

  const fetchInvitations = useCallback(async () => {
    if (!isManager || !industryId) {
      setLoadingInvitations(false);
      return;
    }
    try {
      setLoadingInvitations(true);
      const data = await matchingService.listIndustryInvitations(industryId);
      setLiveInvitations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not load industry invitations:', err.message);
    } finally {
      setLoadingInvitations(false);
    }
  }, [isManager, industryId]);

  useEffect(() => {
    fetchInvitations();
  }, [fetchInvitations]);

  const handleApprove = async (inv) => {
    const cid = inv.challenge_id;
    try {
      setSubmitting((prev) => ({ ...prev, [cid]: true }));
      await matchingService.respondIndustryMatch(
        cid,
        industryId,
        'accept',
        `Approved by Industry Manager ${user?.full_name || ''}`
      );
      showToast(<Trans text="Industry collaboration proposal accepted successfully." />);
      await fetchInvitations();
    } catch (err) {
      showToast(<Trans text={`Approval failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [cid]: false }));
    }
  };

  const openRejectModal = (inv) => {
    setRejectTarget(inv);
    setRejectReason('');
    setRejectError('');
    setRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!rejectReason.trim()) {
      setRejectError(
        lang === 'hi'
          ? 'अस्वीकृति का कारण अनिवार्य है।'
          : 'A mandatory rejection reason must be provided.'
      );
      return;
    }

    const cid = rejectTarget?.challenge_id;
    try {
      setSubmitting((prev) => ({ ...prev, [cid]: true }));
      await matchingService.respondIndustryMatch(
        cid,
        industryId,
        'reject',
        rejectReason.trim()
      );
      showToast(<Trans text="Proposal rejected with recorded feedback." />);
      setRejectModalOpen(false);
      setRejectTarget(null);
      await fetchInvitations();
    } catch (err) {
      setRejectError(err.message);
    } finally {
      setSubmitting((prev) => ({ ...prev, [cid]: false }));
    }
  };

  const handleAssignMentor = async (projectId) => {
    const interestId = selectedEmployees[projectId];
    if (!interestId) {
      showToast(<Trans text="Please select an interested employee to assign as Industry Mentor." />);
      return;
    }

    try {
      setSubmitting((prev) => ({ ...prev, [projectId]: true }));
      await matchingService.selectEmployeeMentor(
        projectId,
        interestId,
        `Assigned as official Industry Mentor by ${user?.full_name || ''}`
      );
      showToast(<Trans text="Official Industry Mentor assigned successfully." />);
      await fetchInvitations();
    } catch (err) {
      showToast(<Trans text={`Mentor assignment failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [projectId]: false }));
    }
  };

  if (!isManager) {
    return (
      <div className="card" style={{ padding: '32px', textAlign: 'center', marginTop: 24 }}>
        <span style={{ fontSize: 48 }}>🔒</span>
        <h2 style={{ marginTop: 12 }}><Trans text="Access Restricted" /></h2>
        <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>
          {lang === 'hi'
            ? 'सहयोग प्रस्ताव केवल अधिकृत उद्योग प्रबंधक (SPOC) के लिए सुलभ हैं।'
            : 'Collaboration proposals are accessible only by authorized Industry Managers / SPOCs.'}
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Industry Collaboration Proposals" /></h1>
          <p>
            {lang === 'hi'
              ? 'शीर्ष-5 मिलान द्वारा आपकी कंपनी को अग्रेषित प्रस्तावों की समीक्षा करें और उद्योग मेंटर नियुक्त करें।'
              : 'Review collaboration proposals routed to your organization via Top-5 matching and assign official Industry Mentors.'}
          </p>
        </div>
      </div>

      {loadingInvitations && (
        <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
          <p><Trans text="Loading collaboration proposals from server..." /></p>
        </div>
      )}

      {!loadingInvitations && liveInvitations.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {liveInvitations.map((inv) => {
            const ch = inv.challenge || {};
            const analysis = inv.ai_analysis || {};
            const proj = inv.project || {};
            const isBusy = submitting[inv.challenge_id] || (proj.project_id && submitting[proj.project_id]);
            const isPending = inv.status === 'invited' || inv.status === 'recommended';
            const isAccepted = inv.status === 'accepted';
            const isRejected = inv.status === 'rejected';

            const skills = parseList(analysis.skills_required || ch.expected_solution);
            const techs = parseList(analysis.technologies_suggested);
            const interestedList = inv.interested_employees || [];
            const assignedMentor = inv.assigned_mentor;

            return (
              <div className="card" key={inv.match_id || inv.challenge_id}>
                <div className="gov-card__head" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge-violet">
                    <Trans text="Priority Rank:" /> #{inv.rank}
                  </span>
                  <span className={`badge ${statusClass[inv.status] || 'badge-blue'}`}>
                    {inv.status}
                  </span>
                  <span className="badge badge-teal">
                    🎯 <Trans text="Match Score:" /> {Number(inv.match_score).toFixed(1)}%
                  </span>
                  {proj.project_id && (
                    <span className="badge badge-outline">
                      📁 {proj.project_id}
                    </span>
                  )}
                </div>

                <h3 className="problem-title" style={{ marginTop: 10 }}>
                  {ch.title || `Challenge #${inv.challenge_id}`}
                </h3>

                <p className="problem-desc">
                  {ch.description || 'No description provided.'}
                </p>

                <div className="problem-meta" style={{ marginTop: 8 }}>
                  📍 <Trans text="Location:" /> {ch.city || ch.location || 'Jharkhand'} ·{' '}
                  <Trans text="Scope:" /> <strong>{ch.impact_scope || 'Area Specific'}</strong>
                  {inv.university_name && (
                    <> · 🏫 <Trans text="University:" /> <strong>{inv.university_name}</strong></>
                  )}
                  {inv.faculty_name && (
                    <> · 👨‍🏫 <Trans text="Faculty:" /> <strong>{inv.faculty_name}</strong></>
                  )}
                </div>

                {inv.match_reason && (
                  <div style={{ marginTop: 8, padding: '8px 12px', background: '#f8fafc', borderRadius: 6, fontSize: '0.9rem', color: '#475569', fontStyle: 'italic' }}>
                    💡 <strong><Trans text="Match Rationale:" /></strong> {inv.match_reason}
                  </div>
                )}

                {/* Skills & Technologies */}
                {(skills.length > 0 || techs.length > 0) && (
                  <div className="skills-block" style={{ marginTop: 12 }}>
                    <div className="skills-block__label" style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
                      🛠️ <Trans text="Required Capabilities & Suggested Tech:" />
                    </div>
                    <div className="skills-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {skills.map((s, i) => (
                        <span className="skill-chip" key={`s-${i}`} style={{ background: '#e0f2fe', color: '#0369a1', padding: '4px 8px', borderRadius: 4, fontSize: 12.5 }}>
                          • {s}
                        </span>
                      ))}
                      {techs.map((t, i) => (
                        <span className="skill-chip" key={`t-${i}`} style={{ background: '#f3e8ff', color: '#6b21a8', padding: '4px 8px', borderRadius: 4, fontSize: 12.5 }}>
                          ⚙️ {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* PENDING ACTIONS: APPROVE / REJECT */}
                {isPending && (
                  <div className="proposal-card__actions" style={{ marginTop: 16, display: 'flex', gap: 10 }}>
                    <button
                      className="btn btn-success btn-sm"
                      disabled={isBusy}
                      onClick={() => handleApprove(inv)}
                      style={{ padding: '8px 18px', fontWeight: 600 }}
                    >
                      {isBusy ? <Trans text="Processing..." /> : <Trans text="[APPROVE]" />}
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      disabled={isBusy}
                      onClick={() => openRejectModal(inv)}
                      style={{ padding: '8px 18px', fontWeight: 600 }}
                    >
                      <Trans text="[REJECT]" />
                    </button>
                  </div>
                )}

                {/* REJECTED DISPLAY */}
                {isRejected && (
                  <div style={{ marginTop: 14, padding: '10px 14px', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6 }}>
                    <strong style={{ color: '#991b1b' }}>❌ <Trans text="Proposal Rejected" /></strong>
                    {inv.response_note && (
                      <p style={{ margin: '4px 0 0 0', color: '#7f1d1d', fontSize: '0.9rem' }}>
                        <Trans text="Reason:" /> {inv.response_note}
                      </p>
                    )}
                  </div>
                )}

                {/* ACCEPTED & MENTOR SELECTION */}
                {isAccepted && (
                  <div style={{ marginTop: 16, borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#0f172a' }}>
                        👷 <Trans text="Interested Employees & Mentor Assignment" />
                      </h4>
                      {assignedMentor ? (
                        <span className="badge badge-teal" style={{ fontWeight: 600 }}>
                          ⭐ <Trans text="Mentor Assigned" />
                        </span>
                      ) : (
                        <span className="badge badge-amber">
                          ⏳ <Trans text="Mentor Selection Open" />
                        </span>
                      )}
                    </div>

                    {assignedMentor && (
                      <div style={{ padding: '10px 14px', background: '#ecfdf5', border: '1px solid #86efac', borderRadius: 6, marginBottom: 12 }}>
                        <div style={{ fontWeight: 600, color: '#065f46' }}>
                          ⭐ <Trans text="Official Industry Mentor:" /> {assignedMentor.employee_name} ({assignedMentor.employee_id})
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#047857', marginTop: 2 }}>
                          {assignedMentor.department} · {assignedMentor.designation}
                        </div>
                      </div>
                    )}

                    {interestedList.length > 0 ? (
                      <div>
                        <table className="data-table" style={{ width: '100%', fontSize: '0.9rem', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                              <th style={{ padding: '8px 12px', width: 60 }}><Trans text="Select" /></th>
                              <th style={{ padding: '8px 12px' }}><Trans text="Employee ID" /></th>
                              <th style={{ padding: '8px 12px' }}><Trans text="Employee Name" /></th>
                              <th style={{ padding: '8px 12px' }}><Trans text="Department" /></th>
                              <th style={{ padding: '8px 12px' }}><Trans text="Designation" /></th>
                              <th style={{ padding: '8px 12px' }}><Trans text="Status" /></th>
                            </tr>
                          </thead>
                          <tbody>
                            {interestedList.map((emp) => {
                              const isSelected = emp.status === 'selected';
                              const currentSelectedId = selectedEmployees[proj.project_id];

                              return (
                                <tr key={emp.interest_id} style={{ borderBottom: '1px solid #f1f5f9', background: isSelected ? '#f0fdf4' : 'transparent' }}>
                                  <td style={{ padding: '8px 12px' }}>
                                    {!assignedMentor ? (
                                      <input
                                        type="radio"
                                        name={`mentor-${proj.project_id}`}
                                        checked={currentSelectedId === emp.interest_id}
                                        onChange={() =>
                                          setSelectedEmployees((prev) => ({
                                            ...prev,
                                            [proj.project_id]: emp.interest_id,
                                          }))
                                        }
                                      />
                                    ) : isSelected ? (
                                      '⭐'
                                    ) : (
                                      '—'
                                    )}
                                  </td>
                                  <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>{emp.employee_id}</td>
                                  <td style={{ padding: '8px 12px', fontWeight: 500 }}>{emp.employee_name || emp.employee_id}</td>
                                  <td style={{ padding: '8px 12px' }}>{emp.department || '—'}</td>
                                  <td style={{ padding: '8px 12px' }}>{emp.designation || '—'}</td>
                                  <td style={{ padding: '8px 12px' }}>
                                    <span className={`badge ${isSelected ? 'badge-teal' : 'badge-blue'}`}>
                                      {emp.status}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>

                        {!assignedMentor && proj.project_id && (
                          <div style={{ marginTop: 12 }}>
                            <button
                              className="btn btn-primary btn-sm"
                              disabled={!selectedEmployees[proj.project_id] || isBusy}
                              onClick={() => handleAssignMentor(proj.project_id)}
                              style={{ padding: '8px 16px' }}
                            >
                              {isBusy ? <Trans text="Assigning..." /> : <Trans text="[Select Employee / Assign Mentor]" />}
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic', margin: '6px 0 0 0' }}>
                        <Trans text="No employees from your company have expressed interest in this project yet." />
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loadingInvitations && liveInvitations.length === 0 && (
        <div className="card empty-state" style={{ padding: '40px 20px', textAlign: 'center' }}>
          <span className="empty-state__icon" style={{ fontSize: 48 }}>🤝</span>
          <h3 style={{ marginTop: 12 }}><Trans text="No Collaboration Proposals" /></h3>
          <p style={{ color: 'var(--text-muted)' }}>
            <Trans text="No active collaboration proposals currently routed to your organization." />
          </p>
        </div>
      )}

      {/* REJECT MODAL */}
      {rejectModalOpen && (
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
              <Trans text="Reject Collaboration Proposal" />
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              {lang === 'hi'
                ? 'कृपया इस सहयोग प्रस्ताव को अस्वीकार करने का कारण दर्ज करें (अनिवार्य):'
                : 'Please specify the reason for rejecting this collaboration proposal (mandatory):'}
            </p>

            <textarea
              rows={4}
              value={rejectReason}
              onChange={(e) => {
                setRejectReason(e.target.value);
                setRejectError('');
              }}
              placeholder={
                lang === 'hi'
                  ? 'उदा. संसाधनों की अनुपलब्धता, रणनीतिक प्राथमिकताओं में भिन्नता...'
                  : 'e.g. Current resource constraints, out of corporate focus area...'
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

            {rejectError && (
              <p style={{ color: '#dc2626', fontSize: '0.85rem', marginTop: 4 }}>
                {rejectError}
              </p>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setRejectModalOpen(false)}
              >
                <Trans text="Cancel" />
              </button>
              <button
                className="btn btn-danger btn-sm"
                onClick={handleConfirmReject}
                disabled={submitting[rejectTarget?.challenge_id]}
              >
                {submitting[rejectTarget?.challenge_id] ? (
                  <Trans text="Submitting..." />
                ) : (
                  <Trans text="Confirm Rejection" />
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
