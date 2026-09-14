import Trans from '../../components/shared/Trans.jsx';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import { useMemo, useState } from 'react';
import TrackingStepper from '../../components/shared/TrackingStepper';
import { matchingService } from '../../services/matchingService';

const priorityBadgeClass = {
  high: 'badge-coral',
  medium: 'badge-amber',
  resolved: 'badge-teal',
  new: 'badge-blue',
};

const allocationStatusLabel = {
  not_started: 'Pending Review',
  awaiting_allocation: 'Awaiting Allocation',
  allocated: 'Allocated',
  rejected: 'Rejected',
  deadline_completed: 'Deadline Completed',
};

export default function ProblemsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { problems, voteProblem, hasVoted, addFeedback } = useProblems();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [feedbackDrafts, setFeedbackDrafts] = useState({});
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // all | unsolved | solved | high | active
  const [matchesByChallenge, setMatchesByChallenge] = useState({});
  const [loadingMatches, setLoadingMatches] = useState({});
  const [expandedMatches, setExpandedMatches] = useState({});

  const toggleMatches = async (challengeId) => {
    if (expandedMatches[challengeId]) {
      setExpandedMatches((prev) => ({ ...prev, [challengeId]: false }));
      return;
    }
    setExpandedMatches((prev) => ({ ...prev, [challengeId]: true }));
    if (!matchesByChallenge[challengeId]) {
      try {
        setLoadingMatches((prev) => ({ ...prev, [challengeId]: true }));
        const list = await matchingService.fetchUniversityMatches(challengeId);
        setMatchesByChallenge((prev) => ({ ...prev, [challengeId]: Array.isArray(list) ? list : [] }));
      } catch (err) {
        console.warn(`Could not load matches for ${challengeId}:`, err.message);
      } finally {
        setLoadingMatches((prev) => ({ ...prev, [challengeId]: false }));
      }
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return problems.filter((p) => {
      if (statusFilter === 'unsolved' && p.type !== 'unsolved') return false;
      if (statusFilter === 'solved' && p.type !== 'solved') return false;
      if (statusFilter === 'high' && p.priorityLevel !== 'high') return false;
      if (statusFilter === 'active' && !(p.type === 'unsolved' && p.allocation?.allocatedTo && p.faculty)) return false;
      if (!q) return true;
      const title = (p.title[lang] || p.title.hi || '').toLowerCase();
      const desc = (p.desc[lang] || p.desc.hi || '').toLowerCase();
      return title.includes(q) || desc.includes(q);
    });
  }, [problems, search, statusFilter, lang]);

  const handleVote = (id) => {
    const recorded = voteProblem(id);
    showToast(recorded ? t.voted : t.alreadyVoted);
  };

  const submitFeedback = (id) => {
    const text = (feedbackDrafts[id] || '').trim();
    if (!text) return;
    addFeedback(id, { user: user?.name || 'Citizen', rating: 5, comment: text });
    setFeedbackDrafts((prev) => ({ ...prev, [id]: '' }));
    showToast(t.feedbackAdded);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{t.problemsTitle}</h1>
          <p>{t.problemsSub}</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/citizen/add-problem')}>{t.addNew}</button>
      </div>

      <div className="card" style={{ padding: '16px 20px' }}>
        <input
          type="text"
          className="search-input"
          placeholder={t.searchPh}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-tabs" style={{ marginTop: 12 }}>
          <div className={`filter-tab${statusFilter === 'all' ? ' active' : ''}`} onClick={() => setStatusFilter('all')}>{t.filterStatusAll}</div>
          <div className={`filter-tab${statusFilter === 'unsolved' ? ' active' : ''}`} onClick={() => setStatusFilter('unsolved')}>{t.filterStatusUnsolved}</div>
          <div className={`filter-tab${statusFilter === 'active' ? ' active' : ''}`} onClick={() => setStatusFilter('active')}>{<Trans text="Active Projects" />}</div>
          <div className={`filter-tab${statusFilter === 'solved' ? ' active' : ''}`} onClick={() => setStatusFilter('solved')}>{t.filterStatusSolved}</div>
          <div className={`filter-tab${statusFilter === 'high' ? ' active' : ''}`} onClick={() => setStatusFilter('high')}>{t.filterHighPriority}</div>
        </div>
      </div>

      <div className="stack">
        {filtered.map((p) => {
          const voted = hasVoted(p.id);
          const isActiveProject = p.type === 'unsolved' && p.allocation?.allocatedTo && p.faculty;
          const isUniSelected =
            p.status === 'university_selected' || p.rawSupabase?.status === 'university_selected';
          return (
            <div className="card" key={p.id}>
              <div className="problem-card__head">
                <span className={`badge ${p.type === 'solved' ? 'badge-teal' : 'badge-amber'}`}>
                  {p.type === 'solved' ? `✅ ${t.solved.toUpperCase()}` : t.unsolved.toUpperCase()}
                </span>
                {isUniSelected && (
                  <span className="badge badge-teal">🎓 {<Trans text="University Assigned" />}</span>
                )}
                {p.source === 'government' ? (
                  <span className="badge badge-violet">{t.govtProblem || '🏛️ Government Problem'}</span>
                ) : p.source === 'industry' ? (
                  <span className="badge badge-teal">{t.indProblem || '🏢 Industry Problem'}</span>
                ) : (
                  <span className="badge badge-gray">{t.citProblem || '👨‍🌾 Citizen Problem'}</span>
                )}
                {p.type !== 'solved' && (
                  <span className={`badge ${priorityBadgeClass[p.priorityLevel] || 'badge-blue'} badge-priority`}>
                    🤖 {t.aiPriority}: {<Trans text={p.aiPriority || ''} />}
                  </span>
                )}
              </div>

              <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
              <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>
              <div className="problem-meta">📍 {t.location}: {p.loc} · {t.scope}: <strong>{<Trans text={p.scope || ''} />}</strong></div>

              {isUniSelected && (
                <div style={{ marginTop: 8, padding: '8px 12px', background: '#ecfdf5', borderRadius: 6, border: '1px solid #a7f3d0' }}>
                  🎓 <strong>{<Trans text="Assigned University:" />}</strong>{' '}
                  {<Trans text="Top-ranked matched institution officially selected and allocated." />}
                </div>
              )}

              {p.id && (
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    className="btn btn-light btn-sm"
                    onClick={() => toggleMatches(p.id)}
                  >
                    🏛️ {expandedMatches[p.id] ? <Trans text="Hide Matched Universities" /> : <Trans text="View Matched Universities" />}
                  </button>
                </div>
              )}

              {expandedMatches[p.id] && (
                <div className="section-box section-box--muted" style={{ marginTop: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <h4 style={{ margin: 0 }}>🎯 <Trans text="Deterministic University Matches" /></h4>
                    {loadingMatches[p.id] && <small style={{ color: '#6b7280' }}>Loading matches...</small>}
                  </div>
                  {matchesByChallenge[p.id]?.length > 0 ? (
                    <div className="stack" style={{ gap: 8, marginTop: 8 }}>
                      {matchesByChallenge[p.id].map((m) => {
                        const isSelected = m.status === 'selected';
                        return (
                          <div
                            key={m.match_id || m.university_id}
                            style={{
                              background: isSelected ? '#f0fdf4' : '#ffffff',
                              border: isSelected ? '1px solid #86efac' : '1px solid #e5e7eb',
                              borderRadius: 6,
                              padding: '10px 14px',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                                #{m.rank} {m.university_name || m.university_id}
                              </span>
                              <div>
                                <span
                                  className={`badge ${
                                    isSelected
                                      ? 'badge-teal'
                                      : m.status === 'accepted'
                                      ? 'badge-blue'
                                      : m.status === 'rejected'
                                      ? 'badge-coral'
                                      : 'badge-gray'
                                  }`}
                                  style={{ marginRight: 6 }}
                                >
                                  {isSelected ? '🏆 Assigned' : m.status}
                                </span>
                                <span className="badge badge-teal">
                                  {Number(m.match_score).toFixed(1)}% Match
                                </span>
                              </div>
                            </div>
                            <p style={{ margin: 0, fontSize: '0.85rem', color: '#4b5563', fontStyle: 'italic' }}>
                              💡 {m.match_reason}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    !loadingMatches[p.id] && (
                      <p style={{ color: '#6b7280', fontSize: '0.85rem', margin: '4px 0' }}>
                        <Trans text="No matched universities recorded for this challenge yet." />
                      </p>
                    )
                  )}
                </div>
              )}

              {isActiveProject && (
                <div className="section-box section-box--muted" style={{ marginTop: 10 }}>
                  <h4>{<Trans text="Active Project — In Progress" />}</h4>
                  <div className="problem-meta">{<Trans text="🏫 University:" />} <strong>{<Trans text={p.allocation.allocatedTo} />}</strong></div>
                  <div className="problem-meta">{<Trans text="👨‍🏫 Faculty:" />} <strong>{p.faculty?.name}</strong></div>
                  <div className="problem-meta">{<Trans text="👨‍🎓 Students Involved:" />} <strong>{p.students?.length || 0}</strong></div>
                  {p.suggestedIndustries?.length > 0 && (
                    <div className="problem-meta">{<Trans text="🏢 Industry Involvement:" />} <strong>{p.suggestedIndustries.join(', ')}</strong></div>
                  )}
                  <div className="problem-meta">{<Trans text="⏳ Status:" />} <span className="badge badge-blue">{<Trans text={allocationStatusLabel[p.allocation.status] || p.allocation.status} />}</span></div>
                </div>
              )}

              {p.type === 'solved' ? (
                <div className="feedback-block">
                  <h4>{t.feedbackHead}</h4>
                  {(p.feedbacks || []).map((f, i) => (
                    <div className="feedback-item" key={i}>
                      <strong>{f.user}:</strong> {'⭐'.repeat(f.rating)} — “{f.comment}”
                    </div>
                  ))}
                  <div className="feedback-form">
                    <input
                      type="text"
                      placeholder={t.feedbackPh}
                      value={feedbackDrafts[p.id] || ''}
                      onChange={(e) => setFeedbackDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      onKeyDown={(e) => e.key === 'Enter' && submitFeedback(p.id)}
                    />
                    <button className="btn btn-success btn-sm" onClick={() => submitFeedback(p.id)}>{t.feedbackSubmit}</button>
                  </div>
                </div>
              ) : (
                <div className="problem-actions">
                  <button className="btn btn-light" disabled={voted} onClick={() => handleVote(p.id)}>
                    👍 {t.vote}: <strong>{p.votes}</strong>{voted ? ' ✓' : ''}
                  </button>
                  <span className="badge badge-blue">{t.scope}: {<Trans text={p.scope} />}</span>
                </div>
              )}

              <div className="tracking-box tracking-box--compact">
                <TrackingStepper step={p.trackingStep} labels={t} />
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && <div className="card empty-state"><span className="empty-state__icon">🗂️</span>{t.noResults}</div>}
      </div>
    </div>
  );
}
