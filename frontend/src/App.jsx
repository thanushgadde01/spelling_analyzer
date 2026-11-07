import React, { useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  FileCheck2,
  FileText,
  Loader2,
  Send,
  Sparkles,
  User,
  X,
} from 'lucide-react';
import './App.css';

function App() {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    study: '',
    graduated: 'no',
    occupation: '',
    hobbies: '',
    goal: '',
    self_intro: '',
    text: '',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(null);

  const wordCount = formData.text.trim() ? formData.text.trim().split(/\s+/).length : 0;

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData((previous) => ({ ...previous, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8000/analyze-and-save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Unable to analyze this text. Please check that the API is running.');
      }

      const data = await response.json();
      setResult(data.analysis);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const copySuggestion = async (suggestion, index) => {
    try {
      await navigator.clipboard.writeText(suggestion);
      setCopied(index);
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setError('The suggestion could not be copied.');
    }
  };

  const accuracy = result
    ? Math.max(0, 100 - Number(result.percentage || 0))
    : 0;
  const corrections = result?.corrections || [];
  const grammarIssues = result?.grammar || [];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <Sparkles size={20} />
          </div>
          <div>
            <span className="eyebrow">Writing intelligence</span>
            <h1>Spelling Analyzer</h1>
          </div>
        </div>
        <div className="status-pill">
          <span className="status-dot" />
          Analysis workspace
        </div>
      </header>

      <main className="workspace">
        <section className="intro">
          <div>
            <span className="eyebrow">Clarity at a glance</span>
            <h2>Polish every message before it goes out.</h2>
            <p>
              Check spelling, surface grammar issues, and get confident
              corrections in seconds.
            </p>
          </div>
          <div className="intro-icon" aria-hidden="true">
            <FileCheck2 size={28} />
          </div>
        </section>

        <div className="workspace-grid">
          <section className="editor-panel panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">Input</span>
                <h3>Review your writing</h3>
              </div>
              <FileText size={20} aria-hidden="true" />
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="name">
                  <User size={15} />
                  Workspace name
                </label>
                <input
                  id="name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter your name"
                />
              </div>

              <button
                className="details-toggle"
                type="button"
                onClick={() => setShowDetails((visible) => !visible)}
                aria-expanded={showDetails}
              >
                Optional profile details
                <ChevronDown className={showDetails ? 'rotate-icon' : ''} size={16} />
              </button>

              {showDetails && (
                <div className="details-grid">
                  <div className="form-group">
                    <label htmlFor="age">Age</label>
                    <input id="age" name="age" value={formData.age} onChange={handleInputChange} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="study">Study</label>
                    <input id="study" name="study" value={formData.study} onChange={handleInputChange} placeholder="e.g. B.Tech" />
                  </div>
                  <div className="form-group">
                    <label htmlFor="graduated">Graduation</label>
                    <select id="graduated" name="graduated" value={formData.graduated} onChange={handleInputChange}>
                      <option value="no">Not graduated</option>
                      <option value="yes">Graduated</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="occupation">Occupation</label>
                    <input id="occupation" name="occupation" value={formData.occupation} onChange={handleInputChange} />
                  </div>
                </div>
              )}

              <div className="form-group editor-group">
                <div className="editor-label">
                  <label htmlFor="text">Text to analyze</label>
                  <span>{wordCount} words</span>
                </div>
                <textarea
                  id="text"
                  name="text"
                  value={formData.text}
                  onChange={handleInputChange}
                  required
                  placeholder="Paste an email, message, or paragraph here..."
                  rows={13}
                />
                <span className="field-hint">Your original formatting and line breaks are preserved.</span>
              </div>

              <button className="primary-button" type="submit" disabled={loading}>
                {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
                {loading ? 'Analyzing...' : 'Analyze writing'}
                {!loading && <ArrowRight size={17} />}
              </button>
            </form>

            {error && (
              <div className="error-message" role="alert">
                <AlertCircle size={18} />
                <span>{error}</span>
                <button type="button" onClick={() => setError(null)} aria-label="Dismiss error">
                  <X size={16} />
                </button>
              </div>
            )}
          </section>

          <section className="dashboard-panel panel">
            {!result ? (
              <div className="empty-dashboard">
                <div className="empty-icon"><BarChart3 size={25} /></div>
                <span className="eyebrow">Analysis dashboard</span>
                <h3>Your report will appear here</h3>
                <p>Submit your writing to see accuracy, corrections, and actionable suggestions.</p>
              </div>
            ) : (
              <div className="results-content">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">Analysis dashboard</span>
                    <h3>Writing report</h3>
                  </div>
                  <span className="level-tag">{result.level}</span>
                </div>

                <div className="metric-bar" aria-label="Writing metrics">
                  <div className="metric">
                    <span>Total words</span>
                    <strong>{result.total_words}</strong>
                  </div>
                  <div className="metric">
                    <span>Error rate</span>
                    <strong>{Number(result.percentage || 0).toFixed(1)}%</strong>
                  </div>
                  <div className="metric metric-success">
                    <span>Accuracy score</span>
                    <strong>{accuracy.toFixed(1)}%</strong>
                  </div>
                </div>

                <div className="feedback-callout">
                  <CheckCircle2 size={18} />
                  <p>{result.feedback}</p>
                </div>

                <div className="diff-card">
                  <div className="diff-column">
                    <span className="section-label">Original text</span>
                    <p>{result.original}</p>
                  </div>
                  <ArrowRight className="diff-arrow" size={18} aria-hidden="true" />
                  <div className="diff-column corrected-copy">
                    <span className="section-label">Corrected text</span>
                    <p>{result.corrected}</p>
                  </div>
                </div>

                <div className="suggestions-section">
                  <div className="section-heading">
                    <div>
                      <span className="section-label">Review queue</span>
                      <h4>Suggestions <span>{corrections.length}</span></h4>
                    </div>
                    <span className="muted-label">Spelling</span>
                  </div>
                  {corrections.length > 0 ? (
                    <div className="suggestions-table">
                      <div className="table-row table-header">
                        <span>Word</span>
                        <span>Correction</span>
                        <span>Confidence</span>
                        <span>Quick action</span>
                      </div>
                      {corrections.map((correction, index) => (
                        <div className="table-row" key={`${correction.start}-${correction.end}`}>
                          <span className="original-word">{correction.original}</span>
                          <span className="suggested-word">{correction.suggestion}</span>
                          <span>
                            <span className={`confidence ${correction.applied ? 'high' : 'medium'}`}>
                              {Math.round(correction.confidence * 100)}%
                            </span>
                          </span>
                          <button
                            className="icon-button"
                            type="button"
                            onClick={() => copySuggestion(correction.suggestion, index)}
                            title="Copy correction"
                          >
                            {copied === index ? <Check size={15} /> : <Clipboard size={15} />}
                            <span>{copied === index ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-issues"><CheckCircle2 size={17} /> No spelling corrections needed.</div>
                  )}
                </div>

                {grammarIssues.length > 0 && (
                  <div className="grammar-section">
                    <div className="section-heading">
                      <div>
                        <span className="section-label">Language quality</span>
                        <h4>Grammar issues <span>{grammarIssues.length}</span></h4>
                      </div>
                    </div>
                    <div className="grammar-list">
                      {grammarIssues.map((issue, index) => (
                        <div className="grammar-row" key={`${issue.start}-${issue.end}-${index}`}>
                          <span className="original-word">{issue.original}</span>
                          <ArrowRight size={14} />
                          <span className="suggested-word">{issue.suggestion || 'Review'}</span>
                          <span>{issue.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="footer">
        <span>Spelling Analyzer</span>
        <span>FastAPI + React workspace</span>
      </footer>
    </div>
  );
}

export default App;
