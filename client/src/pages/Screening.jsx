import { useState } from 'react';
import { useParams } from 'react-router-dom';

export default function Screening({ review }) {
  const { id } = useParams();

  const [selectedId, setSelectedId] = useState(null);
  const [decisionSelections, setDecisionSelections] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  if (!review) return null;

  const papers = review.screening_results || [];
  const included = review.included_papers || [];
  const excluded = review.excluded_papers || [];
  const uncertain = review.uncertain_papers || [];
  const disagreements = review.screening_disagreements || [];
  const agreement = review.screening_agreement || {};

  const getPaperId = (paper, index = 0) =>
    String(
      paper.screening_paper_id ||
      paper.openalex_id ||
      paper.doi ||
      paper.title ||
      `paper_${index}`
    );

  const selectedPaper =
    papers.find((paper, index) => getPaperId(paper, index) === selectedId) ||
    papers[0];

  const getStatusClass = (decision) => {
    const value = (decision || '').toLowerCase();

    if (value === 'include') return 'included';
    if (value === 'exclude') return 'excluded';
    if (value === 'maybe' || value === 'uncertain') return 'maybe';

    return 'unreviewed';
  };

  const updateDecision = (paper, index, decision) => {
    const paperId = getPaperId(paper, index);

    setDecisionSelections((previous) => ({
      ...previous,
      [paperId]: decision,
    }));
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
          uncertain_decisions: decisionSelections,
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

  const selectedCount = Object.values(decisionSelections).filter(
    (decision) => decision === 'include' || decision === 'exclude'
  ).length;

  if (!selectedPaper && papers.length === 0) {
    return (
      <div className="screening-page">
        <div className="screening-empty">
          <h4>No screening results available</h4>
          <p>
            Papers will appear here once the screening agent has processed them.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="screening-page">

      {/* Header */}
      <div className="screening-heading">
        <div>
          <h3>Study Screening</h3>
          <p>
            Review the independent assessments from both AI reviewers.
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

      {/* Screening statistics */}
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

      {/* Dual screening agreement */}
      <section className="screening-agreement">
        <div className="section-heading">
          <div>
            <h4>Inter-reviewer Agreement</h4>
            <p>Comparison of the two independent AI assessments.</p>
          </div>
        </div>

        <div className="screening-agreement-stats">
          <div className="screening-stat">
            <span>Assessed by both</span>
            <strong>{agreement.assessed_pairs ?? 0}</strong>
          </div>

          <div className="screening-stat">
            <span>Agreements</span>
            <strong>{agreement.agreements ?? 0}</strong>
          </div>

          <div className="screening-stat">
            <span>Disagreements</span>
            <strong>{agreement.disagreements ?? 0}</strong>
          </div>

          <div className="screening-stat">
            <span>Agreement rate</span>
            <strong>
              {agreement.agreement_percentage != null
                ? `${agreement.agreement_percentage}%`
                : 'N/A'}
            </strong>
          </div>

          <div className="screening-stat">
            <span>Cohen's kappa</span>
            <strong>
              {agreement.cohens_kappa != null
                ? agreement.cohens_kappa
                : 'N/A'}
            </strong>
          </div>
        </div>

        {agreement.note && (
          <p className="screening-note">{agreement.note}</p>
        )}

        <p className="screening-note">
          Agreement statistics include only papers successfully assessed by
          both reviewers. Papers excluded by the publication-year rule or
          missing an abstract are not counted.
        </p>
      </section>

      {/* Paper review workspace */}
      {papers.length > 0 && (
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
                  {selectedPaper.type ||
                    selectedPaper.journal ||
                    'Publication'}
                </span>

                <span
                  className={`decision-label ${getStatusClass(
                    selectedPaper.screening_decision
                  )}`}
                >
                  {selectedPaper.screening_decision || 'Unreviewed'}
                </span>
              </div>

              <h4>{selectedPaper.title}</h4>

              <div className="paper-metadata">
                <span>
                  <i className="bi bi-people" />
                  {(selectedPaper.authors || []).join(', ') ||
                    'Authors unavailable'}
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

              {/* Reviewer assessments */}
              {selectedPaper.reviewer_assessments && (
                <div className="reviewer-assessments">
                  <h5>Reviewer Assessments</h5>

                  {['reviewer_a', 'reviewer_b'].map((reviewerId) => {
                    const assessment =
                      selectedPaper.reviewer_assessments[reviewerId];

                    if (!assessment) return null;

                    const reviewerLabel =
                      reviewerId === 'reviewer_a'
                        ? 'Reviewer A'
                        : 'Reviewer B';

                    return (
                      <div className="reviewer-assessment" key={reviewerId}>
                        <div className="reviewer-assessment-heading">
                          <strong>{reviewerLabel}</strong>

                          <span
                            className={`decision-label ${getStatusClass(
                              assessment.decision
                            )}`}
                          >
                            {assessment.decision || 'Unavailable'}
                          </span>
                        </div>

                        <p>
                          {assessment.reason ||
                            'No justification available.'}
                        </p>

                        {assessment.status === 'technical_error' && (
                          <span className="screening-note">
                            Assessment failed and requires manual review.
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {selectedPaper.dual_screening_status ===
                'needs_adjudication' && (
                <p className="screening-warning">
                  The reviewers disagreed on this paper. A human decision is
                  required.
                </p>
              )}

              {(selectedPaper.doi ||
                selectedPaper.landing_page_url) && (
                <a
                  href={
                    selectedPaper.landing_page_url ||
                    (selectedPaper.doi.startsWith('http')
                      ? selectedPaper.doi
                      : `https://doi.org/${selectedPaper.doi}`)
                  }
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
                const paperId = getPaperId(paper, index);
                const isActive =
                  getPaperId(selectedPaper, papers.indexOf(selectedPaper)) ===
                  paperId;

                return (
                  <button
                    key={paperId}
                    type="button"
                    className={`queue-item ${isActive ? 'active' : ''}`}
                    onClick={() => setSelectedId(paperId)}
                  >
                    <div className="queue-item-top">
                      <span>Paper {index + 1}</span>

                      <span
                        className={`queue-status ${getStatusClass(
                          paper.screening_decision
                        )}`}
                      >
                        {paper.screening_decision || 'Pending'}
                      </span>
                    </div>

                    <p>{paper.title}</p>

                    {paper.dual_screening_status ===
                      'needs_adjudication' && (
                      <small>Reviewer disagreement</small>
                    )}
                  </button>
                );
              })}
            </div>
          </aside>
        </div>
      )}

      {/* Human adjudication */}
      {review.status === 'awaiting_human_review' && uncertain.length > 0 && (
        <section className="screening-adjudication">
          <div className="section-heading">
            <div>
              <h4>Human Adjudication</h4>
              <p>
                Resolve reviewer disagreements and papers that require manual
                assessment.
              </p>
            </div>

            <span>
              {selectedCount} of {uncertain.length} resolved
            </span>
          </div>

          <div className="adjudication-list">
            {uncertain.map((paper, index) => {
              const paperId = getPaperId(paper, index);
              const currentDecision = decisionSelections[paperId] || '';

              return (
                <div className="adjudication-item" key={paperId}>
                  <div className="adjudication-paper">
                    <strong>{paper.title}</strong>

                    <span className="decision-label maybe">
                      {paper.dual_screening_status === 'needs_adjudication'
                        ? 'Reviewer disagreement'
                        : paper.dual_screening_status === 'technical_error'
                        ? 'Technical issue'
                        : 'Manual assessment required'}
                    </span>

                    <p>
                      {paper.screening_reason ||
                        'Additional assessment is required.'}
                    </p>
                  </div>

                  <div className="adjudication-controls">
                    <button
                      type="button"
                      className={`btn ${
                        currentDecision === 'include'
                          ? 'btn-success'
                          : 'btn-outline-success'
                      }`}
                      onClick={() =>
                        updateDecision(paper, index, 'include')
                      }
                    >
                      Include
                    </button>

                    <button
                      type="button"
                      className={`btn ${
                        currentDecision === 'exclude'
                          ? 'btn-danger'
                          : 'btn-outline-danger'
                      }`}
                      onClick={() =>
                        updateDecision(paper, index, 'exclude')
                      }
                    >
                      Exclude
                    </button>

                    {currentDecision && (
                      <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={() =>
                          updateDecision(paper, index, '')
                        }
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Approval */}
      {review.status === 'awaiting_human_review' && (
        <div className="screening-approval">
          <div>
            <h5>Screening review required</h5>
            <p>
              {uncertain.length > selectedCount
                ? `${uncertain.length - selectedCount} uncertain paper(s) will remain unresolved.`
                : 'All uncertain papers have been adjudicated.'}
              {' '}You can approve the screening and continue to the next stage.
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

      {message && (
        <p className="screening-message success">{message}</p>
      )}

      {error && (
        <p className="screening-message error">{error}</p>
      )}

    </div>
  );
}