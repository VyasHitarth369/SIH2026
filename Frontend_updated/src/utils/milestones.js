// Derives a project milestone timeline from a problem's existing
// lifecycle fields, so every government-tracked problem — old mock
// data or anything fetched from the backend — gets a consistent
// milestone view without needing hand-authored milestone data.

export function getMilestones(problem) {
  const alloc = problem.allocation || {};

  return [
    {
      key: 'submitted',
      label: 'Problem Submitted',
      done: true,
      date: problem.submissionDate,
    },
    {
      key: 'routed',
      label: 'Routed to Universities',
      done: alloc.status && alloc.status !== 'not_started',
      date: alloc.status && alloc.status !== 'not_started' ? problem.submissionDate : null,
    },
    {
      key: 'allocated',
      label: 'University Allocated',
      done: Boolean(alloc.allocatedTo),
      detail: alloc.allocatedTo || null,
    },
    {
      key: 'faculty',
      label: 'Faculty Assigned',
      done: Boolean(problem.faculty),
      detail: problem.faculty?.name || null,
    },
    {
      key: 'team',
      label: 'Student Team Formed',
      done: (problem.students || []).length > 0,
      detail: (problem.students || []).length > 0 ? `${problem.students.length} student(s)` : null,
    },
    {
      key: 'progress',
      label: 'Development In Progress',
      done: (problem.trackingStep || 0) >= 3,
    },
    {
      key: 'deployed',
      label: 'Solution Deployed',
      done: problem.type === 'solved',
    },
  ];
}
