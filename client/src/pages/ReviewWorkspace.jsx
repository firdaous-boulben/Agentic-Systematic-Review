import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';

import SearchResults from './SearchResults';
import Screening from './Screening';
import Extraction from './Extraction';
import QualityAssessment from './QualityAssessment';
import Synthesis from './Synthesis';
import PrismaFlow from './PrismaFlow';
import Report from './Report';
import AuditTrail from './AuditTrail';

const stages = [
  { id: 'protocol', title: 'Protocol', description: 'Research question and eligibility criteria', icon: 'bi-file-earmark-text' },
  { id: 'search', title: 'Literature Search', description: 'Search academic databases', icon: 'bi-search' },
  { id: 'screening', title: 'Title & Abstract Screening', description: 'Assess retrieved studies', icon: 'bi-funnel' },
  { id: 'fulltext', title: 'Full-text Screening', description: 'Evaluate full-text articles', icon: 'bi-file-earmark-pdf' },
  { id: 'extraction', title: 'Data Extraction', description: 'Extract relevant study information', icon: 'bi-table' },
  { id: 'quality', title: 'Quality Assessment', description: 'Evaluate study quality and risk of bias', icon: 'bi-shield-check' },
  { id: 'synthesis', title: 'Evidence Synthesis', description: 'Analyze and synthesize findings', icon: 'bi-diagram-3' },
  { id: 'report', title: 'Final Report', description: 'Generate the systematic review report', icon: 'bi-file-earmark-richtext' },
];

const sections = [
  { id: 'overview', label: 'Overview', icon: 'bi-grid' },
  { id: 'search', label: 'Search Results', icon: 'bi-search' },
  { id: 'screening', label: 'Screening', icon: 'bi-funnel' },
  { id: 'extraction', label: 'Data Extraction', icon: 'bi-table' },
  { id: 'quality', label: 'Quality Assessment', icon: 'bi-shield-check' },
  { id: 'synthesis', label: 'Evidence Synthesis', icon: 'bi-diagram-3' },
  { id: 'prisma', label: 'PRISMA Flow', icon: 'bi-diagram-3' },
  { id: 'report', label: 'Final Report', icon: 'bi-file-earmark-text' },
  { id: 'audit', label: 'Audit Trail', icon: 'bi-clock-history' },
];

const statusLabels = {
  queued: 'Queued',
  running: 'In Progress',
  awaiting_human_review: 'Awaiting Human Review',
  completed: 'Completed',
  failed: 'Failed',
};

function getCurrentStageIndex(currentStage, status) {
  if (status === 'completed') return stages.length;

  const stage = (currentStage || '').toLowerCase();

  if (stage.includes('protocol')) return 0;
  if (stage.includes('search')) return 1;
  if (stage.includes('screen') || stage.includes('human_review')) return 2;
  if (stage.includes('pdf') || stage.includes('full_text')) return 3;
  if (stage.includes('extract')) return 4;
  if (stage.includes('appraisal') || stage.includes('quality')) return 5;
  if (stage.includes('synthesis') || stage.includes('critic')) return 6;
  if (stage.includes('prisma') || stage.includes('report')) return 7;

  return -1;
}

