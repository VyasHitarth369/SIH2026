import { useState, useEffect, useMemo, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useApplications } from '../../context/ApplicationsContext';
import { useToast } from '../../context/ToastContext';
import Milestones from '../../components/shared/Milestones.jsx';
import { STANDARDIZED_MILESTONES } from '../../utils/milestones';
import { apiClient } from '../../services/apiClient';

export default function FacultyProjectsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { problems, assignStudents } = useProblems();
  const { getApplications, selectApplicants } = useApplications();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [backendProjects, setBackendProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all | ongoing | completed
  const [updatingMilestoneId, setUpdatingMilestoneId] = useState(null);
  const [milestoneSelections, setMilestoneSelections] = useState({});
  const [selectedApplicants, setSelectedApplicants] = useState({}); // { [projectId]: Set of applicant ids/emails }
  const [submittingTeamId, setSubmittingTeamId] = useState(null);

  const userEmail = (user?.email || '').toLowerCase();
  const userFacId = user?.stakeholder?.faculty_id || user?.faculty_id || '';
  const userFullName = user?.full_name || user?.name || '';

  // 1. Authoritatively fetch assigned projects for logged-in faculty
  const loadFacultyProjects = useCallback(async () => {
    try {
      setLoading(true);
      // Backend automatically applies authoritative faculty scoping based on authenticated JWT
      const res = await apiClient.get('/projects');
      if (res && res.success && Array.isArray(res.data)) {
        setBackendProjects(res.data);
      } else {
        setBackendProjects([]);
      }
    } catch (err) {
      console.warn('Could not fetch faculty projects from backend:', err.message);
      setBackendProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setBackendProjects([]);
    loadFacultyProjects();
  }, [userEmail, userFacId, loadFacultyProjects]);

  // 2. Adapt backend projects
  const adaptedBackend = useMemo(() => {
    return backendProjects.map((p) => {
      const isCompleted =
        p.status === 'deployed' ||
        p.status === 'solved' ||
        p.status === 'completed' ||
        p.current_milestone === 'Solution Deployed';

      const students = (p.students || p.student_participants || p.student_names || []).map((s) => {
        if (typeof s === 'string') return { name: s, email: '', status: 'Active' };
        return {
          student_id: s.student_id || s.id,
          name: s.name || s.student_name || 'Student',
          email: s.email || '',
          status: s.status || 'Active',
        };
      });

      return {
        id: p.project_id || p.id,
        project_id: p.project_id || p.id,
        title: {
          en: p.title || p.project_title || 'Collaborative Solution Project',
          hi: p.title || p.project_title || 'सहयोगात्मक समाधान परियोजना',
        },
        desc: {
          en: p.description || '',
          hi: p.description || '',
        },
        loc: p.location || `${p.city || ''}, Jharkhand`.trim() || 'Jharkhand, India',
        domain: p.domain || 'Innovation & Engineering',
        faculty: {
          name: p.faculty_name || userFullName || 'Dr. Abhijit Mustafi',
          email: p.faculty_email || userEmail,
        },
        faculty_id: p.faculty_id || userFacId,
        industryName: p.industry_name || 'Tata CSR Water Solutions',
        students,
        applicants: p.applicants || [],
        requiredTechnologies: Array.isArray(p.skills_required)
          ? p.skills_required
          : typeof p.skills_required === 'string' && p.skills_required.includes(',')
          ? p.skills_required.split(',').map((s) => s.trim())
          : [p.skills_required || 'Applied Engineering'].filter(Boolean),
        status: p.status || 'active',
        current_milestone: p.current_milestone || (isCompleted ? 'Solution Deployed' : 'Faculty Assigned'),
        isCompleted,
        allocation: {
          allocatedTo: p.university_name || user?.stakeholder?.university_name || 'BIT Mesra, Ranchi',
          status: 'allocated',
        },
      };
    });
  }, [backendProjects, userEmail, userFacId, userFullName, user]);

  // 3. Filter context problems: STRICTLY ONLY projects assigned to THIS faculty
  const contextAssigned = useMemo(() => {
    return problems
      .filter((p) => {
        const facEmail = (p.faculty?.email || '').toLowerCase();
        const facId = p.faculty_id || p.faculty?.id;
        const matchEmail = userEmail && facEmail && facEmail === userEmail;
        const matchId = userFacId && facId && facId === userFacId;
        return matchEmail || matchId;
      })
      .map((p) => {
        const isCompleted =
          p.type === 'solved' ||
          p.status === 'solved' ||
          p.status === 'completed' ||
          p.status === 'deployed' ||
          p.current_milestone === 'Solution Deployed';

        return {
          ...p,
          project_id: p.id,
          industryName: p.suggestedIndustries?.[0] || p.industry_name || 'Tata CSR Water Solutions',
          isCompleted,
          current_milestone: p.current_milestone || (isCompleted ? 'Solution Deployed' : 'Faculty Assigned'),
        };
      });
  }, [problems, userEmail, userFacId]);

  // Merge backend and context assigned projects
  const allAssignedProjects = useMemo(() => {
    const existingIds = new Set(adaptedBackend.map((p) => String(p.id)));
    return [...adaptedBackend, ...contextAssigned.filter((p) => !existingIds.has(String(p.id)))];
  }, [adaptedBackend, contextAssigned]);

  // Filter tabs
  const filteredProjects = useMemo(() => {
    if (filter === 'ongoing') return allAssignedProjects.filter((p) => !p.isCompleted);
    if (filter === 'completed') return allAssignedProjects.filter((p) => p.isCompleted);
    return allAssignedProjects;
  }, [allAssignedProjects, filter]);

  // Progression stage indices
  const getStageIndex = (stageName) => {
    if (!stageName) return 3; // Faculty Assigned default
    const idx = STANDARDIZED_MILESTONES.findIndex(
      (s) => s.toLowerCase() === stageName.toLowerCase()
    );
    return idx >= 0 ? idx : 3;
  };

  // Handle milestone update
  const handleUpdateMilestone = async (project) => {
    const targetMilestone = milestoneSelections[project.id];
    if (!targetMilestone) {
      showToast(lang === 'hi' ? 'कृपया एक माइलस्टोन चुनें' : 'Please select a milestone');
      return;
    }

    const currentIdx = getStageIndex(project.current_milestone);
    const targetIdx = getStageIndex(targetMilestone);

    // Rule: Cannot move backward
    if (targetIdx < currentIdx) {
      showToast(
        lang === 'hi'
          ? `माइलस्टोन को पीछे नहीं ले जाया जा सकता (${STANDARDIZED_MILESTONES[currentIdx]} → ${targetMilestone})`
          : `Cannot move milestone backward from '${STANDARDIZED_MILESTONES[currentIdx]}' to '${targetMilestone}'`
      );
      return;
    }

    // Rule: Cannot skip required stages
    if (targetIdx > currentIdx + 1) {
      const requiredNext = STANDARDIZED_MILESTONES[currentIdx + 1];
      showToast(
        lang === 'hi'
          ? `चरण छोड़ना अस्वीकृत है। अगला आवश्यक चरण '${requiredNext}' है।`
          : `Skipping stages is not permitted. Next required stage is '${requiredNext}'.`
      );
      return;
    }

    try {
      setUpdatingMilestoneId(project.id);
      const res = await apiClient.patch(`/projects/${project.id}/milestone`, {
        milestone: targetMilestone,
      });

      if (res && res.success) {
        showToast(
          lang === 'hi'
            ? `माइलस्टोन सफलतापूर्वक '${targetMilestone}' पर अपडेट हुआ!`
            : `Milestone successfully updated to '${targetMilestone}'!`
        );

        // Update local state immediately
        setBackendProjects((prev) =>
          prev.map((p) =>
            (p.project_id || p.id) === project.id
              ? {
                  ...p,
                  current_milestone: targetMilestone,
                  status: targetMilestone === 'Solution Deployed' ? 'deployed' : 'active',
                }
              : p
          )
        );

        // If Solution Deployed reached, reset selection
        if (targetMilestone === 'Solution Deployed') {
          setMilestoneSelections((prev) => ({ ...prev, [project.id]: '' }));
        }
      } else {
        showToast(res?.message || 'Failed to update milestone');
      }
    } catch (err) {
      showToast(err.message || 'Error updating milestone');
    } finally {
      setUpdatingMilestoneId(null);
    }
  };

  // Toggle applicant checkbox for team formation
  const toggleApplicant = (projectId, applicantId) => {
    setSelectedApplicants((prev) => {
      const currentSet = new Set(prev[projectId] || []);
      if (currentSet.has(applicantId)) {
        currentSet.delete(applicantId);
      } else {
        currentSet.add(applicantId);
      }
      return { ...prev, [projectId]: currentSet };
    });
  };

  // Confirm team selection with duplicate prevention
  const handleConfirmTeam = async (project, availableApplicants) => {
    const chosenSet = selectedApplicants[project.id] || new Set();
    if (chosenSet.size === 0) {
      showToast(t.selectAtLeastOne || 'Please select at least one student applicant.');
      return;
    }

    const selectedList = availableApplicants.filter((a) =>
      chosenSet.has(a.id || a.student_id || a.studentEmail)
    );

    // Strict duplicate check against existing members
    const existingEmails = new Set(
      (project.students || []).map((s) => (s.email || '').toLowerCase()).filter(Boolean)
    );
    const existingIds = new Set(
      (project.students || []).map((s) => s.student_id || s.id).filter(Boolean)
    );

    const nonDuplicateList = selectedList.filter((a) => {
      const email = (a.studentEmail || a.email || '').toLowerCase();
      const sid = a.student_id || a.id;
      return (!email || !existingEmails.has(email)) && (!sid || !existingIds.has(sid));
    });

    if (nonDuplicateList.length === 0) {
      showToast(
        lang === 'hi'
          ? 'चयनित छात्र पहले से ही प्रोजेक्ट टीम में सक्रिय सदस्य हैं।'
          : 'Selected student(s) are already active members of this project team.'
      );
      return;
    }

    try {
      setSubmittingTeamId(project.id);

      // Call backend membership update for each selected student
      for (const applicant of nonDuplicateList) {
        const studentId = applicant.student_id || applicant.id;
        if (studentId) {
          try {
            await apiClient.patch(`/projects/${project.id}/members/${studentId}`, {
              status: 'active',
            });
          } catch (apiErr) {
            console.warn('Backend student selection note:', apiErr.message);
          }
        }
      }

      // Update context and state
      const newTeamMembers = nonDuplicateList.map((a) => ({
        student_id: a.student_id || a.id,
        name: a.studentName || a.student_name || a.name || 'Student Contributor',
        email: a.studentEmail || a.email || '',
        status: 'Active',
      }));

      const updatedStudents = [...(project.students || []), ...newTeamMembers];

      // Update context problem
      assignStudents(project.id, updatedStudents);
      selectApplicants(
        project.id,
        nonDuplicateList.map((a) => a.id || a.student_id || a.studentEmail)
      );

      // Update local state
      setBackendProjects((prev) =>
        prev.map((p) =>
          (p.project_id || p.id) === project.id
            ? {
                ...p,
                students: updatedStudents,
                current_milestone:
                  p.current_milestone === 'Faculty Assigned'
                    ? 'Student Team Formed'
                    : p.current_milestone,
              }
            : p
        )
      );

      // Clear checked set for this project
      setSelectedApplicants((prev) => ({ ...prev, [project.id]: new Set() }));

      showToast(
        lang === 'hi'
          ? `छात्र टीम की सफलतापूर्वक पुष्टि की गई! (${nonDuplicateList.length} नए छात्र जोड़े गए)`
          : `Team confirmed! ${nonDuplicateList.length} student(s) added without duplicates.`
      );
    } catch (err) {
      showToast(err.message || 'Failed to confirm team selection');
    } finally {
      setSubmittingTeamId(null);
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{lang === 'hi' ? '📁 मेरे प्रोजेक्ट्स' : '📁 My Projects'}</h1>
          <p>
            {lang === 'hi'
              ? 'आपके द्वारा निर्देशित व प्रबंधित प्रोजेक्ट्स, छात्र टीम एवं माइलस्टोन प्रगति'
              : 'Projects, student teams, and milestone progression mentored and managed by you'}
          </p>
        </div>
        <button
          className="btn btn-outline"
          onClick={() => navigate('/faculty/university-problems')}
        >
          {lang === 'hi'
            ? '🏫 विश्वविद्यालय की सभी समस्याएं देखें →'
            : '🏫 View All University Problems →'}
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="card" style={{ padding: '12px 20px', marginBottom: 20 }}>
        <div className="filter-tabs">
          <div
            className={`filter-tab${filter === 'all' ? ' active' : ''}`}
            onClick={() => setFilter('all')}
          >
            <Trans text="All" /> ({allAssignedProjects.length})
          </div>
          <div
            className={`filter-tab${filter === 'ongoing' ? ' active' : ''}`}
            onClick={() => setFilter('ongoing')}
          >
            <Trans text="Ongoing" /> (
            {allAssignedProjects.filter((p) => !p.isCompleted).length})
          </div>
          <div
            className={`filter-tab${filter === 'completed' ? ' active' : ''}`}
            onClick={() => setFilter('completed')}
          >
            <Trans text="Completed" /> (
            {allAssignedProjects.filter((p) => p.isCompleted).length})
          </div>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '30px' }}>
          <Trans text="Loading your projects..." />
        </div>
      )}

      {!loading && filteredProjects.length === 0 && (
        <div className="card empty-state" style={{ textAlign: 'center', padding: 40 }}>
          <span style={{ fontSize: 36 }}>📁</span>
          <h3>
            {filter === 'completed'
              ? (lang === 'hi' ? 'कोई पूर्ण प्रोजेक्ट नहीं है।' : 'No completed projects yet.')
              : (lang === 'hi' ? 'आपको कोई प्रोजेक्ट आवंटित नहीं किया गया है।' : 'No projects assigned to you yet.')}
          </h3>
          <p className="text-muted">
            {lang === 'hi'
              ? 'विश्वविद्यालय प्रशासन द्वारा आपको प्रोजेक्ट आवंटित करने के बाद वे यहाँ दिखाई देंगे।'
              : 'Projects assigned to you by University Administration will appear here.'}
          </p>
        </div>
      )}

      {!loading &&
        filteredProjects.map((p) => {
          const isCompleted = p.isCompleted;
          const currentStageName = p.current_milestone || (isCompleted ? 'Solution Deployed' : 'Faculty Assigned');
          const currentStageIdx = getStageIndex(currentStageName);

          // Get applications/interests from context and backend
          const contextApps = getApplications(p.id) || [];
          const backendApps = p.applicants || [];
          const allApps = [
            ...backendApps,
            ...contextApps.filter(
              (ca) =>
                !backendApps.some(
                  (ba) => (ba.email || ba.studentEmail) === (ca.studentEmail || ca.email)
                )
            ),
          ];

          // Set of confirmed student emails and IDs to prevent duplicate selection
          const confirmedEmails = new Set(
            (p.students || []).map((s) => (s.email || '').toLowerCase()).filter(Boolean)
          );
          const confirmedIds = new Set(
            (p.students || []).map((s) => s.student_id || s.id).filter(Boolean)
          );

          const checkedSet = selectedApplicants[p.id] || new Set();

          return (
            <div className="card" key={p.id} style={{ marginBottom: 24 }}>
              {/* Card Header & Badges */}
              <div className="problem-card__head">
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <span className={`badge ${isCompleted ? 'badge-teal' : 'badge-blue'}`}>
                    {isCompleted ? '✓ Solution Deployed' : '⚡ Ongoing Project'}
                  </span>
                  <span className="badge badge-violet">
                    🏫 {p.allocation?.allocatedTo || 'BIT Mesra, Ranchi'}
                  </span>
                  <span className="badge badge-gray">🏷️ {p.domain}</span>
                </div>
                <span className="badge badge-light" style={{ fontSize: 11 }}>
                  ID: #{String(p.id).slice(0, 12)}
                </span>
              </div>

              {/* Title & Description */}
              <h3 className="problem-title" style={{ marginTop: 10, fontSize: 18 }}>
                {p.title[lang] || p.title.en || p.title.hi}
              </h3>
              <p className="problem-desc" style={{ marginTop: 6, color: '#4b5563' }}>
                {p.desc[lang] || p.desc.en || p.desc.hi}
              </p>

              {/* Standardized Project Details (Part 5 Requirements) */}
              <div
                className="section-box section-box--muted"
                style={{
                  marginTop: 12,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: 12,
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: 8,
                  padding: '12px 16px',
                }}
              >
                <div>
                  <strong>📍 <Trans text="Location:" /></strong> {p.loc}
                </div>
                <div>
                  <strong>🏢 <Trans text="Industry Partner:" /></strong> {p.industryName}
                </div>
                <div>
                  <strong>👨‍🏫 <Trans text="Faculty Mentoring:" /></strong>{' '}
                  <span className="badge badge-blue" style={{ fontWeight: 600 }}>
                    {p.faculty?.name || userFullName}
                  </span>
                </div>
                <div>
                  <strong>🛠️ <Trans text="Skills Required:" /></strong>{' '}
                  {(p.requiredTechnologies || []).join(', ') || 'Engineering, Software'}
                </div>
              </div>

              {/* Confirmed Student Team Working on It */}
              <div style={{ marginTop: 14 }}>
                <strong>👨‍🎓 <Trans text="Student Names Working on It:" /></strong>{' '}
                {p.students && p.students.length > 0 ? (
                  <div style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', marginLeft: 8 }}>
                    {p.students.map((s, idx) => (
                      <span className="badge badge-teal" key={s.email || s.student_id || idx}>
                        👤 {s.name}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted" style={{ fontStyle: 'italic', marginLeft: 6 }}>
                    {lang === 'hi' ? 'कोई छात्र अभी तक चयनित नहीं है' : 'No students confirmed yet'}
                  </span>
                )}
              </div>

              {/* Milestones Component (Exact Standardized 7-stage display) */}
              <div style={{ marginTop: 18, borderTop: '1px solid #e5e7eb', paddingTop: 14 }}>
                <Milestones problem={p} />
              </div>

              {/* ONGOING PROJECT CONTROLS */}
              {!isCompleted && (
                <div style={{ marginTop: 20, borderTop: '1px dashed #cbd5e1', paddingTop: 16 }}>
                  {/* Milestone Progression & Editing */}
                  <div
                    style={{
                      background: '#f0fdf4',
                      border: '1px solid #bbf7d0',
                      borderRadius: 8,
                      padding: '14px 16px',
                      marginBottom: 16,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
                      <div>
                        <h4 style={{ margin: 0, color: '#166534', display: 'flex', alignItems: 'center', gap: 6 }}>
                          📈 <Trans text="Update Project Milestone" />
                        </h4>
                        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#15803d' }}>
                          <Trans text="Current Milestone:" /> <strong>{currentStageName}</strong>
                        </p>
                      </div>

                      {/* Dropdown with Predefined 7-stage sequence */}
                      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                        <select
                          className="form-control"
                          style={{ minWidth: 220, padding: '6px 12px', fontSize: 13, borderRadius: 6 }}
                          value={milestoneSelections[p.id] ?? ''}
                          onChange={(e) =>
                            setMilestoneSelections((prev) => ({ ...prev, [p.id]: e.target.value }))
                          }
                        >
                          <option value="">
                            {lang === 'hi' ? '-- अगला माइलस्टोन चुनें --' : '-- Select Next Milestone --'}
                          </option>
                          {STANDARDIZED_MILESTONES.map((stage, idx) => {
                            const isPastOrCurrent = idx <= currentStageIdx;
                            const isImmediateNext = idx === currentStageIdx + 1;
                            const isFutureSkip = idx > currentStageIdx + 1;

                            return (
                              <option
                                key={stage}
                                value={stage}
                                disabled={isPastOrCurrent || isFutureSkip}
                              >
                                {idx + 1}. {stage}
                                {isPastOrCurrent ? ' (Completed)' : isImmediateNext ? ' ★ (Next Step)' : ' (Locked)'}
                              </option>
                            );
                          })}
                        </select>

                        <button
                          className="btn btn-success btn-sm"
                          disabled={
                            updatingMilestoneId === p.id ||
                            !milestoneSelections[p.id] ||
                            getStageIndex(milestoneSelections[p.id]) <= currentStageIdx
                          }
                          onClick={() => handleUpdateMilestone(p)}
                        >
                          {updatingMilestoneId === p.id ? (
                            <Trans text="Updating..." />
                          ) : (
                            <Trans text="Update Milestone" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Student Interests & Selection Section */}
                  <div
                    style={{
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: 8,
                      padding: '14px 16px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <h4 style={{ margin: 0, color: '#1e293b' }}>
                        👨‍🎓 <Trans text="Student Interests & Selection" /> ({allApps.length})
                      </h4>
                      {allApps.length > 0 && (
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={submittingTeamId === p.id || checkedSet.size === 0}
                          onClick={() => handleConfirmTeam(p, allApps)}
                        >
                          {submittingTeamId === p.id ? (
                            <Trans text="Confirming..." />
                          ) : (
                            <Trans text="Confirm Team Selection" />
                          )}
                        </button>
                      )}
                    </div>

                    {allApps.length === 0 ? (
                      <p className="text-muted" style={{ margin: '8px 0', fontSize: 13 }}>
                        <Trans text="No students have expressed interest yet." />
                      </p>
                    ) : (
                      <div className="stack" style={{ gap: 8 }}>
                        {allApps.map((app) => {
                          const appId = app.id || app.student_id || app.studentEmail;
                          const appEmail = (app.studentEmail || app.email || '').toLowerCase();
                          const appName = app.studentName || app.student_name || app.name || 'Applicant';
                          const isAlreadyInTeam =
                            (appEmail && confirmedEmails.has(appEmail)) ||
                            (app.student_id && confirmedIds.has(app.student_id));

                          const isChecked = checkedSet.has(appId);

                          return (
                            <div
                              key={appId}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 12,
                                padding: '10px 14px',
                                background: isAlreadyInTeam ? '#f1f5f9' : isChecked ? '#eff6ff' : '#ffffff',
                                border: `1px solid ${isAlreadyInTeam ? '#cbd5e1' : isChecked ? '#93c5fd' : '#e2e8f0'}`,
                                borderRadius: 6,
                              }}
                            >
                              {/* Strict Duplicate Prevention: disable checkbox if student is already in team */}
                              <input
                                type="checkbox"
                                checked={isAlreadyInTeam || isChecked}
                                disabled={isAlreadyInTeam}
                                onChange={() => toggleApplicant(p.id, appId)}
                                style={{ cursor: isAlreadyInTeam ? 'not-allowed' : 'pointer', width: 16, height: 16 }}
                              />

                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                                  <strong>{appName}</strong>
                                  <span className="text-muted" style={{ fontSize: 12 }}>
                                    {app.studentEmail || app.email}
                                  </span>
                                  {isAlreadyInTeam && (
                                    <span className="badge badge-teal" style={{ fontSize: 11 }}>
                                      ✓ <Trans text="Selected for Team" />
                                    </span>
                                  )}
                                  {!isAlreadyInTeam && (
                                    <span className="badge badge-yellow" style={{ fontSize: 11 }}>
                                      ⏳ <Trans text="Interest Expressed" />
                                    </span>
                                  )}
                                </div>
                                {(app.idea || app.proposed_solution) && (
                                  <p style={{ margin: '4px 0 0', fontSize: 12.5, color: '#475569' }}>
                                    <strong><Trans text="Proposed Idea:" /></strong> {app.idea || app.proposed_solution}
                                  </p>
                                )}
                                {(app.attachment_url || app.attachment?.url) && (
                                  <div style={{ marginTop: 6 }}>
                                    <a
                                      className="attachment-chip"
                                      href={app.attachment_url || app.attachment?.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                                    >
                                      📄 {app.attachment_name || app.attachment?.name || 'Supporting Document.pdf'}
                                    </a>
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* COMPLETED / SOLUTION DEPLOYED VIEW */}
              {isCompleted && (
                <div
                  style={{
                    marginTop: 16,
                    padding: '12px 16px',
                    background: '#f0fdfa',
                    border: '1px solid #99f6e4',
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 10,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 20 }}>🎉</span>
                    <div>
                      <strong style={{ color: '#0f766e' }}>
                        {lang === 'hi'
                          ? 'परियोजना पूर्ण: समाधान सफलतापूर्वक तैनात कर दिया गया है'
                          : 'Project Completed: Solution Deployed Successfully'}
                      </strong>
                      <div style={{ fontSize: 12.5, color: '#115e59' }}>
                        <Trans text="Completed - Milestone Locked" /> ·{' '}
                        {lang === 'hi' ? 'छात्र प्रमाणपत्र पात्र हैं।' : 'Student e-certificates are unlocked.'}
                      </div>
                    </div>
                  </div>
                  <span className="badge badge-teal" style={{ fontSize: 12 }}>
                    ✓ 7/7 Milestones Completed
                  </span>
                </div>
              )}
            </div>
          );
        })}
    </div>
  );
}

