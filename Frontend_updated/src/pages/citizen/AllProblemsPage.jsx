import { useState, useEffect, useMemo, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import Milestones from '../../components/shared/Milestones.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useToast } from '../../context/ToastContext';
import { fetchChallenges, voteChallenge, fetchChallengeMilestones } from '../../services/challengeService';
import { jharkhandCities, cityLabel } from '../../data/locations';

const statusBadgeClass = {
  submitted: 'badge-blue',
  unsolved: 'badge-amber',
  validated: 'badge-blue',
  existing_solution_found: 'badge-violet',
  accepted_existing_solution: 'badge-teal',
  university_selected: 'badge-teal',
  active: 'badge-teal',
  solved: 'badge-teal',
  rejected: 'badge-coral',
};

export default function AllProblemsPage() {
  const { lang } = useLanguage();
  const { showToast } = useToast();

  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // all | unsolved | active | solved

  // Voting state
  const [votedMap, setVotedMap] = useState({});
  const [votingId, setVotingId] = useState(null);

  // Milestones state
  const [expandedMilestones, setExpandedMilestones] = useState({});
  const [milestonesByChallenge, setMilestonesByChallenge] = useState({});
  const [loadingMilestones, setLoadingMilestones] = useState({});

  const loadChallenges = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchChallenges();
      if (Array.isArray(data)) {
        setChallenges(data);
        const initVoted = {};
        data.forEach((c) => {
          if (c.has_voted) {
            initVoted[c.challenge_id] = true;
          }
        });
        setVotedMap((prev) => ({ ...prev, ...initVoted }));
      }
    } catch (err) {
      console.warn('Failed to load challenges:', err.message);
      showToast(lang === 'hi' ? 'समस्याएं लोड करने में विफल' : 'Failed to load problems');
    } finally {
      setLoading(false);
    }
  }, [lang, showToast]);

  useEffect(() => {
    loadChallenges();
  }, [loadChallenges]);

  const handleVote = async (challengeId) => {
    if (votedMap[challengeId]) {
      showToast(lang === 'hi' ? 'आप पहले ही इस समस्या का समर्थन कर चुके हैं' : 'You have already supported this problem');
      return;
    }

    try {
      setVotingId(challengeId);
      const res = await voteChallenge(challengeId);
      setVotedMap((prev) => ({ ...prev, [challengeId]: true }));
      setChallenges((prev) =>
        prev.map((c) => {
          if (c.challenge_id === challengeId) {
            const newCount = res?.data?.votes_count ?? (c.votes_count || 0) + 1;
            return { ...c, votes_count: newCount, has_voted: true };
          }
          return c;
        })
      );
      showToast(lang === 'hi' ? 'समर्थन दर्ज किया गया!' : 'Problem supported successfully!');
    } catch (err) {
      if (err.status === 400 || (err.message && err.message.includes('already voted'))) {
        setVotedMap((prev) => ({ ...prev, [challengeId]: true }));
        showToast(lang === 'hi' ? 'आप पहले ही समर्थन कर चुके हैं' : 'You have already supported this problem');
      } else {
        showToast(err.message || 'Voting failed');
      }
    } finally {
      setVotingId(null);
    }
  };

  const toggleMilestones = async (challengeId) => {
    if (expandedMilestones[challengeId]) {
      setExpandedMilestones((prev) => ({ ...prev, [challengeId]: false }));
      return;
    }

    setExpandedMilestones((prev) => ({ ...prev, [challengeId]: true }));

    if (!milestonesByChallenge[challengeId]) {
      try {
        setLoadingMilestones((prev) => ({ ...prev, [challengeId]: true }));
        const list = await fetchChallengeMilestones(challengeId);
        setMilestonesByChallenge((prev) => ({
          ...prev,
          [challengeId]: Array.isArray(list) ? list : [],
        }));
      } catch (err) {
        console.warn(`Could not load milestones for ${challengeId}:`, err.message);
      } finally {
        setLoadingMilestones((prev) => ({ ...prev, [challengeId]: false }));
      }
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return challenges.filter((c) => {
      // City filter
      if (selectedCity && c.city !== selectedCity) {
        return false;
      }
      // Status filter
      if (statusFilter === 'unsolved') {
        if (c.status === 'solved' || c.status === 'accepted_existing_solution') return false;
      } else if (statusFilter === 'active') {
        if (!c.project && c.status !== 'active' && c.status !== 'university_selected') return false;
      } else if (statusFilter === 'solved') {
        if (c.status !== 'solved' && c.status !== 'accepted_existing_solution') return false;
      }

      if (!q) return true;
      const title = (c.title || '').toLowerCase();
      const desc = (c.description || '').toLowerCase();
      const loc = (c.location || '').toLowerCase();
      const city = (c.city || '').toLowerCase();
      return title.includes(q) || desc.includes(q) || loc.includes(q) || city.includes(q);
    });
  }, [challenges, search, selectedCity, statusFilter]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{lang === 'hi' ? '🌐 सभी दर्ज समस्याएं' : '🌐 All Reported Problems'}</h1>
          <p>
            {lang === 'hi'
              ? 'झारखंड भर की सार्वजनिक समस्याओं का अन्वेषण करें, महत्वपूर्ण पहलों का समर्थन करें और समाधान की प्रगति देखें।'
              : 'Explore community challenges across Jharkhand, support key initiatives, and track resolution progress.'}
          </p>
        </div>
      </div>

      {/* SEARCH AND FILTERS */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
          <input
            type="text"
            className="search-input"
            placeholder={lang === 'hi' ? 'समस्या, शीर्षक या स्थान खोजें…' : 'Search problems by title, keyword, or location…'}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <select
            value={selectedCity}
            onChange={(e) => setSelectedCity(e.target.value)}
            style={{
              padding: '10px 14px',
              border: '1px solid #d1d5db',
              borderRadius: 8,
              fontSize: '0.95rem',
              backgroundColor: '#fff',
            }}
          >
            <option value="">{lang === 'hi' ? '📍 सभी शहर (झारखंड)' : '📍 All Cities (Jharkhand)'}</option>
            {jharkhandCities.map((c) => (
              <option key={c.value} value={c.value}>
                {c[lang] || c.en}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-tabs" style={{ marginTop: 14 }}>
          <div
            className={`filter-tab${statusFilter === 'all' ? ' active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            {lang === 'hi' ? 'सभी समस्याएं' : 'All Problems'}
          </div>
          <div
            className={`filter-tab${statusFilter === 'unsolved' ? ' active' : ''}`}
            onClick={() => setStatusFilter('unsolved')}
          >
            {lang === 'hi' ? 'सक्रिय / अनिर्धारित' : 'Unsolved'}
          </div>
          <div
            className={`filter-tab${statusFilter === 'active' ? ' active' : ''}`}
            onClick={() => setStatusFilter('active')}
          >
            {lang === 'hi' ? 'परियोजनाएं प्रगति पर' : 'Active Projects'}
          </div>
          <div
            className={`filter-tab${statusFilter === 'solved' ? ' active' : ''}`}
            onClick={() => setStatusFilter('solved')}
          >
            {lang === 'hi' ? 'समाधान पूर्ण' : 'Resolved'}
          </div>
        </div>
      </div>

      {/* CHALLENGES LIST */}
      <div className="stack">
        {loading ? (
          <div className="card" style={{ textAlign: 'center', padding: '48px 20px', color: '#6b7280' }}>
            <span style={{ fontSize: '2.5rem', display: 'block', marginBottom: 12 }}>⏳</span>
            {lang === 'hi' ? 'समस्याएं लोड हो रही हैं…' : 'Loading problems across Jharkhand…'}
          </div>
        ) : filtered.length === 0 ? (
          <div className="card empty-state" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <span className="empty-state__icon" style={{ fontSize: '3rem', marginBottom: 12 }}>🔍</span>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1.25rem', color: '#1f2937' }}>
              {lang === 'hi' ? 'कोई समस्या नहीं मिली' : 'No Problems Found'}
            </h3>
            <p style={{ color: '#6b7280', fontSize: '0.95rem', margin: 0 }}>
              {lang === 'hi'
                ? 'आपके खोज मापदंड से मेल खाती कोई समस्या उपलब्ध नहीं है।'
                : 'No problems match your current search or filter criteria.'}
            </p>
          </div>
        ) : (
          filtered.map((c) => {
            const hasVoted = Boolean(votedMap[c.challenge_id] || c.has_voted);
            const votes = c.votes_count || 0;
            const isSolved = c.status === 'solved' || c.status === 'accepted_existing_solution';
            const hasProject = Boolean(c.project);
            const isExpanded = Boolean(expandedMilestones[c.challenge_id]);
            const milestones = milestonesByChallenge[c.challenge_id] || [];
            const isMilestonesLoading = Boolean(loadingMilestones[c.challenge_id]);

            return (
              <div className="card" key={c.challenge_id} style={{ position: 'relative' }}>
                <div className="problem-card__head">
                  <span className={`badge ${isSolved ? 'badge-teal' : statusBadgeClass[c.status] || 'badge-amber'}`}>
                    {isSolved
                      ? (lang === 'hi' ? '✅ हल हो चुका' : '✅ SOLVED')
                      : (c.status ? c.status.replace(/_/g, ' ').toUpperCase() : 'SUBMITTED')}
                  </span>

                  {hasProject && (
                    <span className="badge badge-teal">
                      🎓 {lang === 'hi' ? 'परियोजना सक्रिय' : 'Active Project'}
                    </span>
                  )}

                  <span className="badge badge-gray">
                    📍 {cityLabel(c.city || c.district, lang) || 'Jharkhand'}
                  </span>

                  {c.impact_scope && (
                    <span className="badge badge-blue">
                      🎯 <Trans text={c.impact_scope} />
                    </span>
                  )}
                </div>

                <h3 className="problem-title" style={{ marginTop: 8, marginBottom: 8 }}>
                  {c.title}
                </h3>

                <p className="problem-desc" style={{ marginBottom: 12, lineHeight: 1.5 }}>
                  {c.description}
                </p>

                <div className="problem-meta" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '0.875rem', color: '#4b5563' }}>
                  <span>📍 {c.location || `${c.address || ''}, ${c.city || ''}`.replace(/^,\s*/, '')}</span>
                  {c.created_at && (
                    <span>📅 {lang === 'hi' ? 'दिनांक:' : 'Date:'} {c.created_at.slice(0, 10)}</span>
                  )}
                  <span>👤 {lang === 'hi' ? 'दर्जकर्ता:' : 'Reported by:'} <strong>{c.submitted_by || 'Citizen'}</strong></span>
                </div>

                {/* PROJECT SUMMARY (IF ACTIVE PROJECT LINKED) */}
                {hasProject && (
                  <div
                    style={{
                      marginTop: 12,
                      padding: '12px 14px',
                      background: '#f8fafc',
                      borderRadius: 8,
                      border: '1px solid #e2e8f0',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600, color: '#1e293b' }}>
                          🏛️ {c.project.project_title || 'Collaborative Solution Project'}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                          {c.project.university_name && `🏫 ${c.project.university_name}`}
                          {c.project.industry_name && ` · 🏢 ${c.project.industry_name}`}
                        </div>
                      </div>
                      <span className="badge badge-teal">
                        {c.project.status ? c.project.status.toUpperCase() : 'IN PROGRESS'}
                      </span>
                    </div>
                  </div>
                )}

                {/* READ-ONLY MILESTONES EXPANDER */}
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    className="btn btn-light btn-sm"
                    onClick={() => toggleMilestones(c.challenge_id)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  >
                    📊 {isExpanded ? (lang === 'hi' ? 'माइलस्टोन छिपाएं' : 'Hide Milestones') : (lang === 'hi' ? 'परियोजना माइलस्टोन देखें' : 'View Project Milestones')}
                  </button>
                </div>

                {/* READ-ONLY MILESTONES LIST */}
                {isExpanded && (
                  <div style={{ marginTop: 12, borderTop: '1px solid #e2e8f0', paddingTop: 12 }}>
                    <Milestones problem={c} isCitizen={true} />

                        {milestones.length > 0 && (
                          <div style={{ marginTop: 16 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                              <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#334155' }}>
                                📋 {lang === 'hi' ? 'विस्तृत कार्य विवरण (केवल पठन)' : 'Detailed Task Breakdown (Read-Only)'}
                              </span>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                              {milestones.map((m) => (
                                <div
                                  key={m.milestone_id}
                                  style={{
                                    background: '#fff',
                                    padding: '10px 14px',
                                    borderRadius: 6,
                                    border: '1px solid #e2e8f0',
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                    <span style={{ fontWeight: 600, fontSize: '0.92rem', color: '#0f172a' }}>
                                      {m.name}
                                    </span>
                                    <span
                                      className={`badge ${
                                        m.status === 'completed'
                                          ? 'badge-teal'
                                          : m.status === 'in_progress'
                                          ? 'badge-blue'
                                          : 'badge-gray'
                                      }`}
                                    >
                                      {m.status ? m.status.replace(/_/g, ' ') : 'pending'}
                                    </span>
                                  </div>

                                  {m.description && (
                                    <p style={{ margin: '0 0 8px 0', fontSize: '0.85rem', color: '#475569' }}>
                                      {m.description}
                                    </p>
                                  )}

                                  {/* PROGRESS BAR (READ-ONLY) */}
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <div
                                      style={{
                                        flex: 1,
                                        height: 6,
                                        background: '#e2e8f0',
                                        borderRadius: 4,
                                        overflow: 'hidden',
                                      }}
                                    >
                                      <div
                                        style={{
                                          width: `${Math.min(100, Math.max(0, m.completion_percentage || 0))}%`,
                                          height: '100%',
                                          background: m.status === 'completed' ? '#10b981' : '#3b82f6',
                                          transition: 'width 0.3s ease',
                                        }}
                                      />
                                    </div>
                                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>
                                      {m.completion_percentage || 0}%
                                    </span>
                                  </div>

                                  {m.deadline && (
                                    <div style={{ marginTop: 6, fontSize: '0.8rem', color: '#94a3b8' }}>
                                      ⏱️ {lang === 'hi' ? 'समय सीमा:' : 'Target Deadline:'} {m.deadline.slice(0, 10)}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                {/* VOTING ACTION BAR */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: 16,
                    paddingTop: 12,
                    borderTop: '1px solid #f1f5f9',
                    flexWrap: 'wrap',
                    gap: 12,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      type="button"
                      className={`btn btn-sm ${hasVoted ? 'btn-success' : 'btn-light'}`}
                      onClick={() => handleVote(c.challenge_id)}
                      disabled={hasVoted || votingId === c.challenge_id}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        fontWeight: 600,
                      }}
                    >
                      {hasVoted ? '✓ ' : '👍 '}
                      {hasVoted
                        ? (lang === 'hi' ? 'समर्थित' : 'Supported')
                        : (lang === 'hi' ? 'समर्थन दें' : 'Support Problem')}
                      {' · '}
                      <strong>{votes}</strong>
                    </button>
                    <span style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      {votes} {votes === 1 ? (lang === 'hi' ? 'नागरिक का समर्थन' : 'citizen support') : (lang === 'hi' ? 'नागरिकों का समर्थन' : 'citizens supported')}
                    </span>
                  </div>

                  <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                    ID: {c.challenge_id}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
