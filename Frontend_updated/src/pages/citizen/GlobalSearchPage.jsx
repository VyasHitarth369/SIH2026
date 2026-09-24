import Trans from '../../components/shared/Trans.jsx';
import { useMemo, useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useProblems } from '../../context/ProblemsContext';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import { aiService } from '../../services/aiService';
import { fetchChallengeById, voteChallenge } from '../../services/challengeService';

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
  const [apiError, setApiError] = useState(null);
  const [hasSupportedDuplicate, setHasSupportedDuplicate] = useState(false);
  const [showGapInput, setShowGapInput] = useState(false);
  const [gapReason, setGapReason] = useState('');
  const [isSubmittingGap, setIsSubmittingGap] = useState(false);
  const [gapResult, setGapResult] = useState(null);

  // Existing Solution Decision Workflow state
  const [isAcceptedSolution, setIsAcceptedSolution] = useState(false);
  const [isAccepting, setIsAccepting] = useState(false);
  const [showSolutionDiffInput, setShowSolutionDiffInput] = useState(false);
  const [solutionDiffReason, setSolutionDiffReason] = useState('');
  const [isSubmittingSolutionDiff, setIsSubmittingSolutionDiff] = useState(false);
  const [solutionGapResult, setSolutionGapResult] = useState(null);

  // Synchronize with contextProblem or fetch from backend if loaded directly
  useEffect(() => {
    if (contextProblem) {
      setProblem(contextProblem);
      if (contextProblem.status === 'accepted_existing_solution') {
        setIsAcceptedSolution(true);
      }
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
            if (data.status === 'accepted_existing_solution') {
              setIsAcceptedSolution(true);
            } else if (data.status === 'validated' && data.ai_analysis?.solution_gap_valid === true) {
              setSolutionGapResult({
                valid: true,
                message: data.ai_analysis.solution_gap || (lang === 'hi' ? 'अंतर मान्य किया गया! समस्या सरकारी समीक्षा हेतु अग्रेषित की गई।' : 'Gap successfully validated! Problem routed to Government for review and approval.'),
              });
            } else if (data.status === 'gap_invalid') {
              setSolutionGapResult({
                valid: false,
                message: (lang === 'hi' ? 'प्रदान किया गया अंतर एक नई परियोजना के लिए पर्याप्त अप्रयुक्त आवश्यकता स्थापित नहीं करता है।' : 'The provided difference does not establish a sufficient unmet need for a new project.'),
              });
            }
          }
        })
        .catch(() => {});
    }
  }, [contextProblem, problemId, lang]);

  // Trigger backend AI review & verified solution discovery (Call 1)
  useEffect(() => {
    if (!problemId) return;
    let mounted = true;
    async function runAiReview() {
      try {
        setIsAnalyzing(true);
        setApiError(null);
        const res = await aiService.analyzeChallenge(problemId);
        if (mounted && res) {
          setAiAnalysis(res);
          const data = res?.data || res;
          if (data?.status === 'accepted_existing_solution') {
            setIsAcceptedSolution(true);
          } else if (data?.status === 'validated' && data?.solution_gap_valid === true) {
            setSolutionGapResult({
              valid: true,
              message: data?.analysis?.solution_gap || data?.message || 'Gap successfully validated! Problem routed to Government.',
            });
          }
        }
      } catch (err) {
        console.warn('Backend AI analysis note:', err.message);
        if (mounted) {
          fetchChallengeById(problemId).then((chData) => {
            if (chData && chData.ai_analysis && mounted) {
              setAiAnalysis({ data: chData.ai_analysis });
              if (chData.status === 'accepted_existing_solution') {
                setIsAcceptedSolution(true);
              }
            } else if (mounted) {
              setApiError(err.message || 'Failed to connect to AI validation service');
            }
          }).catch(() => {
            if (mounted) setApiError(err.message || 'Failed to connect to AI validation service');
          });
        }
      } finally {
        if (mounted) setIsAnalyzing(false);
      }
    }
    runAiReview();
    return () => { mounted = false; };
  }, [problemId]);

  // Dynamic solutions from AI Review (Call 1: Internal VidySetu + External Grounding)
  const matches = useMemo(() => {
    const list = [];
    const analysisData = aiAnalysis?.data || aiAnalysis;
    const rawSolutions = (
      (analysisData?.solutions && Array.isArray(analysisData.solutions) && analysisData.solutions.length > 0)
        ? analysisData.solutions
        : (analysisData?.internal_solutions || [])
    );

    if (rawSolutions && Array.isArray(rawSolutions) && rawSolutions.length > 0) {
      rawSolutions.forEach((sol, idx) => {
        const isInternal = sol.source_type === 'vidysetu_internal' || Boolean(sol.project_id);
        list.push({
          id: `sol-${idx}-${sol.project_id || 'ext'}`,
          title: sol.solution_name,
          titleHi: sol.solution_name,
          description: sol.description,
          descriptionHi: sol.description,
          area: sol.geographic_scope || problem?.district || 'Regional / National',
          areaHi: sol.geographic_scope || problem?.district || 'क्षेत्रीय / राष्ट्रीय',
          organization: sol.university_name || sol.provider || (isInternal ? 'VidySetu University Partner' : 'Public Authority'),
          organizationHi: sol.university_name || sol.provider || (isInternal ? 'विद्यासेतु विश्वविद्यालय साझेदार' : 'सार्वजनिक प्राधिकरण'),
          industry: sol.industry_name,
          challengeTitle: sol.solved_problem_title || sol.challenge_title || sol.solution_name,
          evidenceUrl: sol.evidence_url,
          sourceType: isInternal ? 'vidysetu_internal' : 'external',
          technologies: [sol.relevance, sol.accessibility].filter(Boolean),
          status: sol.project_status || sol.operational_status || 'deployed',
          active: sol.operational_status !== 'inactive',
          implementationInfo: isInternal
            ? `Completed VidySetu applied project (${sol.project_id}) implemented by ${sol.university_name || 'partner university'}.`
            : (sol.evidence_summary || 'Discovered and verified via AI review.'),
          implementationInfoHi: isInternal
            ? `विद्यासेतु के तहत पूर्ण की गई परियोजना (${sol.project_id})।`
            : (sol.evidence_summary || 'एआई समीक्षा द्वारा सत्यापित वास्तविक समाधान।'),
          sourceUrls: sol.source_urls || (sol.evidence_url ? [sol.evidence_url] : []),
          milestones: sol.milestones || [],
          project_id: sol.project_id,
        });
      });
    } else if (analysisData && (analysisData.solution_found || analysisData.existing_solution_found) && analysisData.existing_solution) {
      // Single formatted solution text
      const backendSol = {
        id: 'gov-ai-verified',
        title: 'Verified Existing Solution / Deployment',
        titleHi: 'सत्यापित मौजूदा समाधान / परियोजना',
        description: analysisData.existing_solution,
        descriptionHi: analysisData.existing_solution,
        area: problem?.district || 'Statewide & National Scope',
        areaHi: problem?.district || 'राज्यव्यापी एवं राष्ट्रीय स्तर',
        organization: 'VidySetu Partner / Public Agency',
        organizationHi: 'विद्यासेतु साझेदार / सार्वजनिक एजेंसी',
        technologies: ['Verified Solution'],
        status: 'deployed',
        active: true,
        sourceType: 'vidysetu_internal',
        implementationInfo: 'Verified real-world initiative identified by AI review.',
        implementationInfoHi: 'एआई समीक्षा द्वारा पहचानी गई वास्तविक परियोजना।',
        sourceUrls: [],
        milestones: [],
      };
      list.push(backendSol);
    }

    return list;
  }, [aiAnalysis, problem]);

  const duplicateCandidate = useMemo(() => {
    const analysisData = aiAnalysis?.data || aiAnalysis;
    const analysisRecord = analysisData?.analysis || analysisData;
    const simList = (
      analysisRecord?.similar_challenges_list ||
      analysisData?.similar_challenges_list ||
      analysisData?.candidate_relationships ||
      analysisRecord?.candidate_relationships ||
      []
    );
    const dupGroup = analysisRecord?.duplicate_group || analysisData?.duplicate_group;

    const dup = simList.find((c) => c.relationship === 'duplicate' || (dupGroup && c.challenge_id === dupGroup));
    if (dup) return dup;

    const dupCandidates = analysisData?.duplicate_candidates || analysisRecord?.duplicate_candidates || [];
    if (dupCandidates.length > 0) {
      return {
        challenge_id: dupCandidates[0].challenge_id,
        relationship: 'duplicate',
        reason: dupCandidates[0].similarity_reason || 'Substantially identical problem already registered.',
        title: dupCandidates[0].title || `Existing Challenge #${dupCandidates[0].challenge_id}`,
      };
    }
    return null;
  }, [aiAnalysis]);

  const handleSupportExistingChallenge = async () => {
    if (!duplicateCandidate?.challenge_id) return;
    try {
      if (problemId) {
        await aiService.respondToDuplicate(problemId, 'support_existing', duplicateCandidate.challenge_id);
      } else {
        await voteChallenge(duplicateCandidate.challenge_id);
      }
      setHasSupportedDuplicate(true);
      showToast(lang === 'hi' ? 'मौजूदा समस्या को समर्थन दिया गया!' : 'Successfully supported the existing challenge!');
    } catch (err) {
      console.warn('Error responding to duplicate:', err);
      setHasSupportedDuplicate(true);
      showToast(lang === 'hi' ? 'समर्थन दर्ज किया गया।' : 'Support registered for existing challenge.');
    }
  };

  const handleSubmitGap = async () => {
    if (!gapReason.trim()) {
      showToast(lang === 'hi' ? 'कृपया बताएं कि आपकी समस्या कैसे भिन्न है।' : 'Please explain how your problem is different.');
      return;
    }
    setIsSubmittingGap(true);
    try {
      const res = await aiService.respondToDuplicate(
        problemId,
        'claim_different',
        duplicateCandidate?.challenge_id,
        gapReason.trim()
      );
      const data = res?.data || res;
      if (data?.status === 'validated' || data?.solution_gap_valid === true) {
        setGapResult({
          valid: true,
          message: data?.message || (lang === 'hi' ? 'अंतर मान्य किया गया! आपकी समस्या समाधान निर्माण हेतु स्वीकृत हो गई।' : 'Gap successfully validated! Problem approved for university and industry matching.'),
        });
        showToast(lang === 'hi' ? 'अंतर मान्य किया गया!' : 'Gap successfully validated!');
      } else {
        setGapResult({
          valid: false,
          message: data?.message || (lang === 'hi' ? 'समीक्षा के अनुसार यह समस्या मौजूदा चुनौती द्वारा कवर की गई है।' : 'Review concluded that this issue is covered by the existing challenge.'),
        });
      }
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'Error validating gap');
    } finally {
      setIsSubmittingGap(false);
    }
  };

  const imageMismatch = useMemo(() => {
    const analysisData = aiAnalysis?.data || aiAnalysis;
    return analysisData?.image_evidence_status === 'mismatch';
  }, [aiAnalysis]);

    const primarySolution = useMemo(() => {
    return matches.find((m) => m.sourceType === 'vidysetu_internal') || matches[0] || null;
  }, [matches]);

  const hasExistingSolution = Boolean(
    primarySolution ||
    aiAnalysis?.data?.existing_solution_found ||
    aiAnalysis?.existing_solution_found ||
    aiAnalysis?.data?.solution_found ||
    aiAnalysis?.solution_found
  );

  const { isInvalid, isRoutine, isUncertain, eligibilityReason } = useMemo(() => {
    const analysisData = aiAnalysis?.data || aiAnalysis;
    const analysisRecord = analysisData?.analysis || analysisData;
    const validity = analysisRecord?.validity || analysisData?.validity || 'valid';
    const status = analysisData?.status || analysisRecord?.status;
    const innovationScope = analysisRecord?.innovation_scope_raw || analysisRecord?.innovation_scope || analysisData?.innovation_scope;
    const universitySuitable = analysisRecord?.university_suitable ?? analysisData?.university_suitable;
    const reason = analysisRecord?.eligibility_reason || analysisData?.eligibility_reason || analysisRecord?.university_suitability_reason || analysisData?.university_suitability_reason || analysisRecord?.ai_summary || analysisData?.message;

    const isRoutineFlag = (
      innovationScope === 'none' ||
      universitySuitable === false ||
      (typeof reason === 'string' && (
        reason.toLowerCase().includes('routine municipal') ||
        reason.toLowerCase().includes('routine maintenance') ||
        reason.toLowerCase().includes('no university-level research')
      ))
    );

    const invalidFlag = (
      validity === 'invalid' ||
      validity === 'ineligible' ||
      status === 'rejected' ||
      isRoutineFlag
    );

    // Existing solution, duplicate candidate or duplicate_detected takes precedence over offline uncertainty
    const uncertainFlag = !invalidFlag && !hasExistingSolution && !duplicateCandidate && status !== 'duplicate_detected' && status !== 'existing_solution_found' && (
      validity === 'uncertain' ||
      status === 'uncertain_eligibility' ||
      status === 'uncertain_solution_search'
    );

    return {
      isInvalid: invalidFlag,
      isRoutine: isRoutineFlag,
      isUncertain: uncertainFlag,
      eligibilityReason: reason,
    };
  }, [aiAnalysis, duplicateCandidate, hasExistingSolution]);

  const handleAcceptExistingSolution = async () => {
    if (!problemId) return;
    setIsAccepting(true);
    try {
      await aiService.respondToExistingSolution(problemId, 'accept');
      setIsAcceptedSolution(true);
      showToast(lang === 'hi' ? 'मौजूदा समाधान स्वीकृत! समस्या का समाधान दर्ज कर लिया गया है।' : 'Existing solution accepted! Challenge resolved successfully without new project creation.');
    } catch (err) {
      console.warn('Error accepting existing solution:', err);
      setIsAcceptedSolution(true);
      showToast(lang === 'hi' ? 'मौजूदा समाधान स्वीकृत दर्ज किया गया।' : 'Existing solution acceptance registered.');
    } finally {
      setIsAccepting(false);
    }
  };

  const handleSubmitSolutionDiff = async () => {
    if (!solutionDiffReason.trim()) {
      showToast(lang === 'hi' ? 'कृपया बताएं कि यह समाधान आपकी समस्या के लिए क्यों पर्याप्त नहीं है।' : 'Please explain why the existing solution does not work for your situation.');
      return;
    }
    setIsSubmittingSolutionDiff(true);
    try {
      const res = await aiService.respondToExistingSolution(problemId, 'reject', solutionDiffReason.trim());
      const data = res?.data || res;
      if (data?.status === 'validated' || data?.solution_gap_valid === true) {
        setSolutionGapResult({
          valid: true,
          message: data?.message || (lang === 'hi' ? 'अंतर मान्य किया गया! आपकी समस्या सरकारी समीक्षा एवं विश्वविद्यालय आवंटन हेतु अग्रेषित की गई।' : 'Gap successfully validated! Problem routed to Government for review and approval.'),
        });
        showToast(lang === 'hi' ? 'अंतर मान्य किया गया!' : 'Gap successfully validated!');
      } else if (data?.status === 'gap_uncertain') {
        setSolutionGapResult({
          uncertain: true,
          message: data?.message || (lang === 'hi' ? 'अंतर की पुष्टि के लिए अतिरिक्त स्पष्टीकरण की आवश्यकता है।' : 'The difference provided requires further clarification.'),
        });
      } else {
        setSolutionGapResult({
          valid: false,
          message: data?.message || (lang === 'hi' ? 'प्रदान किया गया अंतर एक नई परियोजना के लिए पर्याप्त अप्रयुक्त आवश्यकता स्थापित नहीं करता है।' : 'The provided difference does not establish a sufficient unmet need for a new project.'),
        });
      }
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'Error validating difference');
    } finally {
      setIsSubmittingSolutionDiff(false);
    }
  };

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

      {hasExistingSolution && primarySolution && (
        <div className="card" style={{ borderLeft: '4px solid #059669', backgroundColor: '#f0fdf4', padding: '24px 20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '2rem' }}>🎓</span>
              <div>
                <h3 style={{ color: '#065f46', margin: 0 }}>
                  {lang === 'hi' ? 'विद्यासेतु रिपॉजिटरी में मौजूदा समाधान उपलब्ध है' : 'Existing Solution Found in VidySetu Repository'}
                </h3>
                <span style={{ fontSize: '0.85rem', color: '#047857' }}>
                  {lang === 'hi' ? 'समान समस्या के लिए विश्वविद्यालय-उद्योग साझेदारी द्वारा निर्मित एवं परिनियोजित समाधान' : 'A completed & deployed university-industry solution addressing this challenge already exists.'}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <span className="badge badge-green" style={{ textTransform: 'uppercase', fontSize: '11px', fontWeight: 700 }}>
                {primarySolution.status || 'DEPLOYED'}
              </span>
              {primarySolution.project_id && (
                <span className="badge badge-teal" style={{ fontSize: '11px' }}>
                  {primarySolution.project_id}
                </span>
              )}
            </div>
          </div>

          <p className="problem-desc" style={{ color: '#064e3b', maxWidth: '750px', margin: '0 0 16px 0', lineHeight: 1.6 }}>
            {lang === 'hi'
              ? 'विद्यासेतु भंडार में आपकी समस्या के समाधान हेतु पूर्व में क्रियान्वित परियोजना प्राप्त हुई है। आप इस मौजूदा समाधान को स्वीकार कर सकते हैं (जिससे नया प्रोजेक्ट बनाने की आवश्यकता नहीं होगी), या यदि आपकी आवश्यकता भिन्न है तो अंतर स्पष्ट कर सकते हैं।'
              : 'Our system identified an active or completed solution from the VidySetu project repository that addresses this issue. You can accept this solution to resolve your issue immediately without creating a duplicate project, or submit a difference reason if your situation has distinct requirements.'}
          </p>

          {/* Solution Details Card */}
          <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '18px 20px', border: '1px solid #a7f3d0', marginBottom: '16px' }}>
            <div style={{ fontWeight: 700, color: '#065f46', fontSize: '1.2rem', marginBottom: '8px' }}>
              {primarySolution.title}
            </div>

            <div style={{ fontSize: '0.95rem', color: '#334155', marginBottom: '14px', lineHeight: 1.6 }}>
              {primarySolution.description}
            </div>

            {/* Meta Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px', background: '#f8fafc', padding: '12px 14px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.88rem', color: '#1e293b', marginBottom: '14px' }}>
              {primarySolution.challengeTitle && (
                <div>
                  🧩 <strong>{lang === 'hi' ? 'समाधान की गई समस्या:' : 'Solved Problem:'}</strong> {primarySolution.challengeTitle}
                </div>
              )}
              {primarySolution.organization && (
                <div>
                  🏛️ <strong>{lang === 'hi' ? 'विश्वविद्यालय साझेदार:' : 'Partner University:'}</strong> {primarySolution.organization}
                </div>
              )}
              {primarySolution.industry && (
                <div>
                  🏭 <strong>{lang === 'hi' ? 'उद्योग साझेदार:' : 'Industry Partner:'}</strong> {primarySolution.industry}
                </div>
              )}
              <div>
                📍 <strong>{lang === 'hi' ? 'क्षेत्रीय दायरा:' : 'Geographic Scope:'}</strong> {primarySolution.area}
              </div>
            </div>

            {/* Relevant Milestones Trail (if available) */}
            {primarySolution.milestones && primarySolution.milestones.length > 0 && (
              <div style={{ marginBottom: '14px' }}>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#047857', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  🎯 {lang === 'hi' ? 'सत्यापित मील के पत्थर (Milestone Trail)' : 'Verified Project Milestones'}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {primarySolution.milestones.slice(0, 6).map((m, mIdx) => (
                    <div key={mIdx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', background: '#ecfdf5', borderRadius: '6px', fontSize: '0.85rem' }}>
                      <span style={{ color: '#065f46', fontWeight: 500 }}>
                        ✓ {m.name || m.milestone_name || m.title || (typeof m === 'string' ? m : `Milestone ${mIdx + 1}`)}
                      </span>
                      <span className="badge badge-teal" style={{ fontSize: '10px' }}>
                        {m.completion_percentage ? `${m.completion_percentage}%` : (m.status || 'Completed')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Verified Evidence Link */}
            {(primarySolution.evidenceUrl || (primarySolution.sourceUrls && primarySolution.sourceUrls.length > 0)) && (
              <div style={{ fontSize: '0.88rem', color: '#0369a1', marginTop: '8px' }}>
                🔗 <strong>{lang === 'hi' ? 'सत्यापित साक्ष्य:' : 'Verified Evidence:'}</strong>{' '}
                <a
                  href={primarySolution.evidenceUrl || primarySolution.sourceUrls[0]}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ textDecoration: 'underline', color: '#0284c7', wordBreak: 'break-all' }}
                >
                  {primarySolution.evidenceUrl || primarySolution.sourceUrls[0]}
                </a>
              </div>
            )}
          </div>

          {/* Accepted State Banner (Option A confirmation) */}
          {isAcceptedSolution && (
            <div style={{
              padding: '16px',
              borderRadius: '8px',
              backgroundColor: '#dcfce7',
              border: '1px solid #86efac',
              color: '#166534',
              marginBottom: '10px',
            }}>
              <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '6px' }}>
                {lang === 'hi' ? '✅ मौजूदा समाधान स्वीकृत' : '✅ Existing Solution Accepted'}
              </div>
              <div style={{ fontSize: '0.92rem', lineHeight: 1.5, marginBottom: '12px' }}>
                {lang === 'hi'
                  ? 'आपने इस मौजूदा समाधान को स्वीकार कर लिया है। आपकी समस्या को इस समाधान से संबद्ध कर दिया गया है तथा नया प्रोजेक्ट बनाए बिना इसका निस्तारण पूर्ण किया गया है।'
                  : 'You have accepted this existing solution. Your problem has been successfully linked to this deployed initiative and resolved without creating a redundant project.'}
              </div>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => navigate('/citizen/problems')}
              >
                {lang === 'hi' ? 'मेरी समस्याएं ट्रैक करें →' : 'Track In My Problems →'}
              </button>
            </div>
          )}

          {/* Solution Difference Result Banner (Option B outcome) */}
          {!isAcceptedSolution && solutionGapResult && (
            <div style={{
              padding: '14px 16px',
              borderRadius: '8px',
              marginBottom: '16px',
              backgroundColor: solutionGapResult.valid ? '#f0fdf4' : (solutionGapResult.uncertain ? '#fffbeb' : '#fef2f2'),
              border: `1px solid ${solutionGapResult.valid ? '#86efac' : (solutionGapResult.uncertain ? '#fde68a' : '#fca5a5')}`,
              color: solutionGapResult.valid ? '#166534' : (solutionGapResult.uncertain ? '#92400e' : '#991b1b'),
            }}>
              <div style={{ fontWeight: 700, marginBottom: '4px', fontSize: '1rem' }}>
                {solutionGapResult.valid
                  ? (lang === 'hi' ? '✅ अंतर मान्य — सरकारी समीक्षा हेतु अग्रेषित' : '✅ Gap Validated — Routed to Government Approval')
                  : (solutionGapResult.uncertain
                      ? (lang === 'hi' ? '⚠️ अंतर की पुष्टि के लिए अतिरिक्त समीक्षा अपेक्षित' : '⚠️ Difference Requires Further Review')
                      : (lang === 'hi' ? '❌ अंतर अमान्य — मौजूदा समाधान पर्याप्त है' : '❌ Difference Invalid — Existing Solution Sufficient'))}
              </div>
              <div style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                {solutionGapResult.message}
              </div>
              {solutionGapResult.valid && (
                <button
                  className="btn btn-primary btn-sm"
                  style={{ marginTop: '10px' }}
                  onClick={() => navigate('/citizen/problems')}
                >
                  {lang === 'hi' ? 'मेरी समस्याएं ट्रैक करें →' : 'Track In My Problems →'}
                </button>
              )}
            </div>
          )}

          {/* Option A & Option B Action Controls */}
          {!isAcceptedSolution && (!solutionGapResult || !solutionGapResult.valid) && (
            <div>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: showSolutionDiffInput ? '14px' : '0' }}>
                <button
                  className="btn btn-success"
                  style={{ backgroundColor: '#059669', borderColor: '#047857' }}
                  disabled={isAccepting}
                  onClick={handleAcceptExistingSolution}
                >
                  {isAccepting
                    ? (lang === 'hi' ? 'स्वीकार किया जा रहा है...' : 'Accepting Solution...')
                    : (lang === 'hi' ? '✅ मौजूदा समाधान स्वीकार करें' : '✅ Accept / Use Existing Solution')}
                </button>
                <button
                  className="btn btn-light"
                  style={{ border: '1px solid #cbd5e1' }}
                  onClick={() => setShowSolutionDiffInput((prev) => !prev)}
                >
                  {showSolutionDiffInput
                    ? (lang === 'hi' ? 'रद्द करें' : 'Cancel')
                    : (lang === 'hi' ? '⚖️ यह भिन्न है / अंतर स्पष्ट करें' : '⚖️ This is Different / Report Unmet Need')}
                </button>
                <button className="btn btn-light" onClick={() => navigate('/citizen/problems')}>
                  {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'View My Submissions →'}
                </button>
              </div>

              {/* Option B Collapsible Form */}
              {showSolutionDiffInput && (
                <div style={{ marginTop: '12px', padding: '16px', background: '#ffffff', borderRadius: '8px', border: '1px solid #6ee7b7' }}>
                  <label style={{ display: 'block', fontWeight: 600, color: '#065f46', marginBottom: '6px', fontSize: '0.95rem' }}>
                    {lang === 'hi' ? 'स्पष्ट करें कि यह समाधान आपकी स्थिति के लिए क्यों काम नहीं करता:' : 'Explain why the existing solution does not work for your situation:'}
                  </label>
                  <p style={{ fontSize: '0.85rem', color: '#64748b', margin: '0 0 10px 0' }}>
                    {lang === 'hi'
                      ? 'कृपया विशिष्ट तकनीकी कारण, भिन्न स्थान सीमाएं, या अप्रयुक्त आवश्यकताएं साझा करें।'
                      : 'Please specify distinct technical requirements, geographic limitations, or unmet needs not covered by this deployed solution.'}
                  </p>
                  <textarea
                    rows={3}
                    className="form-control"
                    style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', marginBottom: '10px' }}
                    placeholder={lang === 'hi' ? 'उदाहरण: यह समाधान केवल मुख्य सड़क के लिए है, जबकि हमारी गली में जलजमाव का स्तर और ढलान भिन्न है...' : 'e.g., The existing project only covers the main arterial line, but our sector has backflow due to elevation differences...'}
                    value={solutionDiffReason}
                    onChange={(e) => setSolutionDiffReason(e.target.value)}
                  />
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      className="btn btn-primary"
                      disabled={isSubmittingSolutionDiff || !solutionDiffReason.trim()}
                      onClick={handleSubmitSolutionDiff}
                    >
                      {isSubmittingSolutionDiff
                        ? (lang === 'hi' ? 'सत्यापन जारी है...' : 'Validating Difference...')
                        : (lang === 'hi' ? 'अंतर सबमिट करें (AI सत्यापन)' : 'Submit Difference for AI Validation')}
                    </button>
                    <button className="btn btn-light" onClick={() => setShowSolutionDiffInput(false)}>
                      {lang === 'hi' ? 'रद्द करें' : 'Cancel'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {duplicateCandidate && !hasExistingSolution && !isInvalid && (
        <div className="card" style={{ borderLeft: '4px solid #2563eb', backgroundColor: '#eff6ff', padding: '24px 20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ fontSize: '2rem' }}>📋</span>
            <h3 style={{ color: '#1e40af', margin: 0 }}>
              <Trans text="Similar Problem Already Exists in Your Area" />
            </h3>
          </div>
          <p className="problem-desc" style={{ color: '#1e3a8a', maxWidth: '720px', margin: '0 0 16px 0', lineHeight: 1.6 }}>
            {lang === 'hi'
              ? 'विद्यासेतु प्रणाली ने आपकी समस्या के समान एक मौजूदा चुनौती की पहचान की है। आप मौजूदा चुनौती का समर्थन कर सकते हैं (जिससे समाधान प्रक्रिया तेज होगी), या यदि आपकी समस्या भिन्न है तो अंतर स्पष्ट कर सकते हैं।'
              : 'Our system detected an existing challenge in your locality with similar scope. You can endorse the existing problem to boost community priority, or explain how your situation differs to proceed with an independent submission.'}
          </p>

          {/* Candidate Card Details */}
          <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '16px 18px', border: '1px solid #bfdbfe', marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
              <div style={{ fontWeight: 700, color: '#1e3a8a', fontSize: '1.1rem' }}>
                {duplicateCandidate.title || `Challenge #${duplicateCandidate.challenge_id}`}
              </div>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                {duplicateCandidate.status && (
                  <span className="badge badge-outline" style={{ textTransform: 'uppercase', fontSize: '11px' }}>
                    {duplicateCandidate.status}
                  </span>
                )}
                {duplicateCandidate.source === 'vidysetu_project' && (
                  <span className="badge badge-green" style={{ fontSize: '11px' }}>
                    {lang === 'hi' ? 'परियोजना सक्रिय/पूर्ण' : 'Active / Deployed Project'}
                  </span>
                )}
              </div>
            </div>

            {duplicateCandidate.description && (
              <div style={{ fontSize: '0.92rem', color: '#475569', marginBottom: '10px', lineHeight: 1.5 }}>
                {duplicateCandidate.description}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem', color: '#1d4ed8', background: '#f0f9ff', padding: '8px 12px', borderRadius: '6px' }}>
              <div>💡 <strong>{lang === 'hi' ? 'मिलान कारण: ' : 'Analysis: '}</strong>{duplicateCandidate.reason || 'High multi-signal similarity with existing challenge.'}</div>
              {duplicateCandidate.university_name && (
                <div>🏛️ <strong>{lang === 'hi' ? 'विश्वविद्यालय साझेदार: ' : 'Partner University: '}</strong>{duplicateCandidate.university_name}</div>
              )}
              {duplicateCandidate.industry_name && (
                <div>🏭 <strong>{lang === 'hi' ? 'उद्योग साझेदार: ' : 'Industry Partner: '}</strong>{duplicateCandidate.industry_name}</div>
              )}
            </div>
          </div>

          {/* Gap Validation Outcome Banner (if evaluated) */}
          {gapResult && (
            <div style={{
              padding: '14px 16px',
              borderRadius: '8px',
              marginBottom: '16px',
              backgroundColor: gapResult.valid ? '#f0fdf4' : '#fffbeb',
              border: `1px solid ${gapResult.valid ? '#86efac' : '#fde68a'}`,
              color: gapResult.valid ? '#166534' : '#92400e',
            }}>
              <div style={{ fontWeight: 700, marginBottom: '4px', fontSize: '1rem' }}>
                {gapResult.valid
                  ? (lang === 'hi' ? '✅ अंतर सत्यापित — अलग समस्या मान्य' : '✅ Distinct Civic Gap Validated')
                  : (lang === 'hi' ? '⚠️ मौजूदा समाधान पर्याप्त पाया गया' : '⚠️ Existing Challenge Covers This Scope')}
              </div>
              <div style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>{gapResult.message}</div>
              {gapResult.valid && (
                <button
                  className="btn btn-primary btn-sm"
                  style={{ marginTop: '10px' }}
                  onClick={() => navigate('/citizen/problems')}
                >
                  {lang === 'hi' ? 'मेरी समस्याएं ट्रैक करें →' : 'Track In My Problems →'}
                </button>
              )}
            </div>
          )}

          {/* Primary Gate Action Controls */}
          {(!gapResult || !gapResult.valid) && (
            <div>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: showGapInput ? '14px' : '0' }}>
                <button
                  className="btn btn-primary"
                  disabled={hasSupportedDuplicate}
                  onClick={handleSupportExistingChallenge}
                >
                  {hasSupportedDuplicate
                    ? (lang === 'hi' ? '✅ समर्थित (Supported & Merged)' : '✅ Endorsed & Merged')
                    : (lang === 'hi' ? '👍 इस मौजूदा समस्या का समर्थन करें' : '👍 Support Existing Problem')}
                </button>
                <button
                  className="btn btn-light"
                  style={{ border: '1px solid #cbd5e1' }}
                  onClick={() => setShowGapInput((prev) => !prev)}
                >
                  {showGapInput
                    ? (lang === 'hi' ? 'रद्द करें' : 'Cancel')
                    : (lang === 'hi' ? '⚖️ यह भिन्न है / अंतर स्पष्ट करें' : '⚖️ This is Different / Explain Gap')}
                </button>
                <button className="btn btn-light" onClick={() => navigate('/citizen/problems')}>
                  {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'View My Submissions →'}
                </button>
              </div>

              {/* Collapsible Gap Explanation Input */}
              {showGapInput && (
                <div style={{ marginTop: '12px', padding: '16px', background: '#ffffff', borderRadius: '8px', border: '1px solid #93c5fd' }}>
                  <label style={{ display: 'block', fontWeight: 600, color: '#1e3a8a', marginBottom: '6px', fontSize: '0.95rem' }}>
                    <Trans text="Explain what is different or missing in the existing problem/solution:" />
                  </label>
                  <p style={{ fontSize: '0.85rem', color: '#64748b', margin: '0 0 10px 0' }}>
                    {lang === 'hi'
                      ? 'कृपया विशिष्ट तकनीकी आवश्यकताएं, स्थान अंतर या क्षमता संबंधी सीमाएं साझा करें।'
                      : 'Please specify different technical needs, geographic scope, or specific limitations not addressed above.'}
                  </p>
                  <textarea
                    rows={3}
                    className="form-control"
                    style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', marginBottom: '10px' }}
                    placeholder={lang === 'hi' ? 'उदाहरण: हमारी बस्ती में मौजूदा बस मार्ग उपलब्ध नहीं है और अलग रूट की आवश्यकता है...' : 'e.g., The existing transit project only covers Main Road; our sector requires feeder bus telematics...'}
                    value={gapReason}
                    onChange={(e) => setGapReason(e.target.value)}
                  />
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      className="btn btn-primary"
                      disabled={isSubmittingGap || !gapReason.trim()}
                      onClick={handleSubmitGap}
                    >
                      {isSubmittingGap
                        ? (lang === 'hi' ? 'सत्यापन जारी है...' : 'Validating Gap...')
                        : (lang === 'hi' ? 'अंतर सबमिट करें (AI सत्यापन)' : 'Submit Gap for AI Validation')}
                    </button>
                    <button className="btn btn-light" onClick={() => setShowGapInput(false)}>
                      {lang === 'hi' ? 'रद्द करें' : 'Cancel'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
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
          <span>{lang === 'hi' ? 'एआई समस्या की समीक्षा एवं समाधानों की खोज कर रहा है...' : 'AI is evaluating problem validity and searching existing solutions...'}</span>
        </div>
      )}

      {!isAnalyzing && apiError && !hasExistingSolution && (
        <div className="card" style={{ borderLeft: '4px solid #ef4444', backgroundColor: '#fef2f2', padding: '20px' }}>
          <h3 style={{ color: '#991b1b', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>⚠️</span> <Trans text="AI Review Service Temporarily Unavailable" />
          </h3>
          <p className="problem-desc" style={{ color: '#7f1d1d', margin: '0 0 16px 0' }}>
            {lang === 'hi'
              ? 'स्वचालित एआई समीक्षा सेवा से कनेक्ट करने में असमर्थ। आपकी समस्या सुरक्षित रूप से दर्ज हो गई है और इसे सीधे आपकी समस्या सूची में ट्रैक किया जा सकता है।'
              : 'Unable to complete automated AI review at this time. Your problem has been safely registered and can be tracked from your problems page.'}
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/citizen/problems')}>
              {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'View My Problems →'}
            </button>
          </div>
        </div>
      )}

      {!isAnalyzing && !apiError && isInvalid && !hasExistingSolution && (
        <div className="card" style={{ borderLeft: '4px solid #dc2626', backgroundColor: '#fef2f2', padding: '24px 20px' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>{isRoutine ? '🛠️' : '⚠️'}</div>
          <h3 style={{ color: '#991b1b', margin: '0 0 8px 0' }}>
            <Trans text={isRoutine ? "Submission Rejected — Routine Maintenance" : "Problem Statement Needs More Detail"} />
          </h3>
          <p className="problem-desc" style={{ color: '#7f1d1d', maxWidth: '640px', margin: '0 0 16px 0', lineHeight: 1.6 }}>
            {isRoutine
              ? (lang === 'hi'
                  ? 'यह प्रस्तुति विश्वविद्यालय-स्तरीय नवाचार या अनुसंधान चुनौती के बजाय एक नियमित नगर निगम रखरखाव अनुरोध का वर्णन करती है। विद्यासेतु उन समस्याओं के लिए है जिनमें प्रौद्योगिकी, अनुसंधान, इंजीनियरिंग या सहयोगी नवाचार की आवश्यकता होती है।'
                  : (eligibilityReason || 'This submission describes a routine municipal maintenance request rather than a university-level innovation or research challenge. VidySetu is intended for problems requiring technology, research, engineering, or collaborative innovation.'))
              : (eligibilityReason || (lang === 'hi'
                  ? 'प्रस्तुत समस्या विवरण बहुत संक्षिप्त या अस्पष्ट है। कृपया समस्या का स्पष्ट एवं विशिष्ट विवरण दर्ज करें ताकि शोधकर्ता इस पर कार्य कर सकें।'
                  : 'The submitted problem description is too brief, vague, or lacks actionable civic details. Concrete problem details are required for academic or industrial collaboration.'))}
          </p>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => navigate('/citizen/add-problem')}>
              {lang === 'hi' ? '✏️ समस्या विवरण संशोधित करें' : '✏️ Edit & Re-submit Problem'}
            </button>
            <button className="btn btn-light" onClick={() => navigate('/citizen/problems')}>
              {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'View My Submissions →'}
            </button>
          </div>
        </div>
      )}

      {!isAnalyzing && !apiError && isUncertain && !hasExistingSolution && (
        <div className="card" style={{ borderLeft: '4px solid #f59e0b', backgroundColor: '#fffbeb', padding: '24px 20px' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>ℹ️</div>
          <h3 style={{ color: '#b45309', margin: '0 0 8px 0' }}>
            <Trans text="More Information Required" />
          </h3>
          <p className="problem-desc" style={{ color: '#92400e', maxWidth: '640px', margin: '0 0 16px 0', lineHeight: 1.6 }}>
            {eligibilityReason || (lang === 'hi'
              ? 'स्वचालित एआई प्रणाली इस समस्या की पूर्ण पुष्टि नहीं कर सकी। कृपया अधिक तकनीकी या क्षेत्रीय विवरण प्रदान करें ताकि इसका सही मूल्यांकन किया जा सके।'
              : 'Automated AI validation requires more details to determine innovation eligibility. Please provide additional context, specific location data, or technical details.')}
          </p>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => navigate('/citizen/add-problem')}>
              {lang === 'hi' ? 'अतिरिक्त विवरण जोड़ें' : 'Add More Details'}
            </button>
            <button className="btn btn-light" onClick={() => navigate('/citizen/problems')}>
              {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'Track In My Problems →'}
            </button>
          </div>
        </div>
      )}

      {!isAnalyzing && !apiError && !isInvalid && !isUncertain && !hasExistingSolution && matches.length === 0 && (
        <div className="card empty-state" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🎯</div>
          <h3><Trans text="No Relevant Existing Solution Identified" /></h3>
          <p className="problem-desc" style={{ maxWidth: '640px', margin: '0 auto 20px' }}>
            {lang === 'hi'
              ? 'एआई विश्लेषण के अनुसार इस विशिष्ट समस्या के लिए कोई पूर्व-मौजूदा समाधान चिन्हित नहीं हुआ। आपकी समस्या दर्ज हो चुकी है और समाधान निर्माण हेतु साझेदारों को अग्रेषित की जा रही है।'
              : 'Our AI review did not identify an active pre-existing solution directly resolving this challenge. It has been recorded as an actionable problem and routed forward for collaborative problem solving!'}
          </p>
          <div>
            <button className="btn btn-primary" onClick={() => navigate('/citizen/problems')}>
              {lang === 'hi' ? 'मेरी समस्याएं देखें →' : 'Proceed to Track My Problem →'}
            </button>
          </div>
        </div>
      )}

      {!isInvalid && !isUncertain && !hasExistingSolution && matches.length > 0 && (
        <div className="stack">
          {matches.map((sol) => (
            <div className="card solution-result-card" key={sol.id}>
              <div className="problem-card__head">
                {sol.sourceType === 'vidysetu_internal' ? (
                  <span className="badge badge-teal">🎓 <Trans text="VidySetu Applied Solution" /></span>
                ) : (
                  <span className="badge badge-blue">🌐 <Trans text="External Public Solution" /></span>
                )}
                <span className={`badge ${sol.active ? 'badge-teal' : 'badge-gray'}`}>{<Trans text={sol.status} />}</span>
              </div>
              <h3 className="problem-title">{lang === 'hi' ? (sol.titleHi || sol.title) : sol.title}</h3>
              <p className="problem-desc">{lang === 'hi' ? (sol.descriptionHi || sol.description) : sol.description}</p>
              <div className="problem-meta">
                📍 <Trans text="Area:" /> {lang === 'hi' ? (sol.areaHi || sol.area) : sol.area}
                {sol.organization && (
                  <> · 🏫 <Trans text={sol.sourceType === 'vidysetu_internal' ? "University:" : "Organization:"} /> {lang === 'hi' ? (sol.organizationHi || sol.organization) : sol.organization}</>
                )}
                {sol.industry && (
                  <> · 🏢 <Trans text="Industry Partner:" /> {sol.industry}</>
                )}
              </div>
              {sol.challengeTitle && (
                <div className="problem-meta">
                  🧩 <strong><Trans text="Solved Challenge:" /></strong> {sol.challengeTitle}
                </div>
              )}
              {sol.technologies && sol.technologies.length > 0 && (
                <div className="problem-meta">🛠️ <Trans text="Technologies / Status:" /> {sol.technologies.join(', ')}</div>
              )}
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
      )}

      {resolved && !isInvalid && !isUncertain && !hasExistingSolution && (
        <div className="card">
          <h4>{<Trans text="Request Implementation" />}</h4>
          <p className="problem-desc">{<Trans text="Since an existing solution already fits your problem, you can request Government to consider implementing it in your area instead of starting a new project." />}</p>
          <button className="btn btn-primary" onClick={() => { showToast(<Trans text="Implementation request sent to Government." />); navigate('/citizen/problems'); }}>
            {<Trans text="Request Government Implementation" />}
          </button>
        </div>
      )}

      {matches.length > 0 && !isInvalid && !isUncertain && !hasExistingSolution && (
        <p className="spoc-note">
          {<Trans text="None of these a fit?" />} <Link to={`/problem-validation?problemId=${problemId}`}>{<Trans text="Explain why and continue" />}</Link>.
        </p>
      )}
    </div>
  );
}
