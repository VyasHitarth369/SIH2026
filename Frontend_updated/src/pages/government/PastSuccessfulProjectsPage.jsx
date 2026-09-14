import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';

export default function PastSuccessfulProjectsPage() {
  const { t, lang } = useLanguage();
  const { problems } = useProblems();
  const solved = problems.filter((p) => p.type === 'solved');

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{t.pastSuccessTitle}</h1>
          <p>{t.pastSuccessSub}</p>
        </div>
      </div>

      {solved.map((p) => (
        <div className="card" key={p.id}>
          <span className="badge badge-teal">✅ {t.solved.toUpperCase()}</span>
          <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
          <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>
          <div className="problem-meta">📍 {t.location}: {p.loc} · 🏷️ {t.category}: <Trans text={p.category} /></div>

          {p.solution && (
            <div className="solution-block">
              <h4>{t.solutionLabel}</h4>
              <p>{p.solution[lang] || p.solution.hi}</p>
            </div>
          )}

          {p.solvedBy && (
            <div className="credit-block">
              <h4>{t.solvedByLabel}</h4>
              <div className="credit-grid">
                <div><span className="credit-tag">👨‍🎓 {t.studentLabel}</span>{p.solvedBy.student}</div>
                <div><span className="credit-tag">🎓 {t.universityLabel}</span><Trans text={p.solvedBy.university} /></div>
                <div><span className="credit-tag">🏢 {t.industryLabel}</span><Trans text={p.solvedBy.industry} /></div>
              </div>
            </div>
          )}
        </div>
      ))}

      {solved.length === 0 && <div className="card">{<Trans text="No successful projects yet." />}</div>}
    </div>
  );
}
