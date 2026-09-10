import { createContext, useContext, useState, useCallback } from 'react';

const ApplicationsContext = createContext(null);

// Shape: { [problemId]: [{ id, studentName, studentEmail, idea, status }] }
// status: 'pending' | 'selected' | 'not-selected'

export function ApplicationsProvider({ children }) {
  const [applicationsByProblem, setApplicationsByProblem] = useState({});

  const hasApplied = useCallback((problemId, studentEmail) => {
    const list = applicationsByProblem[problemId] || [];
    return list.some((a) => a.studentEmail === studentEmail);
  }, [applicationsByProblem]);

  const addApplication = useCallback((problemId, { studentName, studentEmail, idea }) => {
    setApplicationsByProblem((prev) => {
      const list = prev[problemId] || [];
      if (list.some((a) => a.studentEmail === studentEmail)) return prev; // no duplicate applications
      const newApp = {
        id: `${problemId}-${Date.now()}`,
        studentName,
        studentEmail,
        idea,
        status: 'pending',
      };
      return { ...prev, [problemId]: [...list, newApp] };
    });
  }, []);

  const getApplications = useCallback((problemId) => applicationsByProblem[problemId] || [], [applicationsByProblem]);

  /** Faculty confirms a chosen subset of applicant ids as the selected team. */
  const selectApplicants = useCallback((problemId, selectedIds) => {
    setApplicationsByProblem((prev) => {
      const list = prev[problemId] || [];
      const updated = list.map((a) => ({
        ...a,
        status: selectedIds.includes(a.id) ? 'selected' : 'not-selected',
      }));
      return { ...prev, [problemId]: updated };
    });
  }, []);

  const value = { applicationsByProblem, hasApplied, addApplication, getApplications, selectApplicants };

  return <ApplicationsContext.Provider value={value}>{children}</ApplicationsContext.Provider>;
}

export function useApplications() {
  const ctx = useContext(ApplicationsContext);
  if (!ctx) throw new Error('useApplications must be used within ApplicationsProvider');
  return ctx;
}
