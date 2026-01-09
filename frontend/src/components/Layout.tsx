import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '■' },
    { path: '/monitoring', label: 'Monitoring', icon: '●' },
    { path: '/predictions', label: 'Predictions', icon: '▲' },
    { path: '/models', label: 'Model Management', icon: '◆' },
    { path: '/analytics', label: 'Analytics', icon: '▼' },
  ];

  return (
    <div className="layout">
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h1 className="sidebar-title">Churn Platform</h1>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${
                location.pathname === item.path ? 'active' : ''
              }`}
            >
              <span className="nav-icon">{item.icon}</span>
              {sidebarOpen && <span className="nav-label">{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="version-info">
            {sidebarOpen && (
              <>
                <div className="version-label">Platform Version</div>
                <div className="version-number">v0.1.0</div>
              </>
            )}
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="top-header">
          <div className="header-left">
            <h2 className="header-title">
              {navItems.find((item) => item.path === location.pathname)?.label ||
                'Dashboard'}
            </h2>
          </div>
          <div className="header-right">
            <div className="header-status">
              <span className="status-indicator status-healthy"></span>
              <span className="status-text">All Systems Operational</span>
            </div>
          </div>
        </header>

        <div className="content-wrapper">{children}</div>
      </main>
    </div>
  );
};

export default Layout;
