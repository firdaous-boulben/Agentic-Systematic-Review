
import { useState } from 'react';
import { useParams } from 'react-router-dom';

export default function Screening({ review }) {
  const { id } = useParams();

  const [selectedId, setSelectedId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  if (!review) return null;

  const papers = review.screening_results || [];
  const included = review.included_papers || [];
  const excluded = review.excluded_papers || [];
  const uncertain = review.uncertain_papers || [];

  const selectedPaper =
    papers.find(
      (paper) => (paper.openalex_id || paper.doi) === selectedId
    ) || papers[0];

  const getStatusClass = (decision) => {
    const value = (decision || '').toLowerCase();

    if (value === 'include') return 'included';
    if (value === 'exclude') return 'excluded';
    if (value === 'maybe' || value === 'uncertain') return 'maybe';

    return 'unreviewed';
  };

  const approveScreening = async () => {
    setSubmitting(true);
    setError('');
    setMessage('');

    try {
      const response = await fetch(`/api/reviews/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approved: true,
          uncertain_decisions: {},
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Could not approve screening.');
      }

      setMessage('Screening approved. The review is continuing.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="screening-page">

      {/* Header */}
      <div className="screening-heading">
        <div>
          <h3>Study Screening</h3>
          <p>
            Review the papers classified by the screening agent.
          </p>
        </div>

        <span className="screening-phase">
          {review.status === 'awaiting_human_review'
            ? 'Pending approval'
            : review.status === 'completed'
            ? 'Completed'
            : 'Automated screening'}
        </span>
      </div>

      {/* Statistics */}
      <div className="screening-stats">
        <div className="screening-stat">
          <span>Total screened</span>
          <strong>{papers.length}</strong>
        </div>

        <div className="screening-stat">
          <span>Included</span>
          <strong className="included-number">{included.length}</strong>
        </div>

        <div className="screening-stat">
          <span>Excluded</span>
          <strong className="excluded-number">{excluded.length}</strong>
        </div>

        <div className="screening-stat">
          <span>Uncertain</span>
          <strong className="maybe-number">{uncertain.length}</strong>
        </div>
      </div>

      {/* Paper review workspace */}
      {papers.length === 0 ? (
        <div className="screening-empty">
          <h4>No screening results available</h4>
          <p>
            Papers will appear here once the screening agent has processed them.
          </p>
        </div>
      ) : (
        <div className="screening-workspace">

          {/* Selected paper */}
          <div className="paper-review">
            <div className="paper-navigation">
              <span>
                Paper {papers.indexOf(selectedPaper) + 1} of {papers.length}
              </span>

              <span>
                {selectedPaper.year || 'Year unavailable'}
              </span>
            </div>

            <div className="paper-card">
              <div className="paper-card-top">
                <span className="paper-type">
                  {selectedPaper.type || selectedPaper.journal || 'Publication'}
                </span>

                <span className={`decision-label ${getStatusClass(selectedPaper.screening_decision)}`}>
                  {selectedPaper.screening_decision || 'Unreviewed'}
                </span>
              </div>

              <h4>{selectedPaper.title}</h4>

              <div className="paper-metadata">
                <span>
                  <i className="bi bi-people" />
                  {(selectedPaper.authors || []).join(', ') || 'Authors unavailable'}
                </span>

                {selectedPaper.year && (
                  <span>
                    <i className="bi bi-calendar3" />
                    {selectedPaper.year}
                  </span>
                )}

                {selectedPaper.source && (
                  <span>
                    <i className="bi bi-database" />
                    {selectedPaper.source}
                  </span>
                )}

                {selectedPaper.journal && (
                  <span>
                    <i className="bi bi-journal-text" />
                    {selectedPaper.journal}
                  </span>
                )}
              </div>

              <div className="paper-abstract-heading">
                <h5>Abstract</h5>
              </div>

              <p className="paper-abstract">
                {selectedPaper.abstract || 'No abstract available.'}
              </p>

              {selectedPaper.screening_reason && (
                <div className="screening-reason">
                  <strong>Screening justification</strong>
                  <p>{selectedPaper.screening_reason}</p>
                </div>
              )}

              {(selectedPaper.doi || selectedPaper.landing_page_url) && (
                <a
                  href={selectedPaper.landing_page_url || selectedPaper.doi}
                  target="_blank"
                  rel="noreferrer"
                  className="paper-link"
                >
                  View publication
                  <i className="bi bi-box-arrow-up-right" />
                </a>
              )}
            </div>
          </div>

          {/* Paper queue */}
          <aside className="screening-sidebar">
            <h5>Screened Papers ({papers.length})</h5>

            <div className="paper-queue">
              {papers.map((paper, index) => {
                const paperId = paper.openalex_id || paper.doi || String(index);
                const isActive =
                  (selectedPaper.openalex_id || selectedPaper.doi || String(papers.indexOf(selectedPaper))) === paperId;

                return (
                  <button
                    key={paperId}
                    type="button"
                    className={`queue-item ${isActive ? 'active' : ''}`}
                    onClick={() => setSelectedId(paperId)}
                  >
                    <div className="queue-item-top">
                      <span>Paper {index + 1}</span>
                      <span className={`queue-status ${getStatusClass(paper.screening_decision)}`}>
                        {paper.screening_decision || 'Pending'}
                      </span>
                    </div>

                    <p>{paper.title}</p>
                  </button>
                );
              })}
            </div>
          </aside>
        </div>
      )}

      {/* Approval */}
      {review.status === 'awaiting_human_review' && (
        <div className="screening-approval">
          <div>
            <h5>Screening review required</h5>
            <p>
              Check the screening results before approving the next stage.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={approveScreening}
            disabled={submitting}
          >
            {submitting ? 'Submitting...' : 'Approve Screening'}
          </button>
        </div>
      )}

      {message && <p className="screening-message success">{message}</p>}
      {error && <p className="screening-message error">{error}</p>}

    </div>
  );
}
