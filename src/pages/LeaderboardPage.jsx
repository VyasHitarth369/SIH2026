import { useMemo, useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { domains, leaderboardStudents, weightedScore } from '../data/leaderboardData';
import StudentDetailModal from '../components/shared/StudentDetailModal';
import Trans from '../components/shared/Trans.jsx';

export default function LeaderboardPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [activeDomain, setActiveDomain] = useState(domains[0].value);
  const [selectedStudent, setSelectedStudent] = useState(null);

  const isIndustrySpoc = user?.role === 'industry';

  const ranked = useMemo(() => {
    return leaderboardStudents
      .filter((s) => s.domain === activeDomain)
      .map((s) => ({ ...s, score: weightedScore(s) }))
      .sort((a, b) => b.score - a.score);
  }, [activeDomain]);

  const mailHref = (student) => {
    const subject = encodeURIComponent(`Opportunity for ${student.name} — via SamadhanSetu Leaderboard`);
    const body = encodeURIComponent(
      `Hi ${student.name},\n\nWe came across your work on "${student.problemTitle.en}" on the SamadhanSetu leaderboard and would like to discuss an opportunity with you.\n\nRegards,`
    );
    return `mailto:${student.email}?subject=${subject}&body=${body}`;
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{t.leaderboardTitle}</h1>
          <p>{t.leaderboardSub}</p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 20px' }}>
        <div className="filter-tabs">
          {domains.map((d) => (
            <div
              key={d.value}
              className={`filter-tab${activeDomain === d.value ? ' active' : ''}`}
              onClick={() => setActiveDomain(d.value)}
            >
              {d[lang] || d.en}
            </div>
          ))}
        </div>
      </div>

      {!isIndustrySpoc && <p className="spoc-note">{t.spocOnlyNote}</p>}

      <div className="stack">
        {ranked.map((student, index) => (
          <div className="card leaderboard-card" key={student.id}>
            <div className="leaderboard-card__rank">#{index + 1}</div>

            <div className="leaderboard-card__body" onClick={() => setSelectedStudent(student)} role="button" tabIndex={0}>
              <div className="leaderboard-card__head">
                <strong className="leaderboard-card__name">{student.name}</strong>
                <span className="badge badge-blue">{student.score} / 5 {t.combinedScore}</span>
              </div>
              <div className="problem-meta">🏫 <Trans text={student.university} /> · 🏷️ {domains.find((d) => d.value === student.domain)?.[lang] || domains.find((d) => d.value === student.domain)?.en || ''}</div>
              <div className="problem-meta">🛠️ <Trans text="Skills:" /> {student.skills.join(', ')}</div>
              <div className="problem-meta">📁 <Trans text="Solved Problem:" /> {student.problemTitle[lang] || student.problemTitle.hi || student.problemTitle.en}</div>
              {student.achievements?.length > 0 && (
                <div className="problem-meta">🏅 <Trans text="Achievements:" /> {student.achievements.join(', ')}</div>
              )}
              <div className="leaderboard-card__scores">
                <span>🎓 {t.facultyScoreLabel}: <strong>{student.facultyReview.score}</strong></span>
                <span>💬 {t.citizenScoreLabel}: <strong>{student.citizenFeedbackScore}</strong></span>
              </div>
              <span className="leaderboard-card__view">{t.viewDetails}</span>
            </div>

            {isIndustrySpoc && (
              <div className="leaderboard-card__actions" style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 140, justifyContent: 'center' }}>
                <a className="btn btn-primary btn-sm" href={mailHref(student)}>
                  {t.emailBtn || '✉️ Email'}
                </a>
                <a
                  className="btn btn-light btn-sm"
                  href={student.linkedin || `https://www.linkedin.com/in/${student.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t.linkedinBtn || '🔗 LinkedIn'}
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      <StudentDetailModal student={selectedStudent} onClose={() => setSelectedStudent(null)} />
    </div>
  );
}
