import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { governmentService } from '../../services/governmentService';
import Milestones from '../../components/shared/Milestones.jsx';

export default function PastSuccessfulProjectsPage() {
  const { t, lang } = useLanguage();
  const [solvedProblems, setSolvedProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadSolvedProblems = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await governmentService.fetchGovernmentProblems({ category: 'solved' });
      const list = res?.data || (Array.isArray(res) ? res : []);
      setSolvedProblems(list);
    } catch (err) {
      console.warn('Could not fetch solved problems from government API:', err.message);
      setError(err.message || 'Failed to load solved problems');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSolvedProblems();
  }, [loadSolvedProblems]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Solved Problems & Deployed Solutions" /></h1>
          <p>
            {lang === 'hi'
              ? 'सफलतापूर्वक हल की गई नागरिक समस्याएं एवं विश्वविद्यालयों व उद्योगों द्वारा कार्यान्वित तकनीकी समाधान।'
              : 'Authoritative registry of resolved civic challenges and validated technological deployments across Jharkhand.'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '36px' }}>
          <span className="spinner" style={{ display: 'inline-block', marginRight: 10 }} />
          <span>{lang === 'hi' ? 'हल की गई समस्याएं लोड हो रही हैं...' : 'Loading solved challenges and deployments...'}</span>
        </div>
      )}

      {error && !loading && (
        <div className="card" style={{ padding: '16px', background: '#fffbeb', borderLeft: '4px solid #f59e0b' }}>
          <p style={{ margin: 0, color: '#92400e' }}>
            <strong>{lang === 'hi' ? 'त्रुटि:' : 'Notice:'}</strong> {error}
          </p>
          <button className="btn btn-sm btn-outline" onClick={loadSolvedProblems} style={{ marginTop: 8 }}>
            <Trans text="Retry" />
          </button>
        </div>
      )}

      {!loading && !error && solvedProblems.length === 0 && (
        <div className="card empty-state" style={{ textAlign: 'center', padding: '36px' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>✅</div>
          <h3><Trans text="No Solved Problems Yet" /></h3>
          <p className="problem-desc">
            {lang === 'hi'
              ? 'वर्तमान में कोई भी समस्या "सफलतापूर्वक हल" श्रेणी में दर्ज नहीं है।'
              : 'No challenges have reached final deployment / resolved status yet in the database.'}
          </p>
        </div>
      )}

      {!loading && solvedProblems.map((p) => {
        const titleText = p.title || p.project_title || 'Resolved Challenge';
        const descText = p.description || p.project_description || '';
        const locText = p.location && p.location !== '-' ? p.location : `${p.city || p.district || 'Jharkhand'}, India`;

        return (
          <div className="card" key={p.challenge_id || p.id}>
            <div className="problem-card__head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="badge badge-teal">✅ {lang === 'hi' ? 'हल किया गया' : 'RESOLVED / DEPLOYED'}</span>
                <span className="badge badge-violet">ID: #{p.challenge_id || p.id}</span>
                {p.project_id && <span className="badge badge-outline">Project: {p.project_id}</span>}
              </div>
              <span className="badge badge-blue">
                {p.category || 'Civic Infrastructure'}
              </span>
            </div>

            <h3 className="problem-title" style={{ marginTop: 12 }}>{titleText}</h3>
            <p className="problem-desc">{descText}</p>

            <div className="problem-meta" style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>
              📍 <strong>{lang === 'hi' ? 'स्थान:' : 'Location:'}</strong> {locText}
              {p.district && <span> · 🏛️ {p.district}</span>}
            </div>

            {/* Implemented Solution & Milestone Evidence */}
            {p.project_title && (
              <div className="solution-block" style={{ marginTop: 14 }}>
                <h4 style={{ margin: '0 0 6px 0' }}>💡 <Trans text="Implemented Technological Solution" /></h4>
                <div style={{ fontWeight: 600, color: '#1e3a8a', marginBottom: 4 }}>{p.project_title}</div>
                {p.evidence_url && (
                  <div style={{ marginTop: 6, fontSize: 12.5 }}>
                    🔗 <strong><Trans text="Deployment Evidence:" /></strong>{' '}
                    <a href={p.evidence_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>
                      {p.evidence_url}
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* Credit Grid: Multi-Institutional Ownership */}
            <div className="credit-block" style={{ marginTop: 14 }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: 13, textTransform: 'uppercase', color: '#475569' }}>
                <Trans text="Institutional Execution Partners" />
              </h4>
              <div className="credit-grid">
                <div>
                  <span className="credit-tag">🎓 <Trans text="University" /></span>
                  <strong>{p.university_name || 'Academic Institution'}</strong>
                </div>
                <div>
                  <span className="credit-tag">👨‍🏫 <Trans text="Faculty Lead" /></span>
                  <strong>{p.faculty_name || 'Faculty Advisor'}</strong>
                </div>
                <div>
                  <span className="credit-tag">🏢 <Trans text="Industry Partner" /></span>
                  <strong>{p.industry_name || 'Industry Partner'}</strong>
                </div>
              </div>
            </div>

            {/* Standardized Milestone Progress */}
            <div style={{ marginTop: 16 }}>
              <Milestones problem={p} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
