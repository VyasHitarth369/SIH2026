import Trans from '../../components/shared/Trans.jsx';
import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import Countdown from '../../components/shared/Countdown';
import { matchingService } from '../../services/matchingService';

const statusLabel = {
  invited: 'Pending Review',
  accepted: 'Accepted',
  selected: 'Allocated / Selected',
  not_selected: 'Not Selected',
  rejected: 'Rejected',
  expired: 'Deadline Expired',
  not_started: 'Pending Review',
  awaiting_allocation: 'Awaiting Allocation',
  allocated: 'Allocated',
  deadline_completed: 'Deadline Completed',
};

const statusClass = {
  invited: 'badge-amber',
  accepted: 'badge-teal',
  selected: 'badge-teal',
  not_selected: 'badge-gray',
  rejected: 'badge-coral',
  expired: 'badge-gray',
  not_started: 'badge-blue',
  awaiting_allocation: 'badge-amber',
  allocated: 'badge-teal',
  deadline_completed: 'badge-gray',
};

export default function IncomingProblemsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems, respondToAllocation } = useProblems();
  const { showToast } = useToast();
  const [filter, setFilter] = useState('pending'); // pending | decided
  const [liveInvitations, setLiveInvitations] = useState([]);
  const [loadingLive, setLoadingLive] = useState(false);
  const [submitting, setSubmitting] = useState({});

  const uniId =
    user?.stakeholder?.university_id ||
    user?.profile?.university_id ||
    (user?.role === 'university_admin' ? 'U001' : null);

  const myUniversity =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    'Birla Institute of Technology (BIT) Mesra, Ranchi';

  const fetchLive = useCallback(async () => {
    if (!uniId) return;
    try {
      setLoadingLive(true);
      const data = await matchingService.listUniversityInvitations(uniId);
      setLiveInvitations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not fetch live university invitations:', err.message);
    } finally {
      setLoadingLive(false);
    }
  }, [uniId]);

  useEffect(() => {
    let active = true;
    if (uniId) {
      matchingService
        .listUniversityInvitations(uniId)
        .then((data) => {
          if (active) setLiveInvitations(Array.isArray(data) ? data : []);
        })
        .catch((err) => console.warn('Could not fetch live university invitations:', err.message));
    }
    return () => {
      active = false;
    };
  }, [uniId]);

  const decideLive = async (item, decision) => {
    const cid = item.challenge_id;
    try {
      setSubmitting((prev) => ({ ...prev, [cid]: true }));
      await matchingService.respondUniversityMatch(
        cid,
        uniId,
        decision,
        `Action recorded by ${user?.full_name || 'University Administration'}`
      );
      showToast(
        <Trans
          text={decision === 'accept' ? 'Problem statement accepted successfully.' : 'Problem statement rejected.'}
        />
      );
      await fetchLive();
    } catch (err) {
      showToast(<Trans text={`Action failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [cid]: false }));
    }
  };

  // Mock problems fallback
  const incomingMock = problems.filter((p) => p.allocation?.queue?.includes(myUniversity));
  const filteredMock = incomingMock.filter((p) => {
    const myResponse = p.allocation.responses[myUniversity];
    if (filter === 'pending') return myResponse === 'awaiting';
    return myResponse !== 'awaiting';
  });

  const decideMock = async (problem, decision) => {
    respondToAllocation(problem.id, myUniversity, decision);
    showToast(<Trans text={decision === 'accepted' ? 'Problem accepted.' : 'Problem rejected.'} />);
  };

  const hasLive = liveInvitations.length > 0;
  const filteredLive = liveInvitations.filter((inv) => {
    if (filter === 'pending') return inv.status === 'invited';
    return inv.status !== 'invited';
  });

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Incoming Problem Statements" />}</h1>
          <p>
            {lang === 'hi'
              ? `सरकार एवं नागरिकों से ${myUniversity} को प्राथमिकता क्रम में प्रेषित समस्या विवरण।`
              : `Problem statements routed to ${myUniversity}, in deterministic priority order.`}
          </p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div
            className={`filter-tab${filter === 'pending' ? ' active' : ''}`}
            onClick={() => setFilter('pending')}
          >
            {<Trans text="Pending Decision" />}
          </div>
          <div
            className={`filter-tab${filter === 'decided' ? ' active' : ''}`}
            onClick={() => setFilter('decided')}
          >
            {<Trans text="Already Decided" />}
          </div>
        </div>
      </div>

      {loadingLive && (
        <div className="card" style={{ padding: '16px', textAlign: 'center' }}>
          <p>{lang === 'hi' ? 'निमंत्रण लोड हो रहे हैं...' : 'Loading invitations from server...'}</p>
        </div>
      )}

      {hasLive ? (
        filteredLive.map((inv) => {
          const ch = inv.challenge || {};
          const analysis = inv.ai_analysis || {};
          const status = inv.status;
          const deadlineMs = inv.response_deadline ? new Date(inv.response_deadline).getTime() : null;
          const displayStatus = inv.status;
          const isBusy = submitting[inv.challenge_id];

          return (
            <div className="card" key={inv.match_id || inv.challenge_id}>
              <div className="problem-card__head">
                <span className={`badge ${statusClass[displayStatus] || 'badge-blue'}`}>
                  {statusLabel[displayStatus] || displayStatus}
                </span>
                <span className="badge badge-blue">
                  {<Trans text="Your Priority Rank:" />} #{inv.rank}
                </span>
                <span className="badge badge-teal">
                  🎯 {<Trans text="Match Score:" />} {Number(inv.match_score).toFixed(1)}%
                </span>
              </div>

              <h3 className="problem-title">{ch.title || `Challenge #${inv.challenge_id}`}</h3>
              <p className="problem-desc">{ch.description || 'No description provided.'}</p>

              <div className="problem-meta">
                📍 <Trans text="Location:" /> {ch.city || 'Jharkhand'} · <Trans text="Category:" />{' '}
                <strong>{ch.category || 'Civic Issue'}</strong> · <Trans text="Scope:" />{' '}
                {ch.impact_scope || 'Area Specific'}
              </div>

              {inv.match_reason && (
                <div className="problem-meta" style={{ marginTop: 6, color: '#4b5563', fontStyle: 'italic' }}>
                  💡 <Trans text="Match Rationale:" /> {inv.match_reason}
                </div>
              )}

              {(analysis.skills_required?.length > 0 || analysis.technologies_suggested?.length > 0) && (
                <div className="skills-block">
                  <div className="skills-block__label">🛠️ <Trans text="Required Skills & Tech:" /></div>
                  <div className="skills-chips">
                    {[...(analysis.skills_required || []), ...(analysis.technologies_suggested || [])].map(
                      (skill, idx) => (
                        <span className="skill-chip" key={`${skill}-${idx}`}>
                          {skill}
                        </span>
                      )
                    )}
                  </div>
                </div>
              )}

              {deadlineMs && status === 'invited' && (
                <div style={{ margin: '10px 0' }}>
                  <span style={{ fontWeight: 600, marginRight: 8 }}>
                    ⏳ {lang === 'hi' ? 'समय सीमा शेष:' : 'Response Deadline:'}
                  </span>
                  <Countdown deadlineAt={deadlineMs} />
                </div>
              )}

              {status === 'invited' && !isExpired && (
                <div className="proposal-card__actions" style={{ marginTop: 14 }}>
                  <button
                    className="btn btn-success btn-sm"
                    disabled={isBusy}
                    onClick={() => decideLive(inv, 'accept')}
                  >
                    {isBusy ? <Trans text="Processing..." /> : <Trans text="Accept Problem" />}
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={isBusy}
                    onClick={() => decideLive(inv, 'reject')}
                  >
                    {isBusy ? <Trans text="Processing..." /> : <Trans text="Reject" />}
                  </button>
                </div>
              )}

              {status === 'accepted' && (
                <div style={{ marginTop: 12, padding: '8px 12px', background: '#ecfdf5', borderRadius: 6, color: '#065f46' }}>
                  ✅ <strong>{lang === 'hi' ? 'स्वीकृत' : 'Accepted'}:</strong>{' '}
                  {lang === 'hi'
                    ? 'आपने इस चुनौती को स्वीकार कर लिया है। अंतिम चयन की प्रतीक्षा है।'
                    : 'Your institution accepted this invitation. Awaiting deadline and final selection.'}
                </div>
              )}

              {status === 'selected' && (
                <div style={{ marginTop: 12, padding: '8px 12px', background: '#e0f2fe', borderRadius: 6, color: '#0369a1' }}>
                  🏆 <strong>{lang === 'hi' ? 'चयनित' : 'Officially Selected'}:</strong>{' '}
                  {lang === 'hi'
                    ? 'यह समस्या आधिकारिक तौर पर आपके विश्वविद्यालय को आवंटित कर दी गई है।'
                    : 'This challenge has been officially allocated to your university. Faculty allocation is now open.'}
                </div>
              )}
            </div>
          );
        })
      ) : (
        filteredMock.map((p) => {
          const myRank = p.allocation.queue.indexOf(myUniversity) + 1;
          const myResponse = p.allocation.responses[myUniversity];
          const status = p.allocation.status;

          return (
            <div className="card" key={p.id}>
              <div className="problem-card__head">
                <span className={`badge ${statusClass[status]}`}>{statusLabel[status]}</span>
                <span className="badge badge-blue">
                  {<Trans text="Your Rank:" />} #{myRank}
                </span>
                {myResponse !== 'awaiting' && (
                  <span className={`badge ${myResponse === 'accepted' ? 'badge-teal' : 'badge-coral'}`}>
                    {lang === 'hi'
                      ? myResponse === 'accepted'
                        ? 'आपने स्वीकार किया'
                        : 'आपने अस्वीकार किया'
                      : `You ${myResponse}`}
                  </span>
                )}
              </div>

              <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
              <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>
              <div className="problem-meta">
                📍 <Trans text="Location:" /> {p.loc} · <Trans text="Domain:" />{' '}
                {<Trans text={p.domain || p.category} />}
              </div>

              {p.requiredTechnologies?.length > 0 && (
                <div className="skills-block">
                  <div className="skills-block__label">🛠️ <Trans text="Required Skills:" /></div>
                  <div className="skills-chips">
                    {p.requiredTechnologies.map((skill) => (
                      <span className="skill-chip" key={skill}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {p.allocation.deadlineAt && status === 'awaiting_allocation' && (
                <div style={{ margin: '10px 0' }}>
                  <Countdown deadlineAt={p.allocation.deadlineAt} />
                </div>
              )}

              {myResponse === 'awaiting' && (
                <div className="proposal-card__actions" style={{ marginTop: 14 }}>
                  <button className="btn btn-success btn-sm" onClick={() => decideMock(p, 'accepted')}>
                    {<Trans text="Accept Problem" />}
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => decideMock(p, 'rejected')}>
                    {<Trans text="Reject" />}
                  </button>
                </div>
              )}
            </div>
          );
        })
      )}

      {((hasLive && filteredLive.length === 0) || (!hasLive && filteredMock.length === 0)) && (
        <div className="card empty-state">
          <span className="empty-state__icon">📭</span>
          {filter === 'pending' ? (
            <Trans text="No problem statements currently awaiting your decision." />
          ) : (
            <Trans text="No decided problems yet." />
          )}
        </div>
      )}
    </div>
  );
}
