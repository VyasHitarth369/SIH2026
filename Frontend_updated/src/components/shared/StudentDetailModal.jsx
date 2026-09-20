import { useLanguage } from '../../context/LanguageContext';
import Trans from './Trans.jsx';
import { EmailIcon, LinkedinIcon, GithubIcon } from './Icons.jsx';

export default function StudentDetailModal({ student, onClose }) {
  const { t, lang } = useLanguage();
  if (!student) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <button className="modal-box__close" onClick={onClose} aria-label={t.close}>✕</button>

        <h3 className="modal-box__name">{student.name}</h3>
        <div className="problem-meta">{student.university}</div>

        <div className="section-box section-box--muted" style={{ marginTop: 14 }}>
          <h4>{t.problemLabel}</h4>
          <p className="problem-title" style={{ fontSize: 15, margin: '4px 0' }}>{student.problemTitle[lang] || student.problemTitle.hi}</p>
          <p className="problem-desc">{student.problemDesc[lang] || student.problemDesc.hi}</p>
          <p className="problem-desc" style={{ marginTop: 8 }}><strong>{t.solutionLabel}:</strong> {student.solution[lang] || student.solution.hi}</p>
        </div>

        <div className="section-box" style={{ marginTop: 12 }}>
          <h4>{t.roleOfStudent}</h4>
          <p className="problem-desc">{student.role[lang] || student.role.hi}</p>
        </div>

        <div className="grid" style={{ marginTop: 12 }}>
          <div className="card" style={{ marginBottom: 0 }}>
            <h4 style={{ fontSize: 13, color: 'var(--primary-dark)', marginBottom: 6 }}>{t.facultyReviewLabel}</h4>
            <div className="stat-figure" style={{ fontSize: 22 }}>{student.facultyReview.score} / 5</div>
            <p className="problem-desc">{student.facultyReview.comment[lang] || student.facultyReview.comment.hi}</p>
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <h4 style={{ fontSize: 13, color: 'var(--teal-dark)', marginBottom: 6 }}>{t.citizenFeedbackLabel}</h4>
            <div className="stat-figure" style={{ fontSize: 22, color: 'var(--teal)' }}>{student.citizenFeedbackScore} / 5</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 14, flexWrap: 'wrap' }}>
          <a
            className="btn btn-primary btn-block icon-btn"
            href={`mailto:${student.email}?subject=${encodeURIComponent(`Opportunity for ${student.name} — via VidySetu`)}`}
          >
            <EmailIcon /> <Trans text="Email" />
          </a>
          <a
            className="btn btn-light btn-block icon-btn"
            href={student.linkedin || `https://www.linkedin.com/in/${student.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <LinkedinIcon /> LinkedIn
          </a>
          <a
            className="btn btn-light btn-block icon-btn"
            href={student.github || `https://github.com/${student.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <GithubIcon /> <Trans text="GitHub" />
          </a>
        </div>
      </div>
    </div>
  );
}
