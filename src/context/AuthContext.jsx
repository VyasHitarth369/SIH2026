import { createContext, useContext, useState, useMemo } from 'react';

const AuthContext = createContext(null);

// New stakeholder model (the old "Authority" role and the "university"
// role with a uniRole sub-selector have been removed). Student, Faculty,
// and University Administration are now distinct top-level roles.
const ROLE_HOME = {
  citizen: '/citizen/problems',
  student: '/student/projects',
  faculty: '/faculty/projects',
  'university-admin': '/university-admin/dashboard',
  government: '/government/dashboard',
  industry: '/industry-employee/dashboard',
};

export const ROLES = [
  { value: 'citizen', label: 'Citizen', labelKey: 'roleOptCitizen' },
  { value: 'student', label: 'Student', labelKey: 'roleOptStudent' },
  { value: 'faculty', label: 'Faculty', labelKey: 'roleOptFaculty' },
  { value: 'university-admin', label: 'University Administration', labelKey: 'roleOptUniversityAdmin' },
  { value: 'government', label: 'Government', labelKey: 'roleOptGovernment' },
  { value: 'industry', label: 'Industry Employee', labelKey: 'roleOptIndustry' },
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  /**
   * `profile` carries every role-specific field collected at login/registration
   * (university, department, company, skills, etc). Since there is no real
   * backend, this is stored purely in memory for the session.
   */
  const login = ({ name, email, password, role, profile }) => {
    if (!email || !email.trim()) throw new Error('Email is required.');
    if (!password || !password.trim()) throw new Error('Password is required.');
    if (!role) throw new Error('Please select a stakeholder role.');

    const session = {
      name: name?.trim() || 'User',
      email: email.trim(),
      role,
      profile: profile || {},
    };
    setUser(session);
    return session;
  };

  const updateProfile = (patch) => {
    setUser((prev) => {
      if (!prev) return prev;
      const { name, email, ...rest } = patch;
      return {
        ...prev,
        name: name !== undefined && name !== '' ? name : prev.name,
        email: email !== undefined && email !== '' ? email : prev.email,
        profile: { ...prev.profile, ...rest },
      };
    });
  };

  const logout = () => setUser(null);

  const homePath = useMemo(() => {
    if (!user) return '/';
    return ROLE_HOME[user.role] || '/';
  }, [user]);

  const value = { user, login, logout, updateProfile, homePath, isAuthed: !!user };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
