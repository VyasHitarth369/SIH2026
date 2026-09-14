import { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { supabase } from '../services/supabaseClient';
import { apiClient } from '../services/apiClient';

const AuthContext = createContext(null);

// Standardized role home paths with backwards-compatible aliases
const ROLE_HOME = {
  citizen: '/citizen/problems',
  student: '/student/projects',
  faculty: '/faculty/projects',
  university_admin: '/university-admin/dashboard',
  'university-admin': '/university-admin/dashboard',
  government: '/government/dashboard',
  industry_employee: '/industry-employee/dashboard',
  industry: '/industry-employee/dashboard',
};

export const ROLES = [
  { value: 'citizen', label: 'Citizen', labelKey: 'roleOptCitizen' },
  { value: 'student', label: 'Student', labelKey: 'roleOptStudent' },
  { value: 'faculty', label: 'Faculty', labelKey: 'roleOptFaculty' },
  { value: 'university_admin', label: 'University Administration', labelKey: 'roleOptUniversityAdmin' },
  { value: 'government', label: 'Government', labelKey: 'roleOptGovernment' },
  { value: 'industry_employee', label: 'Industry Employee', labelKey: 'roleOptIndustry' },
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Helper to fetch authoritative profile from backend using the current token
  const fetchAuthoritativeUser = useCallback(async () => {
    const res = await apiClient.get('/auth/me');
    if (!res || !res.success || !res.data) {
      throw new Error('Failed to retrieve user profile from backend');
    }
    return res.data;
  }, []);

  // Restore session from Supabase on mount
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session && isMounted) {
          try {
            const authoritativeUser = await fetchAuthoritativeUser();
            if (isMounted) {
              setUser(authoritativeUser);
            }
          } catch (profileErr) {
            console.warn('Could not load authoritative profile on restore:', profileErr.message);
            if (isMounted) setUser(null);
          }
        } else if (isMounted) {
          setUser(null);
        }
      } catch (err) {
        console.warn('Failed to restore Supabase session:', err.message);
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    restoreSession();

    // Listen for auth state changes; keep callback synchronous
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        if (isMounted) setUser(null);
      } else if (event === 'TOKEN_REFRESHED' || event === 'USER_UPDATED') {
        // Safe async call outside the synchronous callback
        setTimeout(() => {
          if (isMounted) {
            fetchAuthoritativeUser()
              .then((authData) => {
                if (isMounted) setUser(authData);
              })
              .catch(() => {});
          }
        }, 0);
      }
    });

    return () => {
      isMounted = false;
      subscription?.unsubscribe();
    };
  }, [fetchAuthoritativeUser]);

  /**
   * Login strictly via Supabase Auth email/password.
   * Role is never selected on login; it is authoritatively loaded from /api/auth/me.
   */
  const login = async ({ email, password }) => {
    if (!email || !email.trim()) throw new Error('Email is required.');
    if (!password || !password.trim()) throw new Error('Password is required.');

    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password: password.trim(),
    });

    if (error) {
      throw new Error(error.message || 'Login failed');
    }

    if (!data.session) {
      throw new Error('No session returned. Please check your account credentials.');
    }

    const authoritativeUser = await fetchAuthoritativeUser();
    setUser(authoritativeUser);
    return authoritativeUser;
  };

  /**
   * Signup creates a Supabase Auth user.
   * Submitted role is strictly registration metadata (never authoritative).
   */
  const signup = async ({ name, email, password, role, profile }) => {
    if (!email || !email.trim()) throw new Error('Email is required.');
    if (!password || !password.trim()) throw new Error('Password is required.');

    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password: password.trim(),
      options: {
        data: {
          full_name: name?.trim() || '',
          role: role || 'citizen',
          ...(profile || {}),
        },
      },
    });

    if (error) {
      throw new Error(error.message || 'Signup failed');
    }

    // If an active session is returned immediately, establish authenticated state
    if (data.session) {
      try {
        const authoritativeUser = await fetchAuthoritativeUser();
        setUser(authoritativeUser);
        return { user: authoritativeUser, session: data.session, needsEmailConfirmation: false };
      } catch {
        // Fallback if backend profile lookup is slightly delayed
      }
    }

    // Otherwise email confirmation is required; user is not yet authenticated
    return {
      user: data.user,
      session: null,
      needsEmailConfirmation: true,
    };
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.warn('Sign out warning:', err.message);
    } finally {
      setUser(null);
    }
  };

  const updateProfile = (patch) => {
    setUser((prev) => {
      if (!prev) return prev;
      const { full_name, name, email, ...rest } = patch;
      return {
        ...prev,
        full_name: full_name || name || prev.full_name,
        email: email || prev.email,
        profile: { ...(prev.profile || {}), ...rest },
      };
    });
  };

  const homePath = useMemo(() => {
    if (!user) return '/';
    return ROLE_HOME[user.role] || '/';
  }, [user]);

  const value = {
    user,
    login,
    signup,
    logout,
    updateProfile,
    homePath,
    isAuthed: !!user,
    isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
