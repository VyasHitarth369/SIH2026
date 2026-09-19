// Derives a project milestone timeline from a problem's existing
// lifecycle fields, so every government-tracked problem — old mock
// data or anything fetched from the backend — gets a consistent
// milestone view without needing hand-authored milestone data.

export const STANDARDIZED_MILESTONES = [
  'Problem Submitted',
  'Routed to Universities',
  'University Allocated',
  'Faculty Assigned',
  'Student Team Formed',
  'Development In Progress',
  'Solution Deployed',
];

const STAGE_INDEX_MAP = {
  'problem submitted': 0,
  'submitted': 0,
  'routed to universities': 1,
  'routed': 1,
  'university allocated': 2,
  'allocated': 2,
  'faculty assigned': 3,
  'faculty': 3,
  'student team formed': 4,
  'team': 4,
  'development in progress': 5,
  'progress': 5,
  'solution deployed': 6,
  'deployed': 6,
  'solved': 6,
  'completed': 6,
};

export function getMilestones(problem, isCitizen = false) {
  if (!problem) return [];
  const alloc = problem.allocation || {};

  const isCompleted =
    problem.type === 'solved' ||
    problem.status === 'solved' ||
    problem.status === 'deployed' ||
    problem.status === 'completed' ||
    problem.status === 'accepted_existing_solution' ||
    problem.current_milestone === 'Solution Deployed';

  const currentIdx = isCompleted
    ? 6
    : problem.current_milestone
    ? (STAGE_INDEX_MAP[problem.current_milestone.toLowerCase()] ?? 3)
    : -1;

  return [
    {
      key: 'submitted',
      label: 'Problem Submitted',
      done: currentIdx >= 0 || true,
      date: problem.submissionDate || (problem.created_at ? problem.created_at.slice(0, 10) : null),
    },
    {
      key: 'routed',
      label: 'Routed to Universities',
      done: currentIdx >= 1 || Boolean(alloc.status && alloc.status !== 'not_started') || Boolean(problem.routed_at || problem.status === 'routed' || problem.status === 'university_selected' || problem.status === 'active' || isCompleted),
      date: alloc.status && alloc.status !== 'not_started' ? problem.submissionDate : null,
    },
    {
      key: 'allocated',
      label: 'University Allocated',
      done: currentIdx >= 2 || Boolean(alloc.allocatedTo || problem.allocated_university || problem.university_name || problem.status === 'university_selected' || problem.status === 'active' || isCompleted),
      detail: alloc.allocatedTo || problem.allocated_university || problem.university_name || (problem.project?.university_name) || null,
    },
    {
      key: 'faculty',
      label: 'Faculty Assigned',
      done: currentIdx >= 3 || Boolean(problem.faculty || problem.faculty_assigned || problem.faculty_name || problem.status === 'active' || isCompleted),
      detail: isCitizen ? (problem.faculty || problem.faculty_name ? 'Assigned' : null) : (problem.faculty?.name || problem.faculty_name || null),
    },
    {
      key: 'team',
      label: 'Student Team Formed',
      done: currentIdx >= 4 || (problem.students || []).length > 0 || Boolean(problem.team_formed || isCompleted),
      detail: isCitizen ? ((problem.students || []).length > 0 ? 'Formed' : null) : ((problem.students || []).length > 0 ? `${problem.students.length} student(s)` : null),
    },
    {
      key: 'progress',
      label: 'Development In Progress',
      done: currentIdx >= 5 || (problem.trackingStep || 0) >= 3 || problem.status === 'active' || isCompleted,
    },
    {
      key: 'deployed',
      label: 'Solution Deployed',
      done: currentIdx >= 6 || isCompleted,
    },
  ];
}

