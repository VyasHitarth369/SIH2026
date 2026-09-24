import Trans from '../../components/shared/Trans.jsx';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useProblems } from '../../context/ProblemsContext';
import { useToast } from '../../context/ToastContext';
import Milestones from '../../components/shared/Milestones.jsx';
import governmentService from '../../services/governmentService';

const priorityBadgeClass = { high: 'badge-coral', medium: 'badge-amber', resolved: 'badge-teal', new: 'badge-blue' };

function adaptGovProblem(gp) {
  const isRejected = ['rejected', 'no_university_assigned'].includes(gp.status);
  const isSolved =
    ['resolved', 'solved', 'completed', 'accepted_existing_solution', 'deployed'].includes(gp.status) ||
    ['deployed', 'solved', 'completed'].includes(gp.project_status) ||
    gp.current_milestone === 'Solution Deployed';
  const isRouted =
    !isSolved &&
    ['routed', 'university_selected', 'project_created', 'in_project', 'active', 'prototype', 'pilot'].includes(gp.status);

  return {
    id: gp.challenge_id,
    challenge_id: gp.challenge_id,
    title: { hi: gp.title, en: gp.title },
    desc: { hi: gp.description, en: gp.description },
    loc: gp.location && gp.location !== '-' ? gp.location : gp.city || gp.district || 'Jharkhand',
    city: gp.city,
    district: gp.district,
    status: gp.status || 'submitted',
    project_status: gp.project_status,
    project_id: gp.project_id,
    project_title: gp.project_title,
    current_milestone: gp.current_milestone || (isSolved ? 'Solution Deployed' : (gp.faculty_name ? 'Faculty Assigned' : 'University Allocated')),
    milestone_progress_pct: gp.milestone_progress_pct,
    submitted_by: gp.submitted_by,
    source: (gp.submitted_by || '').toLowerCase().includes('gov')
      ? 'government'
      : (gp.submitted_by || '').toLowerCase().includes('ind')
      ? 'industry'
      : 'citizen',
    category: gp.category || 'General Civic',
    domain: gp.category || 'General Civic',
    requiredTechnologies: gp.required_technologies ? gp.required_technologies.split(',').map((s) => s.trim()) : [],
    priorityLevel: gp.innovation_scope === 'high' ? 'high' : 'medium',
    aiPriority: (gp.innovation_scope || 'NORMAL').toUpperCase(),
    votes: 1,
    allocation: {
      status: isRejected ? 'rejected' : isSolved ? 'solved' : isRouted ? 'allocated' : 'not_started',
      allocatedTo: gp.university_name || null,
    },
    faculty: gp.faculty_name ? { name: gp.faculty_name } : null,
    faculty_name: gp.faculty_name,
    students: [],
    suggestedIndustries: gp.industry_name ? [gp.industry_name] : [],
    industry_name: gp.industry_name,
    submissionDate: gp.created_at ? gp.created_at.slice(0, 10) : '—',
    government_rejection_reason: gp.government_rejection_reason,
    government_reviewed_at: gp.government_reviewed_at,
    government_reviewed_by: gp.government_reviewed_by,
    university_rejections: gp.university_rejections || [],
    top_universities: gp.top_universities || gp.university_matches || [],
    top_industries: gp.top_industries || [],
    industry_matching_status: gp.industry_matching_status || 'Pending',
    raw: gp,
  };
}

