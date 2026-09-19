import { useState, useEffect } from 'react';
import Trans from '../../components/shared/Trans.jsx';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { useProblems } from '../../context/ProblemsContext';
import Milestones from '../../components/shared/Milestones.jsx';
import { apiClient } from '../../services/apiClient';

export default function UniversityProblemsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const { problems } = useProblems();
  const [backendProjects, setBackendProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  // Authoritative student university resolution
  const userUni =
    user?.stakeholder?.university_name ||
    user?.profile?.university ||
    user?.profile?.studentUniversity ||
    user?.university ||
    '';

  useEffect(() => {
    let isMounted = true;
    async function loadOngoingProjects() {
      try {
        setLoading(true);
        const res = await apiClient.get('/projects?approved_only=true');
        if (isMounted && res && res.success && Array.isArray(res.data)) {
          setBackendProjects(res.data);
        }
      } catch (err) {
        console.warn('Failed to load ongoing university projects from backend:', err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadOngoingProjects();
    return () => {
      isMounted = false;
    };
  }, []);

  // Adapt backend project records to standard problem representation
  const adaptedBackend = backendProjects.map((p) => ({
    id: p.project_id || p.id,
    project_id: p.project_id,
    title: { en: p.title || p.project_title || '', hi: p.title || p.project_title || '' },
    desc: { en: p.description || '', hi: p.description || '' },
    loc: p.location || `${p.city || ''}, ${p.district || ''}`.replace(/^,\s*|,\s*$/g, '') || 'Jharkhand, India',
    domain: p.domain || 'Innovation & Engineering',
    category: p.category || 'Civic Problem',
    faculty: p.faculty_name ? { name: p.faculty_name, email: p.faculty_email } : null,
    industryName: p.industry_name || null,
    students: (p.student_participants || p.student_names || []).map((s) => (typeof s === 'string' ? { name: s } : s)),
    requiredTechnologies: Array.isArray(p.skills_required)
      ? p.skills_required
      : typeof p.skills_required === 'string' && p.skills_required.includes(',')
      ? p.skills_required.split(',').map((s) => s.trim())
      : [p.skills_required || 'Applied Engineering'].filter(Boolean),
    status: p.status || 'active',
    allocation: { allocatedTo: p.university_name || userUni, status: 'allocated' },
    isBackend: true,
  }));

  // Context problems allocated to student's university that have passed approval workflow
  const approvedContextProblems = problems.filter((p) => {
    const isAllocatedToMyUni =
      p.allocation?.allocatedTo &&
      (userUni
        ? p.allocation.allocatedTo.toLowerCase().includes(userUni.toLowerCase()) ||
          userUni.toLowerCase().includes(p.allocation.allocatedTo.toLowerCase())
        : true);

    const isApproved =
      p.govApproved &&
      p.universityAdminStatus !== 'pending_review' &&
      p.universityAdminStatus !== 'rejected' &&
      p.status !== 'proposed' &&
      p.status !== 'rejected';

    return isAllocatedToMyUni && isApproved;
  });

  // Combine and deduplicate by ID
  const existingIds = new Set(adaptedBackend.map((p) => String(p.id)));
  const combined = [
    ...adaptedBackend,
    ...approvedContextProblems.filter((p) => !existingIds.has(String(p.id))),
  ];

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>
            <Trans text="Ongoing Problems in University" />
          </h1>
          <p>
            {lang === 'hi'
              ? `${userUni || 'आपके विश्वविद्यालय'} द्वारा वर्तमान में हल की जा रही स्वीकृत समस्याएं`
              : `Approved problems currently being solved by ${userUni || 'your university'}`}
          </p>
        </div>
      </div>

      {loading && combined.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <p className="problem-desc"><Trans text="Loading ongoing university problems..." /></p>
        </div>
      ) : combined.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <p className="problem-desc">
            <Trans text="No ongoing approved problems found for your university at this time." />
          </p>
        </div>
      ) : (
        combined.map((p) => {
          const studentNames = (p.students || []).map((s) => s.name || s).filter(Boolean);
          const facultyName = p.faculty?.name || p.faculty_name;
          const industryName = p.industryName || p.industry_name || (p.suggestedIndustries && p.suggestedIndustries[0]);

          return (
            <div className="card" key={p.id}>
              <div className="problem-card__head">
                <span className="badge badge-blue">
                  🏫 {p.allocation?.allocatedTo || userUni || <Trans text="University Allocated" />}
                </span>
                <span className="badge badge-teal">
                  <Trans text={p.status === 'solved' || p.status === 'completed' ? 'Solved' : 'Active / In Progress'} />
                </span>
                <span className="badge badge-violet">
                  ID: #{String(p.id).startsWith('PRJ-') ? p.id : `PRJ-JH-${p.id}`}
                </span>
              </div>

              <h3 className="problem-title">{p.title[lang] || p.title.en || p.title.hi}</h3>
              <p className="problem-desc">{p.desc[lang] || p.desc.en || p.desc.hi}</p>

              <div className="problem-meta" style={{ marginTop: 8 }}>
                📍 <strong><Trans text="Location:" /></strong> {p.loc}
              </div>

              {p.requiredTechnologies?.length > 0 && (
                <div className="skills-block" style={{ marginTop: 10 }}>
                  <div className="skills-block__label">
                    🛠️ <strong><Trans text="Skills Required:" /></strong>
                  </div>
                  <div className="skills-chips" style={{ marginTop: 4 }}>
                    {p.requiredTechnologies.map((skill, idx) => (
                      <span className="skill-chip" key={idx}>{skill}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="section-box section-box--muted" style={{ marginTop: 14 }}>
                <div className="problem-meta">
                  👨‍🏫 <strong><Trans text="Faculty Mentoring:" /></strong>{' '}
                  {facultyName ? (
                    <strong>{facultyName}</strong>
                  ) : (
                    <span style={{ color: 'var(--amber)' }}><Trans text="Not yet allocated" /></span>
                  )}
                </div>

                <div className="problem-meta" style={{ marginTop: 6 }}>
                  🏢 <strong><Trans text="Industry Name:" /></strong>{' '}
                  {industryName ? (
                    <strong>{industryName}</strong>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </div>

                <div className="problem-meta" style={{ marginTop: 6 }}>
                  👨‍🎓 <strong><Trans text="Student Names Working on It:" /></strong>{' '}
                  {studentNames.length > 0 ? (
                    <span><strong>{studentNames.join(', ')}</strong> ({studentNames.length})</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}><Trans text="Team selection in progress" /></span>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <Milestones problem={p} isCitizen={false} />
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
