import { useState, useEffect, useCallback, useRef } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import apiClient from '../../services/apiClient';

export default function MOUPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [mous, setMous] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states
  const [viewingMOU, setViewingMOU] = useState(null);
  const [uploadingForMOU, setUploadingForMOU] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(false);
  const fileInputRef = useRef(null);

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

  // Handle MOU file upload to Supabase Storage via backend
  const handleUploadSubmit = async () => {
    if (!uploadFile) {
      showToast(lang === 'hi' ? 'कृपया अपलोड करने के लिए एक फ़ाइल चुनें।' : 'Please select a document file to upload.');
      return;
    }
    if (uploadFile.size > 10 * 1024 * 1024) {
      showToast(lang === 'hi' ? 'फ़ाइल का आकार 10 MB से कम होना चाहिए।' : 'File size must be 10 MB or less.');
      return;
    }

    const pid = uploadingForMOU?.project_id;
    if (!pid) return;

    try {
      setUploadProgress(true);
      const formData = new FormData();
      formData.append('file', uploadFile);

      await apiClient.post(`/projects/${pid}/mou`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      showToast(lang === 'hi' ? 'हस्ताक्षरित समझौता ज्ञापन (MOU) सफलतापूर्वक अपलोड किया गया।' : 'Signed MOU document successfully uploaded and saved.');
      setUploadingForMOU(null);
      setUploadFile(null);
      await fetchMOUs();
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || 'MOU upload failed');
    } finally {
      setUploadProgress(false);
    }
  };

  const handlePrintMOU = () => {
    window.print();
  };

  const handleDownloadMOU = async (mou) => {
    if (!mou?.project_id) return;
    try {
      showToast(lang === 'hi' ? 'MOU दस्तावेज़ डाउनलोड हो रहा है...' : 'Downloading authoritative MOU document...');
      await apiClient.downloadBlob(`/projects/${mou.project_id}/mou/download`, `VidySetu-MOU-${mou.project_id}.pdf`);
      showToast(lang === 'hi' ? 'MOU दस्तावेज़ सफलतापूर्वक डाउनलोड हो गया।' : 'MOU document downloaded successfully.');
    } catch (err) {
      showToast(err.message || 'Failed to download MOU');
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1><Trans text="Memorandum of Understanding (MOU)" /></h1>
          <p>
            {lang === 'hi'
              ? `${myUniversity} द्वारा उद्योग भागीदारों एवं सरकार के साथ आधिकारिक त्रिपक्षीय सहयोग समझौते।`
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
                {m.has_document && (
                  <span className="badge badge-teal">
                    ✓ <Trans text="Signed MOU Stored" />
                  </span>
                )}
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

              {/* ACTION BAR: THREE DISTINCT ACTIONS [VIEW], [DOWNLOAD], [PRINT] */}
              <div className="proposal-card__actions" style={{ marginTop: 16, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                {/* 1. VIEW MOU */}
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setViewingMOU(m)}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  📜 <Trans text="View MOU" />
                </button>

                {/* 2. DOWNLOAD REAL PDF/DOCX (NO PRINT PREVIEW) */}
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => handleDownloadMOU(m)}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  📥 <Trans text="Download MOU" />
                </button>

                {/* 3. PRINT MOU */}
                <button
                  type="button"
                  className="btn btn-light btn-sm"
                  onClick={() => {
                    setViewingMOU(m);
                    setTimeout(() => window.print(), 300);
                  }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  🖨️ <Trans text="Print MOU" />
                </button>

                {/* Status indicator */}
                {m.has_document ? (
                  <span className="badge badge-teal" style={{ padding: '6px 10px', fontSize: 11.5 }}>
                    ✓ <Trans text="Signed Copy Stored" />
                  </span>
                ) : (
                  <span className="badge badge-gray" style={{ padding: '6px 10px', fontSize: 11.5 }}>
                    ⏳ <Trans text="Official Template" />
                  </span>
                )}

                {/* 4. UPLOAD SIGNED COPY */}
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setUploadingForMOU(m);
                    setUploadFile(null);
                  }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}
                >
                  📤 <Trans text="Upload Signed MOU" />
                </button>
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

      {/* UPLOAD MODAL */}
      {uploadingForMOU && (
        <div className="modal-backdrop" style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 16 }}>
          <div className="card" style={{ maxWidth: 480, width: '100%', background: '#fff', borderRadius: 12, padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 17 }}>📤 <Trans text="Upload Official Signed MOU" /></h3>
              <button className="btn btn-sm btn-light" onClick={() => setUploadingForMOU(null)}>✕</button>
            </div>

            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
              {lang === 'hi'
                ? `परियोजना "${uploadingForMOU.project_title}" (${uploadingForMOU.project_id}) के लिए विधिवत हस्ताक्षरित समझौता ज्ञापन अपलोड करें।`
                : `Upload the duly signed Memorandum of Understanding document for project "${uploadingForMOU.project_title}" (${uploadingForMOU.project_id}).`}
            </p>

            <div className="field">
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                <Trans text="Select Document (PDF, DOCX, PNG, JPG — Max 10MB)" />
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                style={{ marginTop: 6 }}
              />
              {uploadFile && (
                <div style={{ marginTop: 8, fontSize: 12.5, color: '#059669', fontWeight: 600 }}>
                  ✓ {uploadFile.name} ({(uploadFile.size / (1024 * 1024)).toFixed(2)} MB)
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
              <button
                className="btn btn-light btn-sm"
                onClick={() => setUploadingForMOU(null)}
                disabled={uploadProgress}
              >
                <Trans text="Cancel" />
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleUploadSubmit}
                disabled={!uploadFile || uploadProgress}
              >
                {uploadProgress ? <Trans text="Uploading to Secure Storage..." /> : <Trans text="Upload & Save" />}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TRIPARTITE MOU DOCUMENT VIEWER MODAL (PRINTABLE / PDF PATTERN LIKE E-CERTIFICATE) */}
      {viewingMOU && (
        <div className="modal-backdrop" style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 16, overflowY: 'auto' }}>
          <div className="card mou-printable-container" style={{ maxWidth: 840, width: '100%', background: '#fff', borderRadius: 12, padding: 32, maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="badge badge-amber" style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' }}>📜 <Trans text="VidySetu MOU Draft / Template" /></span>
                <span className="badge badge-violet">ID: #{viewingMOU.mou_id}</span>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => handleDownloadMOU(viewingMOU)}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  📥 <Trans text="Download PDF" />
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handlePrintMOU}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  🖨️ <Trans text="Print" />
                </button>
                <button type="button" className="btn btn-sm btn-light" onClick={() => setViewingMOU(null)}>✕</button>
              </div>
            </div>

            {/* VISUAL OFFICIAL MOU DOCUMENT FRAME */}
            <div
              className="mou-frame"
              style={{
                border: '4px double #1E3A8A',
                padding: '36px 32px',
                background: '#FFFEFA',
                borderRadius: 8,
                boxShadow: 'inset 0 0 30px rgba(30, 58, 138, 0.04)',
              }}
            >
              {/* Header */}
              <div style={{ textAlign: 'center', borderBottom: '2px solid #1E3A8A', paddingBottom: 16, marginBottom: 20 }}>
                <div style={{ fontSize: 32, marginBottom: 4 }}>🏛️</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#1E3A8A', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  GOVERNMENT OF JHARKHAND
                </div>
                <div style={{ fontSize: 12, color: '#64748B' }}>
                  Department of Higher & Technical Education
                </div>
                <h2 style={{ fontSize: 18, color: '#0F172A', marginTop: 10, marginBottom: 2, letterSpacing: '0.03em' }}>
                  MEMORANDUM OF UNDERSTANDING
                </h2>
                <div style={{ fontSize: 13, color: '#b45309', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>
                  <Trans text="VidySetu MOU Draft / Template" />
                </div>
                <div style={{ fontSize: 12, color: '#2563EB', fontWeight: 600, marginTop: 4 }}>
                  VidySetu Tripartite Innovation & Research Collaborative Agreement
                </div>

                {/* Review Disclaimer Notice */}
                <div style={{
                  background: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderRadius: 6,
                  padding: '10px 14px',
                  marginTop: 14,
                  marginBottom: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  fontSize: 12,
                  color: '#92400e',
                  textAlign: 'left',
                }}>
                  <span style={{ fontSize: 18 }}>⚠️</span>
                  <div>
                    <strong><Trans text="DRAFT TEMPLATE — FOR INSTITUTIONAL REVIEW ONLY" />:</strong>{' '}
                    <Trans text="This document serves as an institutional preview and draft template for collaborative alignment. It is NOT an executed legal instrument until formally signed by all three authorized signatories and uploaded to the secure VidySetu repository." />
                  </div>
                </div>
              </div>

              {/* Parties */}
              <div style={{ fontSize: 13, lineHeight: 1.6, color: '#1E293B', marginBottom: 20 }}>
                <p>
                  This Memorandum of Understanding is entered into as of <strong>{viewingMOU.effective_date || 'Current Session'}</strong> by and between:
                </p>
                <ol style={{ paddingLeft: 20, marginTop: 8 }}>
                  <li style={{ marginBottom: 6 }}>
                    <strong>Party 1 (Government Authority):</strong> Department of Higher & Technical Education, Government of Jharkhand.
                  </li>
                  <li style={{ marginBottom: 6 }}>
                    <strong>Party 2 (Academic Institution):</strong> <strong>{viewingMOU.university_name}</strong> (Institution ID: {viewingMOU.university_id}).
                  </li>
                  <li>
                    <strong>Party 3 (Industrial Partner):</strong> <strong>{viewingMOU.industry_name}</strong> (Industry ID: {viewingMOU.industry_id}).
                  </li>
                </ol>
              </div>

              {/* Project Details */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: 14, borderRadius: 6, marginBottom: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', textTransform: 'uppercase' }}>
                  Collaborative Project Statement
                </div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#0F172A', marginTop: 4 }}>
                  {viewingMOU.project_title}
                </div>
                <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                  Project Reference ID: {viewingMOU.project_id}
                </div>
              </div>

              {/* Formal Clauses */}
              <div style={{ fontSize: 12.5, color: '#334155', lineHeight: 1.6, marginBottom: 24 }}>
                <div style={{ fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>Key Collaboration Terms:</div>
                <ul style={{ paddingLeft: 18, margin: 0 }}>
                  <li style={{ marginBottom: 4 }}>
                    <strong>Scope & Objective:</strong> Development, prototyping, and deployment of field-tested solutions for verified regional civic challenges.
                  </li>
                  <li style={{ marginBottom: 4 }}>
                    <strong>Student & Faculty Engagement:</strong> Academic guides and student researchers shall receive institutional resources, direct industry mentorship, and academic credit.
                  </li>
                  <li style={{ marginBottom: 4 }}>
                    <strong>Industry Participation:</strong> Industrial mentors shall provide technical guidance, testing infrastructure, and potential CSR/deployment grants upon pilot validation.
                  </li>
                  <li>
                    <strong>Government Monitoring:</strong> All progress milestones, impact metrics, and final deployment outcomes shall be tracked authoritatively on the VidySetu state platform.
                  </li>
                </ul>
              </div>

              {/* Signatory Blocks */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, borderTop: '1px solid #E2E8F0', paddingTop: 20, textAlign: 'center' }}>
                <div>
                  <div style={{ height: 40, borderBottom: '1px dashed #94A3B8', marginBottom: 6 }}></div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>For Government of Jharkhand</div>
                  <div style={{ fontSize: 11, color: '#64748B' }}>Authorized Officer</div>
                </div>

                <div>
                  <div style={{ height: 40, borderBottom: '1px dashed #94A3B8', marginBottom: 6 }}></div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>For {viewingMOU.university_name}</div>
                  <div style={{ fontSize: 11, color: '#64748B' }}>Dean / Registrar (Academic)</div>
                </div>

                <div>
                  <div style={{ height: 40, borderBottom: '1px dashed #94A3B8', marginBottom: 6 }}></div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>For {viewingMOU.industry_name}</div>
                  <div style={{ fontSize: 11, color: '#64748B' }}>Authorized Director / SPOC</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
