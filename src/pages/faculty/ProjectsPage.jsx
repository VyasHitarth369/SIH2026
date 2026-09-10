import Trans from '../../components/shared/Trans.jsx';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { useApplications } from '../../context/ApplicationsContext';

export default function FacultyProjectsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const { getApplications } = useApplications();
  const navigate = useNavigate();

  const myUniversity = user?.profile?.university;
  // Section 17: any active project belonging to the university is visible to
  // all of its authorized faculty, not just the one formally allotted.
  const universityProjects = problems.filter((p) => p.allocation?.allocatedTo && (!myUniversity || p.allocation.allocatedTo === myUniversity));

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{lang === 'hi' ? '📁 मेरे प्रोजेक्ट्स' : '📁 My Projects'}</h1>
          <p>{lang === 'hi' ? 'आपके द्वारा प्रबंधित प्रोजेक्ट्स एवं छात्र टीम' : 'Projects and student teams managed by you'}</p>
        </div>
        <button className="btn btn-outline" onClick={() => navigate('/faculty/university-problems')}>
          {lang === 'hi' ? '🏫 विश्वविद्यालय की सभी समस्याएं देखें →' : '🏫 View All University Problems →'}
        </button>
      </div>

      {universityProjects.map((p) => {
        const applications = getApplications(p.id);
        const studentsWorking = p.students?.length || applications.filter((a) => a.status === 'selected').length || applications.length;
        const isMine = p.faculty?.email === user?.email;

        return (
          <div className="card" key={p.id}>
            <div className="problem-card__head">
              <span className={`badge ${isMine ? 'badge-blue' : 'badge-gray'}`}>{<Trans text={isMine ? 'Allotted to You' : 'University Active Project'} />}</span>
              {p.type === 'solved' && <span className="badge badge-teal">{<Trans text="Solved" />}</span>}
            </div>
            <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
            <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>
            <div className="problem-meta"><Trans text="Domain:" /> {<Trans text={p.domain || p.category} />} · <Trans text="Required Tech:" /> {(p.requiredTechnologies || []).join(', ') || '—'}</div>
            {p.suggestedIndustries?.length > 0 && <div className="problem-meta"><Trans text="Suggested Industries:" /> {p.suggestedIndustries.join(', ')}</div>}
            <div className="problem-meta"><Trans text="👨‍🏫 Faculty:" /> {p.faculty?.name || <Trans text="Not yet allocated" />}</div>

            <div className="proposal-card__actions" style={{ marginTop: 10 }}>
              <button className="btn btn-light btn-sm" onClick={() => navigate(`/faculty/students/${p.id}`)}>
                <Trans text="Students Working:" /> <strong>{studentsWorking}</strong> →
              </button>
            </div>
          </div>
        );
      })}
      {universityProjects.length === 0 && <div className="card">{<Trans text="No active projects allocated to your university yet." />}</div>}
    </div>
  );
}
