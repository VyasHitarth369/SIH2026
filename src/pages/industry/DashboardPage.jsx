import Trans from '../../components/shared/Trans.jsx';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { collaborationProposals } from '../../data/orgData';

export default function IndustryDashboardPage() {
  const { user } = useAuth();
  const { problems } = useProblems();
  const navigate = useNavigate();

  const relevantProjects = problems.filter((p) => (p.suggestedIndustries || []).length > 0 || (p.assignedUnits || []).some((u) => u.toLowerCase().includes('tata') || u.toLowerCase().includes('industry')));
  const pendingProposals = collaborationProposals.filter((p) => p.status === 'Pending Review').length;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Industry Employee Dashboard" />}</h1>
          <p>{user?.profile?.company || <Trans text="Welcome" />}</p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Relevant Projects" />}</div><div className="kpi-card__value">{relevantProjects.length}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Proposals Pending Review" />}</div><div className="kpi-card__value">{pendingProposals}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Total Proposals" />}</div><div className="kpi-card__value">{collaborationProposals.length}</div></div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>{<Trans text="Collaboration Proposals" />}</h3>
          <p className="problem-desc">{<Trans text="Review proposals submitted by universities looking for industry partners." />}</p>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/industry-employee/proposals')}>{<Trans text="View Proposals" />}</button>
        </div>
        <div className="card">
          <h3>{<Trans text="Leaderboard" />}</h3>
          <p className="problem-desc">{<Trans text="Browse top-performing students and reach out for opportunities." />}</p>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/leaderboard')}>{<Trans text="Go to Leaderboard" />}</button>
        </div>
      </div>
    </div>
  );
}
