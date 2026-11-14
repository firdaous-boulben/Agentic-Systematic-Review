import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const getStatusLabel = (status) => {
  const labels = {
    queued: 'Queued',
    running: 'In Progress',
    awaiting_human_review: 'Awaiting Review',
    completed: 'Completed',
    failed: 'Failed',
  };

  return labels[status] || status;
};

const getStatusClass = (status) => {
  if (status === 'completed') return 'completed';
  if (status === 'failed') return 'failed';
  if (status === 'awaiting_human_review') return 'awaiting';
  return 'in-progress';
};

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const response = await fetch('/api/reviews/');

        if (!response.ok) {
          throw new Error('Failed to load reviews.');
        }

        const data = await response.json();
        setReviews(data);
      } catch (err) {
        setError(err.message || 'Unable to connect to the backend.');
      } finally {
        setLoading(false);
      }
    };

    fetchReviews();
  }, []);

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch = review.topic
      .toLowerCase()
      .includes(search.toLowerCase());

    const matchesStatus =
      status === 'All' || getStatusLabel(review.status) === status;

    return matchesSearch && matchesStatus;
  });

  const completedCount = reviews.filter(
    (review) => review.status === 'completed'
  ).length;

  const inProgressCount = reviews.filter(
    (review) =>
      ['running', 'queued'].includes(review.status)
  ).length;

  const totalPapers = reviews.reduce(
    (total, review) => total + review.papers,
    0
  );

  return (
    <div className="reviews-page">
      <div className="page-intro">
        <div>
          <h3>My Reviews</h3>
          <p>Manage and monitor all your systematic literature reviews.</p>
        </div>

        <Link to="/new-review" className="btn btn-primary-custom">
          <i className="bi bi-plus-lg"></i>
          Create New Review
        </Link>
      </div>

      <div className="review-overview">
        <div>
          <span>Total Reviews</span>
          <h4>{reviews.length}</h4>
        </div>
        <div>
          <span>In Progress</span>
          <h4>{inProgressCount}</h4>
        </div>
        <div>
          <span>Completed</span>
          <h4>{completedCount}</h4>
        </div>
        <div>
          <span>Total Papers</span>
          <h4>{totalPapers.toLocaleString()}</h4>
        </div>
      </div>

      <div className="reviews-toolbar">
        <div className="review-search">
          <i className="bi bi-search"></i>
          <input
            type="text"
            placeholder="Search reviews by topic..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="form-select review-filter"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="All">All statuses</option>
          <option value="Queued">Queued</option>
          <option value="In Progress">In Progress</option>
          <option value="Awaiting Review">Awaiting Review</option>
          <option value="Completed">Completed</option>
          <option value="Failed">Failed</option>
        </select>
      </div>

      <div className="reviews-list">
        <div className="reviews-list-header">
          <h5>All Research Projects</h5>
          <span>{filteredReviews.length} reviews found</span>
        </div>

        {loading ? (
          <div className="empty-reviews">
            <span className="spinner-border spinner-border-sm me-2"></span>
            Loading reviews...
          </div>
        ) : error ? (
          <div className="empty-reviews">
            <h6>Unable to load reviews</h6>
            <p>{error}</p>
          </div>
        ) : filteredReviews.length > 0 ? (
          filteredReviews.map((review) => (
            <div className="review-list-item" key={review.id}>
              <div className="review-list-icon">
                <i className="bi bi-journal-text"></i>
              </div>

              <div className="review-list-info">
                <div className="review-list-title">
                  <h6>{review.topic}</h6>

                  <span className={`status-badge ${getStatusClass(review.status)}`}>
                    <span></span>
                    {getStatusLabel(review.status)}
                  </span>
                </div>

                <div className="review-list-meta">
                  <span>
                    <i className="bi bi-file-earmark-text"></i>
                    {review.papers} papers
                  </span>

                  <span>
                    {review.created_at ? (
                      <>
                        <i className="bi bi-calendar3"></i>
                        Created {new Date(review.created_at).toLocaleDateString()}
                      </>
                    ) : (
                      <>
                        <i className="bi bi-calendar3"></i>
                        Creation date unavailable
                      </>
                    )}
                  </span>
                </div>
              </div>

              <Link
                to={`/reviews/${review.id}`}
                className="review-open-btn"
                title="Open review"
              >
                <i className="bi bi-arrow-up-right"></i>
              </Link>
            </div>
          ))
        ) : (
          <div className="empty-reviews">
            <i className="bi bi-search"></i>
            <h6>{reviews.length === 0 ? 'No reviews yet' : 'No reviews found'}</h6>
            <p>
              {reviews.length === 0
                ? 'Create a new review to get started.'
                : 'Try changing your search or filters.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}