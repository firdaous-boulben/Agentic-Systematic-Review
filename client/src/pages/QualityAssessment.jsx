
import { useState } from 'react';

const ratingStyles = {
  High: 'high',
  Moderate: 'moderate',
  Low: 'low',
  'Insufficient Information': 'insufficient',
};

const formatLabel = (value = '') =>
  String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

function QualityAssessment({ review }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const qualityResults = Array.isArray(review?.quality_results)
    ? review.quality_results
    : [];

  const currentStudy = qualityResults[currentIndex] || null;
  const appraisal = currentStudy?.quality_appraisal || {};
  const assessments =
    appraisal.assessments &&
    typeof appraisal.assessments === 'object'
      ? appraisal.assessments
      : {};

  const criteria = Object.entries(assessments);

  const verificationItems = Array.isArray(appraisal.full_text_verification)
    ? appraisal.full_text_verification
    : [];

  const totalStudies = qualityResults.length;

  const getStudyRating = (study) => {
    const studyAssessments = study?.quality_appraisal?.assessments || {};
    const ratings = Object.values(studyAssessments)
      .map((item) => item?.rating)
      .filter(Boolean);

    if (ratings.length === 0) return 'Not assessed';

    if (ratings.includes('Low')) return 'Needs attention';
    if (ratings.includes('Insufficient Information')) {
      return 'Information missing';
    }
    if (ratings.includes('Moderate')) return 'Moderate';

    return 'High';
  };

  const getRatingClass = (rating) =>
    ratingStyles[rating] || 'unknown';

  return (
    <div className="quality-page">
      <div className="page-intro">
        <div>
          <h3>Quality Assessment</h3>
          <p>
            Review the methodological quality and reliability of the
            included studies based on the Quality Appraisal Agent's
            assessments.
          </p>
        </div>

        <span className="status-badge status-in-progress">
          {totalStudies} studies assessed
        </span>
      </div>

      {/* Overview */}
      <div className="quality-overview">
        <div className="quality-stat">
          <span>Studies assessed</span>
          <strong>{totalStudies}</strong>
        </div>

        <div className="quality-stat">
          <span>Assessment criteria</span>
          <strong>
            {currentStudy ? criteria.length : 0}
          </strong>
        </div>

        <div className="quality-stat">
          <span>Verification points</span>
          <strong>
            {currentStudy ? verificationItems.length : 0}
          </strong>
        </div>

        <div className="quality-stat">
          <span>Current appraisal</span>
          <strong className="quality-overview-rating">
            {currentStudy ? getStudyRating(currentStudy) : '—'}
          </strong>
        </div>
      </div>

      {qualityResults.length === 0 ? (
        <div className="quality-empty">
          <h4>No quality assessment available yet</h4>
          <p>
            Quality appraisal results will appear here once the
            Quality Appraisal Agent has processed the included studies.
          </p>
        </div>
      ) : (
        <div className="quality-layout">
          {/* Study list */}
          <aside className="quality-study-list">
            <div className="quality-list-heading">
              <h5>Assessed Studies</h5>
              <span>{totalStudies} studies</span>
            </div>

            {qualityResults.map((study, index) => (
              <button
                type="button"
                key={study.openalex_id || study.doi || index}
                className={`quality-study-item ${
                  currentIndex === index ? 'active' : ''
                }`}
                onClick={() => setCurrentIndex(index)}
              >
                <div className="quality-study-top">
                  <span className="quality-study-number">
                    {index + 1}
                  </span>

                  <span
                    className={`quality-status ${getRatingClass(
                      getStudyRating(study)
                    )}`}
                  >
                    {getStudyRating(study)}
                  </span>
                </div>

                <strong>{study.title || 'Untitled study'}</strong>

                <small>
                  {study.year || 'Year unavailable'}
                  {study.source ? ` · ${study.source}` : ''}
                </small>
              </button>
            ))}
          </aside>

          {/* Selected study assessment */}
          {currentStudy && (
            <main className="quality-assessment-panel">
              <div className="quality-study-header">
                <div>
                  <span className="section-eyebrow">
                    STUDY {currentIndex + 1} OF {totalStudies}
                  </span>

                  <h5>
                    {currentStudy.title || 'Untitled study'}
                  </h5>

                  <p>
                    {currentStudy.authors?.length
                      ? currentStudy.authors.join(', ')
                      : 'Authors unavailable'}
                    {currentStudy.year
                      ? ` · ${currentStudy.year}`
                      : ''}
                  </p>

                  {currentStudy.url && (
                    <a
                      href={currentStudy.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="quality-publication-link"
                    >
                      View Publication
                    </a>
                  )}
                </div>

                <div
                  className={`quality-score-display ${getRatingClass(
                    getStudyRating(currentStudy)
                  )}`}
                >
                  <strong>{getStudyRating(currentStudy)}</strong>
                  <span>Overall appraisal</span>
                </div>
              </div>

              {/* Study type */}
              <div className="quality-study-type">
                <span>Study Type:  </span>
                <strong>
                  {appraisal.study_type || 'Not reported'}
                </strong>
              </div>

              {/* Assessment criteria */}
              <section className="quality-section">
                <div className="quality-section-heading">
                  <div>
                    <h6>Assessment Results</h6>
                    <p>
                      Appraisal criteria and the agent's justifications.
                    </p>
                  </div>

                  <span>{criteria.length} criteria</span>
                </div>

                {criteria.length === 0 ? (
                  <p className="quality-no-data">
                    No individual assessment criteria are available.
                  </p>
                ) : (
                  <div className="quality-criteria-list">
                    {criteria.map(([key, assessment], index) => {
                      const rating = assessment?.rating || 'Not rated';

                      return (
                        <div className="quality-criterion" key={key}>
                          <div className="quality-criterion-header">
                            <div className="quality-criterion-title">
                              <span>{index + 1}. </span>
                              <strong>{formatLabel(key)}</strong>
                            </div>

                            <span
                              className={`quality-rating ${getRatingClass(
                                rating
                              )}`}
                            >
                              {rating}
                            </span>
                          </div>

                          {assessment?.reason && (
                            <p className="quality-criterion-reason">
                              {assessment.reason}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* Full-text verification */}
              <section className="quality-section">
                <div className="quality-section-heading">
                  <div>
                    <h6>Full-Text Verification</h6>
                    <p>
                      Information requiring further verification or
                      clarification from the full text.
                    </p>
                  </div>

                  <span>{verificationItems.length} points</span>
                </div>

                {verificationItems.length === 0 ? (
                  <p className="quality-no-data">
                    No additional verification points reported.
                  </p>
                ) : (
                  <div className="quality-verification-list">
                    {verificationItems.map((item, index) => (
                      <div
                        className="quality-verification-item"
                        key={index}
                      >
                        <span>{index + 1}</span>
                        <p>{String(item)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </main>
          )}
        </div>
      )}

      {/* Navigation */}
      {totalStudies > 1 && (
        <div className="quality-navigation">
          <button
            type="button"
            className="btn btn-light"
            disabled={currentIndex === 0}
            onClick={() =>
              setCurrentIndex((index) => index - 1)
            }
          >
            <i className="bi bi-arrow-left me-2"></i>
            Previous Study
          </button>

          <button
            type="button"
            className="btn btn-light"
            disabled={currentIndex === totalStudies - 1}
            onClick={() =>
              setCurrentIndex((index) => index + 1)
            }
          >
            Next Study
            <i className="bi bi-arrow-right ms-2"></i>
          </button>
        </div>
      )}
    </div>
  );
}

export default QualityAssessment;