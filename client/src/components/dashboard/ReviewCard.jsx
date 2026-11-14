import { Link } from 'react-router-dom';

const statusLabels = {
  queued: 'Queued',
  running: 'In Progress',
  awaiting_human_review: 'Awaiting Review',
  completed: 'Completed',
  failed: 'Failed',
};

const statusClasses = {
  queued: 'queued',
  running: 'in-progress',
  awaiting_human_review: 'awaiting',
  completed: 'completed',
  failed: 'failed',
};

function formatDate(date) {
  if (!date) return 'Date unavailable';

  return new Date(date).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function ReviewCard({ review }) {
  const status = review.status || 'queued';

  return (
    <Link
      to={`/reviews/${review.id}`}
      className="review-card dashboard-review-card"
    >
      <div className="review-card-top">
        <span className="review-category">Systematic Review</span>

        <span className={`status-badge ${statusClasses[status] || ''}`}>
          <span></span>
          {statusLabels[status] || status}
        </span>
      </div>

      <h6>{review.topic || 'Untitled Review'}</h6>

      <div className="review-meta">
        <span>
          <i className="bi bi-file-earmark-text"></i>
          {review.papers || 0} papers
        </span>

        <span>
          <i className="bi bi-calendar3"></i>
          {formatDate(review.created_at)}
        </span>
      </div>

      <div className="review-card-footer">
        <span>Review</span>
        <span className="review-open-link">
          Open review <i className="bi bi-arrow-right"></i>
        </span>
      </div>
    </Link>
  );
}
