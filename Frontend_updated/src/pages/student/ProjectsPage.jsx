import Trans from '../../components/shared/Trans.jsx';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useApplications } from '../../context/ApplicationsContext';
import { useToast } from '../../context/ToastContext';
import FileUploadField from '../../components/shared/FileUploadField';
import { PdfIcon } from '../../components/shared/Icons.jsx';
import apiClient from '../../services/apiClient';

export default function StudentProjectsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const { hasApplied, addApplication, getApplications } = useApplications();
  const { showToast } = useToast();
  const [openIdeaFor, setOpenIdeaFor] = useState(null);
  const [ideaDrafts, setIdeaDrafts] = useState({});
  const [attachmentDrafts, setAttachmentDrafts] = useState({});
  const [backendProjects, setBackendProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submittingId, setSubmittingId] = useState(null);

  const studentEmail = (user?.email || '').toLowerCase();
  const studentName = user?.name || user?.full_name || 'Student';
  const studentId = user?.stakeholder?.student_id || user?.student_id;
  const myUniversity = user?.profile?.university || user?.stakeholder?.university_name;

  // Authoritatively load approved projects for student's university from backend
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/projects?approved_only=true');
      if (res && res.success && Array.isArray(res.data)) {
        setBackendProjects(res.data);
      }
    } catch (err) {
      console.warn('Failed to load student projects from backend:', err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Adapt backend project records with authoritative applicant & membership status
  const adaptedBackend = useMemo(() => {
    return backendProjects.map((p) => {
      const myApplicant = (p.applicants || []).find(
        (a) => (studentId && a.student_id === studentId) ||
               (studentEmail && (a.email || a.studentEmail || '').toLowerCase() === studentEmail)
      );
      const isMember = p.is_member || (p.students || []).some(
        (s) => (studentId && (s.student_id || s.id) === studentId) ||
               (studentEmail && (s.email || '').toLowerCase() === studentEmail)
      );
      const applied = Boolean(myApplicant || isMember);

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
        domain: p.domain || 'Innovation & Engineering',
        category: p.category || 'Civic Problem',
        allocation: {
          allocatedTo: p.university_name || myUniversity || 'Partner University',
          status: 'allocated',
        },
        faculty: p.faculty_name ? { name: p.faculty_name, email: p.faculty_email } : null,
        requiredTechnologies: Array.isArray(p.skills_required)
          ? p.skills_required
          : typeof p.skills_required === 'string' && p.skills_required.includes(',')
          ? p.skills_required.split(',').map((s) => s.trim())
          : [p.skills_required || 'Applied Engineering'].filter(Boolean),
        applied,
        myApplication: myApplicant
          ? {
              status: myApplicant.status || 'pending',
              idea: myApplicant.proposed_solution || myApplicant.idea || '',
              attachment: myApplicant.attachment_url
                ? { url: myApplicant.attachment_url, name: myApplicant.attachment_name || 'Supporting Document.pdf' }
                : null,
            }
          : isMember
          ? { status: 'selected', idea: '' }
          : null,
        isBackend: true,
      };
    });
  }, [backendProjects, studentId, studentEmail, myUniversity]);

  // Merge backend projects with context problems for full coverage
  const available = useMemo(() => {
    const existingIds = new Set(adaptedBackend.map((p) => String(p.id)));
    const contextAvailable = problems
      .filter((p) => p.allocation?.allocatedTo && (!myUniversity || p.allocation.allocatedTo.toLowerCase().includes(myUniversity.toLowerCase()) || myUniversity.toLowerCase().includes(p.allocation.allocatedTo.toLowerCase())))
      .filter((p) => !existingIds.has(String(p.id)))
      .map((p) => {
        const applied = hasApplied(p.id, studentEmail);
        const myApp = getApplications(p.id).find((a) => (a.studentEmail || '').toLowerCase() === studentEmail);
        return {
          ...p,
          applied,
          myApplication: myApp,
        };
      });
    return [...adaptedBackend, ...contextAvailable];
  }, [adaptedBackend, problems, myUniversity, studentEmail, hasApplied, getApplications]);

  const submitApplication = async (id) => {
    const idea = (ideaDrafts[id] || '').trim();
    if (!idea) {
      showToast(t.ideaRequired);
      return;
    }
    const attachment = attachmentDrafts[id] || null;

    try {
      setSubmittingId(id);
      const payload = {
        role: 'applicant',
        proposed_solution: idea,
        attachment_url: attachment?.url || null,
        attachment_name: attachment?.name || null,
      };

      const res = await apiClient.post(`/projects/${id}/student-interest`, payload);
      if (res && (res.success || res.data)) {
        showToast(t.challengeApplied);
        setOpenIdeaFor(null);
        setIdeaDrafts((prev) => ({ ...prev, [id]: '' }));
        setAttachmentDrafts((prev) => ({ ...prev, [id]: null }));
        // Also update ApplicationsContext for in-memory sync
        addApplication(id, { studentName, studentEmail, idea, attachment });
        // Authoritatively reload projects from backend
        await loadProjects();
      } else {
        showToast(res?.message || 'Failed to submit student interest.');
      }
    } catch (err) {
      showToast(err.message || 'Error submitting application.');
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <div>
      <div className="page-head"><h1><Trans text="New Projects" /></h1></div>
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>{t.availableChallenges}</h3>

        {available.map((p) => {
          const applied = p.applied || hasApplied(p.id, studentEmail);
          const myApplication = p.myApplication || getApplications(p.id).find((a) => (a.studentEmail || '').toLowerCase() === studentEmail);

          return (
            <div className="student-challenge" key={p.id}>
              <span className="badge badge-blue"><Trans text="Domain:" /> {<Trans text={p.domain || p.category} />}</span>
              <h4 className="student-challenge__title">{p.title[lang] || p.title.en || p.title.hi}</h4>
              <p className="student-challenge__desc">{p.desc[lang] || p.desc.en || p.desc.hi}</p>
              <div className="problem-meta">🏫 <Trans text="University:" /> {<Trans text={p.allocation.allocatedTo} />} · 👨‍🏫 <Trans text="Faculty:" /> {p.faculty?.name || <Trans text="Not yet allocated" />}</div>

              {p.requiredTechnologies?.length > 0 && (
                <div className="skills-block">
                  <div className="skills-block__label">🛠️ <Trans text="Required Skills:" /></div>
                  <div className="skills-chips">
                    {p.requiredTechnologies.map((skill) => (
                      <span className="skill-chip" key={skill}>{skill}</span>
                    ))}
                  </div>
                </div>
              )}

              {applied ? (
                <div className="applied-box">
                  <span className="badge badge-teal">✅ {t.applied}</span>
                  {myApplication?.status === 'selected' && <span className="badge badge-teal">🎉 {t.selectedForTeam}</span>}
                  {myApplication?.status === 'not-selected' && <span className="badge badge-coral">{t.notSelected}</span>}
                  {myApplication?.idea && (
                    <p className="applied-box__idea"><strong>{<Trans text="Proposed Solution Idea:" />}</strong> {myApplication.idea}</p>
                  )}
                  {myApplication?.attachment && (
                    <a className="attachment-chip" href={myApplication.attachment.url} target="_blank" rel="noopener noreferrer">
                      <PdfIcon /> {myApplication.attachment.name}
                    </a>
                  )}
                </div>
              ) : openIdeaFor === p.id ? (
                <div className="idea-form">
                  <label>{<Trans text="Proposed Solution Idea" />}</label>
                  <textarea
                    placeholder={lang === 'hi' ? 'इस समस्या के लिए अपने प्रस्तावित समाधान का विचार बताएं...' : 'Describe your proposed solution idea for this problem...'}
                    value={ideaDrafts[p.id] || ''}
                    onChange={(e) => setIdeaDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    disabled={submittingId === p.id}
                  />
                  <div style={{ marginTop: 10 }}>
                    <FileUploadField
                      label={<Trans text="Attach Supporting PDF (optional)" />}
                      accept="application/pdf"
                      kind="document"
                      dragLabel={<Trans text="Drag & drop a PDF here, or click to browse" />}
                      onChange={(file) => setAttachmentDrafts((prev) => ({ ...prev, [p.id]: file }))}
                    />
                  </div>
                  <div className="idea-form__actions">
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={submittingId === p.id}
                      onClick={() => submitApplication(p.id)}
                    >
                      {submittingId === p.id ? (lang === 'hi' ? 'जमा हो रहा है...' : 'Submitting...') : t.submitApplication}
                    </button>
                    <button
                      className="btn btn-light btn-sm"
                      disabled={submittingId === p.id}
                      onClick={() => setOpenIdeaFor(null)}
                    >
                      {t.cancel}
                    </button>
                  </div>
                </div>
              ) : (
                <button className="btn btn-primary btn-sm" onClick={() => setOpenIdeaFor(p.id)}>{t.applyForChallenge}</button>
              )}
            </div>
          );
        })}
        {!loading && available.length === 0 && <p>{<Trans text="No projects are available for your university right now." />}</p>}
      </div>
    </div>
  );
}
