import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { initialProblems } from '../data/mockData';
import { fetchChallenges, fetchMyChallenges, voteChallenge } from '../services/challengeService';

const ProblemsContext = createContext(null);

const ALLOCATION_WINDOW_MS = 3 * 24 * 60 * 60 * 1000; // 3-day window for accepting/rejecting

/** Adapts a Supabase `challenges` row into the frontend problem data model. */
function adaptSupabaseChallenge(ch) {
  const titleText = ch.title || '';
  const descText = ch.description || '';
  const proj = ch.project || ch.rawSupabase?.project || null;
  const uniName = ch.university_name || proj?.university_name || null;
  const facName = ch.faculty_name || proj?.faculty_name || null;
  const indName = ch.industry_name || proj?.industry_name || null;

  return {
    id: ch.challenge_id || ch.id,
    type: ch.status === 'solved' ? 'solved' : 'unsolved',
    status: ch.status || 'submitted',
    current_milestone: ch.current_milestone || proj?.current_milestone || null,
    votes: 1,
    source: ch.submitted_by === 'government' ? 'government' : ch.submitted_by === 'industry' ? 'industry' : 'citizen',
    submissionDate: ch.created_at ? ch.created_at.slice(0, 10) : new Date().toISOString().slice(0, 10),
    govApproved: ch.submitted_by === 'government',
    universityAdminStatus: 'pending_review',
    assignedUnits: [],
    replies: [],
    trackingStep: 1,
    priorityLevel: 'new',
    aiPriority: 'NEW REPORT',
    allocation: {
      queue: [],
      responses: {},
      deadlineAt: null,
      allocatedTo: uniName,
      status: proj ? 'allocated' : ch.status === 'routed' ? 'awaiting_allocation' : 'not_started',
    },
    faculty: facName ? { name: facName } : null,
    faculty_name: facName,
    university_name: uniName,
    industry_name: indName,
    students: [],
    requiredTechnologies: [],
    suggestedIndustries: indName ? [indName] : [],
    domain: 'General Civic',
    category: 'Civic Issue',
    title: { hi: titleText, en: titleText },
    desc: { hi: descText, en: descText },
    loc: ch.location || `${ch.address || ''}, ${ch.city || ''} - ${ch.pincode || ''}`.replace(/^,\s*|,\s*$/g, ''),
    district: ch.district || ch.city || '',
    city: ch.city || '',
    address: ch.address || '',
    pincode: ch.pincode || '',
    scope: ch.impact_scope || 'Area Specific',
    attachments: [
      ch.photo ? { kind: 'photo', url: ch.photo, name: 'Photo' } : null,
      ch.video ? { kind: 'video', url: ch.video, name: 'Video' } : null,
      ch.document ? { kind: 'document', url: ch.document, name: 'Document' } : null,
    ].filter(Boolean),
    university_rejections: ch.university_rejections || [],
    government_rejection_reason: ch.government_rejection_reason || null,
    government_reviewed_at: ch.government_reviewed_at || null,
    government_reviewed_by: ch.government_reviewed_by || null,
    project: proj,
    rawSupabase: ch,
  };
}

/** Recomputes allocation status for a single problem's `allocation` block. */
function evaluateAllocation(allocation) {
  const { queue, responses } = allocation;
  const acceptedInOrder = queue.filter((u) => responses[u] === 'accepted');

  if (acceptedInOrder.length === 0) {
    const allRejected = queue.every((u) => responses[u] === 'rejected');
    return { ...allocation, status: allRejected ? 'rejected' : allocation.status };
  }

  const topAccepted = acceptedInOrder[0];
  const topAcceptedRank = queue.indexOf(topAccepted);

  // The highest-priority university accepting settles it immediately; timeline disappears.
  if (topAcceptedRank === 0) {
    return { ...allocation, status: 'allocated', allocatedTo: topAccepted, deadlineAt: null };
  }

  // A lower-priority university accepted first — hold provisionally until
  // either a higher-priority one also accepts, or the 3-day deadline passes.
  return {
    ...allocation,
    status: 'awaiting_allocation',
    allocatedTo: null,
    deadlineAt: allocation.deadlineAt || Date.now() + ALLOCATION_WINDOW_MS,
  };
}

