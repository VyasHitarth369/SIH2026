import { useState, useEffect } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import { apiClient } from '../../services/apiClient';

export default function CertificatePage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);

  const studentName = user?.name || user?.full_name || 'Student Contributor';
  const studentId = user?.stakeholder?.student_id || user?.profile?.studentId || 'STU-JH-2026';
  const studentUni =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    user?.profile?.studentUniversity ||
    'Government Partner University';

  useEffect(() => {
    let isMounted = true;
    async function loadCertificates() {
      try {
        setLoading(true);
        const res = await apiClient.get('/projects/certificates');
        if (isMounted && res && res.success && Array.isArray(res.data)) {
          setCertificates(res.data);
        }
      } catch (err) {
        console.warn('Could not fetch certificates from backend:', err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadCertificates();
    return () => {
      isMounted = false;
    };
  }, []);

  // Also evaluate completed/solved projects from context where this student participated
  const contextCertificates = problems.filter((p) => {
    const isEnrolled = (p.students || []).some(
      (s) => (user?.email && s.email === user.email) || (user?.name && s.name === user.name)
    );
    return isEnrolled;
  }).map((p) => {
    // Solution Deployed rule:
    // ONLY eligible if status is 'deployed', 'solved', or 'completed'
    const isDeployed = p.type === 'solved' || p.status === 'solved' || p.status === 'completed' || p.status === 'deployed';
    const pTitle = p.title?.[lang] || p.title?.en || p.title?.hi || 'Problem Statement';

    return {
      project_id: p.id,
      project_title: pTitle,
      status: p.status || (isDeployed ? 'solved' : 'active'),
      is_eligible: isDeployed,
      lock_reason: isDeployed
        ? null
        : (lang === 'hi'
          ? 'प्रमाणपत्र लॉक है: प्रमाणपत्र केवल तभी उपलब्ध होगा जब परियोजना "समाधान तैनात" (Solution Deployed) के अंतिम चरण पर पहुंच जाएगी।'
          : 'Certificate is locked: The certificate will become available only after the project reaches the final milestone: "Solution Deployed".'),
      certificate: isDeployed
        ? {
            certificate_id: `JH-SS-CERT-${p.id}-${studentId}`,
            project_id: p.id,
            project_title: pTitle,
            challenge_title: pTitle,
            student_id: studentId,
            student_name: studentName,
            university_name: p.allocation?.allocatedTo || studentUni,
            faculty_name: p.faculty?.name || 'Assigned Faculty Guide',
            industry_name: p.suggestedIndustries?.[0] || 'Industry Innovation Partner',
            status: 'eligible',
            milestone_reached: 'Solution Deployed',
            completion_date: p.submissionDate || '2026-09-18',
            verification_code: `SS-${String(p.id).padStart(6, '0')}-${studentId}`.toUpperCase(),
            issuer: 'Government of Jharkhand — Department of Higher & Technical Education',
            platform: 'Samadhan Setu / Concordia Innovation Platform',
          }
        : null,
    };
  });

  const existingPids = new Set(certificates.map((c) => String(c.project_id)));
  const combined = [
    ...certificates,
    ...contextCertificates.filter((c) => !existingPids.has(String(c.project_id))),
  ];

  const handleDownload = (cert) => {
    // Print-to-PDF format with native clean rendering
    window.print();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>
            <Trans text="E-Certificate Portal" />
          </h1>
          <p>
            {lang === 'hi'
              ? 'सफलतापूर्वक पूर्ण की गई परियोजनाओं के लिए आधिकारिक ई-प्रमाणपत्र प्राप्त एवं डाउनलोड करें'
              : 'View and download official E-Certificates for successfully completed and deployed projects'}
          </p>
        </div>
      </div>

      {loading && combined.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <p className="problem-desc"><Trans text="Verifying certificate eligibility..." /></p>
        </div>
      ) : combined.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🎓</div>
          <h3><Trans text="No Project Certificates Found" /></h3>
          <p className="problem-desc">
            {lang === 'hi'
              ? 'प्रमाणपत्र प्राप्त करने के लिए आपको किसी परियोजना का सक्रिय सदस्य होना चाहिए और परियोजना "समाधान तैनात" चरण तक पहुंचनी चाहिए।'
              : 'To receive a certificate, you must be a member of a project that has successfully reached the "Solution Deployed" milestone.'}
          </p>
        </div>
      ) : (
        combined.map((item) => {
          const { project_id, project_title, is_eligible, lock_reason, certificate } = item;

          return (
            <div key={project_id} style={{ marginBottom: 28 }}>
              {/* CLEAR HEADING ABOVE CERTIFICATE MANDATED BY PART 6 */}
              <div
                style={{
                  background: 'linear-gradient(135deg, #1E3A8A 0%, #0284C7 100%)',
                  color: '#FFFFFF',
                  padding: '16px 20px',
                  borderRadius: '10px 10px 0 0',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                }}
              >
                <div style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.85 }}>
                  <Trans text="Project Associated" />
                </div>
                <h2 style={{ margin: '4px 0 0', fontSize: '1.25rem', color: '#FFFFFF', fontWeight: 700 }}>
                  <Trans text="Problem:" /> {project_title}
                </h2>
              </div>

              {/* GATED STATE: LOCKED BEFORE SOLUTION DEPLOYED */}
              {!is_eligible ? (
                <div
                  className="card"
                  style={{
                    borderRadius: '0 0 10px 10px',
                    marginTop: 0,
                    borderTop: 'none',
                    background: '#F8FAFC',
                    padding: '28px 24px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                    <div style={{ fontSize: 32 }}>🔒</div>
                    <div>
                      <span className="badge badge-amber" style={{ marginBottom: 8 }}>
                        <Trans text="Certificate Locked (In Progress)" />
                      </span>
                      <h4 style={{ margin: '6px 0', color: '#0F172A' }}>
                        <Trans text="Certificate is not yet available for this problem" />
                      </h4>
                      <p className="problem-desc" style={{ maxWidth: 640 }}>
                        {lock_reason || (
                          <Trans text="A certificate will only be issued once the project reaches the final 'Solution Deployed' milestone." />
                        )}
                      </p>
                      <div className="problem-meta" style={{ marginTop: 12 }}>
                        ⏳ <strong><Trans text="Current Status:" /></strong> <span className="badge badge-blue">{item.status || 'Active'}</span> · 🛡️ <strong><Trans text="Rule:" /></strong> <Trans text="Mandatory Solution Deployed Verification" />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                /* ELIGIBLE STATE: ONLY AFTER SOLUTION DEPLOYED */
                <div
                  className="card certificate-printable-container"
                  style={{
                    borderRadius: '0 0 10px 10px',
                    marginTop: 0,
                    borderTop: 'none',
                    padding: '28px 24px',
                  }}
                >
                  {/* Action Bar */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                    <div>
                      <span className="badge badge-teal">
                        ✓ <Trans text="Eligible & Verified" />
                      </span>
                      <span className="badge badge-violet" style={{ marginLeft: 8 }}>
                        ID: {certificate?.certificate_id}
                      </span>
                    </div>
                    <button
                      className="btn btn-primary"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 600 }}
                      onClick={() => handleDownload(certificate)}
                    >
                      <span>📥</span>
                      <Trans text="Download Certificate (PDF / Print)" />
                    </button>
                  </div>

                  {/* VISUAL OFFICIAL E-CERTIFICATE */}
                  <div
                    className="certificate-frame"
                    style={{
                      border: '6px double #1E3A8A',
                      padding: '36px 32px',
                      background: '#FFFEFA',
                      borderRadius: 8,
                      position: 'relative',
                      boxShadow: 'inset 0 0 40px rgba(217, 119, 6, 0.05)',
                      textAlign: 'center',
                    }}
                  >
                    {/* Emblem / Header */}
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                      <div style={{ fontSize: 32 }}>🏛️</div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#1E3A8A', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                          GOVERNMENT OF JHARKHAND
                        </div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>
                          Department of Higher & Technical Education
                        </div>
                      </div>
                    </div>

                    <div style={{ margin: '14px 0 4px', fontSize: 14, letterSpacing: '0.15em', fontWeight: 600, color: '#B45309', textTransform: 'uppercase' }}>
                      CONCORDIA / SAMADHAN SETU INNOVATION PLATFORM
                    </div>

                    <h1
                      style={{
                        fontFamily: 'Georgia, serif',
                        fontSize: '1.85rem',
                        color: '#0F172A',
                        margin: '10px 0 16px',
                        letterSpacing: '0.03em',
                      }}
                    >
                      CERTIFICATE OF EXCELLENCE
                    </h1>

                    <p style={{ fontStyle: 'italic', color: '#475569', margin: '0 0 12px', fontSize: 15 }}>
                      This is officially awarded to
                    </p>

                    <h2
                      style={{
                        fontSize: '1.75rem',
                        color: '#1E3A8A',
                        margin: '4px 0',
                        fontWeight: 800,
                        textDecoration: 'underline',
                        textUnderlineOffset: '6px',
                      }}
                    >
                      {certificate?.student_name}
                    </h2>

                    <p style={{ color: '#334155', fontWeight: 600, fontSize: 14, margin: '8px 0 18px' }}>
                      Student ID: {certificate?.student_id} · {certificate?.university_name}
                    </p>

                    <p style={{ maxWidth: 700, margin: '0 auto 16px', color: '#334155', fontSize: 14.5, lineHeight: 1.6 }}>
                      In recognition of outstanding dedication and successful contribution as a core student researcher and engineering developer to the resolution and deployment of the innovation project:
                    </p>

                    <div
                      style={{
                        background: '#EFF6FF',
                        border: '1px solid #BFDBFE',
                        borderRadius: 6,
                        padding: '12px 18px',
                        maxWidth: 680,
                        margin: '0 auto 20px',
                        fontWeight: 700,
                        fontSize: '1.05rem',
                        color: '#1E3A8A',
                      }}
                    >
                      "{certificate?.project_title}"
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-around', margin: '24px auto 10px', maxWidth: 650, textAlign: 'center', borderTop: '1px solid #E2E8F0', paddingTop: 18 }}>
                      <div>
                        <div style={{ fontWeight: 700, color: '#0F172A', fontSize: 13 }}>{certificate?.faculty_name || 'Dr. Faculty Guide'}</div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Faculty Project Mentor</div>
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, color: '#0F172A', fontSize: 13 }}>{certificate?.industry_name || 'Industry Innovation SPOC'}</div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Industry Collaborative Partner</div>
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, color: '#0F172A', fontSize: 13 }}>State Innovation Council</div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Samadhan Setu Authority</div>
                      </div>
                    </div>

                    <div style={{ marginTop: 18, fontSize: 11, color: '#94A3B8', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Date of Deployment: {certificate?.completion_date}</span>
                      <span>Verification Code: {certificate?.verification_code}</span>
                      <span>Status: Solution Deployed ✓</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
