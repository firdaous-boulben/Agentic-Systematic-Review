import logo from '../assets/logo.png';

const features = [
  {
    icon: 'bi-search',
    title: 'Literature Discovery',
    description:
      'Retrieve relevant academic publications from research sources based on the review topic and search strategy.',
  },
  {
    icon: 'bi-diagram-3',
    title: 'Agentic Workflow',
    description:
      'Coordinate specialized AI agents to handle screening, data extraction, quality appraisal and synthesis.',
  },
  {
    icon: 'bi-clipboard-check',
    title: 'Human Oversight',
    description:
      'Keep researchers involved in critical decisions through human review and approval.',
  },
  {
    icon: 'bi-file-earmark-text',
    title: 'Structured Reporting',
    description:
      'Organize review findings, document the selection process and generate a structured final report.',
  },
];

const technologies = [
  { name: 'React', category: 'Frontend', icon: 'bi-code-slash' },
  { name: 'Vite', category: 'Development', icon: 'bi-lightning-charge' },
  { name: 'Python', category: 'Backend', icon: 'bi-terminal' },
  { name: 'FastAPI', category: 'API Framework', icon: 'bi-hdd-network' },
  { name: 'LangGraph', category: 'Agent Orchestration', icon: 'bi-diagram-3' },
];

export default function About() {
  return (
    <div className="page-container about-page">
      <div className="page-heading mb-4">
        <div>
          <h2>About ReviewAI</h2>
          <p>Discover the platform and the technology behind it.</p>
        </div>
      </div>

      <section className="about-hero">
        <div className="about-hero-content">
          <span className="about-eyebrow">
            <i className="bi bi-stars"></i>
            AI-POWERED RESEARCH ASSISTANT
          </span>

          <h1>Making systematic reviews more structured and transparent.</h1>

          <p>
            ReviewAI is an agentic AI platform designed to assist researchers
            throughout the systematic literature review process. It combines
            specialized AI agents, human oversight and structured workflows
            to support rigorous and reproducible research.
          </p>

          <div className="about-version">
            <span>ReviewAI</span>
            <span className="about-version-divider"></span>
            <span>Version 1.0.0</span>
          </div>
        </div>

        <div className="about-hero-visual">
          <div className="about-orbit orbit-one"></div>
          <div className="about-orbit orbit-two"></div>
          <div className="about-hero-icon">
            <img src={logo} alt="ReviewAI logo" />
          </div>
          <div className="about-floating-icon floating-one">
            <i className="bi bi-journal-text"></i>
          </div>
          <div className="about-floating-icon floating-two">
            <i className="bi bi-robot"></i>
          </div>
          <div className="about-floating-icon floating-three">
            <i className="bi bi-check2-circle"></i>
          </div>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-heading">
          <span>WHAT THE PLATFORM OFFERS</span>
          <h3>Designed for the research process</h3>
          <p>
            From discovering publications to producing a structured review,
            ReviewAI supports the key stages of the workflow.
          </p>
        </div>

        <div className="about-features">
          {features.map((feature, index) => (
            <div className="about-feature-card" key={feature.title}>
              <div className="about-feature-top">
                <div className="about-feature-icon">
                  <i className={`bi ${feature.icon}`}></i>
                </div>
                <span>0{index + 1}</span>
              </div>
              <h5>{feature.title}</h5>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="about-bottom-grid">
        <div className="about-panel">
          <div className="about-panel-heading">
            <div className="about-panel-icon">
              <i className="bi bi-diagram-2"></i>
            </div>
            <div>
              <h4>Review methodology</h4>
              <p>A structured approach to evidence synthesis.</p>
            </div>
          </div>

          <div className="about-methodology">
            <div>
              <strong>PRISMA 2020</strong>
              <span>Reporting guideline</span>
            </div>
            <i className="bi bi-check-circle-fill"></i>
          </div>

          <p className="about-panel-description">
            The platform follows the PRISMA 2020 framework to organize
            study identification, screening, eligibility assessment and
            inclusion, supporting transparent reporting of the review process.
          </p>
        </div>

        <div className="about-panel">
          <div className="about-panel-heading">
            <div className="about-panel-icon">
              <i className="bi bi-cpu"></i>
            </div>
            <div>
              <h4>Technology stack</h4>
              <p>Tools and frameworks powering ReviewAI.</p>
            </div>
          </div>

          <div className="about-technologies">
            {technologies.map((technology) => (
              <div className="about-technology" key={technology.name}>
                <i className={`bi ${technology.icon}`}></i>
                <div>
                  <strong>{technology.name}</strong>
                  <span>{technology.category}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="about-footer">
        <i className="bi bi-stars"></i>
        <span>ReviewAI — Supporting transparent and reproducible research.</span>
      </footer>
    </div>
  );
}
