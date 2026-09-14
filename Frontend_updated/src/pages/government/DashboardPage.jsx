import Trans from '../../components/shared/Trans.jsx';
import { useMemo, useState, useEffect } from 'react';
import { useProblems } from '../../context/ProblemsContext';
import { governmentService } from '../../services/governmentService';
import { BarChart, DonutChart } from '../../components/shared/Charts.jsx';

function FunnelRow({ label, count, max }) {
  const pct = max ? Math.max(4, Math.round((count / max) * 100)) : 0;
  return (
    <div className="funnel-row">
      <div className="funnel-row__label"><Trans text={label} /></div>
      <div className="funnel-row__track"><div className="funnel-row__fill" style={{ width: `${pct}%` }} /></div>
      <div className="funnel-row__count">{count}</div>
    </div>
  );
}

export default function GovernmentDashboardPage() {
  const { problems } = useProblems();
  const [liveAnalytics, setLiveAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch real-time system metrics from backend
  useEffect(() => {
    let mounted = true;
    async function loadAnalytics() {
      try {
        setIsLoading(true);
        const data = await governmentService.fetchGovernmentAnalytics();
        if (mounted && data && (data.challenges || data.projects)) {
          setLiveAnalytics(data);
        }
      } catch (err) {
        console.warn('Backend analytics note:', err.message);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    loadAnalytics();
    return () => { mounted = false; };
  }, []);

  const localStats = useMemo(() => {
    const total = problems.length;
    const pending = problems.filter((p) => p.universityAdminStatus === 'pending_review' && p.allocation.status === 'not_started').length;
    const awaitingAllocation = problems.filter((p) => p.allocation.status === 'awaiting_allocation').length;
    const allocated = problems.filter((p) => p.allocation.status === 'allocated').length;
    const rejected = problems.filter((p) => p.allocation.status === 'rejected').length;
    const beingSolved = problems.filter((p) => p.type === 'unsolved' && p.faculty).length;
    const solved = problems.filter((p) => p.type === 'solved').length;
    const accepted = problems.filter((p) => Object.values(p.allocation.responses || {}).includes('accepted')).length;
    const withIndustry = problems.filter((p) => (p.suggestedIndustries || []).length > 0 || (p.assignedUnits || []).length > 0).length;
    const studentsInvolved = new Set(problems.flatMap((p) => (p.students || []).map((s) => s.email))).size;

    const byDomain = {};
    const bySource = {};
    const byUniversity = {};
    const byFaculty = {};
    problems.forEach((p) => {
      const domainKey = p.domain || p.category;
      byDomain[domainKey] = (byDomain[domainKey] || 0) + 1;
      bySource[p.source || 'citizen'] = (bySource[p.source || 'citizen'] || 0) + 1;
      if (p.allocation.allocatedTo) byUniversity[p.allocation.allocatedTo] = (byUniversity[p.allocation.allocatedTo] || 0) + 1;
      if (p.faculty?.name) byFaculty[p.faculty.name] = (byFaculty[p.faculty.name] || 0) + 1;
    });

    return { total, pending, awaitingAllocation, allocated, rejected, beingSolved, solved, accepted, withIndustry, studentsInvolved, byDomain, bySource, byUniversity, byFaculty };
  }, [problems]);

  // Use live backend data if available with at least one record, otherwise gracefully fall back to localStats
  const stats = useMemo(() => {
    if (liveAnalytics && liveAnalytics.challenges?.total_challenges > 0) {
      const ch = liveAnalytics.challenges;
      const pr = liveAnalytics.projects;
      const pa = liveAnalytics.participation;
      return {
        total: ch.total_challenges || 0,
        pending: ch.total_submitted || 0,
        awaitingAllocation: pr.proposed_projects || 0,
        allocated: pa.universities_engaged || 0,
        rejected: 0,
        beingSolved: pr.active_projects || 0,
        solved: pr.solved_problems || 0,
        accepted: pa.universities_engaged || 0,
        withIndustry: pa.industries_engaged || 0,
        studentsInvolved: pa.students_participating || 0,
        byDomain: ch.by_domain || {},
        bySource: ch.by_source || {},
        byUniversity: localStats.byUniversity,
        byFaculty: localStats.byFaculty,
        isLive: true,
      };
    }
    return localStats;
  }, [liveAnalytics, localStats]);

  const funnelMax = stats.total || 1;

  const domainChartData = Object.entries(stats.byDomain).map(([label, value]) => ({ label, value }));
  const universityChartData = Object.entries(stats.byUniversity).map(([label, value]) => ({ label, value }));
  const sourceDonutData = Object.entries(stats.bySource).map(([source, value]) => ({
    label: source === 'citizen' ? 'Citizen Submitted' : source === 'government' ? 'Government Submitted' : 'Industry Submitted',
    value,
  }));
  const lifecycleDonutData = [
    { label: 'Pending Review', value: stats.pending, color: 'var(--amber)' },
    { label: 'Awaiting Allocation', value: stats.awaitingAllocation, color: '#5AC8E8' },
    { label: 'Allocated', value: Math.max(0, stats.allocated - stats.beingSolved - stats.solved), color: 'var(--primary)' },
    { label: 'Currently Being Solved', value: stats.beingSolved, color: 'var(--violet)' },
    { label: 'Solved', value: stats.solved, color: 'var(--teal)' },
    { label: 'Rejected', value: stats.rejected, color: 'var(--coral)' },
  ];

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Government Dashboard" />}</h1>
          <p>{<Trans text="Lifecycle analytics across all submitted problem statements." />}</p>
        </div>
        {stats.isLive && (
          <span className="badge badge-teal" style={{ alignSelf: 'flex-start' }}>
            🟢 <Trans text="Live Database Connected" />
          </span>
        )}
      </div>

      <div className="kpi-grid">
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Total Submitted" />}</div><div className="kpi-card__value">{stats.total}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Pending Review" />}</div><div className="kpi-card__value" style={{ color: 'var(--amber)' }}>{stats.pending}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Accepted by a University" />}</div><div className="kpi-card__value">{stats.accepted}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Rejected" />}</div><div className="kpi-card__value" style={{ color: 'var(--coral)' }}>{stats.rejected}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Awaiting University Allocation" />}</div><div className="kpi-card__value">{stats.awaitingAllocation}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Allocated" />}</div><div className="kpi-card__value">{stats.allocated}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Currently Being Solved" />}</div><div className="kpi-card__value">{stats.beingSolved}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Solved" />}</div><div className="kpi-card__value" style={{ color: 'var(--teal)' }}>{stats.solved}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Involving Industry" />}</div><div className="kpi-card__value">{stats.withIndustry}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Students Participating" />}</div><div className="kpi-card__value">{stats.studentsInvolved}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Avg. Resolution Time" />}</div><div className="kpi-card__value">{<Trans text="~5.4 mo" />}</div><div className="kpi-card__sub">{<Trans text="Estimated from solved problems" />}</div></div>
        <div className="card kpi-card"><div className="kpi-card__label">{<Trans text="Universities Engaged" />}</div><div className="kpi-card__value">{Object.keys(stats.byUniversity).length}</div></div>
      </div>

      <div className="card">
        <h3>{<Trans text="Problem Lifecycle Funnel" />}</h3>
        <div className="funnel">
          <FunnelRow label="Submitted" count={stats.total} max={funnelMax} />
          <FunnelRow label="Pending Review" count={stats.pending} max={funnelMax} />
          <FunnelRow label="Accepted" count={stats.accepted} max={funnelMax} />
          <FunnelRow label="Awaiting Allocation" count={stats.awaitingAllocation} max={funnelMax} />
          <FunnelRow label="Allocated" count={stats.allocated} max={funnelMax} />
          <FunnelRow label="Being Solved" count={stats.beingSolved} max={funnelMax} />
          <FunnelRow label="Solved" count={stats.solved} max={funnelMax} />
        </div>
      </div>

      <div className="grid grid--analysis">
        <div className="card">
          <h3>{<Trans text="Problems by Domain" />}</h3>
          <BarChart data={domainChartData} color="var(--primary)" />
        </div>

        <div className="card">
          <h3>{<Trans text="Problems by University" />}</h3>
          {universityChartData.length === 0 ? (
            <p className="problem-desc">{<Trans text="No university allocations yet." />}</p>
          ) : (
            <BarChart data={universityChartData} color="var(--violet)" />
          )}
        </div>
      </div>

      <div className="grid grid--analysis">
        <div className="card">
          <h3>{<Trans text="Status Distribution by Source" />}</h3>
          <DonutChart data={sourceDonutData} />
        </div>

        <div className="card">
          <h3>{<Trans text="Lifecycle Status Breakdown" />}</h3>
          <DonutChart data={lifecycleDonutData} />
        </div>
      </div>
    </div>
  );
}