export default function ReviewWorkspace() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();

  const initialSection = searchParams.get('section') || 'overview';
  const [activeSection, setActiveSection] = useState(initialSection);

  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const fetchReview = async () => {
      try {
        const response = await fetch(`/api/reviews/${id}`);

        if (!response.ok) {
          throw new Error(
            response.status === 404
              ? 'Review not found.'
              : 'Failed to load review.'
          );
        }

        const data = await response.json();

        if (isMounted) {
          setReview(data);
          setError('');
        }
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchReview();

    // Refresh the pipeline state while the review is running.
    const interval = setInterval(fetchReview, 5000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [id]);

  if (loading) {
    return <div className="empty-reviews">Loading review...</div>;
  }

  if (error || !review) {
    return (
      <div className="empty-reviews">
        <h5>Unable to open review</h5>
        <p>{error || 'Review data is unavailable.'}</p>
        <Link to="/reviews" className="btn btn-primary-custom">
          Back to My Reviews
        </Link>
      </div>
    );
  }

  const status = review.status || 'running';
  const currentStageIndex = getCurrentStageIndex(
    review.current_stage,
    status
  );

  const completedStages = currentStageIndex < 0
    ? 0
    : Math.min(currentStageIndex, stages.length);

  const progress = Math.round(
    (completedStages / stages.length) * 100
  );

  const paperCount =
    (review.included_papers?.length || 0) +
    (review.excluded_papers?.length || 0) +
    (review.uncertain_papers?.length || 0);

  const currentStageLabel = status === 'awaiting_human_review'
    ? 'Awaiting Human Review'
    : review.current_stage?.replaceAll('_', ' ') || 'Initializing';

  return (
    <div className="workspace-page">
      <div className="workspace-breadcrumb">
        <Link to="/reviews">My Reviews</Link>
        <i className="bi bi-chevron-right"></i>
        <span>Review Workspace</span>
      </div>

      <div className="workspace-heading">
        <div>
          <div className="workspace-title-row">
            <h2>{review.topic}</h2>
            <span className="review-status-badge">
              {statusLabels[status] || status}
            </span>
          </div>
          <p>{review.research_question || 'Systematic literature review'}</p>
        </div>

        <button
          className="btn btn-outline-primary"
          onClick={() => setActiveSection('audit')}
        >
          <i className="bi bi-clock-history me-2"></i>
          View Activity
        </button>
      </div>

      <div className="workspace-overview-cards">
        <div className="workspace-stat">
          <span>Pipeline Progress</span>
          <strong>{progress}%</strong>
          <div className="progress">
            <div
              className="progress-bar"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        <div className="workspace-stat">
          <span>Screened Papers</span>
          <strong>{paperCount}</strong>
          <small>Included, excluded and uncertain</small>
        </div>

        <div className="workspace-stat">
          <span>Completed Stages</span>
          <strong>{completedStages}/{stages.length}</strong>
          <small>Pipeline execution</small>
        </div>

        <div className="workspace-stat">
          <span>Current Stage</span>
          <strong className="current-stage-text">
            {currentStageLabel}
          </strong>
          <small>Automatically updated</small>
        </div>
      </div>

      <div className="workspace-layout">
        <aside className="workspace-nav">
          <h6>REVIEW WORKSPACE</h6>

          {sections.map((section) => (
            <button
              key={section.id}
              className={`workspace-nav-item ${
                activeSection === section.id ? 'active' : ''
              }`}
              onClick={() => setActiveSection(section.id)}
            >
              <i className={`bi ${section.icon}`}></i>
              {section.label}
            </button>
          ))}
        </aside>

        <main className="workspace-main">
          {activeSection === 'overview' ? (
            <>
              <div className="workspace-section-heading">
                <div>
                  <h3>Review Pipeline</h3>
                  <p>Track the progress of each stage of your review.</p>
                </div>
                <span className="pipeline-count">
                  {completedStages} of {stages.length} completed
                </span>
              </div>

              <div className="pipeline-list">
                {stages.map((stage, index) => {
                  let stageStatus = 'pending';

                  if (index < completedStages) {
                    stageStatus = 'completed';
                  } else if (index === currentStageIndex && status !== 'completed') {
                    stageStatus = 'in-progress';
                  }

                  if (status === 'failed' && index === currentStageIndex) {
                    stageStatus = 'failed';
                  }

                  return (
                    <div className="pipeline-stage" key={stage.id}>
                      <div className={`pipeline-icon ${stageStatus}`}>
                        <i className={`bi ${stage.icon}`}></i>
                      </div>

                      <div className="pipeline-stage-info">
                        <h5>{index + 1}. {stage.title}</h5>
                        <p>{stage.description}</p>
                      </div>

                      <span className={`stage-status ${stageStatus}`}>
                        {stageStatus === 'in-progress'
                          ? status === 'awaiting_human_review'
                            ? 'Awaiting Approval'
                            : 'In Progress'
                          : stageStatus === 'failed'
                            ? 'Failed'
                            : stageStatus === 'completed'
                              ? 'Completed'
                              : 'Pending'}
                      </span>

                      <button
                        className="stage-open-btn"
                        onClick={() => setActiveSection(
                          ['protocol', 'search'].includes(stage.id)
                            ? 'search'
                            : ['fulltext', 'screening'].includes(stage.id)
                              ? 'screening'
                              : stage.id
                        )}
                        title="Open stage"
                      >
                        <i className="bi bi-chevron-right"></i>
                      </button>
                    </div>
                  );
                })}
              </div>
            </>
          ) : activeSection === 'search' ? (
            <SearchResults review={review} />
          ) : activeSection === 'screening' ? (
            <Screening review={review} />
          ) : activeSection === 'extraction' ? (
            <Extraction review={review} />
          ) : activeSection === 'quality' ? (
            <QualityAssessment review={review} />
          ) : activeSection === 'synthesis' ? (
            <Synthesis review={review} />
          ) : activeSection === 'prisma' ? (
            <PrismaFlow review={review} />
          ) : activeSection === 'report' ? (
            <Report review={review} reviewId={id} />
          ) : activeSection === 'audit' ? (
            <AuditTrail review={review} />
          ) : (
            <WorkspaceSection section={activeSection} />
          )}
        </main>
      </div>
    </div>
  );
}

function WorkspaceSection({ section }) {
  const content = {
    
  };

  const item = content[section];

  return (
    <div className="workspace-placeholder">
      <div className="placeholder-icon">
        <i className={`bi ${item?.icon || 'bi-grid'}`}></i>
      </div>
      <h3>{item?.title || 'Review Section'}</h3>
      <p>{item?.description}</p>
      <div className="placeholder-message">{item?.message}</div>
    </div>
  );
}