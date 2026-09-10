import Trans, { translateText } from '../components/shared/Trans.jsx';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useProblems } from '../context/ProblemsContext';
import { useToast } from '../context/ToastContext';
import { roleFieldsConfig } from '../components/auth/roleFieldsConfig';

const roleTitles = {
  citizen: 'Citizen',
  student: 'Student',
  faculty: 'Faculty',
  'university-admin': 'University Administration',
  government: 'Government',
  industry: 'Industry Employee',
};

function Field({ label, value }) {
  const displayVal = Array.isArray(value) ? value.join(', ') : value;
  return (
    <div>
      <div className="profile-field__label"><Trans text={label} /></div>
      <div className="profile-field__value">
        {displayVal ? <Trans text={String(displayVal)} /> : <span style={{ color: 'var(--text-muted)' }}>—</span>}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const { lang } = useLanguage();
  const { problems } = useProblems();
  const { showToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(user?.name || '');
  const [draftEmail, setDraftEmail] = useState(user?.email || '');
  const [draft, setDraft] = useState(user?.profile || {});

  if (!user) return null;
  const p = user.profile || {};
  const roleFields = roleFieldsConfig[user.role] || [];

  const startEdit = () => {
    setDraftName(user.name || '');
    setDraftEmail(user.email || '');
    setDraft({ ...(user.profile || {}) });
    setEditing(true);
  };

  const save = () => {
    updateProfile({
      name: draftName.trim() || user.name,
      email: draftEmail.trim() || user.email,
      ...draft,
    });
    setEditing(false);
    showToast(<Trans text="Profile updated." />);
  };

  // Role-specific derived data pulled from the live problems dataset.
  let extraSection = null;
  if (user.role === 'citizen') {
    const submitted = problems.filter((prob) => prob.source === 'citizen');
    extraSection = (
      <div className="card">
        <h3>{<Trans text="Submitted Problems / Applications" />}</h3>
        {submitted.length === 0 && <p className="problem-desc">{<Trans text="No problems submitted yet." />}</p>}
        {submitted.map((prob) => (
          <div className="problem-meta" key={prob.id}>• {prob.title[lang] || prob.title.hi} — <span className="badge badge-blue"><Trans text={prob.type === 'solved' ? 'Solved' : 'In Progress'} /></span></div>
        ))}
      </div>
    );
  } else if (user.role === 'student') {
    const myProjects = problems.filter((prob) => (prob.students || []).some((s) => s.email === user.email));
    extraSection = (
      <div className="card">
        <h3>{<Trans text="Projects & Solved Problems" />}</h3>
        {myProjects.length === 0 && <p className="problem-desc">{<Trans text="Not yet assigned to a project." />}</p>}
        {myProjects.map((prob) => <div className="problem-meta" key={prob.id}>• {prob.title[lang] || prob.title.hi}</div>)}
      </div>
    );
  } else if (user.role === 'faculty') {
    const myUniversity = p.university;
    const myProjects = problems.filter((prob) => prob.faculty?.email === user.email || (myUniversity && prob.allocation?.allocatedTo === myUniversity));
    extraSection = (
      <div className="card">
        <h3>{<Trans text="Assigned Problems & Students" />}</h3>
        {myProjects.map((prob) => (
          <div className="problem-meta" key={prob.id}>• {prob.title[lang] || prob.title.hi} — <Trans text={`${prob.students?.length || 0} students`} /></div>
        ))}
        {myProjects.length === 0 && <p className="problem-desc">{<Trans text="No assigned problems yet." />}</p>}
      </div>
    );
  } else if (user.role === 'university-admin') {
    const myUniversity = p.university;
    const managed = problems.filter((prob) => prob.allocation?.queue?.includes(myUniversity));
    extraSection = (
      <div className="card">
        <h3>{<Trans text="Managed Problems & Faculty Allocations" />}</h3>
        {managed.map((prob) => (
          <div className="problem-meta" key={prob.id}>• {prob.title[lang] || prob.title.hi} — {prob.faculty ? <Trans text={`Allocated to ${prob.faculty.name}`} /> : <Trans text="Not yet allocated" />}</div>
        ))}
        {managed.length === 0 && <p className="problem-desc">{<Trans text="No managed problems yet." />}</p>}
      </div>
    );
  } else if (user.role === 'government') {
    extraSection = (
      <div className="card">
        <h3>{<Trans text="Problem Lifecycle Overview" />}</h3>
        <div className="problem-meta"><Trans text="Total Submitted:" /> {problems.length}</div>
        <div className="problem-meta"><Trans text="Solved" />: {problems.filter((prob) => prob.type === 'solved').length}</div>
      </div>
    );
  } else if (user.role === 'industry') {
    extraSection = (
      <div className="card">
        <h3>{<Trans text="Collaboration Opportunities" />}</h3>
        <p className="problem-desc">{<Trans text="View collaboration proposals and connect with top students from the Leaderboard." />}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{<Trans text="My Profile" />}</h1>
          <p><Trans text={roleTitles[user.role]} /></p>
        </div>
        {!editing ? (
          <button className="btn btn-light" onClick={startEdit}>{<Trans text="Edit Profile" />}</button>
        ) : (
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={save}>{<Trans text="Save" />}</button>
            <button className="btn btn-light" onClick={() => setEditing(false)}>{<Trans text="Cancel" />}</button>
          </div>
        )}
      </div>

      <div className="card">
        <div className="profile-header">
          <div className="profile-avatar">{user.name?.[0]?.toUpperCase() || '?'}</div>
          <div>
            <h3 style={{ margin: 0 }}>{user.name}</h3>
            <div className="problem-meta">{user.email}</div>
          </div>
        </div>

        {!editing ? (
          <div className="profile-fields">
            <Field label="Full Name" value={user.name} />
            <Field label="Email Address" value={user.email} />
            <Field label="Role" value={roleTitles[user.role] || user.role} />
            {user.role === 'citizen' && <Field label="City" value={p.city} />}
            {roleFields.map((f) => (
              <Field key={f.key} label={f.label} value={p[f.key]} />
            ))}
            {Object.entries(p)
              .filter(([k]) => k !== 'city' && !roleFields.some((f) => f.key === k))
              .map(([key, value]) => (
                <Field key={key} label={key.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase())} value={value} />
              ))}
          </div>
        ) : (
          <div className="profile-fields role-fields">
            <div className="field">
              <label><Trans text="Full Name" /> *</label>
              <input type="text" value={draftName} onChange={(e) => setDraftName(e.target.value)} required />
            </div>
            <div className="field">
              <label><Trans text="Email Address" /> *</label>
              <input type="email" value={draftEmail} onChange={(e) => setDraftEmail(e.target.value)} required />
            </div>
            {user.role === 'citizen' && (
              <div className="field">
                <label><Trans text="City" /></label>
                <input type="text" value={draft.city || ''} onChange={(e) => setDraft((d) => ({ ...d, city: e.target.value }))} />
              </div>
            )}
            {roleFields.map((f) => (
              <div className="field" key={f.key}>
                <label><Trans text={f.label} />{f.required ? ' *' : ''}</label>
                {f.type === 'select' ? (
                  <select
                    value={draft[f.key] || ''}
                    onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                  >
                    <option value="">{<Trans text="Select…" />}</option>
                    {f.options.map((opt) => (
                      <option key={opt} value={opt}>{translateText(opt, lang)}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={Array.isArray(draft[f.key]) ? draft[f.key].join(', ') : (draft[f.key] || '')}
                    onChange={(e) => {
                      const val = e.target.value;
                      setDraft((d) => ({ ...d, [f.key]: f.isList ? val.split(',').map((s) => s.trim()).filter(Boolean) : val }));
                    }}
                    placeholder={translateText(f.label, lang)}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {extraSection}
    </div>
  );
}
