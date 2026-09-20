import Trans from '../../components/shared/Trans.jsx';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import Milestones from '../../components/shared/Milestones.jsx';
import governmentService from '../../services/governmentService';

const priorityBadgeClass = { high: 'badge-coral', medium: 'badge-amber', resolved: 'badge-teal', new: 'badge-blue' };

function adaptGovProblem(gp) {
  const isRejected = gp.status === 'rejected';
  const isRouted = ['routed', 'university_selected', 'project_created', 'in_project', 'active', 'solved', 'completed'].includes(gp.status);
  return {
    id: gp.challenge_id,
    challenge_id: gp.challenge_id,
    title: { hi: gp.title, en: gp.title },
    desc: { hi: gp.description, en: gp.description },
    loc: gp.location || gp.city || gp.district || 'Jharkhand',
    city: gp.city,
    district: gp.district,
    status: gp.status || 'submitted',
    submitted_by: gp.submitted_by,
    source: (gp.submitted_by || '').toLowerCase().includes('gov')
      ? 'government'
      : (gp.submitted_by || '').toLowerCase().includes('ind')
      ? 'industry'
      : 'citizen',
    category: gp.category || 'General Civic',
    domain: gp.category || 'General Civic',
    requiredTechnologies: gp.required_technologies ? gp.required_technologies.split(',').map((s) => s.trim()) : [],
    priorityLevel: gp.innovation_scope === 'high' ? 'high' : 'medium',
    aiPriority: (gp.innovation_scope || 'NORMAL').toUpperCase(),
    votes: 1,
    allocation: {
      status: isRejected ? 'rejected' : isRouted ? 'allocated' : 'not_started',
      allocatedTo: gp.university_name || null,
    },
    faculty: gp.faculty_name ? { name: gp.faculty_name } : null,
    faculty_name: gp.faculty_name,
    students: [],
    suggestedIndustries: gp.industry_name ? [gp.industry_name] : [],
    industry_name: gp.industry_name,
    submissionDate: gp.created_at ? gp.created_at.slice(0, 10) : '—',
    government_rejection_reason: gp.government_rejection_reason,
    government_reviewed_at: gp.government_reviewed_at,
    government_reviewed_by: gp.government_reviewed_by,
    university_rejections: gp.university_rejections || [],
    raw: gp,
  };
}

