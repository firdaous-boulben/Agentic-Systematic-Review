
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function Report({ review, reviewId }) {
  const [reportContent, setReportContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!review?.final_report || !reviewId) {
      setReportContent('');
      setError('');
      setLoading(false);
      return;
    }

    const controller = new AbortController();

    const fetchReport = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await fetch(
          `/api/reviews/${reviewId}/report`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error(
            response.status === 404
              ? 'The report file could not be found.'
              : 'Unable to load the report.'
          );
        }

        const content = await response.text();
        setReportContent(content);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'An error occurred while loading the report.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchReport();

    return () => controller.abort();
  }, [reviewId, review?.final_report]);

  const handlePrint = () => {
    window.print();
  };

  const wordCount = reportContent
    .replace(/[#*`_\[\]()]/g, '')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

  const exportUrl = (format) => `/api/reviews/${reviewId}/export/${format}`;

  return (
    <div className="report-page">
      <div className="page-intro report-page-intro">
        <div>
          <h3>Final Report</h3>
          <p>View the generated report and download it in your preferred format.</p>
        </div>

        <div className="report-export-actions">
          <a
            className="report-export-btn"
            href={exportUrl('markdown')}
            onClick={(e) => {
              if (!review?.final_report || loading) e.preventDefault();
            }}
          >
            <i className="bi bi-markdown"></i>
            <span>Markdown</span>
          </a>

          <a
            className="report-export-btn"
            href={exportUrl('pdf')}
            onClick={(e) => {
              if (!review?.final_report || loading) e.preventDefault();
            }}
          >
            <i className="bi bi-file-earmark-pdf"></i>
            <span>PDF</span>
          </a>

          <a
            className="report-export-btn"
            href={exportUrl('docx')}
            onClick={(e) => {
              if (!review?.final_report || loading) e.preventDefault();
            }}
          >
            <i className="bi bi-file-earmark-word"></i>
            <span>Word</span>
          </a>

          <a
            className="report-export-btn"
            href={exportUrl('bibtex')}
            onClick={(e) => {
              if (!review?.final_report || loading) e.preventDefault();
            }}
          >
            <i className="bi bi-journal-text"></i>
            <span>BibTeX</span>
          </a>
        </div>
      </div>

      <div className="report-overview">
        <div className="report-overview-stat">
          <span>Report status</span>
          <strong>
            {loading
              ? 'Loading'
              : reportContent
                ? 'Generated'
                : 'Unavailable'}
          </strong>
        </div>

        <div className="report-overview-stat">
          <span>Word count</span>
          <strong>{wordCount.toLocaleString()}</strong>
        </div>

        <div className="report-overview-stat">
          <span>Format</span>
          <strong>Markdown</strong>
        </div>
      </div>

      <div className="report-preview-panel">
        <div className="report-preview-heading">
          <div>
            <h5>Generated Report</h5>
            <p>
              {review?.topic || 'Systematic Literature Review'}
            </p>
          </div>

          <button
            className="btn btn-light btn-sm"
            onClick={handlePrint}
            disabled={!reportContent || loading}
          >
            <i className="bi bi-printer me-2"></i>
            Print
          </button>
        </div>

        {loading ? (
          <div className="report-state">
            <div className="spinner-border" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p>Loading generated report...</p>
          </div>
        ) : error ? (
          <div className="report-state report-error">
            <i className="bi bi-exclamation-circle"></i>
            <p>{error}</p>
          </div>
        ) : !reportContent ? (
          <div className="report-state">
            <i className="bi bi-file-earmark-text"></i>
            <h5>Report not available yet</h5>
            <p>
              The report will appear here once the review pipeline
              has generated it.
            </p>
          </div>
        ) : (
          <article className="report-document" id="report-document">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {reportContent}
            </ReactMarkdown>
          </article>
        )}
      </div>
    </div>
  );
}

export default Report;