import Sidebar from './Sidebar';
import Header from './Header';

export default function MainLayout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />

      <div className="main-section">
        <Header />
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}