import Trans from '../../components/shared/Trans.jsx';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { collaborationProposals } from '../../data/orgData';
import { DonutChart, BarChart } from '../../components/shared/Charts.jsx';

export default function IndustryDashboardPage() {
  const { user } = useAuth();
  const { problems } = useProblems();
  const navigate = useNavigate();

  const relevantProjects = problems.filter((p) => (p.suggestedIndustries || []).length > 0 || (p.assignedUnits || []).some((u) => u.toLowerCase().includes('tata') || u.toLowerCase().includes('industry')));
  const pendingProposals = collaborationProposals.filter((p) => p.status === 'Pending Review').length;

  const proposalStatusDonutData = useMemo(() => {
    const byStatus = {};
    collaborationProposals.forEach((p) => { byStatus[p.status] = (byStatus[p.status] || 0) + 1; });
    const colorMap = { 'Pending Review': 'var(--amber)', Accepted: 'var(--teal)', Rejected: 'var(--coral)' };
    return Object.entries(byStatus).map(([label, value]) => ({ label, value, color: colorMap[label] }));
  }, []);

  const relevantByDomainData = useMemo(() => {
    const byDomain = {};
    relevantProjects.forEach((p) => {
      const key = p.domain || p.category;
      byDomain[key] = (byDomain[key] || 0) + 1;
    });
    return Object.entries(byDomain).map(([label, value]) => ({ label, value }));
  }, [relevantProjects]);

  const isManager = Boolean(
    user?.is_spoc ||
    user?.approval_authority ||
    user?.stakeholder?.approval_authority
  );

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{isManager ? <Trans text="Industry Manager (SPOC) Dashboard" /> : <Trans text="Industry Employee Dashboard" />}</h1>
          <p>{user?.profile?.company || user?.stakeholder?.industry_name || <Trans text="Welcome" />}</p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Relevant Projects" />}</div><div className="kpi-card__value">{relevantProjects.length}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Proposals Pending Review" />}</div><div className="kpi-card__value">{pendingProposals}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Total Proposals" />}</div><div className="kpi-card__value">{collaborationProposals.length}</div></div>
      </div>

      <div className="grid grid--analysis">
        <div className="card">
          <h3>{<Trans text="Proposal Status Breakdown" />}</h3>
          <DonutChart data={proposalStatusDonutData} />
        </div>
        <div className="card">
          <h3>{<Trans text="Relevant Projects by Domain" />}</h3>
          {relevantByDomainData.length === 0 ? (
            <p className="problem-desc">{<Trans text="No data available yet." />}</p>
          ) : (
            <BarChart data={relevantByDomainData} color="var(--teal)" />
          )}
        </div>
      </div>

      <div className="grid">
        {isManager ? (
          <div className="card">
            <h3>{<Trans text="Collaboration Proposals" />}</h3>
            <p className="problem-desc">{<Trans text="Review proposals submitted by universities looking for industry partners." />}</p>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/industry-employee/proposals')}>{<Trans text="View Proposals" />}</button>
          </div>
        ) : (
          <div className="card">
            <h3>{<Trans text="My Mentorship Projects" />}</h3>
            <p className="problem-desc">{<Trans text="View the projects where you have been assigned as official Industry Mentor." />}</p>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/industry-employee/my-projects')}>{<Trans text="View My Projects" />}</button>
          </div>
        )}
        <div className="card">
          <h3>{<Trans text="Leaderboard" />}</h3>
          <p className="problem-desc">{<Trans text="Browse top-performing students and reach out for opportunities." />}</p>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/leaderboard')}>{<Trans text="Go to Leaderboard" />}</button>
        </div>
      </div>
    </div>
  );
}
