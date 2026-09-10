import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import Countdown from '../../components/shared/Countdown';

const statusLabel = {
  not_started: 'Pending Review',
  awaiting_allocation: 'Awaiting Allocation',
  allocated: 'Allocated',
  rejected: 'Rejected',
  deadline_completed: 'Deadline Completed',
};
const statusClass = {
  not_started: 'badge-blue',
  awaiting_allocation: 'badge-amber',
  allocated: 'badge-teal',
  rejected: 'badge-coral',
  deadline_completed: 'badge-gray',
};

export default function IncomingProblemsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems, respondToAllocation } = useProblems();
  const { showToast } = useToast();
  const [filter, setFilter] = useState('pending'); // pending | decided

  const myUniversity = user?.profile?.university || 'BIT Mesra, Ranchi';

  const incoming = problems.filter((p) => p.allocation?.queue?.includes(myUniversity));
  const filtered = incoming.filter((p) => {
    const myResponse = p.allocation.responses[myUniversity];
    if (filter === 'pending') return myResponse === 'awaiting';
    return myResponse !== 'awaiting';
  });

  const decide = (problem, decision) => {
    respondToAllocation(problem.id, myUniversity, decision);
    showToast(<Trans text={decision === 'accepted' ? 'Problem accepted.' : 'Problem rejected.'} />);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Incoming Problem Statements" />}</h1>
          <p>{lang === 'hi' ? `सरकार से ${myUniversity} को प्राथमिकता क्रम में प्रेषित समस्या विवरण।` : `Problem statements routed from Government to ${myUniversity}, in priority order.`}</p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div className={`filter-tab${filter === 'pending' ? ' active' : ''}`} onClick={() => setFilter('pending')}>{<Trans text="Pending Decision" />}</div>
          <div className={`filter-tab${filter === 'decided' ? ' active' : ''}`} onClick={() => setFilter('decided')}>{<Trans text="Already Decided" />}</div>
        </div>
      </div>

      {filtered.map((p) => {
        const myRank = p.allocation.queue.indexOf(myUniversity) + 1;
        const myResponse = p.allocation.responses[myUniversity];
        const selectedByOther = p.allocation.allocatedTo && p.allocation.allocatedTo !== myUniversity;

        return (
          <div className="card" key={p.id}>
            <div className="gov-card__head">
              <span className="badge badge-violet">ID: #CH-JH-{p.id}</span>
              <span className={`badge ${statusClass[p.allocation.status] || 'badge-blue'}`}>{<Trans text={statusLabel[p.allocation.status] || p.allocation.status} />}</span>
              <span className="badge badge-outline"><Trans text={`Your Priority Rank: #${myRank}`} /></span>
            </div>

            <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
            <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>

            <div className="gov-card__details">
              <div>📍 <strong>{<Trans text="Location:" />}</strong> {p.loc}</div>
              <div>🏷️ <strong>{<Trans text="Domain:" />}</strong> {<Trans text={p.domain || p.category} />}</div>
              <div>💡 <strong>{<Trans text="Required Technologies:" />}</strong> {(p.requiredTechnologies || []).join(', ') || '—'}</div>
              <div>🏢 <strong>{<Trans text="Suggested Industries:" />}</strong> {(p.suggestedIndustries || []).join(', ') || '—'}</div>
              <div>👍 <strong>{<Trans text="Citizen Votes:" />}</strong> {p.votes}</div>
              <div>📅 <strong>{<Trans text="Submitted:" />}</strong> {p.submissionDate}</div>
            </div>

            {p.allocation.status === 'awaiting_allocation' && !p.allocation.allocatedTo && !selectedByOther && (
              <div className="allocation-track" style={{ marginTop: 10 }}>
                <div className="allocation-track__row">
                  <span>{lang === 'hi' ? 'स्वीकार या अस्वीकार करने की समय सीमा:' : 'Deadline for accepting/rejecting:'}</span>
                  <Countdown deadlineAt={p.allocation.deadlineAt} />
                </div>
              </div>
            )}

            {selectedByOther ? (
              <div className="section-box section-box--amber" style={{ marginTop: 12 }}>
                <strong>
                  {lang === 'hi'
                    ? `यह समस्या ${p.allocation.allocatedTo} द्वारा चुनी गई है इसलिए आपको इस पर काम नहीं करना होगा।`
                    : `This problem is selected by ${p.allocation.allocatedTo} so you would not have to work on this.`}
                </strong>
              </div>
            ) : myResponse === 'awaiting' ? (
              <div className="proposal-card__actions" style={{ marginTop: 12 }}>
                <button className="btn btn-success btn-sm" onClick={() => decide(p, 'accepted')}>{<Trans text="Accept" />}</button>
                <button className="btn btn-light btn-sm" onClick={() => decide(p, 'rejected')}>{<Trans text="Reject" />}</button>
              </div>
            ) : (
              <div className="proposal-card__actions" style={{ marginTop: 12 }}>
                <span className={`badge ${myResponse === 'accepted' ? 'badge-teal' : 'badge-coral'}`}>
                  <Trans text={myResponse === 'accepted' ? 'You Accepted This Problem' : 'You Rejected This Problem'} />
                </span>
              </div>
            )}
          </div>
        );
      })}

      {filtered.length === 0 && <div className="card">{<Trans text="No problems in this view right now." />}</div>}
    </div>
  );
}
