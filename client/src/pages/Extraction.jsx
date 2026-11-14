
import { useMemo, useState } from 'react';

const fieldLabels = {
  study_type: 'Study Type',
  research_objective: 'Research Objective',
  research_context: 'Research Context',
  participants_and_sample: 'Participants and Sample',
  study_design: 'Study Design',
  methods_and_approaches: 'Methods and Approaches',
  data_sources: 'Data Sources',
  evaluation_methods: 'Evaluation Methods',
  main_findings: 'Main Findings',
  limitations: 'Limitations',
  missing_information: 'Missing Information',
};

const formatLabel = (value = '') =>
  String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const getPaperId = (paper, index) =>
  paper.openalex_id || paper.doi || paper.title || index;

function Extraction({ review }) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const extractedPapers = Array.isArray(review?.extracted_data)
    ? review.extracted_data
    : [];

  const includedPapers = Array.isArray(review?.included_papers)
    ? review.included_papers
    : [];

  const extractionFailures = Array.isArray(review?.extraction_failures)
    ? review.extraction_failures
    : [];

  const selectedPaper = extractedPapers[selectedIndex] || null;

  const information = selectedPaper?.extracted_information || {};

  const evidence = Array.isArray(selectedPaper?.evidence)
    ? selectedPaper.evidence
    : [];

  const topicExtractions =
    information.topic_specific_extractions &&
    typeof information.topic_specific_extractions === 'object' &&
    !Array.isArray(information.topic_specific_extractions)
      ? information.topic_specific_extractions
      : {};

  const standardFields = useMemo(
    () =>
      Object.entries(fieldLabels)
        .filter(([key]) => {
          const value = information[key];
          return value !== undefined && value !== null && value !== '';
        })
        .map(([key, label]) => ({
          key,
          label,
          value: information[key],
        })),
    [information]
  );

  const extractedCount = extractedPapers.length;
  const includedCount = includedPapers.length;
  const failureCount = extractionFailures.length;

  const progress =
    includedCount > 0
      ? Math.min(100, Math.round((extractedCount / includedCount) * 100))
      : 0;

  const getEvidence = (field) =>
    evidence.filter(
      (item) =>
        item &&
        typeof item === 'object' &&
        item.field?.toLowerCase() === field.toLowerCase()
    );

  const renderValue = (value) => {
    if (value === null || value === undefined || value === '') {
      return <span className="extraction-no-value">Not reported</span>;
    }

    if (Array.isArray(value)) {
      return value.length > 0 ? (
        <ul>
          {value.map((item, index) => (
            <li key={index}>
              {typeof item === 'object'
                ? JSON.stringify(item)
                : String(item)}
            </li>
          ))}
        </ul>
      ) : (
        <span className="extraction-no-value">Not reported</span>
      );
    }

    if (typeof value === 'object') {
      return (
        <pre>{JSON.stringify(value, null, 2)}</pre>
      );
    }

    return <p>{String(value)}</p>;
  };

  return (
    <div className="extraction-page">
      <div className="extraction-heading">
        <div>
          <h2>Data Extraction</h2>
          <p>
            Review the information extracted from the included studies
            and its supporting evidence.
          </p>
        </div>
      </div>

      {/* Extraction overview */}
      <div className="extraction-overview">
        <div className="extraction-overview-card">
          <span>Included Studies</span>
          <strong>{includedCount}</strong>
        </div>

        <div className="extraction-overview-card">
          <span>Extracted Studies</span>
          <strong>{extractedCount}</strong>
        </div>

        <div className="extraction-overview-card">
          <span>Remaining</span>
          <strong>{Math.max(0, includedCount - extractedCount)}</strong>
        </div>

        <div className="extraction-overview-card">
          <span>Extraction Failures</span>
          <strong>{failureCount}</strong>
        </div>
      </div>

      {/* Progress */}
      <div className="extraction-progress">
        <div className="extraction-progress-header">
          <span>Extraction Progress</span>
          <strong>{progress}%</strong>
        </div>

        <div className="extraction-progress-track">
          <div
            className="extraction-progress-bar"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Extraction failures */}
      {failureCount > 0 && (
        <div className="extraction-failures">
          <h3>Extraction Issues</h3>

          {extractionFailures.map((failure, index) => (
            <div className="extraction-failure-item" key={index}>
              {typeof failure === 'string'
                ? failure
                : failure?.title ||
                  failure?.reason ||
                  failure?.error ||
                  JSON.stringify(failure)}
            </div>
          ))}
        </div>
      )}

      {/* Main content */}
      {extractedPapers.length === 0 ? (
        <div className="extraction-empty">
          <h3>No extracted data available yet</h3>
          <p>
            Extracted study information will appear here once the
            extraction agent has processed the included studies.
          </p>
        </div>
      ) : (
        <div className="extraction-layout">
          {/* Studies list */}
          <aside className="extraction-paper-list">
            <h3>Extracted Studies ({extractedCount})</h3>

            {extractedPapers.map((paper, index) => (
              <button
                type="button"
                key={getPaperId(paper, index)}
                className={`extraction-paper-item ${
                  selectedIndex === index ? 'active' : ''
                }`}
                onClick={() => setSelectedIndex(index)}
              >
                <span className="extraction-paper-number">
                  {index + 1}
                </span>

                <span className="extraction-paper-info">
                  <strong>{paper.title || 'Untitled study'}</strong>
                  <small>
                    {paper.year || 'Year unavailable'}
                    {paper.source ? ` · ${paper.source}` : ''}
                  </small>
                </span>
              </button>
            ))}
          </aside>

          {/* Selected study */}
          {selectedPaper && (
            <main className="extraction-form-panel">
              <div className="extraction-paper-header">
                <div>
                  <h3>{selectedPaper.title || 'Untitled study'}</h3>
                  <p>
                    {selectedPaper.authors?.length
                      ? selectedPaper.authors.join(', ')
                      : 'Authors unavailable'}
                    {selectedPaper.year
                      ? ` · ${selectedPaper.year}`
                      : ''}
                  </p>
                </div>

                {selectedPaper.url && (
                  <a
                    href={selectedPaper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="paper-link"
                  >
                    View Publication
                  </a>
                )}
              </div>

              <div className="extraction-metadata">
                <div>
                  <span>Extraction Source</span>
                  <strong>
                    {formatLabel(
                      selectedPaper.extraction_source || 'Not specified'
                    )}
                  </strong>
                </div>

                <div>
                  <span>Evidence Items</span>
                  <strong>{selectedPaper.evidence_count ?? evidence.length}</strong>
                </div>

                <div>
                  <span>PDF Processing</span>
                  <strong>
                    {selectedPaper.pdf_text_processed
                      ? 'Processed'
                      : 'Not processed'}
                  </strong>
                </div>
              </div>

              {/* Standard extracted fields */}
              <section className="extraction-data-section">
                <h3>Extracted Information</h3>

                {standardFields.length === 0 ? (
                  <p className="extraction-no-value">
                    No standard extraction fields available.
                  </p>
                ) : (
                  standardFields.map(({ key, label, value }) => {
                    const fieldEvidence = getEvidence(key);

                    return (
                      <div className="extraction-data-field" key={key}>
                        <h4>{label}</h4>

                        <div className="extraction-data-value">
                          {renderValue(value)}
                        </div>

                        {fieldEvidence.length > 0 && (
                          <div className="extraction-field-evidence">
                            <strong>
                              Supporting Evidence ({fieldEvidence.length})
                            </strong>

                            {fieldEvidence.map((item, index) => (
                              <div
                                className="evidence-card"
                                key={`${item.field}-${index}`}
                              >
                                {item.claim && <p>{item.claim}</p>}

                                {item.supporting_passage && (
                                  <blockquote>
                                    {item.supporting_passage}
                                  </blockquote>
                                )}

                                <div className="evidence-meta">
                                  {item.source_pdf && (
                                    <span>
                                      Source: {item.source_pdf}
                                    </span>
                                  )}

                                  {item.page_number != null && (
                                    <span>
                                      Page: {item.page_number}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </section>

              {/* Topic-specific extracted fields */}
              {Object.keys(topicExtractions).length > 0 && (
                <section className="extraction-data-section">
                  <h3>Topic-Specific Information</h3>

                  {Object.entries(topicExtractions).map(([key, value]) => {
                    const fieldEvidence = getEvidence(key);

                    return (
                      <div className="extraction-data-field" key={key}>
                        <h4>{key}</h4>

                        <div className="extraction-data-value">
                          {renderValue(value)}
                        </div>

                        {fieldEvidence.length > 0 && (
                          <div className="extraction-field-evidence">
                            <strong>
                              Supporting Evidence ({fieldEvidence.length})
                            </strong>

                            {fieldEvidence.map((item, index) => (
                              <div
                                className="evidence-card"
                                key={`${item.field}-${index}`}
                              >
                                {item.claim && <p>{item.claim}</p>}

                                {item.supporting_passage && (
                                  <blockquote>
                                    {item.supporting_passage}
                                  </blockquote>
                                )}

                                <div className="evidence-meta">
                                  {item.source_pdf && (
                                    <span>
                                      Source: {item.source_pdf}
                                    </span>
                                  )}

                                  {item.page_number != null && (
                                    <span>
                                      Page: {item.page_number}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </section>
              )}

              {/* All evidence */}
              {evidence.length > 0 && (
                <section className="extraction-data-section">
                  <h3>All Supporting Evidence ({evidence.length})</h3>

                  <div className="extraction-all-evidence">
                    {evidence.map((item, index) => {
                      if (!item || typeof item !== 'object') return null;

                      return (
                        <details className="evidence-card" key={index}>
                          <summary>
                            {item.field
                              ? formatLabel(item.field)
                              : `Evidence ${index + 1}`}
                          </summary>

                          {item.claim && <p>{item.claim}</p>}

                          {item.supporting_passage && (
                            <blockquote>
                              {item.supporting_passage}
                            </blockquote>
                          )}

                          <div className="evidence-meta">
                            {item.source_pdf && (
                              <span>Source: {item.source_pdf}</span>
                            )}

                            {item.page_number != null && (
                              <span>Page: {item.page_number}</span>
                            )}
                          </div>
                        </details>
                      );
                    })}
                  </div>
                </section>
              )}
            </main>
          )}
        </div>
      )}
    </div>
  );
}

export default Extraction;