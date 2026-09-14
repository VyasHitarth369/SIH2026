import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';

export default function GovStudentsPage() {
  const { lang } = useLanguage();
  const { problems } = useProblems();
  const rows = problems.flatMap((p) => (p.students || []).map((s) => ({ ...s, problem: p })));

  return (
    <div>
      <div className="page-head"><h1>{<Trans text="Students Solving Problems" />}</h1></div>
      <div className="card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>{<Trans text="Student" />}</th><th>{<Trans text="University" />}</th><th>{<Trans text="Domain" />}</th><th>{<Trans text="Technologies" />}</th><th>{<Trans text="Problem" />}</th><th>{<Trans text="Status" />}</th></tr>
            </thead>
            <tbody>
              {rows.map((s, i) => (
                <tr key={i}>
                  <td>{s.name}</td>
                  <td><Trans text={s.university} /></td>
                  <td><Trans text={s.domain} /></td>
                  <td>{(s.technologies || []).join(', ')}</td>
                  <td>{s.problem.title[lang] || s.problem.title.hi}</td>
                  <td><span className="badge badge-blue"><Trans text={s.status} /></span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && <p className="problem-desc" style={{ padding: 16 }}>{<Trans text="No students currently assigned." />}</p>}
        </div>
      </div>
    </div>
  );
}
