import { NavLink } from 'react-router-dom';
import logo from '../../assets/logo.png';

const navigation = [
  {
    title: 'WORKSPACE',
    items: [
      { label: 'Dashboard', icon: 'bi-grid-1x2-fill', path: '/' },
      { label: 'My Reviews', icon: 'bi-journals', path: '/reviews' },
      { label: 'New Review', icon: 'bi-plus-circle', path: '/new-review' },
    ],
  },
  {
    title: 'RESOURCES',
    items: [
      { label: 'Reports', icon: 'bi-file-earmark-text', path: '/reports' },
      { label: 'About', icon: 'bi-info-circle', path: '/about' },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <img src={logo} alt="ReviewAI logo" />
        </div>
        <div>
          <h5>ReviewAI</h5>
          <span>Research workspace</span>
        </div>
      </div>

      <div className="sidebar-content">
        {navigation.map((group) => (
          <div className="nav-group" key={group.title}>
            <p className="nav-heading">{group.title}</p>

            {group.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''}`
                }
              >
                <i className={`bi ${item.icon}`}></i>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-footer">
          <span>ReviewAI</span>
          <small>v1.0.0</small>
        </div>
      </div>
    </aside>
  );
}