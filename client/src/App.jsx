import { Routes, Route } from 'react-router-dom';

import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import Reviews from './pages/Reviews';
import NewReview from './pages/NewReview';
import ReviewWorkspace from './pages/ReviewWorkspace';
import Reports from './pages/Reports';
import About from './pages/About';

function Placeholder({ title }) {
  return (
    <div className="placeholder-page">
      <i className="bi bi-cone-striped"></i>
      <h4>{title}</h4>
      <p>This section will be implemented in the next development steps.</p>
    </div>
  );
}

export default function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/reviews/:id" element={<ReviewWorkspace />} />
        <Route path="/new-review" element={<NewReview />} />
        <Route path="/reviews" element={<Reviews />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </MainLayout>
  );
}