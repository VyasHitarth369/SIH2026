import Trans from '../../components/shared/Trans.jsx';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';

export default function UniversityAdminDashboardPage() {
  const { user } = useAuth();
  const { problems } = useProblems();
  const navigate = useNavigate();
  const myUniversity = user?.profile?.university || 'BIT Mesra, Ranchi';

  const stats = useMemo(() => {
    const incoming = problems.filter((p) => p.allocation?.queue?.includes(myUniversity) && p.allocation.responses[myUniversity] === 'awaiting');
    const accepted = problems.filter((p) => p.allocation?.responses?.[myUniversity] === 'accepted');
    const allocatedToUs = problems.filter((p) => p.allocation?.allocatedTo === myUniversity);
    const facultyAssigned = allocatedToUs.filter((p) => p.faculty);
    const studentsWorking = allocatedToUs.reduce((sum, p) => sum + (p.students?.length || 0), 0);
    return { incoming: incoming.length, accepted: accepted.length, allocatedToUs: allocatedToUs.length, facultyAssigned: facultyAssigned.length, studentsWorking };
  }, [problems, myUniversity]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="University Administration Dashboard" />}</h1>
          <p>{myUniversity}</p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="card kpi-card">
          <div className="kpi-card__label">{<Trans text="Incoming from Government" />}</div>
          <div className="kpi-card__value">{stats.incoming}</div>
        </div>
        <div className="card kpi-card">
          <div className="kpi-card__label">{<Trans text="Accepted by Us" />}</div>
          <div className="kpi-card__value">{stats.accepted}</div>
        </div>
        <div className="card kpi-card">
          <div className="kpi-card__label">{<Trans text="Students Working" />}</div>
          <div className="kpi-card__value">{stats.studentsWorking}</div>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>{<Trans text="Review Incoming Problems" />}</h3>
          <p className="problem-desc">{<Trans text="Review problem statements sent by Government and Accept or Reject them." />}</p>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/university-admin/problems')}>{<Trans text="Go to Incoming Problems" />}</button>
        </div>
        <div className="card">
          <h3>{<Trans text="Manage Allocations" />}</h3>
          <p className="problem-desc">{<Trans text="Monitor allocation priority/deadline status and allocate accepted problems to faculty." />}</p>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/university-admin/allocations')}>{<Trans text="Go to Allocations" />}</button>
        </div>
      </div>
    </div>
  );
}
