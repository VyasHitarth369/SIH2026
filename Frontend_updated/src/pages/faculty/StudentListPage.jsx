import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';
import { useApplications } from '../../context/ApplicationsContext';
import { useToast } from '../../context/ToastContext';
import { studentDirectory } from '../../data/orgData';
import { PdfIcon } from '../../components/shared/Icons.jsx';

export default function StudentListPage() {
  const { problemId } = useParams();
  const { t, lang } = useLanguage();
  const { problems, assignStudents } = useProblems();
  const { getApplications, selectApplicants } = useApplications();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [checked, setChecked] = useState([]);

  const problem = problems.find((p) => String(p.id) === String(problemId));
  if (!problem) {
    return (
      <div className="card empty-state">
        <span className="empty-state__icon">🔍</span>
        <Trans text="Problem not found." />
        <div style={{ marginTop: 12 }}><Link to="/faculty/projects">{<Trans text="Back to Projects" />}</Link></div>
      </div>
    );
  }

  const applications = getApplications(problem.id);
  const confirmedStudents = problem.students || [];

  const toggle = (id) => setChecked((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const confirmSelection = () => {
    if (checked.length === 0) {
      showToast(t.selectAtLeastOne);
      return;
    }
    selectApplicants(problem.id, checked);

    // Build full student records for the confirmed team, enriching with
    // directory data (university/domain/technologies) where we have a match.
    const selectedApps = applications.filter((a) => checked.includes(a.id));
    const existingEmails = new Set((problem.students || []).map((s) => s.email?.toLowerCase()));
    const newStudents = selectedApps
      .filter((a) => !existingEmails.has(a.studentEmail?.toLowerCase()))
      .map((a) => {
        const dirMatch = studentDirectory.find((s) => s.email === a.studentEmail);
        return {
          name: a.studentName,
          email: a.studentEmail,
          university: dirMatch?.university || problem.allocation?.allocatedTo,
          domain: dirMatch?.domain || problem.domain,
          technologies: dirMatch?.technologies || problem.requiredTechnologies || [],
          status: 'Active',
          proposedSolution: a.idea ? a.idea.slice(0, 60) : '',
          proposedSolutionDesc: a.idea || '',
        };
      });
    if (newStudents.length === 0 && selectedApps.length > 0) {
      showToast(lang === 'hi' ? 'चयनित छात्र पहले से ही टीम में हैं।' : 'Selected student(s) are already in the team.');
      return;
    }
    assignStudents(problem.id, [...(problem.students || []), ...newStudents]);
    showToast(t.teamConfirmed);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Students Working on This Problem" />}</h1>
          <p className="problem-title" style={{ fontSize: 16 }}>{problem.title[lang] || problem.title.hi}</p>
        </div>
        <button className="btn btn-light" onClick={() => navigate('/faculty/projects')}>{<Trans text="← Back to Projects" />}</button>
      </div>

      {confirmedStudents.length > 0 && (
        <div className="card">
          <h4>{<Trans text="Confirmed Team" />}</h4>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{<Trans text="Name" />}</th><th>{<Trans text="Email" />}</th><th>{<Trans text="University" />}</th><th>{<Trans text="Domain / Skills" />}</th><th>{<Trans text="Technologies" />}</th><th>{<Trans text="Status" />}</th><th>{<Trans text="Proposed Solution" />}</th>
                </tr>
              </thead>
              <tbody>
                {confirmedStudents.map((s) => (
                  <tr key={s.email}>
                    <td>{s.name}</td>
                    <td>{s.email}</td>
                    <td>{s.university}</td>
                    <td>{s.domain}</td>
                    <td>{(s.technologies || []).join(', ')}</td>
                    <td><span className="badge badge-blue">{<Trans text={s.status || ''} />}</span></td>
                    <td>
                      <strong>{s.proposedSolution}</strong>
                      <div className="problem-desc" style={{ margin: '4px 0 0' }}>{s.proposedSolutionDesc}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <h4><Trans text={`Interested Applicants (${applications.length})`} /></h4>
        {applications.length === 0 && <p className="applicants-empty">{t.noApplicationsYet}</p>}
        {applications.map((app) => {
          const isAlreadyInTeam = (problem.students || []).some(
            (s) => s.email?.toLowerCase() === app.studentEmail?.toLowerCase()
          );
          return (
            <label
              className={`applicant-row${app.status === 'selected' || isAlreadyInTeam ? ' applicant-row--selected' : ''}`}
              key={app.id}
              style={isAlreadyInTeam ? { opacity: 0.8, cursor: 'not-allowed' } : {}}
            >
              <input
                type="checkbox"
                checked={isAlreadyInTeam || checked.includes(app.id)}
                disabled={isAlreadyInTeam}
                onChange={() => !isAlreadyInTeam && toggle(app.id)}
              />
              <div className="applicant-row__body">
                <div className="applicant-row__head">
                  <strong>{app.studentName}</strong>
                  <span className="problem-meta">{app.studentEmail}</span>
                  {isAlreadyInTeam ? (
                    <span className="badge badge-teal"><Trans text="Already in Team" /></span>
                  ) : (
                    <>
                      {app.status === 'selected' && <span className="badge badge-teal">{t.selectedForTeam}</span>}
                      {app.status === 'not-selected' && <span className="badge badge-coral">{t.notSelected}</span>}
                    </>
                  )}
                </div>
                <p className="applicant-row__idea"><strong>{<Trans text="Proposed Solution Idea:" />}</strong> {app.idea}</p>
              {app.attachment && (
                <a
                  className="attachment-chip"
                  href={app.attachment.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  <PdfIcon /> {app.attachment.name}
                </a>
              )}
              </div>
            </label>
          );
        })}
        {applications.length > 0 && (
          <button className="btn btn-success btn-sm" onClick={confirmSelection}>{t.confirmTeam}</button>
        )}
      </div>
    </div>
  );
}
