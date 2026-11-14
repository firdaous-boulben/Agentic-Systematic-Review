
function AuditTrail({ review }) {
  const logs = review?.execution_logs || [];

  return (
    <div className="audit-page">
      <div className="page-intro">
        <div>
          <h3>Audit Trail</h3>
          <p>
            Chronological record of the review pipeline's execution.
          </p>
        </div>
      </div>

      <div className="audit-overview">
        <div className="audit-stat">
          <span>Total events</span>
          <strong>{logs.length}</strong>
        </div>
      </div>

      <div className="audit-timeline">
        {logs.length > 0 ? (
          [...logs].reverse().map((log, index) => (
            <div className="audit-event" key={index}>
              <div className="audit-event-marker">
                <i className="bi bi-check-circle"></i>
              </div>

              <div className="audit-event-content">
                <p>{typeof log === 'string' ? log : log.message}</p>

                {typeof log !== 'string' && log.timestamp && (
                  <span className="audit-event-time">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="audit-empty">
            <i className="bi bi-clock-history"></i>
            <h5>No execution logs available</h5>
            <p>
              Events will appear here as the review pipeline progresses.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default AuditTrail;