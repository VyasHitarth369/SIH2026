import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function ProtectedRoute({ allowRoles, children }) {
  const { user, homePath } = useAuth();

  if (!user) return <Navigate to="/" replace />;
  if (allowRoles && !allowRoles.includes(user.role)) return <Navigate to={homePath} replace />;

  return children;
}
