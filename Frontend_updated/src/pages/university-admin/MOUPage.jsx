import { useState, useEffect, useCallback } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import apiClient from '../../services/apiClient';

export default function MOUPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [mous, setMous] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const myUniversity =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    'University Administration';

  const fetchMOUs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.get('/projects/university/mous');
      if (res && res.data && Array.isArray(res.data)) {
        setMous(res.data);
      } else {
        setMous([]);
      }
    } catch (err) {
      console.warn('Could not fetch university MOUs:', err.message);
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
          <h1><Trans text="Memorandum of Understanding (MOU)" /></h1>
          <p>
            {lang === 'hi'
              ? `${myUniversity} द्वारा उद्योग भागीदारों एवं सरकार के साथ आधिकारिक सहयोग समझौते।`
              : `Official tri-party collaboration agreements and partnerships for ${myUniversity}.`}
          </p>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: '24px', textAlign: 'center' }}>
          <p>{lang === 'hi' ? 'समझौता ज्ञापन लोड हो रहे हैं...' : 'Loading university MOUs from server...'}</p>
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
                      🏫 <Trans text="University Institution:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.university_name}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                      🏢 <Trans text="Collaborating Industry Partner:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.industry_name}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                      🏛️ <Trans text="Government Involvement:" />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', marginTop: 2 }}>
                      {m.government_partner}
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
        <div className="card empty-state">
          <span className="empty-state__icon">📁</span>
          <h3><Trans text="No MOU Available" /></h3>
          <p>
            {lang === 'hi'
              ? 'वर्तमान में आपके विश्वविद्यालय के लिए कोई सक्रिय समझौता ज्ञापन (MOU) रिकॉर्ड उपलब्ध नहीं है।'
              : 'No active Memorandum of Understanding (MOU) records found for your university.'}
          </p>
        </div>
      )}
    </div>
  );
}