/** Called once a deadline has passed: grants to the highest-priority accepter. */
function finalizeAllocation(allocation) {
  const acceptedInOrder = allocation.queue.filter((u) => allocation.responses[u] === 'accepted');
  if (acceptedInOrder.length === 0) {
    return { ...allocation, status: 'deadline_completed', allocatedTo: null, deadlineAt: null };
  }
  return { ...allocation, status: 'allocated', allocatedTo: acceptedInOrder[0], deadlineAt: null };
}

export function ProblemsProvider({ children }) {
  const [problems, setProblems] = useState(initialProblems);
  const [myProblems, setMyProblems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMyProblems, setIsLoadingMyProblems] = useState(false);
  const votedIdsRef = useRef(new Set());

  // Load real challenges from FastAPI / Supabase backend on mount
  useEffect(() => {
    let isMounted = true;
    async function loadBackendChallenges() {
      try {
        setIsLoading(true);
        const remote = await fetchChallenges();
        if (isMounted && Array.isArray(remote) && remote.length > 0) {
          const adapted = remote.map(adaptSupabaseChallenge);
          setProblems((prev) => {
            const existingIds = new Set(prev.map((p) => String(p.id)));
            const fresh = adapted.filter((a) => !existingIds.has(String(a.id)));
            return [...fresh, ...prev];
          });
        }
      } catch (err) {
        // Backend might be offline during development; keep initialProblems
        console.warn('Backend challenges not loaded (server may be offline):', err.message);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadBackendChallenges();
    return () => { isMounted = false; };
  }, []);

  const refreshMyProblems = useCallback(async () => {
    try {
      setIsLoadingMyProblems(true);
      const remote = await fetchMyChallenges();
      if (Array.isArray(remote)) {
        setMyProblems(remote.map(adaptSupabaseChallenge));
      } else {
        setMyProblems([]);
      }
    } catch (err) {
      console.warn('Could not load user challenges:', err.message);
      setMyProblems([]);
    } finally {
      setIsLoadingMyProblems(false);
    }
  }, []);

  // Periodically check for problems whose allocation deadline has passed
  // while still "awaiting_allocation", and auto-finalize them.
  useEffect(() => {
    const interval = setInterval(() => {
      setProblems((prev) => {
        let changed = false;
        const next = prev.map((p) => {
          if (p.allocation?.status === 'awaiting_allocation' && p.allocation.deadlineAt && Date.now() >= p.allocation.deadlineAt) {
            changed = true;
            return { ...p, allocation: finalizeAllocation(p.allocation) };
          }
          return p;
        });
        return changed ? next : prev;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const addProblem = useCallback((problem) => {
    const newId = problem.id || problem.challenge_id || Date.now();
    const newProblem = {
      id: newId,
      challenge_id: newId,
      type: 'unsolved',
      votes: 1,
      source: problem.source || 'citizen',
      submissionDate: new Date().toISOString().slice(0, 10),
      govApproved: problem.source === 'government',
      universityAdminStatus: 'pending_review',
      assignedUnits: [],
      replies: [],
      trackingStep: 1,
      priorityLevel: 'new',
      aiPriority: 'NEW REPORT',
      allocation: { queue: [], responses: {}, deadlineAt: null, allocatedTo: null, status: 'not_started' },
      faculty: null,
      students: [],
      requiredTechnologies: [],
      suggestedIndustries: [],
      domain: problem.domain || 'General Civic',
      ...problem,
    };
    setProblems((prev) => [newProblem, ...prev]);
    setMyProblems((prev) => [newProblem, ...prev]);
    return newId;
  }, []);

  const hasVoted = useCallback((id) => votedIdsRef.current.has(id), []);

  const voteProblem = useCallback(async (id) => {
    if (votedIdsRef.current.has(id)) return false;
    votedIdsRef.current.add(id);

    try {
      await voteChallenge(id);
    } catch (err) {
      // If already voted or network issue, maintain state
      console.warn('Voting note:', err.message);
    }

    setProblems((prev) => prev.map((p) => (p.id === id ? { ...p, votes: (p.votes || 0) + 1, has_voted: true } : p)));
    setMyProblems((prev) => prev.map((p) => (p.id === id ? { ...p, votes: (p.votes || 0) + 1, has_voted: true } : p)));
    return true;
  }, []);

  const addFeedback = useCallback((id, feedback) => {
    const updateFn = (p) => {
      if (p.id !== id) return p;
      const feedbacks = p.feedbacks ? [...p.feedbacks, feedback] : [feedback];
      return { ...p, feedbacks };
    };
    setProblems((prev) => prev.map(updateFn));
    setMyProblems((prev) => prev.map(updateFn));
  }, []);

  /** Legacy allocation helper still used by the read-only Government view. */
  const allocateProblem = useCallback((id, { scope, assignedUnits }) => {
    setProblems((prev) => prev.map((p) => {
      if (p.id !== id) return p;
      return {
        ...p,
        scope,
        assignedUnits,
        govApproved: true,
        trackingStep: 2,
        replies: [...p.replies, { unit: assignedUnits[0], status: 'Pending Reply', msg: 'Assignment offer sent by Government.' }],
      };
    }));
  }, []);

  /** University Administration sends a problem into the allocation queue (Section 5/6). */
  const routeToUniversities = useCallback((id, universityQueue) => {
    setProblems((prev) => prev.map((p) => {
      if (p.id !== id) return p;
      const responses = {};
      universityQueue.forEach((u) => { responses[u] = 'awaiting'; });
      return {
        ...p,
        govApproved: true,
        universityAdminStatus: 'pending_review',
        allocation: {
          queue: universityQueue,
          responses,
          deadlineAt: Date.now() + ALLOCATION_WINDOW_MS,
          allocatedTo: null,
          status: 'awaiting_allocation',
        },
      };
    }));
  }, []);

  /** University Administration accepts/rejects a problem statement (Section 5C, 6). */
  const respondToAllocation = useCallback((problemId, universityName, decision) => {
    setProblems((prev) => prev.map((p) => {
      if (p.id !== problemId) return p;
      const responses = { ...p.allocation.responses, [universityName]: decision };
      const updatedAllocation = evaluateAllocation({ ...p.allocation, responses });
      return {
        ...p,
        universityAdminStatus: decision === 'accepted' ? 'accepted' : p.universityAdminStatus,
        allocation: updatedAllocation,
        trackingStep: updatedAllocation.status === 'allocated' ? Math.max(p.trackingStep, 2) : p.trackingStep,
      };
    }));
  }, []);

  /** University Administration allocates an approved+allocated problem to one of its faculty (Section 5D). */
  const assignFaculty = useCallback((problemId, faculty) => {
    setProblems((prev) => prev.map((p) => (p.id === problemId ? { ...p, faculty, trackingStep: Math.max(p.trackingStep, 2) } : p)));
  }, []);

  /** Faculty confirms which students are working on the problem, with their proposed solution (Section 4). */
  const assignStudents = useCallback((problemId, students) => {
    setProblems((prev) => prev.map((p) => (p.id === problemId ? { ...p, students, trackingStep: Math.max(p.trackingStep, 3) } : p)));
  }, []);

  const markSolved = useCallback((problemId, solutionInfo) => {
    setProblems((prev) => prev.map((p) => (p.id === problemId ? { ...p, type: 'solved', trackingStep: 4, ...solutionInfo } : p)));
  }, []);

  const refreshChallenges = useCallback(async () => {
    try {
      setIsLoading(true);
      const remote = await fetchChallenges();
      if (Array.isArray(remote)) {
        const adapted = remote.map(adaptSupabaseChallenge);
        setProblems((prev) => {
          const remoteMap = new Map(adapted.map((a) => [String(a.id), a]));
          const merged = prev.map((p) => remoteMap.get(String(p.id)) || p);
          const currentIds = new Set(merged.map((p) => String(p.id)));
          const fresh = adapted.filter((a) => !currentIds.has(String(a.id)));
          return [...fresh, ...merged];
        });
      }
    } catch (err) {
      console.warn('Could not refresh challenges:', err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const value = {
    problems,
    myProblems,
    isLoading,
    isLoadingMyProblems,
    refreshChallenges,
    refreshMyProblems,
    addProblem,
    voteProblem,
    hasVoted,
    addFeedback,
    allocateProblem,
    routeToUniversities,
    respondToAllocation,
    assignFaculty,
    assignStudents,
    markSolved,
  };

  return <ProblemsContext.Provider value={value}>{children}</ProblemsContext.Provider>;
}

export function useProblems() {
  const ctx = useContext(ProblemsContext);
  if (!ctx) throw new Error('useProblems must be used within ProblemsProvider');
  return ctx;
}
