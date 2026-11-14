
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function NewReview() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reviewId, setReviewId] = useState('');

  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();

    if (topic.trim().length < 3) {
      setError('Please enter a valid research topic.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/reviews/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: topic.trim(),
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to create review.');
      }

      setReviewId(result.review_id);

      localStorage.setItem('active_review_id', result.review_id);

    } catch (err) {
      setError(err.message || 'Unable to connect to the backend.');
    } finally {
      setLoading(false);
    }
  };

  if (reviewId) {
    return (
      <div className="wizard-success">
        <div className="success-icon">
          <i className="bi bi-check-lg"></i>
        </div>

        <h2>Review Started!</h2>

        <p>
          Your research topic has been submitted successfully.
          The AI pipeline is now processing your review.
        </p>

        <p>
          <strong>Review ID:</strong> {reviewId}
        </p>

        <div className="success-actions">
          <button
            className="btn btn-primary"
            onClick={() => navigate('/reviews')}
          >
            View My Reviews
          </button>

          <button
            className="btn btn-light"
            onClick={() => {
              setTopic('');
              setReviewId('');
            }}
          >
            Create Another Review
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="new-review-page">
      <div className="page-heading">
        <div>
          <h2>Create a New Review</h2>
          <p>
            Start an AI-assisted systematic literature review.
          </p>
        </div>
      </div>

      <div className="wizard-container">
        <div className="wizard-content">
          <h3>Research Topic</h3>

          <p className="section-description">
            Enter your research topic. The AI agents will generate
            the review protocol, research question, eligibility
            criteria, and search strategy.
          </p>

          <form onSubmit={submit}>
            <div className="mb-4">
              <label className="form-label">
                Research Topic *
              </label>

              <textarea
                className="form-control"
                rows="4"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            {error && (
              <div className="wizard-error">
                {error}
              </div>
            )}

            <div className="wizard-footer">
              <button
                type="button"
                className="btn btn-light"
                onClick={() => navigate('/reviews')}
                disabled={loading}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || topic.trim().length < 3}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2"></span>
                    Starting Review...
                  </>
                ) : (
                  <>
                    <i className="bi bi-play-fill me-2"></i>
                    Start Review
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}