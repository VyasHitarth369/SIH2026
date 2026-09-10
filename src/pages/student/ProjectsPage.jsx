import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useApplications } from '../../context/ApplicationsContext';
import { useToast } from '../../context/ToastContext';

export default function StudentProjectsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const { hasApplied, addApplication, getApplications } = useApplications();
  const { showToast } = useToast();
  const [openIdeaFor, setOpenIdeaFor] = useState(null);
  const [ideaDrafts, setIdeaDrafts] = useState({});

  // Any problem allocated to the student's university is visible — students
  // are not restricted from seeing projects just because faculty hasn't
  // formally assigned a team yet (mirrors Section 17's faculty visibility rule).
  const myUniversity = user?.profile?.university;
  const available = problems.filter((p) => p.allocation?.allocatedTo && (!myUniversity || p.allocation.allocatedTo === myUniversity));
  const studentEmail = user?.email || 'student@example.com';
  const studentName = user?.name || 'Student';

  const submitApplication = (id) => {
    const idea = (ideaDrafts[id] || '').trim();
    if (!idea) {
      showToast(t.ideaRequired);
      return;
    }
    addApplication(id, { studentName, studentEmail, idea });
    setOpenIdeaFor(null);
    showToast(t.challengeApplied);
  };

  return (
    <div>
      <div className="page-head"><h1>{t.studentTitle}</h1></div>
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>{t.availableChallenges}</h3>

        {available.map((p) => {
          const applied = hasApplied(p.id, studentEmail);
          const myApplication = getApplications(p.id).find((a) => a.studentEmail === studentEmail);

          return (
            <div className="student-challenge" key={p.id}>
              <span className="badge badge-blue"><Trans text="Domain:" /> {<Trans text={p.domain || p.category} />}</span>
              <h4 className="student-challenge__title">{p.title[lang] || p.title.hi}</h4>
              <p className="student-challenge__desc">{p.desc[lang] || p.desc.hi}</p>
              <div className="problem-meta">🏫 <Trans text="University:" /> {<Trans text={p.allocation.allocatedTo} />} · 👨‍🏫 <Trans text="Faculty:" /> {p.faculty?.name || <Trans text="Not yet allocated" />}</div>

              {applied ? (
                <div className="applied-box">
                  <span className="badge badge-teal">✅ {t.applied}</span>
                  {myApplication?.status === 'selected' && <span className="badge badge-teal">🎉 {t.selectedForTeam}</span>}
                  {myApplication?.status === 'not-selected' && <span className="badge badge-coral">{t.notSelected}</span>}
                  <p className="applied-box__idea"><strong>{<Trans text="Proposed Solution Idea:" />}</strong> {myApplication?.idea}</p>
                </div>
              ) : openIdeaFor === p.id ? (
                <div className="idea-form">
                  <label>{<Trans text="Proposed Solution Idea" />}</label>
                  <textarea
                    placeholder={lang === 'hi' ? 'इस समस्या के लिए अपने प्रस्तावित समाधान का विचार बताएं...' : 'Describe your proposed solution idea for this problem...'}
                    value={ideaDrafts[p.id] || ''}
                    onChange={(e) => setIdeaDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))}
                  />
                  <div className="idea-form__actions">
                    <button className="btn btn-primary btn-sm" onClick={() => submitApplication(p.id)}>{t.submitApplication}</button>
                    <button className="btn btn-light btn-sm" onClick={() => setOpenIdeaFor(null)}>{t.cancel}</button>
                  </div>
                </div>
              ) : (
                <button className="btn btn-primary btn-sm" onClick={() => setOpenIdeaFor(p.id)}>{t.applyForChallenge}</button>
              )}
            </div>
          );
        })}
        {available.length === 0 && <p>{<Trans text="No projects are available for your university right now." />}</p>}
      </div>
    </div>
  );
}
