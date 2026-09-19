import Trans from '../../components/shared/Trans.jsx';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import { useEffect, useMemo, useState } from 'react';
import Milestones from '../../components/shared/Milestones.jsx';

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
  const { myProblems, refreshMyProblems, isLoadingMyProblems, voteProblem, hasVoted, addFeedback } = useProblems();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [feedbackDrafts, setFeedbackDrafts] = useState({});
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // all | unsolved | solved | high | active
  const [expandedMilestones, setExpandedMilestones] = useState({});

  useEffect(() => {
    refreshMyProblems();
  }, [refreshMyProblems]);

  const toggleMilestones = (id) => {
    setExpandedMilestones((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return myProblems.filter((p) => {
      if (statusFilter === 'unsolved' && p.type !== 'unsolved') return false;
      if (statusFilter === 'solved' && p.type !== 'solved') return false;
      if (statusFilter === 'high' && p.priorityLevel !== 'high') return false;
      if (statusFilter === 'active' && !(p.type === 'unsolved' && p.allocation?.allocatedTo && p.faculty)) return false;
      if (!q) return true;
      const title = (p.title?.[lang] || p.title?.en || p.title?.hi || '').toLowerCase();
      const desc = (p.desc?.[lang] || p.desc?.en || p.desc?.hi || '').toLowerCase();
      return title.includes(q) || desc.includes(q);
    });
  }, [myProblems, search, statusFilter, lang]);

  const handleVote = async (id) => {
    const recorded = await voteProblem(id);
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
          const isSolved = p.type === 'solved' || p.status === 'solved' || p.status === 'accepted_existing_solution';
          const isActiveProject = !isSolved && (
            (p.type === 'unsolved' && p.allocation?.allocatedTo) ||
            p.status === 'university_selected' ||
            p.status === 'active' ||
            p.rawSupabase?.status === 'university_selected' ||
            p.rawSupabase?.status === 'active'
          );
          const isUnsolved = !isSolved && !isActiveProject;

          const uniName = p.allocation?.allocatedTo || p.university || p.university_name || (isActiveProject ? 'Pending Allocation' : null);
          const indName = (p.suggestedIndustries && p.suggestedIndustries.length > 0)
            ? p.suggestedIndustries.join(', ')
            : (p.industry || (isActiveProject ? 'Pending Assignment' : null));

          return (
            <div className="card" key={p.id}>
              <div className="problem-card__head">
                <span className={`badge ${isSolved ? 'badge-teal' : isActiveProject ? 'badge-teal' : 'badge-amber'}`}>
                  {isSolved
                    ? `✅ ${(t.solved || 'SOLVED').toUpperCase()}`
                    : isActiveProject
                    ? `🎓 ${lang === 'hi' ? 'सक्रिय परियोजना' : 'ACTIVE PROJECT'}`
                    : (t.unsolved || 'UNSOLVED').toUpperCase()}
                </span>
                {p.source === 'government' ? (
                  <span className="badge badge-violet">{t.govtProblem || '🏛️ Government Problem'}</span>
                ) : p.source === 'industry' ? (
                  <span className="badge badge-teal">{t.indProblem || '🏢 Industry Problem'}</span>
                ) : (
                  <span className="badge badge-gray">{t.citProblem || '👨‍🌾 Citizen Problem'}</span>
                )}
                {!isSolved && (
                  <span className={`badge ${priorityBadgeClass[p.priorityLevel] || 'badge-blue'} badge-priority`}>
                    🤖 {t.aiPriority}: <Trans text={p.aiPriority || ''} />
                  </span>
                )}
              </div>

              <h3 className="problem-title">{p.title?.[lang] || p.title?.en || p.title?.hi || p.title}</h3>
              <p className="problem-desc">{p.desc?.[lang] || p.desc?.en || p.desc?.hi || p.desc}</p>
              <div className="problem-meta">
                <span>📍 <strong>{t.location}:</strong> {p.loc}</span>
                <span>🎯 <strong>{t.scope}:</strong> <Trans text={p.scope || ''} /></span>
              </div>

              {/* Working/Active: University Name and Industry Name (No private faculty/student details) */}
              {isActiveProject && (
                <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
                  <h4 style={{ marginBottom: 8 }}><Trans text="Active Project — In Progress" /></h4>
                  <div className="problem-meta">
                    <span>🏫 <strong><Trans text="Assigned University:" /></strong> <Trans text={uniName || 'Pending Allocation'} /></span>
                    <span>🏢 <strong><Trans text="Assigned Industry:" /></strong> <Trans text={indName || 'Pending Assignment'} /></span>
                  </div>
                </div>
              )}

              {/* Solved: University Name, Industry Name, and Existing Feedback Feature */}
              {isSolved && (
                <>
                  <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
                    <h4 style={{ marginBottom: 8 }}><Trans text="Solution Delivered" /></h4>
                    <div className="problem-meta">
                      <span>🏫 <strong><Trans text="Assigned University:" /></strong> <Trans text={uniName || 'Resolved'} /></span>
                      <span>🏢 <strong><Trans text="Assigned Industry:" /></strong> <Trans text={indName || 'Resolved'} /></span>
                    </div>
                  </div>

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
                </>
              )}

              {/* Voting for Unsolved / Active problems */}
              {!isSolved && (
                <div className="problem-actions">
                  <button className="btn btn-light" disabled={voted} onClick={() => handleVote(p.id)}>
                    👍 {t.vote}: <strong>{p.votes}</strong>{voted ? ' ✓' : ''}
                  </button>
                  <span className="badge badge-blue">{t.scope}: <Trans text={p.scope} /></span>
                </div>
              )}

              {/* Standardized 7-Stage Milestone View (Read-Only for Citizens) */}
              <div style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="btn btn-light btn-sm"
                  onClick={() => toggleMilestones(p.id)}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  📊 {expandedMilestones[p.id] ? <Trans text="Hide Milestones" /> : <Trans text="View Milestones" />}
                </button>
              </div>

              {expandedMilestones[p.id] && (
                <Milestones problem={p} isCitizen={true} />
              )}
            </div>
          );
        })}

        {isLoadingMyProblems ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
            <span style={{ fontSize: '2rem', display: 'block', marginBottom: 8 }}>⏳</span>
            {lang === 'hi' ? 'आपकी समस्याएं लोड हो रही हैं…' : 'Loading your submitted problems…'}
          </div>
        ) : myProblems.length === 0 ? (
          <div className="card empty-state" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <span className="empty-state__icon" style={{ fontSize: '3rem', marginBottom: 12 }}>📋</span>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1.25rem', color: '#1f2937' }}>
              {lang === 'hi' ? 'आपने अभी तक कोई समस्या दर्ज नहीं की है' : "You haven't submitted any problems yet"}
            </h3>
            <p style={{ color: '#6b7280', maxWidth: 460, margin: '0 auto 20px auto', fontSize: '0.95rem' }}>
              {lang === 'hi'
                ? 'अपने क्षेत्र की किसी नागरिक समस्या की रिपोर्ट करें और समाधान हेतु विश्वविद्यालय शोधकर्ताओं से जुड़ें।'
                : 'Report a civic problem in your area to connect with universities and track the solution lifecycle.'}
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/citizen/add-problem')}>
              {lang === 'hi' ? '➕ पहली समस्या दर्ज करें' : '➕ Submit Your First Problem'}
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="card empty-state">
            <span className="empty-state__icon">🗂️</span>
            {t.noResults}
          </div>
        ) : null}
      </div>
    </div>
  );
}
