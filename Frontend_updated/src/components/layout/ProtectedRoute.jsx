import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function ProtectedRoute({ allowRoles, children }) {
  const { user, homePath, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--text-muted, #666)' }}>Checking authentication...</p>
      </div>
    );
  }

  if (!user) return <Navigate to="/" replace />;

  if (allowRoles && Array.isArray(allowRoles)) {
    // Support aliases: university_admin / university-admin, industry_employee / industry
    const normalizedUserRole = user.role;
    const isAuthorized = allowRoles.some((r) => {
      if (r === normalizedUserRole) return true;
      if ((r === 'university-admin' || r === 'university_admin') && (normalizedUserRole === 'university_admin' || normalizedUserRole === 'university-admin')) return true;
      if ((r === 'industry' || r === 'industry_employee') && (normalizedUserRole === 'industry_employee' || normalizedUserRole === 'industry')) return true;
      return false;
    });

    if (!isAuthorized) {
      return <Navigate to={homePath} replace />;
    }
  }

  return children;
}
