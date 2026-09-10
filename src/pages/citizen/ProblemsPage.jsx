import Trans from '../../components/shared/Trans.jsx';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import { useMemo, useState } from 'react';
import TrackingStepper from '../../components/shared/TrackingStepper';

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
          return (
            <div className="card" key={p.id}>
              <div className="problem-card__head">
                <span className={`badge ${p.type === 'solved' ? 'badge-teal' : 'badge-amber'}`}>
                  {p.type === 'solved' ? `✅ ${t.solved.toUpperCase()}` : t.unsolved.toUpperCase()}
                </span>
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
