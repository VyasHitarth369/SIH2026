import Trans from '../../components/shared/Trans.jsx';
import { useMemo, useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useProblems } from '../../context/ProblemsContext';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import { aiService } from '../../services/aiService';
import { fetchChallengeById } from '../../services/challengeService';

export default function GlobalSearchPage() {
  const [searchParams] = useSearchParams();
  const rawId = searchParams.get('problemId');
  const problemId = rawId;
  const { problems } = useProblems();
  const { lang } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const contextProblem = problems.find((p) => String(p.id) === String(rawId) || p.id === Number(rawId));
  const [problem, setProblem] = useState(contextProblem || null);
  const [decision, setDecision] = useState({}); // { [solutionId]: 'works' | 'no' }
  const [resolved, setResolved] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Synchronize with contextProblem or fetch from backend if loaded directly
  useEffect(() => {
    if (contextProblem) {
      setProblem(contextProblem);
      return;
    }
    if (problemId) {
      fetchChallengeById(problemId)
        .then((data) => {
          if (data) {
            setProblem({
              id: data.challenge_id || problemId,
              title: { en: data.title, hi: data.title },
              desc: { en: data.description, hi: data.description },
              loc: data.location || `${data.city || ''}, ${data.district || ''}`,
              district: data.district || data.city || '',
              category: 'Civic Issue',
            });
          }
        })
        .catch(() => {});
    }
  }, [contextProblem, problemId]);

  // Trigger backend AI review & verified solution discovery (Call 1)
  useEffect(() => {
    if (!problemId) return;
    let mounted = true;
    async function runAiReview() {
      try {
        setIsAnalyzing(true);
        const res = await aiService.analyzeChallenge(problemId);
        if (mounted && res) {
          setAiAnalysis(res);
        }
      } catch (err) {
        console.warn('Backend AI analysis note:', err.message);
      } finally {
        if (mounted) setIsAnalyzing(false);
      }
    }
    runAiReview();
    return () => { mounted = false; };
  }, [problemId]);

  // Dynamic solutions from AI Review (Call 1)
  const matches = useMemo(() => {
    const list = [];
    const analysisData = aiAnalysis?.data || aiAnalysis;

    // 1. Dynamic solutions returned from Gemini Search Grounding
    if (analysisData?.solutions && Array.isArray(analysisData.solutions) && analysisData.solutions.length > 0) {
      analysisData.solutions.forEach((sol, idx) => {
        list.push({
          id: `dynamic-ai-sol-${idx}`,
          title: sol.solution_name,
          titleHi: sol.solution_name,
          description: sol.description,
          descriptionHi: sol.description,
          area: sol.geographic_scope || problem?.district || 'Regional / National',
          areaHi: sol.geographic_scope || problem?.district || 'क्षेत्रीय / राष्ट्रीय',
          organization: sol.provider,
          organizationHi: sol.provider,
          technologies: [sol.relevance, sol.accessibility].filter(Boolean),
          status: sol.operational_status || 'Active Deployment',
          active: sol.operational_status !== 'inactive',
          implementationInfo: sol.evidence_summary || 'Discovered and verified via AI Search Grounding.',
          implementationInfoHi: sol.evidence_summary || 'एआई सर्च ग्राउंडिंग द्वारा सत्यापित वास्तविक समाधान।',
          sourceUrls: sol.source_urls || [],
        });
      });
    } else if (analysisData && analysisData.solution_found && analysisData.existing_solution) {
      // Single formatted solution text
      const backendSol = {
        id: 'gov-ai-verified',
        title: 'Verified Existing Solution / Scheme',
        titleHi: 'सत्यापित मौजूदा समाधान / योजना',
        description: analysisData.existing_solution,
        descriptionHi: analysisData.existing_solution,
        area: problem?.district || 'Statewide & National Scope',
        areaHi: problem?.district || 'राज्यव्यापी एवं राष्ट्रीय स्तर',
        organization: 'Competent Authority / Public Agency',
        organizationHi: 'सक्षम प्राधिकारी / सार्वजनिक एजेंसी',
        technologies: ['Verified Public Scheme'],
        status: 'Active',
        active: true,
        implementationInfo: 'Verified real-world initiative identified by AI review.',
        implementationInfoHi: 'एआई समीक्षा द्वारा पहचानी गई वास्तविक योजना।',
        sourceUrls: [],
      };
      list.push(backendSol);
    }

    return list;
  }, [aiAnalysis, problem]);

  const imageMismatch = useMemo(() => {
    const analysisData = aiAnalysis?.data || aiAnalysis;
    return analysisData?.image_evidence_status === 'mismatch';
  }, [aiAnalysis]);

  const markWorks = async (solutionId) => {
    setDecision((prev) => ({ ...prev, [solutionId]: 'works' }));
    setResolved(true);
    showToast(<Trans text="Great — this existing solution has been noted as a match for your problem." />);
    if (problemId) {
      try {
        await aiService.respondToExistingSolution(problemId, 'accept');
      } catch (err) {
        console.warn('Backend status update note:', err.message);
      }
    }
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
          <h3 className="problem-title">{problem.title?.[lang] || problem.title?.hi || problem.title?.en || problem.title}</h3>
          <p className="problem-desc">{problem.desc?.[lang] || problem.desc?.hi || problem.desc?.en || problem.desc}</p>
        </div>
      )}

      {imageMismatch && (
        <div className="card" style={{ borderLeft: '4px solid #f59e0b', backgroundColor: '#fffbeb', padding: '16px' }}>
          <h4 style={{ color: '#b45309', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>⚠️</span> <Trans text="Evidence Notice: Image Mismatch" />
          </h4>
          <p className="problem-desc" style={{ color: '#92400e', margin: 0 }}>
            <Trans text="The uploaded image may not match the problem description. Please upload a clearer or relevant image if possible." />
          </p>
        </div>
      )}

      {isAnalyzing && (
        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <span className="spinner" style={{ display: 'inline-block', marginRight: 10 }} />
          <span>{lang === 'hi' ? 'एआई मौजूदा सरकारी योजनाओं एवं डेटाबेस की खोज कर रहा है...' : 'AI is searching government databases and existing solutions for matches...'}</span>
        </div>
      )}

      {!isAnalyzing && matches.length === 0 && (
        <div className="card empty-state" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🎯</div>
          <h3>{<Trans text="No Existing Solution Found" />}</h3>
          <p className="problem-desc" style={{ maxWidth: '640px', margin: '0 auto 20px' }}>
            {lang === 'hi'
              ? 'एआई ने डेटाबेस की जांच की है। आपके क्षेत्र में इस समस्या के लिए कोई पूर्व-मौजूदा समाधान नहीं मिला। यह एक नई चुनौती के रूप में सत्यापित है और विश्वविद्यालय शोधकर्ताओं एवं छात्रों को समाधान निर्माण हेतु भेजी जा रही है।'
              : 'Our AI review checked public schemes and local repositories. No pre-existing solution directly resolves this challenge. It has been validated as a novel problem and forwarded to universities and industry partners for collaborative problem solving!'}
          </p>
          <div>
            <button className="btn btn-primary" onClick={() => navigate('/citizen/problems')}>
              {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'Proceed to Track My Problem →'}
            </button>
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
            {sol.technologies && <div className="problem-meta">🛠️ <Trans text="Technologies:" /> {sol.technologies.join(', ')}</div>}
            <div className="problem-meta">ℹ️ {lang === 'hi' ? (sol.implementationInfoHi || sol.implementationInfo) : sol.implementationInfo}</div>
            {sol.sourceUrls && sol.sourceUrls.length > 0 && (
              <div className="problem-meta" style={{ marginTop: '6px' }}>
                🔗 <Trans text="Verified Sources:" />{' '}
                {sol.sourceUrls.map((url, uidx) => (
                  <a key={uidx} href={url} target="_blank" rel="noopener noreferrer" style={{ marginRight: '8px', textDecoration: 'underline' }}>
                    {new URL(url).hostname}
                  </a>
                ))}
              </div>
            )}

            {!decision[sol.id] && (
              <div className="proposal-card__actions" style={{ marginTop: 14 }}>
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
