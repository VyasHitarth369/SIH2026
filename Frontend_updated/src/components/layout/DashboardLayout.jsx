import { Outlet } from 'react-router-dom';
import TopBar from './TopBar';
import Sidebar from './Sidebar';

export default function DashboardLayout() {
  return (
    <div className="app-shell">
      <TopBar />
      <div className="dashboard-layout">
        <Sidebar />
        <main className="dashboard-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
