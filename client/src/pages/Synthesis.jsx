
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function Synthesis({ review }) {
  const [activeTab, setActiveTab] = useState('synthesis');

  const synthesis = review?.synthesis || '';
  const criticFeedback = review?.critic_feedback || '';
  const includedStudies = review?.included_papers || [];
  const validationStatus = review?.validation_status || 'pending';

  const wordCount = synthesis
    .replace(/[#*`|>-]/g, ' ')
    .split(/\s+/)
    .filter(Boolean).length;

  const statusLabel = {
    approved: 'Approved',
    needs_revision: 'Needs revision',
    rejected: 'Rejected',
    pending: 'Pending',
  }[validationStatus] || validationStatus;

  return (
    <div className="synthesis-page">
      <div className="page-intro">
        <div>
          <h3>Evidence Synthesis</h3>
          <p>
            Review the generated synthesis of findings, research themes,
            methodological comparisons, and evidence gaps.
          </p>
        </div>

        <span className={`status-badge ${
          validationStatus === 'approved'
            ? 'status-completed'
            : 'status-in-progress'
        }`}>
          {statusLabel}
        </span>
      </div>

      <div className="synthesis-stats">
        <div className="synthesis-stat">
          <span>Included studies</span>
          <strong>{includedStudies.length}</strong>
        </div>

        <div className="synthesis-stat">
          <span>Synthesis words</span>
          <strong>{wordCount}</strong>
        </div>

        <div className="synthesis-stat">
          <span>Validation</span>
          <strong className="synthesis-status-value">
            {statusLabel}
          </strong>
        </div>
      </div>

      <div className="synthesis-tabs">
        <button
          className={activeTab === 'synthesis' ? 'active' : ''}
          onClick={() => setActiveTab('synthesis')}
        >
          <i className="bi bi-file-text me-2"></i>
          Full Synthesis
        </button>

        <button
          className={activeTab === 'validation' ? 'active' : ''}
          onClick={() => setActiveTab('validation')}
        >
          <i className="bi bi-shield-check me-2"></i>
          Critic Validation
        </button>
      </div>

      {activeTab === 'synthesis' && (
        <div className="synthesis-panel">
          <div className="panel-heading">
            <div>
              <h5>Generated Evidence Synthesis</h5>
              <p>
                Complete synthesis produced by the synthesis agent.
              </p>
            </div>
          </div>

          {synthesis.trim() ? (
            <article className="synthesis-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {synthesis}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="synthesis-empty">
              <i className="bi bi-hourglass-split"></i>
              <p>The evidence synthesis is not available yet.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'validation' && (
        <div className="synthesis-panel">
          <div className="panel-heading">
            <div>
              <h5>Critic Validation</h5>
              <p>
                Feedback and assessment of the generated evidence synthesis.
              </p>
            </div>

            <span className={`validation-badge ${
              validationStatus === 'approved' ? 'approved' : 'pending'
            }`}>
              {statusLabel}
            </span>
          </div>

          {criticFeedback.trim() ? (
            <article className="synthesis-content critic-feedback">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {criticFeedback}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="synthesis-empty">
              <i className="bi bi-hourglass-split"></i>
              <p>Critic feedback is not available yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Synthesis;