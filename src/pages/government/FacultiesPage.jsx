import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';

export default function FacultiesPage() {
  const { lang } = useLanguage();
  const { problems } = useProblems();
  const withFaculty = problems.filter((p) => p.faculty);

  return (
    <div>
      <div className="page-head"><h1>{<Trans text="Assigned Faculties" />}</h1></div>
      <div className="card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>{<Trans text="Faculty" />}</th><th>{<Trans text="Email" />}</th><th>{<Trans text="University" />}</th><th>{<Trans text="Problem" />}</th><th>{<Trans text="Domain" />}</th><th>{<Trans text="Students" />}</th></tr>
            </thead>
            <tbody>
              {withFaculty.map((p) => (
                <tr key={p.id}>
                  <td>{p.faculty.name}</td>
                  <td>{p.faculty.email}</td>
                  <td><Trans text={p.allocation.allocatedTo} /></td>
                  <td>{p.title[lang] || p.title.hi}</td>
                  <td><Trans text={p.domain || p.category} /></td>
                  <td>{p.students?.length || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {withFaculty.length === 0 && <p className="problem-desc" style={{ padding: 16 }}>{<Trans text="No faculty allocations yet." />}</p>}
        </div>
      </div>
    </div>
  );
}
