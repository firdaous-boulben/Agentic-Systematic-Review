
function PrismaFlow({ review }) {
  const data = review?.prisma_data || {};

  const count = (field) => Number(data[field] ?? 0);

  const exclusionReasons = data.full_text_exclusion_reasons || {};

  const formatNumber = (value) => Number(value).toLocaleString();

  const stages = [
    {
      label: 'IDENTIFICATION',
      boxes: [
        {
          title: 'Records identified',
          details: [
            ['Total records identified', count('records_identified')],
          ],
        },
        {
          title: 'Records removed before screening',
          details: [
            ['Duplicates removed', count('duplicates_removed')],
          ],
          variant: 'removal',
        },
      ],
    },
    {
      label: 'SCREENING',
      boxes: [
        {
          title: 'Records screened',
          details: [
            ['Records screened', count('records_screened')],
            ['Not yet screened', count('records_not_yet_screened')],
          ],
        },
        {
          title: 'Records excluded',
          details: [
            ['Excluded after screening', count('records_excluded')],
            ['Uncertain records', count('records_uncertain')],
          ],
          variant: 'removal',
        },
        {
          title: 'Reports sought for retrieval',
          details: [
            ['Reports sought', count('reports_sought_for_retrieval')],
            ['Included after screening', count('records_included_after_screening')],
          ],
        },
      ],
    },
    {
      label: 'ELIGIBILITY',
      boxes: [
        {
          title: 'Reports retrieved',
          details: [
            ['Retrieved', count('reports_retrieved')],
            ['Not retrieved', count('reports_not_retrieved')],
          ],
        },
        {
          title: 'Reports assessed for eligibility',
          details: [
            ['Reports assessed', count('reports_assessed_for_eligibility')],
          ],
        },
        {
          title: 'Reports excluded',
          details: [
            ['Reports excluded', count('reports_excluded')],
            ['Uncertain after full text', count('reports_uncertain_after_full_text')],
          ],
          variant: 'removal',
        },
      ],
    },
    {
      label: 'INCLUDED',
      boxes: [
        {
          title: 'Studies included in the review',
          details: [
            ['Studies included', count('studies_included')],
          ],
          variant: 'included',
        },
      ],
    },
  ];

  const overview = [
    {
      label: 'Records identified',
      value: count('records_identified'),
    },
    {
      label: 'Records screened',
      value: count('records_screened'),
    },
    {
      label: 'Reports assessed',
      value: count('reports_assessed_for_eligibility'),
    },
    {
      label: 'Studies included',
      value: count('studies_included'),
    },
  ];

  const hasData = Object.keys(data).length > 0;

  if (!hasData) {
    return (
      <div className="prisma-page">
        <div className="page-intro">
          <div>
            <h3>PRISMA Flow Diagram</h3>
            <p>
              Track records through identification, screening,
              eligibility, and final inclusion.
            </p>
          </div>
        </div>

        <div className="prisma-empty">
          <i className="bi bi-diagram-3"></i>
          <p>PRISMA data is not available yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="prisma-page">
      <div className="page-intro">
        <div>
          <h3>PRISMA Flow Diagram</h3>
          <p>
            Overview of the records identified, screened, assessed,
            and included in the systematic review.
          </p>
        </div>

        <span className="status-badge status-completed">
          Generated
        </span>
      </div>

      <div className="prisma-overview">
        {overview.map((item) => (
          <div className="prisma-stat" key={item.label}>
            <span>{item.label}</span>
            <strong>{formatNumber(item.value)}</strong>
          </div>
        ))}
      </div>

      {count('records_with_technical_failures') > 0 && (
        <div className="prisma-warning">
          <i className="bi bi-exclamation-triangle"></i>
          <span>
            {formatNumber(count('records_with_technical_failures'))}
            {' '}records encountered technical failures during processing.
          </span>
        </div>
      )}

      <section className="prisma-panel prisma-diagram-panel">
        <div className="prisma-panel-heading">
          <div>
            <h5>PRISMA Flow</h5>
            <p>Record progression through the review process.</p>
          </div>
          <span className="prisma-preview-label">REVIEW DATA</span>
        </div>

        <div className="prisma-diagram">
          {stages.map((stage, stageIndex) => (
            <div className="prisma-stage" key={stage.label}>
              <div className="prisma-stage-label">
                 {stage.label}  
              </div>

              {stage.boxes.map((box, boxIndex) => (
                <div key={box.title}>
                  {boxIndex > 0 && (
                    <div className="prisma-flow-arrow">
                      <i className="bi bi-arrow-down"></i>
                    </div>
                  )}

                  <div className={`prisma-flow-box ${
                    box.variant === 'removal'
                      ? 'prisma-removal-box'
                      : box.variant === 'included'
                        ? 'prisma-included-box'
                        : ''
                  }`}>
                    <strong>{box.title}</strong>

                    {box.details.map(([label, value]) => (
                      <div className="prisma-flow-detail" key={label}>
                        <span>{label}  </span>
                        <b>{formatNumber(value)}</b>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {stageIndex < stages.length - 1 && (
                <div className="prisma-stage-connector">
                  <i className="bi bi-arrow-down"></i>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="prisma-panel">
        <div className="prisma-panel-heading">
          <div>
            <h5>Full-text Exclusion Reasons</h5>
            <p>
              Reasons recorded during the full-text eligibility assessment.
            </p>
          </div>
        </div>

        {Object.keys(exclusionReasons).length > 0 ? (
          <div className="prisma-reasons-list">
            {Object.entries(exclusionReasons).map(([reason, value]) => (
              <div className="prisma-reason-item" key={reason}>
                <span>{reason.replace(/_/g, ' ')}</span>
                <strong>{formatNumber(value)}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="prisma-no-reasons">
            No full-text exclusion reasons were recorded.
          </p>
        )}
      </section>
    </div>
  );
}

export default PrismaFlow;