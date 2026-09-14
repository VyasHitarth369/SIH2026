import Trans from '../../components/shared/Trans.jsx';
import { useMemo, useState, useEffect, useCallback } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { collaborationProposals as initialProposals, domainList, universityNames } from '../../data/orgData';
import { matchingService } from '../../services/matchingService';

const statusClass = {
  'Pending Review': 'badge-amber',
  Accepted: 'badge-teal',
  Rejected: 'badge-coral',
  invited: 'badge-amber',
  recommended: 'badge-blue',
  accepted: 'badge-teal',
  rejected: 'badge-coral',
};

export default function ProposalsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState('invitations'); // invitations | interests | legacy
  const [proposals, setProposals] = useState(initialProposals);
  const [filters, setFilters] = useState({ domain: '', university: '', technology: '', project: '', status: '' });

  // Phase 25 live state
  const [liveInvitations, setLiveInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(false);
  const [eligibleProjects, setEligibleProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [submitting, setSubmitting] = useState({});
  const [interestMessages, setInterestMessages] = useState({});

  const industryId =
    user?.stakeholder?.industry_id ||
    user?.profile?.industry_id ||
    (user?.role === 'industry_employee' ? 'IND002' : null);

  const isSpoc = Boolean(
    user?.role === 'industry_employee' &&
      (user?.is_spoc || user?.approval_authority || user?.stakeholder?.approval_authority)
  );

  const fetchInvitations = useCallback(async () => {
    if (!industryId) return;
    try {
      setLoadingInvitations(true);
      const data = await matchingService.listIndustryInvitations(industryId);
      setLiveInvitations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not load industry invitations:', err.message);
    } finally {
      setLoadingInvitations(false);
    }
  }, [industryId]);

  const fetchEligibleProjects = useCallback(async () => {
    try {
      setLoadingProjects(true);
      const data = await matchingService.listEligibleProjectsForEmployee();
      setEligibleProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not load eligible projects for employee:', err.message);
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    if (activeTab === 'invitations' && industryId) {
      matchingService
        .listIndustryInvitations(industryId)
        .then((data) => {
          if (active) setLiveInvitations(Array.isArray(data) ? data : []);
        })
        .catch((err) => console.warn('Could not load industry invitations:', err.message));
    } else if (activeTab === 'interests') {
      matchingService
        .listEligibleProjectsForEmployee()
        .then((data) => {
          if (active) setEligibleProjects(Array.isArray(data) ? data : []);
        })
        .catch((err) => console.warn('Could not load eligible projects for employee:', err.message));
    }
    return () => {
      active = false;
    };
  }, [activeTab, industryId]);

  const decideSpoc = async (inv, action) => {
    const cid = inv.challenge_id;
    try {
      setSubmitting((prev) => ({ ...prev, [cid]: true }));
      await matchingService.respondIndustryMatch(
        cid,
        industryId,
        action,
        `Decision by SPOC ${user?.full_name || ''}`
      );
      showToast(
        <Trans
          text={action === 'accept' ? 'Collaboration proposal accepted.' : 'Collaboration proposal rejected.'}
        />
      );
      await fetchInvitations();
    } catch (err) {
      showToast(<Trans text={`Action failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [cid]: false }));
    }
  };

  const submitEmployeeInterest = async (projectId) => {
    const msg = (interestMessages[projectId] || '').trim();
    try {
      setSubmitting((prev) => ({ ...prev, [projectId]: true }));
      await matchingService.expressEmployeeInterest(projectId, msg);
      showToast(<Trans text="Interest expressed successfully." />);
      setInterestMessages((prev) => ({ ...prev, [projectId]: '' }));
      await fetchEligibleProjects();
    } catch (err) {
      showToast(<Trans text={`Expression failed: ${err.message}`} />);
    } finally {
      setSubmitting((prev) => ({ ...prev, [projectId]: false }));
    }
  };

  const filteredLegacy = useMemo(
    () =>
      proposals.filter((p) => {
        if (filters.domain && p.domain !== filters.domain) return false;
        if (filters.university && p.university !== filters.university) return false;
        if (filters.status && p.status !== filters.status) return false;
        if (
          filters.technology &&
          !p.requiredTechnologies.some((t) => t.toLowerCase().includes(filters.technology.toLowerCase()))
        )
          return false;
        if (filters.project && !p.projectName.toLowerCase().includes(filters.project.toLowerCase())) return false;
        return true;
      }),
    [proposals, filters]
  );

  const decideLegacy = (id, status) => {
    setProposals((prev) => prev.map((p) => (p.id === id ? { ...p, status } : p)));
    showToast(<Trans text={status === 'Accepted' ? 'Proposal accepted.' : 'Proposal rejected.'} />);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Industry Collaboration & Proposals" />}</h1>
          <p>
            {lang === 'hi'
              ? 'विश्वविद्यालयों से साझेदारी प्रस्ताव एवं कॉर्पोरेट इनोवेशन प्रोजेक्ट्स।'
              : 'University partnership proposals and corporate innovation projects.'}
          </p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div
            className={`filter-tab${activeTab === 'invitations' ? ' active' : ''}`}
            onClick={() => setActiveTab('invitations')}
          >
            🏢 {<Trans text="Collaboration Requests (SPOC)" />}
          </div>
          <div
            className={`filter-tab${activeTab === 'interests' ? ' active' : ''}`}
            onClick={() => setActiveTab('interests')}
          >
            👷 {<Trans text="Employee Project Interest" />}
          </div>
          <div
            className={`filter-tab${activeTab === 'legacy' ? ' active' : ''}`}
            onClick={() => setActiveTab('legacy')}
          >
            📑 {<Trans text="University Proposals (All)" />}
          </div>
        </div>
      </div>

      {/* TAB 1: SPOC COLLABORATION REQUESTS */}
      {activeTab === 'invitations' && (
        <div>
          {loadingInvitations && (
            <div className="card" style={{ padding: 16, textAlign: 'center' }}>
              <p>{<Trans text="Loading collaboration requests from server..." />}</p>
            </div>
          )}

          {liveInvitations.map((inv) => {
            const ch = inv.challenge || {};
            const analysis = inv.ai_analysis || {};
            const isBusy = submitting[inv.challenge_id];
            const canDecide = isSpoc && (inv.status === 'invited' || inv.status === 'recommended');

            return (
              <div className="card" key={inv.match_id || inv.challenge_id}>
                <div className="gov-card__head">
                  <span className="badge badge-violet">
                    {<Trans text="Priority Rank:" />} #{inv.rank}
                  </span>
                  <span className={`badge ${statusClass[inv.status] || 'badge-blue'}`}>
                    {inv.status}
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
                    <div className="skills-block__label">🛠️ <Trans text="Required Capabilities & Tech:" /></div>
                    <div className="skills-chips">
                      {[...(analysis.skills_required || []), ...(analysis.technologies_suggested || [])].map(
                        (s, i) => (
                          <span className="skill-chip" key={`${s}-${i}`}>
                            {s}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                )}

                {canDecide ? (
                  <div className="proposal-card__actions" style={{ marginTop: 14 }}>
                    <button
                      className="btn btn-success btn-sm"
                      disabled={isBusy}
                      onClick={() => decideSpoc(inv, 'accept')}
                    >
                      {isBusy ? <Trans text="Processing..." /> : <Trans text="Accept Collaboration" />}
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      disabled={isBusy}
                      onClick={() => decideSpoc(inv, 'reject')}
                    >
                      {isBusy ? <Trans text="Processing..." /> : <Trans text="Reject" />}
                    </button>
                  </div>
                ) : !isSpoc ? (
                  <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#6b7280' }}>
                    🔒 <Trans text="SPOC approval authority required to submit official institutional decisions." />
                  </div>
                ) : (
                  <div style={{ marginTop: 12, padding: '8px 12px', background: '#f3f4f6', borderRadius: 6 }}>
                    <strong><Trans text="Status:" /></strong> {inv.status}
                  </div>
                )}
              </div>
            );
          })}

          {!loadingInvitations && liveInvitations.length === 0 && (
            <div className="card empty-state">
              <span className="empty-state__icon">🤝</span>
              <Trans text="No active collaboration requests routed to your organization yet." />
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EMPLOYEE PROJECT INTEREST */}
      {activeTab === 'interests' && (
        <div>
          {loadingProjects && (
            <div className="card" style={{ padding: 16, textAlign: 'center' }}>
              <p>{<Trans text="Loading active company projects..." />}</p>
            </div>
          )}

          {eligibleProjects.map((p) => {
            const hasExpressed = Boolean(p.user_interest_status);
            const isBusy = submitting[p.project_id];

            return (
              <div className="card" key={p.project_id}>
                <div className="gov-card__head">
                  <span className="badge badge-blue">
                    {<Trans text="Project ID:" />} {p.project_id}
                  </span>
                  <span className="badge badge-teal">
                    {p.status || 'Active'}
                  </span>
                  {p.university_name && (
                    <span className="badge badge-violet">
                      🏫 {p.university_name}
                    </span>
                  )}
                </div>

                <h3 className="problem-title">{p.project_title || 'Innovation Project'}</h3>
                {p.challenge_title && (
                  <p className="problem-meta">
                    🎯 <Trans text="Linked Problem Statement:" /> <strong>{p.challenge_title}</strong>
                  </p>
                )}

                {hasExpressed ? (
                  <div style={{ marginTop: 12, padding: '10px 14px', background: '#ecfdf5', borderRadius: 6, border: '1px solid #86efac' }}>
                    <div style={{ fontWeight: 600, color: '#065f46', marginBottom: 4 }}>
                      ✅ <Trans text="Interest Expressed" /> ({p.user_interest_status})
                    </div>
                    {p.user_interest_message && (
                      <div style={{ fontSize: '0.9rem', color: '#047857', fontStyle: 'italic' }}>
                        “{p.user_interest_message}”
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ marginTop: 14, background: '#f8fafc', padding: 12, borderRadius: 6 }}>
                    <label style={{ display: 'block', fontWeight: 600, fontSize: '0.85rem', marginBottom: 6 }}>
                      {<Trans text="Express Interest in this Project (Expertise / Proposed Contribution):" />}
                    </label>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="text"
                        placeholder={
                          lang === 'hi'
                            ? 'अपनी विशेषज्ञता एवं योगदान का विवरण लिखें...'
                            : 'Describe your expertise, technical capabilities, or availability...'
                        }
                        value={interestMessages[p.project_id] || ''}
                        onChange={(e) =>
                          setInterestMessages((prev) => ({ ...prev, [p.project_id]: e.target.value }))
                        }
                        style={{ flex: 1, padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 4 }}
                      />
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={isBusy}
                        onClick={() => submitEmployeeInterest(p.project_id)}
                      >
                        {isBusy ? <Trans text="Submitting..." /> : <Trans text="Express Interest" />}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {!loadingProjects && eligibleProjects.length === 0 && (
            <div className="card empty-state">
              <span className="empty-state__icon">💼</span>
              <Trans text="No projects currently partnered with your organization are open for employee interest." />
            </div>
          )}
        </div>
      )}

      {/* TAB 3: LEGACY / ALL PROPOSALS */}
      {activeTab === 'legacy' && (
        <div>
          <div className="card">
            <div className="grid grid--location">
              <div className="field">
                <label>{<Trans text="Domain" />}</label>
                <select value={filters.domain} onChange={(e) => setFilters((f) => ({ ...f, domain: e.target.value }))}>
                  <option value="">{<Trans text="All Domains" />}</option>
                  {domainList.map((d) => (
                    <option key={d} value={d}>
                      {<Trans text={d} />}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>{<Trans text="University" />}</label>
                <select value={filters.university} onChange={(e) => setFilters((f) => ({ ...f, university: e.target.value }))}>
                  <option value="">{<Trans text="All Universities" />}</option>
                  {universityNames.map((u) => (
                    <option key={u} value={u}>
                      {<Trans text={u} />}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>{<Trans text="Status" />}</label>
                <select value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
                  <option value="">{<Trans text="All Statuses" />}</option>
                  <option value="Pending Review">{<Trans text="Pending Review" />}</option>
                  <option value="Accepted">{<Trans text="Accepted" />}</option>
                  <option value="Rejected">{<Trans text="Rejected" />}</option>
                </select>
              </div>
              <div className="field">
                <label>{<Trans text="Technology" />}</label>
                <input
                  type="text"
                  placeholder={lang === 'hi' ? 'उदा. IoT Sensors' : 'e.g. IoT Sensors'}
                  value={filters.technology}
                  onChange={(e) => setFilters((f) => ({ ...f, technology: e.target.value }))}
                />
              </div>
              <div className="field">
                <label>{<Trans text="Project" />}</label>
                <input
                  type="text"
                  placeholder={lang === 'hi' ? 'प्रोजेक्ट का नाम खोजें' : 'Search project name'}
                  value={filters.project}
                  onChange={(e) => setFilters((f) => ({ ...f, project: e.target.value }))}
                />
              </div>
            </div>
          </div>

          {filteredLegacy.map((p) => (
            <div className="card" key={p.id}>
              <div className="gov-card__head">
                <span className="badge badge-violet">{<Trans text={p.university} />}</span>
                <span className={`badge ${statusClass[p.status] || 'badge-blue'}`}>{<Trans text={p.status || ''} />}</span>
                <span className="badge badge-outline">{<Trans text={p.domain} />}</span>
              </div>
              <h3 className="problem-title">{lang === 'hi' ? p.projectNameHi || p.projectName : p.projectName}</h3>
              <p className="problem-desc">{lang === 'hi' ? p.descriptionHi || p.description : p.description}</p>

              <dl className="proposal-card__grid">
                <dt>{<Trans text="Proposed Collaboration" />}</dt>
                <dd>{lang === 'hi' ? p.proposedCollaborationHi || p.proposedCollaboration : p.proposedCollaboration}</dd>
                <dt>{<Trans text="Required Expertise" />}</dt>
                <dd>{lang === 'hi' ? p.requiredExpertiseHi || p.requiredExpertise : p.requiredExpertise}</dd>
                <dt>{<Trans text="Required Technologies" />}</dt>
                <dd>{p.requiredTechnologies.join(', ')}</dd>
                <dt>{<Trans text="Expected Role of Industry" />}</dt>
                <dd>{lang === 'hi' ? p.expectedRoleHi || p.expectedRole : p.expectedRole}</dd>
                <dt>{<Trans text="Submitted On" />}</dt>
                <dd>{new Date(p.dateTime).toLocaleString(lang === 'hi' ? 'hi-IN' : 'en-IN')}</dd>
              </dl>

              {p.status === 'Pending Review' && (
                <div className="proposal-card__actions">
                  <button className="btn btn-success btn-sm" onClick={() => decideLegacy(p.id, 'Accepted')}>
                    {<Trans text="Accept" />}
                  </button>
                  <button className="btn btn-light btn-sm" onClick={() => decideLegacy(p.id, 'Rejected')}>
                    {<Trans text="Reject" />}
                  </button>
                </div>
              )}
            </div>
          ))}

          {filteredLegacy.length === 0 && (
            <div className="card empty-state">
              <span className="empty-state__icon">🤝</span>
              {<Trans text="No proposals match these filters." />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
