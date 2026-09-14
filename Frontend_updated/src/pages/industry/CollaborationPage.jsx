import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';

export default function CollaborationPage() {
  const { t, lang } = useLanguage();
  const { problems } = useProblems();
  const collabs = problems.filter((p) => p.govApproved && p.assignedUnits.length > 0);

  return (
    <div>
      <div className="page-head"><h1>{t.activeCollab}</h1></div>
      {collabs.map((p) => (
        <div className="card" key={p.id}>
          <h3 className="problem-title">{p.title[lang] || p.title.hi}</h3>
          <p className="problem-desc">{p.desc[lang] || p.desc.hi}</p>
          <div className="problem-meta"><Trans text="🤝 Partners:" /> {p.assignedUnits.map((u) => <Trans key={u} text={u} />)}</div>
          {p.replies.map((r, i) => (
            <div className="feedback-item" key={i}><strong><Trans text={r.unit} /></strong> (<Trans text={r.status} />) — {r.msg}</div>
          ))}
        </div>
      ))}
      {collabs.length === 0 && <div className="card">{<Trans text="No active collaborations yet." />}</div>}
    </div>
  );
}
