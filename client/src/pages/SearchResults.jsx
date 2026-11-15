
export default function SearchResults({ review }) {
  if (!review) return null;

  const retrieved = review.retrieved_papers || [];
  const papers = review.unique_papers || [];

  const duplicates = Math.max(0, retrieved.length - papers.length);

  const getSources = (paper) => {
    if (Array.isArray(paper.sources) && paper.sources.length > 0) {
      return paper.sources;
    }

    return paper.source ? [paper.source] : ['Unknown'];
  };

  const sourceCounts = retrieved.reduce((counts, paper) => {
    const source = paper.source || 'Unknown';
    counts[source] = (counts[source] || 0) + 1;
    return counts;
  }, {});

  return (
    <div className="search-results-page">
      <div className="screening-heading">
        <div>
          <h3>Search Results</h3>
          <p>Studies retrieved from academic databases before screening.</p>
        </div>
        <span className="screening-phase">OpenAlex + Crossref</span>
      </div>

      <div className="screening-stats">
        <div className="screening-stat">
          <span>Records retrieved</span>
          <strong>{retrieved.length}</strong>
        </div>

        <div className="screening-stat">
          <span>Unique records</span>
          <strong>{papers.length}</strong>
        </div>

        <div className="screening-stat">
          <span>Duplicates removed</span>
          <strong>{duplicates}</strong>
        </div>

        <div className="screening-stat">
          <span>Ready for screening</span>
          <strong>{papers.length}</strong>
        </div>
      </div>

      {retrieved.length > 0 && (
        <div className="search-source-summary">
          <h4>Records by Source</h4>
          <div className="search-source-list">
            {Object.entries(sourceCounts).map(([source, count]) => (
              <div className="search-source-item" key={source}>
                <span>{source}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {papers.length === 0 ? (
        <div className="screening-empty">
          <h4>No search results available</h4>
          <p>
            Retrieved studies will appear here once the search stage is completed.
          </p>
        </div>
      ) : (
        <>
          <div className="search-results-header">
            <h4>Retrieved Studies</h4>
            <span>{papers.length} unique records</span>
          </div>

          <div className="search-paper-list">
            {papers.map((paper, index) => (
              <article
                className="search-paper-card"
                key={paper.openalex_id || paper.doi || index}
              >
                <div className="search-paper-top">
                  <span>#{index + 1}</span>
                  <span>{getSources(paper).join(' + ')}</span>
                </div>

                <h4>{paper.title || 'Untitled publication'}</h4>

                <p className="search-paper-meta">
                  {(paper.authors || []).join(', ') || 'Authors unavailable'}
                  {paper.year ? ` · ${paper.year}` : ''}
                  {paper.journal ? ` · ${paper.journal}` : ''}
                </p>

                {paper.abstract && (
                  <details>
                    <summary>View abstract</summary>
                    <p className="search-paper-abstract">
                      {paper.abstract}
                    </p>
                  </details>
                )}

                {(paper.landing_page_url || paper.url || paper.doi) && (
                  <a
                    href={
                      paper.landing_page_url ||
                      paper.url ||
                      (paper.doi?.startsWith('http')
                        ? paper.doi
                        : `https://doi.org/${paper.doi}`)
                    }
                    target="_blank"
                    rel="noreferrer"
                    className="paper-link"
                  >
                    View publication
                    <i className="bi bi-box-arrow-up-right" />
                  </a>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
