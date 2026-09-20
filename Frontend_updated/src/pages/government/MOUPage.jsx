import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import apiClient from '../../services/apiClient';

export default function GovernmentMOUPage() {
  const { lang } = useLanguage();
  const [mous, setMous] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMOUs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.get('/government/mous');
      const data = res?.data !== undefined ? res.data : res;
      setMous(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not fetch government MOUs:', err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMOUs();
  }, [fetchMOUs]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Government Memorandum of Understanding (MOU)" /></h1>
          <p>
            {lang === 'hi'
              ? 'विश्वविद्यालयों, उद्योगों एवं झारखंड सरकार के बीच आधिकारिक त्रिपक्षीय सहयोग समझौते।'
              : 'Official tri-party collaboration agreements between Universities, Industries, and Government of Jharkhand.'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: '24px', textAlign: 'center' }}>
          <p>{lang === 'hi' ? 'समझौता ज्ञापन लोड हो रहे हैं...' : 'Loading government MOUs from server...'}</p>
        </div>
      )}

      {error && !loading && (
        <div className="card" style={{ padding: '16px', background: '#fef2f2', border: '1px solid #f87171', color: '#991b1b' }}>
          <p><strong>Error:</strong> {error}</p>
          <button className="btn btn-sm btn-outline" onClick={fetchMOUs} style={{ marginTop: 8 }}>
            <Trans text="Retry" />
          </button>
        </div>
      )}

      {!loading && !error && mous.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {mous.map((m) => (
            <div className="card" key={m.mou_id}>
              <div className="problem-card__head">
                <span className="badge badge-teal">
                  🤝 <Trans text={m.status || 'Active Collaboration'} />
                </span>
                <span className="badge badge-violet">
                  ID: #{m.mou_id}
                </span>
                <span className="badge badge-outline">
                  📁 {m.project_id}
                </span>
              </div>

              <h3 className="problem-title">{m.project_title}</h3>

              <div className="section-box section-box--muted" style={{ marginTop: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                      🏢 <Trans text="Industry Partner:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.industry_name}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                      🏫 <Trans text="Collaborating University:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.university_name}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                      🏛️ <Trans text="Government Authority:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.government_partner || 'Government of Jharkhand'}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                      📅 <Trans text="Effective Date:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.effective_date || 'In Effect'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="proposal-card__actions" style={{ marginTop: 16 }}>
                {m.has_document && m.document_url ? (
                  <a
                    href={m.document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary btn-sm"
                    download
                  >
                    📥 <Trans text="Download MOU Document" />
                  </a>
                ) : (
                  <span
                    className="badge badge-gray"
                    style={{ padding: '8px 14px', fontSize: 12.5, fontWeight: 500 }}
                  >
                    📄 <Trans text="Document Pending / Not Uploaded" />
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && mous.length === 0 && (
        <div className="card empty-state" style={{ padding: '40px 20px', textAlign: 'center' }}>
          <span className="empty-state__icon" style={{ fontSize: 48 }}>📁</span>
          <h3 style={{ marginTop: 12 }}><Trans text="No MOU Available" /></h3>
          <p style={{ maxWidth: 500, margin: '8px auto', color: 'var(--text-muted)' }}>
            {lang === 'hi'
              ? 'वर्तमान में कोई सक्रिय समझौता ज्ञापन (MOU) रिकॉर्ड उपलब्ध नहीं है।'
              : 'No active Memorandum of Understanding (MOU) records found.'}
          </p>
        </div>
      )}
    </div>
  );
}