function getWhyRecommended(u, rank, lang) {
  const isHi = lang === 'hi';
  const skills = Array.isArray(u.matched_skills) ? u.matched_skills.filter(Boolean) : [];
  const techs = Array.isArray(u.matched_technologies) ? u.matched_technologies.filter(Boolean) : [];
  const domains = Array.isArray(u.matched_domains) ? u.matched_domains.filter(Boolean) : [];
  const combined = [...new Set([...skills, ...techs])];
  const count = u.active_projects ?? 0;

  if (u.workload_advantage_applied) {
    if (combined.length > 0) {
      const topTokens = combined.slice(0, 2).join(', ');
      return isHi
        ? `${topTokens} में उपयुक्तता और उपलब्ध क्षमता (${count} सक्रिय परियोजनाएं) के कारण उच्च रैंक प्रदान की गई।`
        : `Ranked higher due to strong technical fit in ${topTokens} and available capacity (${count} active project${count === 1 ? '' : 's'}).`;
    }
    return isHi
      ? `मजबूत उपयुक्तता और उपलब्ध क्षमता (${count} सक्रिय परियोजनाएं) के कारण उच्च रैंक प्रदान की गई।`
      : `Ranked higher due to strong alignment and available capacity (${count} active project${count === 1 ? '' : 's'}).`;
  }

  if (rank === 1) {
    if (combined.length > 0) {
      const topTokens = combined.slice(0, 2).join(', ');
      return isHi
        ? `${count} सक्रिय परियोजनाओं के साथ ${topTokens} में मजबूत मिलान के आधार पर शीर्ष प्राथमिकता।`
        : `Top match based on strong alignment in ${topTokens} with ${count} active project${count === 1 ? '' : 's'}.`;
    }
    return isHi
      ? 'डोमेन विशेषज्ञता, तकनीकी क्षमताओं और विभाग संरेखण में समग्र शीर्ष मिलान।'
      : 'Top overall match across domain expertise, technical capabilities, and department alignment.';
  }

  if (combined.length > 0) {
    const topTokens = combined.slice(0, 2).join(', ');
    return isHi
      ? `${topTokens} में सिद्ध क्षमताओं और प्रासंगिक विशेषज्ञता के आधार पर अनुशंसित।`
      : `Recommended for proven capabilities in ${topTokens} and relevant expertise.`;
  }

  if (domains.length > 0) {
    const topDomains = domains.slice(0, 2).join(', ');
    return isHi
      ? `${topDomains} में प्रासंगिक डोमेन फोकस और संस्थागत अनुसंधान क्षमता पर आधारित मिलान।`
      : `Matched on relevant domain focus in ${topDomains} and institutional research capacity.`;
  }

  return isHi
    ? 'अंतःविषय क्षमताओं और संस्थागत अनुसंधान क्षमता पर आधारित मिलान।'
    : 'Matched on interdisciplinary capabilities and department expertise.';
}

