import Trans from '../../components/shared/Trans.jsx';
import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useProblems } from '../../context/ProblemsContext';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import { existingSolutions } from '../../data/orgData';

function findMatches(problem) {
  if (!problem) return existingSolutions.slice(0, 2);
  const haystack = `${problem.title.en} ${problem.desc.en} ${problem.category || ''}`.toLowerCase();
  const scored = existingSolutions.map((sol) => {
    const hits = sol.keywords.filter((k) => haystack.includes(k)).length;
    const categoryHit = problem.category && sol.matchesCategory === problem.category ? 1 : 0;
    return { sol, score: hits + categoryHit };
  });
  return scored.filter((s) => s.score > 0).sort((a, b) => b.score - a.score).map((s) => s.sol);
}

export default function GlobalSearchPage() {
  const [searchParams] = useSearchParams();
  const problemId = Number(searchParams.get('problemId'));
  const { problems } = useProblems();
  const { lang } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const problem = problems.find((p) => p.id === problemId);
  const matches = useMemo(() => findMatches(problem), [problem]);
  const [decision, setDecision] = useState({}); // { [solutionId]: 'works' | 'no' }
  const [resolved, setResolved] = useState(false);

  const markWorks = (solutionId) => {
    setDecision((prev) => ({ ...prev, [solutionId]: 'works' }));
    setResolved(true);
    showToast(<Trans text="Great — this existing solution has been noted as a match for your problem." />);
  };

  const markDoesNotWork = (solutionId) => {
    setDecision((prev) => ({ ...prev, [solutionId]: 'no' }));
    navigate(`/problem-validation?problemId=${problemId}${solutionId ? `&solutionId=${solutionId}` : ''}`);
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Existing Solutions in Your Area" />}</h1>
          <p>{<Trans text="Before your problem is routed to Government and University Administration, let's check whether a solution already exists." />}</p>
        </div>
      </div>

      {problem && (
        <div className="card">
          <span className="badge badge-blue">{<Trans text="Your Submitted Problem" />}</span>
          <h3 className="problem-title">{problem.title[lang] || problem.title.hi}</h3>
          <p className="problem-desc">{problem.desc[lang] || problem.desc.hi}</p>
        </div>
      )}

      {matches.length === 0 && (
        <div className="card empty-state">
          <span className="empty-state__icon">🔍</span>
          {<Trans text="No closely matching existing solution was found. Your problem will proceed to Government and University Administration for review." />}
          <div style={{ marginTop: 16 }}>
            <button className="btn btn-primary" onClick={() => navigate('/citizen/problems')}>{<Trans text="Continue to My Problems" />}</button>
          </div>
        </div>
      )}

      <div className="stack">
        {matches.map((sol) => (
          <div className="card solution-result-card" key={sol.id}>
            <div className="problem-card__head">
              <span className={`badge ${sol.active ? 'badge-teal' : 'badge-gray'}`}>{<Trans text={sol.status} />}</span>
              {sol.active && <span className="badge badge-blue">{<Trans text="Currently Active" />}</span>}
            </div>
            <h3 className="problem-title">{lang === 'hi' ? (sol.titleHi || sol.title) : sol.title}</h3>
            <p className="problem-desc">{lang === 'hi' ? (sol.descriptionHi || sol.description) : sol.description}</p>
            <div className="problem-meta">📍 <Trans text="Area:" /> {lang === 'hi' ? (sol.areaHi || sol.area) : sol.area} · 🏫 <Trans text="Organization:" /> {lang === 'hi' ? (sol.organizationHi || sol.organization) : sol.organization}</div>
            <div className="problem-meta">🛠️ <Trans text="Technologies:" /> {sol.technologies.join(', ')}</div>
            <div className="problem-meta">ℹ️ {lang === 'hi' ? (sol.implementationInfoHi || sol.implementationInfo) : sol.implementationInfo}</div>

            {!decision[sol.id] && (
              <div className="proposal-card__actions">
                <button className="btn btn-success btn-sm" onClick={() => markWorks(sol.id)}>{<Trans text="✅ This solution works for my problem" />}</button>
                <button className="btn btn-light btn-sm" onClick={() => markDoesNotWork(sol.id)}>{<Trans text="❌ This solution does not solve my problem" />}</button>
              </div>
            )}

            {decision[sol.id] === 'works' && (
              <div className="validation-box validation-box--ok" style={{ marginTop: 12 }}>
                ✅ {<Trans text="Marked as a fit. You may request that Government consider implementing this existing solution in your area." />}
              </div>
            )}
          </div>
        ))}
      </div>

      {resolved && (
        <div className="card">
          <h4>{<Trans text="Request Implementation" />}</h4>
          <p className="problem-desc">{<Trans text="Since an existing solution already fits your problem, you can request Government to consider implementing it in your area instead of starting a new project." />}</p>
          <button className="btn btn-primary" onClick={() => { showToast(<Trans text="Implementation request sent to Government." />); navigate('/citizen/problems'); }}>
            {<Trans text="Request Government Implementation" />}
          </button>
        </div>
      )}

      {matches.length > 0 && (
        <p className="spoc-note">
          {<Trans text="None of these a fit?" />} <Link to={`/problem-validation?problemId=${problemId}`}>{<Trans text="Explain why and continue" />}</Link>.
        </p>
      )}
    </div>
  );
}
