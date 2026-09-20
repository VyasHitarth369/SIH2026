import { Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import DashboardLayout from './components/layout/DashboardLayout';
import ProtectedRoute from './components/layout/ProtectedRoute';

import ProblemsPage from './pages/citizen/ProblemsPage';
import AllProblemsPage from './pages/citizen/AllProblemsPage';
import AddProblemPage from './pages/citizen/AddProblemPage';
import GlobalSearchPage from './pages/citizen/GlobalSearchPage';
import ProblemValidationPage from './pages/citizen/ProblemValidationPage';

import StudentProjectsPage from './pages/student/ProjectsPage';
import StudentUniversityProblemsPage from './pages/student/UniversityProblemsPage';
import StudentMyProjectsPage from './pages/student/MyProjectsPage';
import StudentCertificatePage from './pages/student/CertificatePage';

import FacultyProjectsPage from './pages/faculty/ProjectsPage';
import FacultyStudentListPage from './pages/faculty/StudentListPage';
import UniversityProblemsPage from './pages/faculty/UniversityProblemsPage';

import UniversityAdminDashboardPage from './pages/university-admin/DashboardPage';
import IncomingProblemsPage from './pages/university-admin/IncomingProblemsPage';
import AllocationsPage from './pages/university-admin/AllocationsPage';
import MOUPage from './pages/university-admin/MOUPage';
import UniversityPastProjectsPage from './pages/university-admin/PastProjectsPage';

import GovernmentDashboardPage from './pages/government/DashboardPage';
import ActiveProblemsPage from './pages/government/ActiveProblemsPage';
import FacultiesPage from './pages/government/FacultiesPage';
import GovStudentsPage from './pages/government/StudentsPage';
import GovernmentMOUPage from './pages/government/MOUPage';
import PastSuccessfulProjectsPage from './pages/government/PastSuccessfulProjectsPage';

import IndustryDashboardPage from './pages/industry/DashboardPage';
import ProposalsPage from './pages/industry/ProposalsPage';
import CollaborationPage from './pages/industry/CollaborationPage';
import EmployeeMyProjectsPage from './pages/industry/EmployeeMyProjectsPage';
import IndustryMOUPage from './pages/industry/IndustryMOUPage';
import PastProjectsPage from './pages/PastProjectsPage';

import LeaderboardPage from './pages/LeaderboardPage';
import ProfilePage from './pages/ProfilePage';

const ALL_ROLES = [
  'citizen',
  'student',
  'faculty',
  'university_admin',
  'university-admin',
  'government',
  'industry_employee',
  'industry',
];

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage defaultMode="login" />} />
      <Route path="/signup" element={<LoginPage defaultMode="signup" />} />

      {/* Citizen */}
      <Route element={<ProtectedRoute allowRoles={['citizen']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/citizen/problems" element={<ProblemsPage />} />
        <Route path="/citizen/all-problems" element={<AllProblemsPage />} />
        <Route path="/citizen/add-problem" element={<AddProblemPage />} />
      </Route>

      {/* Citizen-initiated global search / validation flow (still citizen-only) */}
      <Route element={<ProtectedRoute allowRoles={['citizen']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/global-search" element={<GlobalSearchPage />} />
        <Route path="/problem-validation" element={<ProblemValidationPage />} />
      </Route>

      {/* Student */}
      <Route element={<ProtectedRoute allowRoles={['student']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/student/projects" element={<StudentProjectsPage />} />
        <Route path="/student/university-problems" element={<StudentUniversityProblemsPage />} />
        <Route path="/student/my-projects" element={<StudentMyProjectsPage />} />
        <Route path="/student/certificate" element={<StudentCertificatePage />} />
      </Route>

      {/* Faculty */}
      <Route element={<ProtectedRoute allowRoles={['faculty']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/faculty/projects" element={<FacultyProjectsPage />} />
        <Route path="/faculty/university-problems" element={<UniversityProblemsPage />} />
        <Route path="/faculty/students/:problemId" element={<FacultyStudentListPage />} />
      </Route>

      {/* University Administration */}
      <Route element={<ProtectedRoute allowRoles={['university_admin', 'university-admin']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/university-admin/dashboard" element={<UniversityAdminDashboardPage />} />
        <Route path="/university-admin/problems" element={<IncomingProblemsPage />} />
        <Route path="/university-admin/incoming-problems" element={<Navigate to="/university-admin/problems" replace />} />
        <Route path="/university-admin/allocations" element={<AllocationsPage />} />
        <Route path="/university-admin/mou" element={<MOUPage />} />
        <Route path="/university-admin/past-projects" element={<UniversityPastProjectsPage />} />
      </Route>

      {/* Government */}
      <Route element={<ProtectedRoute allowRoles={['government']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/government/dashboard" element={<GovernmentDashboardPage />} />
        <Route path="/government/add-problem" element={<AddProblemPage />} />
        <Route path="/government/active-problems" element={<ActiveProblemsPage />} />
        <Route path="/government/faculties" element={<FacultiesPage />} />
        <Route path="/government/students" element={<Navigate to="/leaderboard" replace />} />
        <Route path="/government/mou" element={<GovernmentMOUPage />} />
        <Route path="/government/solved" element={<PastSuccessfulProjectsPage />} />
      </Route>

      {/* Industry Employee & Manager */}
      <Route element={<ProtectedRoute allowRoles={['industry_employee', 'industry']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/industry-employee/dashboard" element={<IndustryDashboardPage />} />
        <Route path="/industry-employee/add-problem" element={<AddProblemPage />} />
        <Route path="/industry-employee/proposals" element={<ProposalsPage />} />
        <Route path="/industry-employee/collaboration" element={<CollaborationPage />} />
        <Route path="/industry-employee/past-projects" element={<PastProjectsPage />} />
        <Route path="/industry-employee/my-projects" element={<EmployeeMyProjectsPage />} />
        <Route path="/industry-employee/mou" element={<IndustryMOUPage />} />
        {/* Backward-compatible aliases */}
        <Route path="/industry/dashboard" element={<Navigate to="/industry-employee/dashboard" replace />} />
        <Route path="/industry/proposals" element={<Navigate to="/industry-employee/proposals" replace />} />
        <Route path="/industry/collaboration" element={<Navigate to="/industry-employee/collaboration" replace />} />
        <Route path="/industry/collaborations" element={<Navigate to="/industry-employee/collaboration" replace />} />
        <Route path="/industry/past-projects" element={<Navigate to="/industry-employee/past-projects" replace />} />
        <Route path="/industry/mou" element={<Navigate to="/industry-employee/mou" replace />} />
      </Route>

      {/* Shared across roles */}
      <Route element={<ProtectedRoute allowRoles={['student', 'faculty', 'industry_employee', 'industry', 'government']}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/leaderboard" element={<LeaderboardPage />} />
      </Route>

      <Route element={<ProtectedRoute allowRoles={ALL_ROLES}><DashboardLayout /></ProtectedRoute>}>
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<HomePage />} />
    </Routes>
  );
}
