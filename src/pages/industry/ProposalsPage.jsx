import Trans from '../../components/shared/Trans.jsx';
import { useMemo, useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import { collaborationProposals as initialProposals, domainList, universityNames } from '../../data/orgData';

const statusClass = { 'Pending Review': 'badge-amber', Accepted: 'badge-teal', Rejected: 'badge-coral' };

export default function ProposalsPage() {
  const { lang } = useLanguage();
  const { showToast } = useToast();
  const [proposals, setProposals] = useState(initialProposals);
  const [filters, setFilters] = useState({ domain: '', university: '', technology: '', project: '', status: '' });

  const filtered = useMemo(() => proposals.filter((p) => {
    if (filters.domain && p.domain !== filters.domain) return false;
    if (filters.university && p.university !== filters.university) return false;
    if (filters.status && p.status !== filters.status) return false;
    if (filters.technology && !p.requiredTechnologies.some((t) => t.toLowerCase().includes(filters.technology.toLowerCase()))) return false;
    if (filters.project && !p.projectName.toLowerCase().includes(filters.project.toLowerCase())) return false;
    return true;
  }), [proposals, filters]);

  const decide = (id, status) => {
    setProposals((prev) => prev.map((p) => (p.id === id ? { ...p, status } : p)));
    showToast(<Trans text={status === 'Accepted' ? 'Proposal accepted.' : 'Proposal rejected.'} />);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Industry Collaboration Proposals" />}</h1>
          <p>{<Trans text="Proposals submitted by universities for projects relevant to your industry." />}</p>
        </div>
      </div>

      <div className="card">
        <div className="grid grid--location">
          <div className="field">
            <label>{<Trans text="Domain" />}</label>
            <select value={filters.domain} onChange={(e) => setFilters((f) => ({ ...f, domain: e.target.value }))}>
              <option value="">{<Trans text="All Domains" />}</option>
              {domainList.map((d) => <option key={d} value={d}>{<Trans text={d} />}</option>)}
            </select>
          </div>
          <div className="field">
            <label>{<Trans text="University" />}</label>
            <select value={filters.university} onChange={(e) => setFilters((f) => ({ ...f, university: e.target.value }))}>
              <option value="">{<Trans text="All Universities" />}</option>
              {universityNames.map((u) => <option key={u} value={u}>{<Trans text={u} />}</option>)}
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
            <input type="text" placeholder={lang === 'hi' ? 'उदा. IoT Sensors' : 'e.g. IoT Sensors'} value={filters.technology} onChange={(e) => setFilters((f) => ({ ...f, technology: e.target.value }))} />
          </div>
          <div className="field">
            <label>{<Trans text="Project" />}</label>
            <input type="text" placeholder={lang === 'hi' ? 'प्रोजेक्ट का नाम खोजें' : 'Search project name'} value={filters.project} onChange={(e) => setFilters((f) => ({ ...f, project: e.target.value }))} />
          </div>
        </div>
      </div>

      {filtered.map((p) => (
        <div className="card" key={p.id}>
          <div className="gov-card__head">
            <span className="badge badge-violet">{<Trans text={p.university} />}</span>
            <span className={`badge ${statusClass[p.status] || 'badge-blue'}`}>{<Trans text={p.status || ''} />}</span>
            <span className="badge badge-outline">{<Trans text={p.domain} />}</span>
          </div>
          <h3 className="problem-title">{lang === 'hi' ? (p.projectNameHi || p.projectName) : p.projectName}</h3>
          <p className="problem-desc">{lang === 'hi' ? (p.descriptionHi || p.description) : p.description}</p>

          <dl className="proposal-card__grid">
            <dt>{<Trans text="Proposed Collaboration" />}</dt><dd>{lang === 'hi' ? (p.proposedCollaborationHi || p.proposedCollaboration) : p.proposedCollaboration}</dd>
            <dt>{<Trans text="Required Expertise" />}</dt><dd>{lang === 'hi' ? (p.requiredExpertiseHi || p.requiredExpertise) : p.requiredExpertise}</dd>
            <dt>{<Trans text="Required Technologies" />}</dt><dd>{p.requiredTechnologies.join(', ')}</dd>
            <dt>{<Trans text="Expected Role of Industry" />}</dt><dd>{lang === 'hi' ? (p.expectedRoleHi || p.expectedRole) : p.expectedRole}</dd>
            <dt>{<Trans text="Submitted On" />}</dt><dd>{new Date(p.dateTime).toLocaleString(lang === 'hi' ? 'hi-IN' : 'en-IN')}</dd>
          </dl>

          {p.status === 'Pending Review' && (
            <div className="proposal-card__actions">
              <button className="btn btn-success btn-sm" onClick={() => decide(p.id, 'Accepted')}>{<Trans text="Accept" />}</button>
              <button className="btn btn-light btn-sm" onClick={() => decide(p.id, 'Rejected')}>{<Trans text="Reject" />}</button>
            </div>
          )}
        </div>
      ))}
      {filtered.length === 0 && <div className="card empty-state"><span className="empty-state__icon">🤝</span>{<Trans text="No proposals match these filters." />}</div>}
    </div>
  );
}
