import Trans from '../../components/shared/Trans.jsx';
import { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import { facultyDirectory } from '../../data/orgData';
import Countdown from '../../components/shared/Countdown';

const statusLabel = {
  not_started: 'Pending Review',
  awaiting_allocation: 'Awaiting Allocation',
  allocated: 'Allocated',
  rejected: 'Rejected',
  deadline_completed: 'Deadline Completed',
};
const statusClass = {
  not_started: 'badge-blue',
  awaiting_allocation: 'badge-amber',
  allocated: 'badge-teal',
  rejected: 'badge-coral',
  deadline_completed: 'badge-gray',
};

export default function AllocationsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems, assignFaculty } = useProblems();
  const { showToast } = useToast();
  const [facultyChoice, setFacultyChoice] = useState({});

  const myUniversity = user?.profile?.university || 'BIT Mesra, Ranchi';
  const relevant = problems.filter((p) => p.allocation?.responses?.[myUniversity] && p.allocation.responses[myUniversity] !== undefined);
  const myFaculty = facultyDirectory.filter((f) => f.university === myUniversity);

  const allocateFaculty = (problemId) => {
    const facultyId = facultyChoice[problemId];
    const faculty = myFaculty.find((f) => f.id === facultyId);
    if (!faculty) {
      showToast(<Trans text="Please select a faculty member first." />);
      return;
    }
    assignFaculty(problemId, { name: faculty.name, email: faculty.email });
    showToast(<Trans text={`Allocated to ${faculty.name}.`} />);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Allocation Monitoring" />}</h1>
          <p>{lang === 'hi' ? `प्राथमिकता/समय सीमा आवंटन स्थिति ट्रैक करें और ${myUniversity} के लिए स्वीकृत समस्याओं को फैकल्टी को आवंटित करें।` : `Track priority/deadline allocation status and allocate approved problems to faculty for ${myUniversity}.`}</p>
        </div>
      </div>

      {relevant.map((p) => {
        const myResponse = p.allocation.responses[myUniversity];
        const wonAllocation = p.allocation.allocatedTo === myUniversity;
        return (
          <div className="card" key={p.id}>
            <div className="gov-card__head">
              <span className="badge badge-violet">ID: #CH-JH-{p.id}</span>
              <span className={`badge ${statusClass[p.allocation.status] || 'badge-blue'}`}>{<Trans text={statusLabel[p.allocation.status] || p.allocation.status} />}</span>
              <span className={`badge ${myResponse === 'accepted' ? 'badge-teal' : 'badge-coral'}`}><Trans text="Our Response:" /> {<Trans text={myResponse || ''} />}</span>
            </div>

            <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>

            <div className="allocation-track">
              {p.allocation.queue.map((uni, idx) => (
                <div className="allocation-track__row" key={uni}>
                  <span>#{idx + 1} {uni}{uni === myUniversity ? (lang === 'hi' ? ' (आप)' : ' (You)') : ''}</span>
                  <span className={`badge ${p.allocation.responses[uni] === 'accepted' ? 'badge-teal' : p.allocation.responses[uni] === 'rejected' ? 'badge-coral' : 'badge-gray'}`}>
                    {<Trans text={p.allocation.responses[uni] || ''} />}
                  </span>
                </div>
              ))}
            </div>

            {p.allocation.status === 'awaiting_allocation' && !p.allocation.allocatedTo && (
              <div className="allocation-track__row" style={{ marginTop: 8 }}>
                <span>{lang === 'hi' ? 'स्वीकार/अस्वीकार करने की समय सीमा:' : 'Deadline for accepting/rejecting:'}</span>
                <Countdown deadlineAt={p.allocation.deadlineAt} />
              </div>
            )}

            {wonAllocation && !p.faculty && (
              <div className="decision-box" style={{ marginTop: 12 }}>
                <div className="field">
                  <label>{<Trans text="Allocate to Faculty" />}</label>
                  <select value={facultyChoice[p.id] || ''} onChange={(e) => setFacultyChoice((prev) => ({ ...prev, [p.id]: e.target.value }))}>
                    <option value="">{<Trans text="Select faculty…" />}</option>
                    {myFaculty.map((f) => (
                      <option key={f.id} value={f.id}>{f.name} — {f.department} ({f.expertise})</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-success btn-block" onClick={() => allocateFaculty(p.id)}>{<Trans text="Allocate Faculty" />}</button>
              </div>
            )}

            {wonAllocation && p.faculty && (
              <div className="problem-meta" style={{ marginTop: 10 }}>{<Trans text="👨‍🏫 Allocated Faculty:" />} <strong>{p.faculty.name}</strong> ({p.faculty.email})</div>
            )}
          </div>
        );
      })}

      {relevant.length === 0 && <div className="card">{<Trans text="No accepted or rejected problems yet — review Incoming Problems first." />}</div>}
    </div>
  );
}
