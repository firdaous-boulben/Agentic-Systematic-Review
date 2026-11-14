import { useLocation } from 'react-router-dom';

const pageTitles = {
  '/': 'Dashboard',
  '/reviews': 'My Reviews',
  '/new-review': 'Create a Review',
  '/reports': 'Reports',
  '/about': 'About',
};

export default function Header() {
  const location = useLocation();
  const title = pageTitles[location.pathname] || 'Review Workspace';

  return (
    <header className="top-header">
      <div>
        <h6>{title}</h6>
        <span>Research workspace / {title}</span>
      </div>

      <div className="header-actions">
        <button className="header-icon" title="Notifications">
          <i className="bi bi-bell"></i>
          <span className="notification-dot"></span>
        </button>

        <div className="header-divider"></div>

        <div className="header-user">
          <div className="profile-avatar">FB</div>
          <div>
            <strong>Firdaous Boulben</strong>
            <span>Researcher account</span>
          </div>
        </div>
      </div>
    </header>
  );
}