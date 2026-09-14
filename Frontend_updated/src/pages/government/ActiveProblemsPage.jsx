import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';
import Milestones from '../../components/shared/Milestones.jsx';

const priorityBadgeClass = { high: 'badge-coral', medium: 'badge-amber', resolved: 'badge-teal', new: 'badge-blue' };
const statusLabel = {
  not_started: 'Pending Review',
  awaiting_allocation: 'Awaiting Allocation',
  allocated: 'Allocated',
  rejected: 'Rejected',
  deadline_completed: 'Deadline Completed',
};

export default function ActiveProblemsPage() {
  const { t, lang } = useLanguage();
  const { problems, routeToUniversities } = useProblems();
  const [filter, setFilter] = useState('all');
  const [expandedMilestones, setExpandedMilestones] = useState(null);

  const filtered = problems.filter((p) => {
    if (filter === 'pending') return p.allocation.status === 'not_started';
    if (filter === 'allocated') return p.allocation.status === 'allocated';
    if (filter === 'solved') return p.type === 'solved';
    return true;
  });

  const handleRoute = (id) => {
    const queue = ['BIT Mesra, Ranchi', 'NIT Jamshedpur', 'IIT (ISM) Dhanbad', 'BAU Ranchi'];
    routeToUniversities(id, queue);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Active Problems" />}</h1>
          <p>{<Trans text="Monitoring view. Accept/Reject decisions are now made by University Administration." />}</p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div className={`filter-tab${filter === 'all' ? ' active' : ''}`} onClick={() => setFilter('all')}>{t.filterAll} ({problems.length})</div>
          <div className={`filter-tab${filter === 'pending' ? ' active' : ''}`} onClick={() => setFilter('pending')}>{t.filterPending}</div>
          <div className={`filter-tab${filter === 'allocated' ? ' active' : ''}`} onClick={() => setFilter('allocated')}>{t.filterApproved}</div>
          <div className={`filter-tab${filter === 'solved' ? ' active' : ''}`} onClick={() => setFilter('solved')}>{t.filterHistory}</div>
        </div>
      </div>

      {filtered.map((p) => (
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
            <span className={`badge ${priorityBadgeClass[p.priorityLevel] || 'badge-blue'}`}>{t.aiPriority}: {<Trans text={p.aiPriority} />}</span>
            <span className="badge badge-outline">{<Trans text={statusLabel[p.allocation.status] || p.allocation.status} />}</span>
          </div>

          <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
          <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>

          <div className="gov-card__details">
            <div>📍 <strong>{t.location}:</strong> {p.loc}</div>
            <div>🏷️ <strong>{<Trans text="Domain:" />}</strong> {<Trans text={p.domain || p.category} />}</div>
            <div>💡 <strong>{<Trans text="Required Technologies:" />}</strong> {(p.requiredTechnologies || []).join(', ') || '—'}</div>
            <div>👍 <strong>{t.citizenVotes}:</strong> {p.votes}</div>
            <div>🏫 <strong>{<Trans text="University:" />}</strong> {p.allocation.allocatedTo ? <Trans text={p.allocation.allocatedTo} /> : <Trans text="Not yet allocated" />}</div>
            <div>👨‍🏫 <strong>{<Trans text="Faculty:" />}</strong> {p.faculty?.name || '—'}</div>
            <div>👨‍🎓 <strong>{<Trans text="Students:" />}</strong> {p.students?.length || 0}</div>
            <div>🏢 <strong>{<Trans text="Suggested Industry:" />}</strong> {(p.suggestedIndustries || []).join(', ') || '—'}</div>
            <div>📅 <strong>{<Trans text="Submitted:" />}</strong> {p.submissionDate}</div>
          </div>

          <div className="proposal-card__actions" style={{ marginTop: 12 }}>
            {p.allocation.status === 'not_started' && (
              <button className="btn btn-primary btn-sm" onClick={() => handleRoute(p.id)}>
                {lang === 'hi' ? '🏛️ विश्वविद्यालयों को अग्रेषित करें (3-दिवसीय समय सीमा)' : '🏛️ Route to Universities (3-Day Deadline)'}
              </button>
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
      ))}
      {filtered.length === 0 && <div className="card">{<Trans text="No problems match this filter." />}</div>}
    </div>
  );
}