export default function ActiveProblemsPage() {
  const { t, lang } = useLanguage();
  const { problems: fallbackProblems } = useProblems();
  const { showToast } = useToast();

  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({
    all: 0,
    pending: 0,
    allocated: 0,
    rejected: 0,
    solved: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [expandedMilestones, setExpandedMilestones] = useState(null);
  const [expandedTop5, setExpandedTop5] = useState(new Set());

  const toggleTop5 = (problemId) => {
    setExpandedTop5((prev) => {
      const next = new Set(prev);
      if (next.has(problemId)) {
        next.delete(problemId);
      } else {
        next.add(problemId);
      }
      return next;
    });
  };

  const [expandedTop5Ind, setExpandedTop5Ind] = useState(new Set());

  const toggleTop5Ind = (problemId) => {
    setExpandedTop5Ind((prev) => {
      const next = new Set(prev);
      if (next.has(problemId)) {
        next.delete(problemId);
      } else {
        next.add(problemId);
      }
      return next;
    });
  };

  // Reject Modal state
  const [rejectingProblem, setRejectingProblem] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  const loadProblems = useCallback(async (targetCategory = filter) => {
    setIsLoading(true);
    try {
      const res = await governmentService.fetchGovernmentProblems({
        category: targetCategory,
      });
      const data = Array.isArray(res) ? res : res?.data || res?.items || [];
      if (res?.counts) {
        setCounts(res.counts);
      }
      if (Array.isArray(data) && data.length > 0) {
        setItems(data.map(adaptGovProblem));
      } else if (!targetCategory || targetCategory === 'all') {
        if (fallbackProblems && fallbackProblems.length > 0) {
          setItems(fallbackProblems);
        } else {
          setItems([]);
        }
      } else {
        setItems([]);
      }
    } catch (err) {
      console.warn('Could not load authoritative government problems, using fallback:', err.message);
      if (fallbackProblems && fallbackProblems.length > 0) {
        setItems(fallbackProblems);
      }
    } finally {
      setIsLoading(false);
    }
  }, [filter, fallbackProblems]);

  useEffect(() => {
    loadProblems('all');
  }, [loadProblems]);

  const handleTabChange = (cat) => {
    setFilter(cat);
    loadProblems(cat);
  };

  const handleApprove = async (id) => {
    setIsSubmittingDecision(true);
    try {
      const res = await governmentService.approveProblem(id);
      showToast(lang === 'hi' ? 'समस्या स्वीकृत और शीर्ष विश्वविद्यालयों को प्रेषित की गई।' : 'Problem approved and routed to top matching universities.');
      await loadProblems(filter);
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'Failed to approve problem');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const openRejectModal = (problem) => {
    setRejectingProblem(problem);
    setRejectReason('');
  };

  const closeRejectModal = () => {
    setRejectingProblem(null);
    setRejectReason('');
  };

  const handleConfirmReject = async () => {
    const trimmed = rejectReason.trim();
    if (!trimmed) {
      showToast(lang === 'hi' ? 'अस्वीकृति का कारण अनिवार्य है।' : 'Rejection reason is mandatory.');
      return;
    }
    if (!rejectingProblem) return;

    setIsSubmittingDecision(true);
    try {
      const res = await governmentService.rejectProblem(rejectingProblem.id, trimmed);
      showToast(lang === 'hi' ? 'समस्या आधिकारिक कारण के साथ अस्वीकृत कर दी गई।' : 'Problem declined with recorded reason.');
      closeRejectModal();
      await loadProblems(filter);
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'Failed to reject problem');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const filtered = useMemo(() => {
    if (filter === 'all') return items;
    return items.filter((p) => {
      const st = p.status || p.raw?.status;
      const isSolved =
        ['resolved', 'solved', 'completed', 'accepted_existing_solution', 'deployed'].includes(st) ||
        ['deployed', 'solved', 'completed'].includes(p.project_status) ||
        p.current_milestone === 'Solution Deployed';

      if (filter === 'pending') {
        return ['submitted', 'validated', 'under_review', 'uncertain_eligibility', 'existing_solution_found', 'ineligible_gap'].includes(st);
      }
      if (filter === 'allocated') {
        return (
          !isSolved &&
          ['routed', 'university_selected', 'project_created', 'in_project', 'active', 'prototype', 'pilot'].includes(st)
        );
      }
      if (filter === 'rejected') {
        return ['rejected', 'no_university_assigned'].includes(st);
      }
      if (filter === 'solved') {
        return isSolved;
      }
      return true;
    });
  }, [items, filter]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="Active Problems" />}</h1>
          <p>{<Trans text="Government Authority Review & Problem Lifecycle Monitoring." />}</p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          <div className={`filter-tab${filter === 'all' ? ' active' : ''}`} onClick={() => handleTabChange('all')}>
            {t.filterAll} ({counts.all})
          </div>
          <div className={`filter-tab${filter === 'pending' ? ' active' : ''}`} onClick={() => handleTabChange('pending')}>
            {t.filterPending || 'Pending Review'} ({counts.pending})
          </div>
          <div className={`filter-tab${filter === 'allocated' ? ' active' : ''}`} onClick={() => handleTabChange('allocated')}>
            {lang === 'hi' ? 'स्वीकृत और अग्रेषित' : 'Approved & Routed'} ({counts.allocated})
          </div>
          <div className={`filter-tab${filter === 'rejected' ? ' active' : ''}`} onClick={() => handleTabChange('rejected')}>
            {lang === 'hi' ? 'अस्वीकृत' : 'Rejected'} ({counts.rejected})
          </div>
          <div className={`filter-tab${filter === 'solved' ? ' active' : ''}`} onClick={() => handleTabChange('solved')}>
            {t.filterHistory || 'Solved'} ({counts.solved})
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
          <span style={{ fontSize: '2rem', display: 'block', marginBottom: 8 }}>⏳</span>
          {lang === 'hi' ? 'समस्याएं लोड हो रही हैं…' : 'Loading monitored problems…'}
        </div>
      ) : (
        filtered.map((p) => {
          const st = p.status || p.raw?.status;
          const isSolved =
            ['resolved', 'solved', 'completed', 'accepted_existing_solution', 'deployed'].includes(st) ||
            ['deployed', 'solved', 'completed'].includes(p.project_status) ||
            p.current_milestone === 'Solution Deployed';
          const isApprovedRouted =
            !isSolved &&
            ['routed', 'university_selected', 'project_created', 'in_project', 'active', 'prototype', 'pilot'].includes(st);
          const isPending = ['submitted', 'validated', 'under_review', 'uncertain_eligibility', 'existing_solution_found', 'ineligible_gap'].includes(st);
          const isRejected = ['rejected', 'no_university_assigned'].includes(st);

          return (
            <div className="card" key={p.id}>
              <div className="gov-card__head">
                <span className="badge badge-violet">ID: #CH-JH-{p.id}</span>
                {p.source === 'government' ? (
                  <span className="badge badge-violet">{t.govtProblem || '🏛️ Government Problem'}</span>
                ) : p.source === 'industry' ? (
                  <span className="badge badge-teal">{t.indProblem || '🏢 Industry Problem'}</span>
                ) : (
                  <span className="badge badge-gray">{t.citProblem || '👨‍🌾 Citizen Problem'}</span>
                )}
                <span className={`badge ${priorityBadgeClass[p.priorityLevel] || 'badge-blue'}`}>
                  {t.aiPriority}: {<Trans text={p.aiPriority} />}
                </span>

                {/* Authoritative Status Badge */}
                {isPending && (
                  <span className="badge badge-amber">
                    ⏳ {lang === 'hi' ? 'सरकारी समीक्षा लंबित' : 'Pending Government Review'}
                  </span>
                )}
                {isApprovedRouted && (
                  <span className="badge badge-teal">
                    ✅ {lang === 'hi' ? 'स्वीकृत एवं विश्वविद्यालयों को अग्रेषित' : 'Approved & Routed to Universities'}
                  </span>
                )}
                {isRejected && (
                  <span className="badge badge-coral">
                    ❌ {lang === 'hi' ? 'अस्वीकृत' : 'Rejected by Government'}
                  </span>
                )}
                {isSolved && (
                  <span className="badge badge-teal">
                    🏆 {lang === 'hi' ? 'समाधान पूर्ण' : 'Solved'}
                  </span>
                )}
              </div>

              <h3 className="problem-title">{p.title[lang] || p.title.hi || p.title.en}</h3>
              <p className="problem-desc">{p.desc[lang] || p.desc.hi || p.desc.en}</p>

              <div className="gov-card__details">
                <div>📍 <strong>{t.location}:</strong> {p.loc}</div>
                <div>🏷️ <strong>{<Trans text="Domain:" />}</strong> {<Trans text={p.domain || p.category} />}</div>
                <div>💡 <strong>{<Trans text="Required Technologies:" />}</strong> {(p.requiredTechnologies || []).join(', ') || '—'}</div>
                <div>👍 <strong>{t.citizenVotes}:</strong> {p.votes}</div>
                <div>🏫 <strong>{<Trans text="University:" />}</strong> {p.allocation.allocatedTo ? <Trans text={p.allocation.allocatedTo} /> : <Trans text="Not yet allocated" />}</div>
                <div>👨‍🏫 <strong>{<Trans text="Faculty:" />}</strong> {p.faculty?.name || p.faculty_name || '—'}</div>
                <div>🏢 <strong>{<Trans text="Suggested Industry:" />}</strong> {(p.suggestedIndustries || []).join(', ') || p.industry_name || '—'}</div>
                <div>📅 <strong>{<Trans text="Submitted:" />}</strong> {p.submissionDate}</div>
              </div>

              {/* AI-Ranked Top 5 Universities (Read-Only) */}
              {p.top_universities && p.top_universities.length > 0 ? (
                (() => {
                  const topUnis = p.top_universities.slice(0, 5);
                  const isExpanded = expandedTop5.has(p.id);
                  return (
                    <div style={{ marginTop: 14 }}>
                      <div
                        role="button"
                        tabIndex={0}
                        onClick={() => toggleTop5(p.id)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTop5(p.id); } }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '11px 14px',
                          background: isExpanded ? '#f1f5f9' : '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: isExpanded ? '8px 8px 0 0' : 8,
                          cursor: 'pointer',
                          userSelect: 'none',
                          transition: 'background 0.15s ease',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontSize: 16 }}>🏛️</span>
                          <strong style={{ fontSize: 13, color: '#1e293b' }}>
                            {lang === 'hi' ? 'एआई-रैंक शीर्ष 5 विश्वविद्यालय' : 'AI-Ranked Top 5 Universities'}
                          </strong>
                          <span style={{ fontSize: 11, fontWeight: 500, color: '#64748b', background: '#e2e8f0', padding: '2px 8px', borderRadius: 12 }}>
                            {topUnis.length} {lang === 'hi' ? 'सिफारिशें • सरकारी दृश्य • केवल पढ़ने के लिए' : 'recommendations • Government View • Read Only'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#2563eb' }}>
                          <span>
                            {isExpanded
                              ? (lang === 'hi' ? '▲ शीर्ष 5 छिपाएं' : '▲ Hide Top 5')
                              : (lang === 'hi' ? '▼ शीर्ष 5 देखें' : '▼ View Top 5')}
                          </span>
                        </div>
                      </div>

                      {isExpanded && (
                        <div style={{
                          padding: '14px 16px',
                          background: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderTop: 'none',
                          borderRadius: '0 0 8px 8px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 12,
                        }}>
                          {topUnis.map((u, uIdx) => {
                            const rank = u.rank || (uIdx + 1);
                            const score = Math.round(u.match_score ?? u.score ?? 0);
                            const activeCount = u.active_projects ?? 0;
                            const isWorkloadBalanced = Boolean(u.workload_advantage_applied);
                            const status = (u.status || 'recommended').toLowerCase();
                            const statusConfig = {
                              accepted: { bg: '#dcfce7', text: '#15803d', labelEn: 'Accepted', labelHi: 'स्वीकृत' },
                              declined: { bg: '#fee2e2', text: '#b91c1c', labelEn: 'Declined', labelHi: 'अस्वीकृत' },
                              rejected: { bg: '#fee2e2', text: '#b91c1c', labelEn: 'Declined', labelHi: 'अस्वीकृत' },
                              selected: { bg: '#e0e7ff', text: '#4338ca', labelEn: 'Selected', labelHi: 'चयनित' },
                              pending: { bg: '#fef3c7', text: '#b45309', labelEn: 'Pending Review', labelHi: 'समीक्षाधीन' },
                              pending_review: { bg: '#fef3c7', text: '#b45309', labelEn: 'Pending Review', labelHi: 'समीक्षाधीन' },
                              recommended: { bg: '#eff6ff', text: '#1d4ed8', labelEn: 'Recommended', labelHi: 'सिफारिश की गई' },
                            }[status] || { bg: '#eff6ff', text: '#1d4ed8', labelEn: 'Recommended', labelHi: 'सिफारिश की गई' };

                            const rankBadgeStyle = rank === 1
                              ? { background: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' }
                              : rank === 2
                              ? { background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1' }
                              : rank === 3
                              ? { background: '#ffedd5', color: '#9a3412', border: '1px solid #fdba74' }
                              : { background: '#f8fafc', color: '#64748b', border: '1px solid #e2e8f0' };

                            const skillsStr = Array.isArray(u.matched_skills) && u.matched_skills.length > 0 ? u.matched_skills.join(', ') : '';
                            const techsStr = Array.isArray(u.matched_technologies) && u.matched_technologies.length > 0 ? u.matched_technologies.join(', ') : '';
                            const domainsStr = Array.isArray(u.matched_domains) && u.matched_domains.length > 0 ? u.matched_domains.join(', ') : (u.domain || '');
                            const whyRecommended = getWhyRecommended(u, rank, lang);

                            return (
                              <div
                                key={u.university_id || uIdx}
                                style={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                  padding: '12px 14px',
                                  background: '#ffffff',
                                  border: '1px solid #e2e8f0',
                                  borderRadius: 8,
                                  gap: 10,
                                }}
                              >
                                {/* Header row */}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <span style={{
                                      width: 26,
                                      height: 26,
                                      borderRadius: '50%',
                                      ...rankBadgeStyle,
                                      fontWeight: 700,
                                      fontSize: 12,
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                    }}>
                                      #{rank}
                                    </span>
                                    <strong style={{ fontSize: 14, color: '#1e293b' }}>
                                      {u.university_name || u.name || 'University'}
                                    </strong>
                                  </div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{
                                      fontSize: 12,
                                      fontWeight: 600,
                                      color: score >= 70 ? '#15803d' : '#0369a1',
                                      background: score >= 70 ? '#f0fdf4' : '#f0f9ff',
                                      padding: '2px 8px',
                                      borderRadius: 12,
                                      border: `1px solid ${score >= 70 ? '#bbf7d0' : '#bae6fd'}`,
                                    }}>
                                      {score}% {lang === 'hi' ? 'मैच' : 'Match'}
                                    </span>
                                    <span style={{
                                      fontSize: 11,
                                      padding: '2px 8px',
                                      borderRadius: 12,
                                      background: statusConfig.bg,
                                      color: statusConfig.text,
                                      fontWeight: 600,
                                    }}>
                                      {lang === 'hi' ? statusConfig.labelHi : statusConfig.labelEn}
                                    </span>
                                  </div>
                                </div>

                                {/* Structured 4-item Metadata Grid */}
                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                                  gap: '10px 14px',
                                  background: '#f8fafc',
                                  padding: '10px 12px',
                                  borderRadius: 6,
                                  fontSize: 12,
                                }}>
                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'सक्रिय परियोजनाएं' : 'Active Projects'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 600 }}>
                                      {activeCount} {activeCount === 1 ? (lang === 'hi' ? 'परियोजना' : 'project') : (lang === 'hi' ? 'परियोजनाएं' : 'projects')}
                                      {isWorkloadBalanced && (
                                        <span style={{ marginLeft: 6, fontSize: 11, color: '#b45309', background: '#fef3c7', padding: '1px 6px', borderRadius: 4, fontWeight: 500 }}>
                                          ⚖️ {lang === 'hi' ? 'कार्यभार संतुलित' : 'Workload-balanced'}
                                        </span>
                                      )}
                                    </div>
                                  </div>

                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'मिलान कौशल' : 'Matching Skills'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 500 }}>
                                      {skillsStr || (lang === 'hi' ? 'सामान्य संरेखण' : 'General alignment')}
                                    </div>
                                  </div>

                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'मिलान प्रौद्योगिकियां' : 'Matching Technologies'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 500 }}>
                                      {techsStr || (lang === 'hi' ? 'मानक स्टैक' : 'Standard stack')}
                                    </div>
                                  </div>

                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'प्रासंगिक क्षेत्र' : 'Relevant Areas'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 500 }}>
                                      {domainsStr || (lang === 'hi' ? 'अंतःविषय' : 'Interdisciplinary')}
                                    </div>
                                  </div>
                                </div>

                                {/* Workload balancing transparency notice (if advantage applied) */}
                                {isWorkloadBalanced && (
                                  <div style={{ fontSize: 11, color: '#92400e', background: '#fef3c7', border: '1px solid #fde68a', padding: '5px 10px', borderRadius: 5, fontWeight: 500 }}>
                                    ⚖️ {lang === 'hi' ? 'कार्यभार संतुलित — कम सक्रिय परियोजनाओं को प्राथमिकता दी गई' : 'Workload-balanced — Lower active workload preference applied'}
                                  </div>
                                )}

                                {/* Why Recommended line */}
                                <div style={{ fontSize: 12, color: '#334155', background: '#f1f5f9', padding: '6px 10px', borderRadius: 5, lineHeight: 1.4 }}>
                                  <strong>{lang === 'hi' ? 'सिफारिश का कारण: ' : 'Why Recommended: '}</strong>
                                  {whyRecommended}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })()
              ) : isApprovedRouted ? (
                <div style={{ marginTop: 14, padding: '12px 16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13, color: '#64748b' }}>
                  ℹ️ {lang === 'hi' ? 'विश्वविद्यालय मिलान निर्धारित — सिफारिशें शीघ्र ही दिखाई देंगी।' : 'University matching scheduled — Recommendations will appear shortly.'}
                </div>
              ) : null}

              {/* AI-Ranked Top 5 Recommended Industries Collapsible Panel */}
              {Array.isArray(p.top_industries) && p.top_industries.length > 0 && (
                (() => {
                  const topInds = p.top_industries;
                  const isExpandedInd = expandedTop5Ind.has(p.id);
                  const indTimelineStatus = p.industry_matching_status || 'Pending';
                  const timelineStatusStyle = {
                    Accepted: { bg: '#dcfce7', text: '#15803d', border: '#86efac' },
                    Sent: { bg: '#e0e7ff', text: '#4338ca', border: '#c7d2fe' },
                    Rejected: { bg: '#fee2e2', text: '#b91c1c', border: '#fca5a5' },
                    Generated: { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
                    Pending: { bg: '#fef3c7', text: '#b45309', border: '#fde68a' },
                  }[indTimelineStatus] || { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1' };

                  return (
                    <div style={{ marginTop: 10, width: '100%' }}>
                      <div
                        onClick={() => toggleTop5Ind(p.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 14px',
                          background: isExpandedInd ? '#f8fafc' : '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: isExpandedInd ? '8px 8px 0 0' : 8,
                          cursor: 'pointer',
                          userSelect: 'none',
                          transition: 'background-color 0.15s ease',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>
                            🏭 {lang === 'hi' ? 'शीर्ष 5 अनुशंसित उद्योग' : 'Top 5 Recommended Industries'}
                          </span>
                          <span style={{
                            fontSize: 11,
                            padding: '2px 8px',
                            borderRadius: 12,
                            background: timelineStatusStyle.bg,
                            color: timelineStatusStyle.text,
                            border: `1px solid ${timelineStatusStyle.border}`,
                            fontWeight: 600,
                          }}>
                            {lang === 'hi' ? `स्थिति: ${indTimelineStatus}` : `Status: ${indTimelineStatus}`}
                          </span>
                          <span style={{ fontSize: 11, color: '#64748b' }}>
                            {topInds.length} {lang === 'hi' ? 'सिफारिशें • सरकारी दृश्य • केवल पढ़ने के लिए' : 'recommendations • Government View • Read Only'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#2563eb' }}>
                          <span>
                            {isExpandedInd
                              ? (lang === 'hi' ? '▲ शीर्ष 5 छिपाएं' : '▲ Hide Top 5')
                              : (lang === 'hi' ? '▼ शीर्ष 5 देखें' : '▼ View Top 5')}
                          </span>
                        </div>
                      </div>

                      {isExpandedInd && (
                        <div style={{
                          padding: '14px 16px',
                          background: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderTop: 'none',
                          borderRadius: '0 0 8px 8px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 12,
                        }}>
                          {topInds.map((ind, iIdx) => {
                            const rank = ind.rank || (iIdx + 1);
                            const score = Math.round(ind.match_score ?? ind.score ?? 0);
                            const indStatus = (ind.status || 'recommended').toLowerCase();
                            const indStatusConfig = {
                              accepted: { bg: '#dcfce7', text: '#15803d', labelEn: 'Accepted', labelHi: 'स्वीकृत' },
                              declined: { bg: '#fee2e2', text: '#b91c1c', labelEn: 'Declined', labelHi: 'अस्वीकृत' },
                              rejected: { bg: '#fee2e2', text: '#b91c1c', labelEn: 'Declined', labelHi: 'अस्वीकृत' },
                              sent: { bg: '#e0e7ff', text: '#4338ca', labelEn: 'Invitation Sent', labelHi: 'निमंत्रण भेजा गया' },
                              invited: { bg: '#e0e7ff', text: '#4338ca', labelEn: 'Invitation Sent', labelHi: 'निमंत्रण भेजा गया' },
                              recommended: { bg: '#eff6ff', text: '#1d4ed8', labelEn: 'Recommended', labelHi: 'सिफारिश की गई' },
                            }[indStatus] || { bg: '#eff6ff', text: '#1d4ed8', labelEn: 'Recommended', labelHi: 'सिफारिश की गई' };

                            const rankBadgeStyle = rank === 1
                              ? { background: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' }
                              : rank === 2
                              ? { background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1' }
                              : rank === 3
                              ? { background: '#ffedd5', color: '#9a3412', border: '1px solid #fdba74' }
                              : { background: '#f8fafc', color: '#64748b', border: '1px solid #e2e8f0' };

                            const skillsStr = Array.isArray(ind.matched_skills) && ind.matched_skills.length > 0 ? ind.matched_skills.join(', ') : '';
                            const techsStr = Array.isArray(ind.matched_technologies) && ind.matched_technologies.length > 0 ? ind.matched_technologies.join(', ') : '';

                            return (
                              <div
                                key={ind.industry_id || iIdx}
                                style={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                  padding: '12px 14px',
                                  background: '#ffffff',
                                  border: '1px solid #e2e8f0',
                                  borderRadius: 8,
                                  gap: 10,
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <span style={{
                                      width: 26,
                                      height: 26,
                                      borderRadius: '50%',
                                      ...rankBadgeStyle,
                                      fontWeight: 700,
                                      fontSize: 12,
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                    }}>
                                      #{rank}
                                    </span>
                                    <div>
                                      <strong style={{ fontSize: 14, color: '#1e293b' }}>
                                        {ind.industry_name || 'Industry Partner'}
                                      </strong>
                                      {ind.sector && (
                                        <span style={{ marginLeft: 8, fontSize: 12, color: '#64748b' }}>
                                          ({ind.sector})
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{
                                      fontSize: 12,
                                      fontWeight: 600,
                                      color: score >= 70 ? '#15803d' : '#0369a1',
                                      background: score >= 70 ? '#f0fdf4' : '#f0f9ff',
                                      padding: '2px 8px',
                                      borderRadius: 12,
                                      border: `1px solid ${score >= 70 ? '#bbf7d0' : '#bae6fd'}`,
                                    }}>
                                      {score}% {lang === 'hi' ? 'मैच' : 'Match'}
                                    </span>
                                    <span style={{
                                      fontSize: 11,
                                      padding: '2px 8px',
                                      borderRadius: 12,
                                      background: indStatusConfig.bg,
                                      color: indStatusConfig.text,
                                      fontWeight: 600,
                                    }}>
                                      {lang === 'hi' ? indStatusConfig.labelHi : indStatusConfig.labelEn}
                                    </span>
                                  </div>
                                </div>

                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                                  gap: '10px 14px',
                                  background: '#f8fafc',
                                  padding: '10px 12px',
                                  borderRadius: 6,
                                  fontSize: 12,
                                }}>
                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'प्रासंगिक डोमेन / क्षेत्र' : 'Domain / Sector'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 600 }}>
                                      {ind.domain || ind.sector || (lang === 'hi' ? 'उद्योग' : 'Industry')}
                                    </div>
                                  </div>
                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'संरेखित विशेषज्ञता' : 'Specialization'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 500 }}>
                                      {skillsStr || (lang === 'hi' ? 'डोमेन संरेखण' : 'Domain alignment')}
                                    </div>
                                  </div>
                                  <div>
                                    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: 2 }}>
                                      {lang === 'hi' ? 'संरेखित प्रौद्योगिकियां' : 'Technologies'}
                                    </div>
                                    <div style={{ color: '#1e293b', fontWeight: 500 }}>
                                      {techsStr || (lang === 'hi' ? 'लागू प्रौद्योगिकी स्टैक' : 'Applied Tech Stack')}
                                    </div>
                                  </div>
                                </div>

                                {ind.match_reason && (
                                  <div style={{ fontSize: 12, color: '#334155', background: '#f1f5f9', padding: '6px 10px', borderRadius: 5, lineHeight: 1.4 }}>
                                    <strong>{lang === 'hi' ? 'सिफारिश का कारण: ' : 'Why Recommended: '}</strong>
                                    {ind.match_reason}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })()
              )}

              {/* Government Rejection Reason Display */}
              {isRejected && (
                <div style={{ marginTop: 12, padding: '12px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8 }}>
                  <div style={{ fontWeight: 600, color: '#991b1b', marginBottom: 4 }}>
                    🚫 <Trans text="Government Rejection Reason:" />
                  </div>
                  <div style={{ fontSize: 13, color: '#7f1d1d' }}>
                    {p.government_rejection_reason || <Trans text="Declined by government authority." />}
                  </div>
                  {p.government_reviewed_at && (
                    <div style={{ fontSize: 11, color: '#991b1b', marginTop: 4 }}>
                      {new Date(p.government_reviewed_at).toLocaleString()}
                    </div>
                  )}
                </div>
              )}

              {/* University Rejection Feedback (if any university SPOC rejected) */}
              {p.university_rejections && p.university_rejections.length > 0 && (
                <div style={{ marginTop: 12, padding: '12px 14px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8 }}>
                  <div style={{ fontWeight: 600, color: '#92400e', marginBottom: 6 }}>
                    ⚠️ <Trans text="University Rejection Feedback:" />
                  </div>
                  {p.university_rejections.map((rej, idx) => (
                    <div key={idx} style={{ fontSize: 13, color: '#78350f', marginBottom: 4 }}>
                      <strong>{rej.university_name || rej.university_id}:</strong> {rej.rejection_reason}
                      {rej.responded_at && (
                        <span style={{ fontSize: 11, color: '#92400e', marginLeft: 6 }}>
                          ({new Date(rej.responded_at).toLocaleDateString()})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="proposal-card__actions" style={{ marginTop: 14, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                {/* Government Gate: Approve & Reject buttons ONLY for pending challenges */}
                {isPending && (
                  <>
                    <button
                      className="btn btn-success btn-sm"
                      disabled={isSubmittingDecision}
                      onClick={() => handleApprove(p.id)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                    >
                      ✓ {lang === 'hi' ? 'स्वीकृत करें एवं शीर्ष विश्वविद्यालयों को भेजें' : 'Approve & Route to Universities'}
                    </button>
                    <button
                      className="btn btn-outline-danger btn-sm"
                      disabled={isSubmittingDecision}
                      onClick={() => openRejectModal(p)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        borderColor: '#dc2626',
                        color: '#dc2626',
                        background: 'transparent',
                        padding: '6px 12px',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontWeight: 500,
                      }}
                    >
                      ✕ {lang === 'hi' ? 'अस्वीकृत करें' : 'Decline Problem'}
                    </button>
                  </>
                )}

                <button
                  className="btn btn-light btn-sm"
                  onClick={() => setExpandedMilestones(expandedMilestones === p.id ? null : p.id)}
                >
                  {expandedMilestones === p.id ? <Trans text="Hide Milestones" /> : <Trans text="View Milestones" />}
                </button>
              </div>

              {expandedMilestones === p.id && <Milestones problem={p} />}
            </div>
          );
        })
      )}

      {filtered.length === 0 && !isLoading && (
        <div className="card">{<Trans text="No problems match this filter." />}</div>
      )}

      {/* Mandatory Rejection Reason Modal */}
      {rejectingProblem && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 16,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 520,
              width: '100%',
              backgroundColor: '#ffffff',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            }}
          >
            <h3 style={{ margin: '0 0 8px 0', color: '#991b1b', display: 'flex', alignItems: 'center', gap: 8 }}>
              🚫 <Trans text="Decline Problem Statement" />
            </h3>
            <p style={{ fontSize: 14, color: '#4b5563', margin: '0 0 16px 0' }}>
              <Trans text="Please state the official reason for declining this problem statement. This explanation will be permanently recorded and visible to the submitting citizen and system audit." />
            </p>

            <div style={{ marginBottom: 12, fontSize: 13, color: '#1f2937' }}>
              <strong><Trans text="Problem:" /></strong> {rejectingProblem.title[lang] || rejectingProblem.title.hi || rejectingProblem.title.en}
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                <Trans text="Rejection Reason (Mandatory):" />
              </label>
              <textarea
                rows={4}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder={lang === 'hi' ? 'अस्वीकृति का स्पष्ट कारण दर्ज करें...' : 'Enter clear justification for declining this problem statement...'}
                style={{
                  width: '100%',
                  padding: 10,
                  borderRadius: 6,
                  border: '1px solid #d1d5db',
                  fontSize: 14,
                  fontFamily: 'inherit',
                  resize: 'vertical',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                className="btn btn-light"
                onClick={closeRejectModal}
                disabled={isSubmittingDecision}
              >
                <Trans text="Cancel" />
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmReject}
                disabled={isSubmittingDecision || !rejectReason.trim()}
                style={{ backgroundColor: '#dc2626', borderColor: '#dc2626' }}
              >
                {isSubmittingDecision ? <Trans text="Saving..." /> : <Trans text="Confirm Decline" />}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