export default function ActiveProblemsPage() {
  const { t, lang } = useLanguage();
  const { problems: fallbackProblems } = useProblems();
  const { showToast } = useToast();

  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [expandedMilestones, setExpandedMilestones] = useState(null);

  // Reject Modal state
  const [rejectingProblem, setRejectingProblem] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  const loadProblems = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await governmentService.fetchGovernmentProblems();
      if (Array.isArray(data) && data.length > 0) {
        setItems(data.map(adaptGovProblem));
      } else if (fallbackProblems && fallbackProblems.length > 0) {
        setItems(fallbackProblems);
      } else {
        setItems([]);
      }
    } catch (err) {
      console.warn('Could not load authoritative government problems, using fallback:', err.message);
      if (fallbackProblems && fallbackProblems.length > 0) {
        setItems(fallbackProblems);
      }
    } finally {
      setIsLoading(false);
    }
  }, [fallbackProblems]);

  useEffect(() => {
    loadProblems();
  }, [loadProblems]);

  const handleApprove = async (id) => {
    setIsSubmittingDecision(true);
    try {
      const res = await governmentService.approveProblem(id);
      showToast(lang === 'hi' ? 'समस्या स्वीकृत और शीर्ष विश्वविद्यालयों को प्रेषित की गई।' : 'Problem approved and routed to top matching universities.');
      setItems((prev) =>
        prev.map((item) =>
          item.id === id
            ? {
                ...item,
                status: 'routed',
                allocation: { ...item.allocation, status: 'allocated' },
                government_reviewed_at: res?.government_reviewed_at || new Date().toISOString(),
                government_rejection_reason: null,
              }
            : item
        )
      );
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'Failed to approve problem');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const openRejectModal = (problem) => {
    setRejectingProblem(problem);
    setRejectReason('');
  };

  const closeRejectModal = () => {
    setRejectingProblem(null);
    setRejectReason('');
  };

  const handleConfirmReject = async () => {
    const trimmed = rejectReason.trim();
    if (!trimmed) {
      showToast(lang === 'hi' ? 'अस्वीकृति का कारण अनिवार्य है।' : 'Rejection reason is mandatory.');
      return;
    }
    if (!rejectingProblem) return;

    setIsSubmittingDecision(true);
    try {
      const res = await governmentService.rejectProblem(rejectingProblem.id, trimmed);
      showToast(lang === 'hi' ? 'समस्या आधिकारिक कारण के साथ अस्वीकृत कर दी गई।' : 'Problem declined with recorded reason.');
      setItems((prev) =>
        prev.map((item) =>
          item.id === rejectingProblem.id
            ? {
                ...item,
                status: 'rejected',
                allocation: { ...item.allocation, status: 'rejected' },
                government_rejection_reason: trimmed,
                government_reviewed_at: res?.government_reviewed_at || new Date().toISOString(),
              }
            : item
        )
      );
      closeRejectModal();
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'Failed to reject problem');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const filtered = useMemo(() => {
    return items.filter((p) => {
      const st = p.status || p.raw?.status;
      const isPending = st === 'submitted' || st === 'validated' || st === 'under_review';
      const isApprovedRouted = ['routed', 'university_selected', 'project_created', 'in_project', 'active'].includes(st);
      const isRejected = st === 'rejected';
      const isSolved = st === 'solved' || st === 'completed' || p.type === 'solved';

      if (filter === 'pending') return isPending;
      if (filter === 'allocated') return isApprovedRouted;
      if (filter === 'rejected') return isRejected;
      if (filter === 'solved') return isSolved;
      return true;
    });
  }, [items, filter]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Active Problems" />}</h1>
          <p>{<Trans text="Government Authority Review & Problem Lifecycle Monitoring." />}</p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div className={`filter-tab${filter === 'all' ? ' active' : ''}`} onClick={() => setFilter('all')}>
            {t.filterAll} ({items.length})
          </div>
          <div className={`filter-tab${filter === 'pending' ? ' active' : ''}`} onClick={() => setFilter('pending')}>
            {t.filterPending || 'Pending Review'}
          </div>
          <div className={`filter-tab${filter === 'allocated' ? ' active' : ''}`} onClick={() => setFilter('allocated')}>
            {lang === 'hi' ? 'स्वीकृत और अग्रेषित' : 'Approved & Routed'}
          </div>
          <div className={`filter-tab${filter === 'rejected' ? ' active' : ''}`} onClick={() => setFilter('rejected')}>
            {lang === 'hi' ? 'अस्वीकृत' : 'Rejected'}
          </div>
          <div className={`filter-tab${filter === 'solved' ? ' active' : ''}`} onClick={() => setFilter('solved')}>
            {t.filterHistory || 'Solved'}
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
          <span style={{ fontSize: '2rem', display: 'block', marginBottom: 8 }}>⏳</span>
          {lang === 'hi' ? 'समस्याएं लोड हो रही हैं…' : 'Loading monitored problems…'}
        </div>
      ) : (
        filtered.map((p) => {
          const st = p.status || p.raw?.status;
          const isPending = st === 'submitted' || st === 'validated' || st === 'under_review';
          const isApprovedRouted = ['routed', 'university_selected', 'project_created', 'in_project', 'active'].includes(st);
          const isRejected = st === 'rejected';
          const isSolved = st === 'solved' || st === 'completed';

          return (
            <div className="card" key={p.id}>
              <div className="gov-card__head">
                <span className="badge badge-violet">ID: #CH-JH-{p.id}</span>
                {p.source === 'government' ? (
                  <span className="badge badge-violet">{t.govtProblem || '🏛️ Government Problem'}</span>
                ) : p.source === 'industry' ? (
                  <span className="badge badge-teal">{t.indProblem || '🏢 Industry Problem'}</span>
                ) : (
                  <span className="badge badge-gray">{t.citProblem || '👨‍🌾 Citizen Problem'}</span>
                )}
                <span className={`badge ${priorityBadgeClass[p.priorityLevel] || 'badge-blue'}`}>
                  {t.aiPriority}: {<Trans text={p.aiPriority} />}
                </span>

                {/* Authoritative Status Badge */}
                {isPending && (
                  <span className="badge badge-amber">
                    ⏳ {lang === 'hi' ? 'सरकारी समीक्षा लंबित' : 'Pending Government Review'}
                  </span>
                )}
                {isApprovedRouted && (
                  <span className="badge badge-teal">
                    ✅ {lang === 'hi' ? 'स्वीकृत एवं विश्वविद्यालयों को अग्रेषित' : 'Approved & Routed to Universities'}
                  </span>
                )}
                {isRejected && (
                  <span className="badge badge-coral">
                    ❌ {lang === 'hi' ? 'अस्वीकृत' : 'Rejected by Government'}
                  </span>
                )}
                {isSolved && (
                  <span className="badge badge-teal">
                    🏆 {lang === 'hi' ? 'समाधान पूर्ण' : 'Solved'}
                  </span>
                )}
              </div>

              <h3 className="problem-title">{p.title[lang] || p.title.hi || p.title.en}</h3>
              <p className="problem-desc">{p.desc[lang] || p.desc.hi || p.desc.en}</p>

              <div className="gov-card__details">
                <div>📍 <strong>{t.location}:</strong> {p.loc}</div>
                <div>🏷️ <strong>{<Trans text="Domain:" />}</strong> {<Trans text={p.domain || p.category} />}</div>
                <div>💡 <strong>{<Trans text="Required Technologies:" />}</strong> {(p.requiredTechnologies || []).join(', ') || '—'}</div>
                <div>👍 <strong>{t.citizenVotes}:</strong> {p.votes}</div>
                <div>🏫 <strong>{<Trans text="University:" />}</strong> {p.allocation.allocatedTo ? <Trans text={p.allocation.allocatedTo} /> : <Trans text="Not yet allocated" />}</div>
                <div>👨‍🏫 <strong>{<Trans text="Faculty:" />}</strong> {p.faculty?.name || p.faculty_name || '—'}</div>
                <div>🏢 <strong>{<Trans text="Suggested Industry:" />}</strong> {(p.suggestedIndustries || []).join(', ') || p.industry_name || '—'}</div>
                <div>📅 <strong>{<Trans text="Submitted:" />}</strong> {p.submissionDate}</div>
              </div>

              {/* Government Rejection Reason Display */}
              {isRejected && (
                <div style={{ marginTop: 12, padding: '12px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8 }}>
                  <div style={{ fontWeight: 600, color: '#991b1b', marginBottom: 4 }}>
                    🚫 <Trans text="Government Rejection Reason:" />
                  </div>
                  <div style={{ fontSize: 13, color: '#7f1d1d' }}>
                    {p.government_rejection_reason || <Trans text="Declined by government authority." />}
                  </div>
                  {p.government_reviewed_at && (
                    <div style={{ fontSize: 11, color: '#991b1b', marginTop: 4 }}>
                      {new Date(p.government_reviewed_at).toLocaleString()}
                    </div>
                  )}
                </div>
              )}

              {/* University Rejection Feedback (if any university SPOC rejected) */}
              {p.university_rejections && p.university_rejections.length > 0 && (
                <div style={{ marginTop: 12, padding: '12px 14px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8 }}>
                  <div style={{ fontWeight: 600, color: '#92400e', marginBottom: 6 }}>
                    ⚠️ <Trans text="University Rejection Feedback:" />
                  </div>
                  {p.university_rejections.map((rej, idx) => (
                    <div key={idx} style={{ fontSize: 13, color: '#78350f', marginBottom: 4 }}>
                      <strong>{rej.university_name || rej.university_id}:</strong> {rej.rejection_reason}
                      {rej.responded_at && (
                        <span style={{ fontSize: 11, color: '#92400e', marginLeft: 6 }}>
                          ({new Date(rej.responded_at).toLocaleDateString()})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="proposal-card__actions" style={{ marginTop: 14, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                {/* Government Gate: Approve & Reject buttons ONLY for pending challenges */}
                {isPending && (
                  <>
                    <button
                      className="btn btn-success btn-sm"
                      disabled={isSubmittingDecision}
                      onClick={() => handleApprove(p.id)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                    >
                      ✓ {lang === 'hi' ? 'स्वीकृत करें एवं शीर्ष विश्वविद्यालयों को भेजें' : 'Approve & Route to Universities'}
                    </button>
                    <button
                      className="btn btn-outline-danger btn-sm"
                      disabled={isSubmittingDecision}
                      onClick={() => openRejectModal(p)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        borderColor: '#dc2626',
                        color: '#dc2626',
                        background: 'transparent',
                        padding: '6px 12px',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontWeight: 500,
                      }}
                    >
                      ✕ {lang === 'hi' ? 'अस्वीकृत करें' : 'Decline Problem'}
                    </button>
                  </>
                )}

                <button
                  className="btn btn-light btn-sm"
                  onClick={() => setExpandedMilestones(expandedMilestones === p.id ? null : p.id)}
                >
                  {expandedMilestones === p.id ? <Trans text="Hide Milestones" /> : <Trans text="View Milestones" />}
                </button>
              </div>

              {expandedMilestones === p.id && <Milestones problem={p} />}
            </div>
          );
        })
      )}

      {filtered.length === 0 && !isLoading && (
        <div className="card">{<Trans text="No problems match this filter." />}</div>
      )}

      {/* Mandatory Rejection Reason Modal */}
      {rejectingProblem && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 16,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 520,
              width: '100%',
              backgroundColor: '#ffffff',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            }}
          >
            <h3 style={{ margin: '0 0 8px 0', color: '#991b1b', display: 'flex', alignItems: 'center', gap: 8 }}>
              🚫 <Trans text="Decline Problem Statement" />
            </h3>
            <p style={{ fontSize: 14, color: '#4b5563', margin: '0 0 16px 0' }}>
              <Trans text="Please state the official reason for declining this problem statement. This explanation will be permanently recorded and visible to the submitting citizen and system audit." />
            </p>

            <div style={{ marginBottom: 12, fontSize: 13, color: '#1f2937' }}>
              <strong><Trans text="Problem:" /></strong> {rejectingProblem.title[lang] || rejectingProblem.title.hi || rejectingProblem.title.en}
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                <Trans text="Rejection Reason (Mandatory):" />
              </label>
              <textarea
                rows={4}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder={lang === 'hi' ? 'अस्वीकृति का स्पष्ट कारण दर्ज करें...' : 'Enter clear justification for declining this problem statement...'}
                style={{
                  width: '100%',
                  padding: 10,
                  borderRadius: 6,
                  border: '1px solid #d1d5db',
                  fontSize: 14,
                  fontFamily: 'inherit',
                  resize: 'vertical',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                className="btn btn-light"
                onClick={closeRejectModal}
                disabled={isSubmittingDecision}
              >
                <Trans text="Cancel" />
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmReject}
                disabled={isSubmittingDecision || !rejectReason.trim()}
                style={{ backgroundColor: '#dc2626', borderColor: '#dc2626' }}
              >
                {isSubmittingDecision ? <Trans text="Saving..." /> : <Trans text="Confirm Decline" />}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

