
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import StatCard from '../components/dashboard/StatCard';
import ReviewCard from '../components/dashboard/ReviewCard';

export default function Dashboard() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const response = await fetch('/api/reviews/');

        if (!response.ok) {
          throw new Error('Failed to load dashboard data.');
        }

        const data = await response.json();
        setReviews(data);
      } catch (err) {
        setError(err.message || 'Something went wrong.');
      } finally {
        setLoading(false);
      }
    };

    fetchReviews();
  }, []);

  const statistics = useMemo(() => {
    const active = reviews.filter((review) =>
      ['queued', 'running', 'awaiting_human_review'].includes(review.status)
    ).length;

    const completed = reviews.filter(
      (review) => review.status === 'completed'
    ).length;

    const papers = reviews.reduce(
      (total, review) => total + (review.papers || 0),
      0
    );

    return [
      {
        title: 'Total Reviews',
        value: reviews.length,
        icon: 'bi-journals',
        color: 'blue',
      },
      {
        title: 'Active Reviews',
        value: active,
        icon: 'bi-arrow-repeat',
        color: 'teal',
      },
      {
        title: 'Completed Reviews',
        value: completed,
        icon: 'bi-check-circle',
        color: 'green',
      },
      {
        title: 'Processed Papers',
        value: papers,
        icon: 'bi-file-earmark-text',
        color: 'orange',
      },
    ];
  }, [reviews]);

  const recentReviews = useMemo(
    () =>
      [...reviews]
        .sort((a, b) => {
          if (!a.created_at) return 1;
          if (!b.created_at) return -1;
          return new Date(b.created_at) - new Date(a.created_at);
        })
        .slice(0, 3),
    [reviews]
  );

  return (
    <div className="dashboard">
      <section className="welcome-section">
        <div>
          <p className="welcome-date">RESEARCH OVERVIEW</p>
          <h3>Welcome back, Firdaous!</h3>
          <p>
            Manage your systematic reviews and track your AI research
            workflows from one place.
          </p>
        </div>

        <Link to="/new-review" className="btn btn-primary-custom">
          <i className="bi bi-plus-lg"></i>
          New Review
        </Link>
      </section>

      {error && (
        <div className="dashboard-error">
          {error}
        </div>
      )}

      <section className="stats-grid">
        {statistics.map((item) => (
          <StatCard key={item.title} item={item} />
        ))}
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <h5>Recent Reviews</h5>
            <p>Your latest research projects</p>
          </div>

          <Link to="/reviews" className="view-all">
            View all <i className="bi bi-arrow-right"></i>
          </Link>
        </div>

        {loading ? (
          <p className="dashboard-message">Loading reviews...</p>
        ) : recentReviews.length > 0 ? (
          <div className="reviews-grid">
            {recentReviews.map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>
        ) : (
          <div className="dashboard-message">
            <p>No reviews yet.</p>
            <Link to="/new-review">Create your first review</Link>
          </div>
        )}
      </section>

      <section className="dashboard-bottom">
        <div className="dashboard-panel quick-panel">
          <div className="section-heading">
            <div>
              <h5>Quick Actions</h5>
              <p>Continue your research</p>
            </div>
          </div>

          <Link to="/new-review" className="quick-action">
            <div className="quick-icon blue">
              <i className="bi bi-plus-circle"></i>
            </div>
            <div>
              <strong>Create a new review</strong>
              <span>Start a systematic literature review</span>
            </div>
            <i className="bi bi-chevron-right"></i>
          </Link>

          <Link to="/reviews" className="quick-action">
            <div className="quick-icon teal">
              <i className="bi bi-journals"></i>
            </div>
            <div>
              <strong>Browse your reviews</strong>
              <span>Manage existing research projects</span>
            </div>
            <i className="bi bi-chevron-right"></i>
          </Link>

          <Link to="/reports" className="quick-action">
            <div className="quick-icon green">
              <i className="bi bi-file-earmark-pdf"></i>
            </div>
            <div>
              <strong>View reports</strong>
              <span>Access generated research outputs</span>
            </div>
            <i className="bi bi-chevron-right"></i>
          </Link>
        </div>
      </section>
    </div>
  );
}