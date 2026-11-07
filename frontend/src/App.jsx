import React, { useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CheckCircle, XCircle, TrendingUp, Award, User, BookOpen, Briefcase, Target } from 'lucide-react';
import './App.css';
import './Review.css';

const COLORS = ['#4CAF50', '#f44336'];

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
    text: ''
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showReport, setShowReport] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setShowReport(false);

    try {
      const response = await fetch('http://localhost:8000/analyze-and-save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to analyze text');
      }

      const data = await response.json();
      setResult(data.analysis);
      setShowReport(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getLevelColor = (level) => {
    switch(level) {
      case 'Advanced': return '#4CAF50';
      case 'Needs Improvement': return '#FF9800';
      case 'Beginner': return '#f44336';
      case 'Very Poor': return '#9C27B0';
      default: return '#2196F3';
    }
  };

  const getLevelIcon = (level) => {
    switch(level) {
      case 'Advanced': return <Award className="level-icon" />;
      case 'Needs Improvement': return <TrendingUp className="level-icon" />;
      default: return <BookOpen className="level-icon" />;
    }
  };

  const pieData = result ? [
    { name: 'Correct', value: result.total_words - result.mistakes },
    { name: 'Mistakes', value: result.mistakes }
  ] : [];

  const barData = result ? [
    { name: 'Total Words', value: result.total_words, fill: '#2196F3' },
    { name: 'Correct', value: result.total_words - result.mistakes, fill: '#4CAF50' },
    { name: 'Mistakes', value: result.mistakes, fill: '#f44336' }
  ] : [];

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>📝 English Spelling Analyzer</h1>
          <p>Analyze your English writing and get instant feedback</p>
        </div>
      </header>

      <div className="container">
        <div className="form-section">
          <h2>👤 Personal Information</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label>
                  <User size={16} />
                  Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter your name"
                />
              </div>

              <div className="form-group">
                <label>🎂 Age</label>
                <input
                  type="text"
                  name="age"
                  value={formData.age}
                  onChange={handleInputChange}
                  placeholder="Enter your age"
                />
              </div>

              <div className="form-group">
                <label>
                  <BookOpen size={16} />
                  Study
                </label>
                <input
                  type="text"
                  name="study"
                  value={formData.study}
                  onChange={handleInputChange}
                  placeholder="e.g., B.Tech, M.Sc"
                />
              </div>

              <div className="form-group">
                <label>🎓 Graduated?</label>
                <select
                  name="graduated"
                  value={formData.graduated}
                  onChange={handleInputChange}
                >
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </div>

              {formData.graduated === 'yes' && (
                <>
                  <div className="form-group">
                    <label>
                      <Briefcase size={16} />
                      Occupation
                    </label>
                    <input
                      type="text"
                      name="occupation"
                      value={formData.occupation}
                      onChange={handleInputChange}
                      placeholder="Your current job"
                    />
                  </div>

                  <div className="form-group">
                    <label>🎯 Hobbies</label>
                    <input
                      type="text"
                      name="hobbies"
                      value={formData.hobbies}
                      onChange={handleInputChange}
                      placeholder="Your hobbies"
                    />
                  </div>

                  <div className="form-group full-width">
                    <label>
                      <Target size={16} />
                      Future Goal
                    </label>
                    <input
                      type="text"
                      name="goal"
                      value={formData.goal}
                      onChange={handleInputChange}
                      placeholder="What's your goal?"
                    />
                  </div>

                  <div className="form-group full-width">
                    <label>📝 Self Introduction (50 words)</label>
                    <textarea
                      name="self_intro"
                      value={formData.self_intro}
                      onChange={handleInputChange}
                      placeholder="Tell us about yourself..."
                      rows="3"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="form-group full-width">
              <label>
                ✍️ Text to Analyze *
              </label>
              <textarea
                name="text"
                value={formData.text}
                onChange={handleInputChange}
                required
                placeholder="Enter your English sentence or paragraph here..."
                rows="5"
                className="text-input"
              />
            </div>

            <button 
              type="submit" 
              className="submit-btn"
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="spinner"></div>
                  Analyzing...
                </>
              ) : (
                <>
                  🔍 Analyze Text
                </>
              )}
            </button>
          </form>

          {error && (
            <div className="error-message">
              <XCircle size={20} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {showReport && result && (
          <div className="results-section">
            <h2>📊 Analysis Report</h2>

            {/* Summary Cards */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#2196F3' }}>
                  📝
                </div>
                <div className="stat-info">
                  <h3>{result.total_words}</h3>
                  <p>Total Words</p>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#4CAF50' }}>
                  <CheckCircle size={24} />
                </div>
                <div className="stat-info">
                  <h3>{result.total_words - result.mistakes}</h3>
                  <p>Correct Words</p>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#f44336' }}>
                  <XCircle size={24} />
                </div>
                <div className="stat-info">
                  <h3>{result.mistakes}</h3>
                  <p>Mistakes</p>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#FF9800' }}>
                  📈
                </div>
                <div className="stat-info">
                  <h3>{result.percentage.toFixed(1)}%</h3>
                  <p>Error Rate</p>
                </div>
              </div>
            </div>

            {/* Level Badge */}
            <div className="level-badge" style={{ background: getLevelColor(result.level) }}>
              {getLevelIcon(result.level)}
              <div>
                <h3>{result.level}</h3>
                <p>{result.feedback}</p>
              </div>
            </div>

            {/* Charts */}
            <div className="charts-grid">
              <div className="chart-card">
                <h3>📊 Accuracy Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-card">
                <h3>📈 Word Statistics</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={barData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Text Comparison */}
            <div className="text-comparison">
              <div className="text-box">
                <h3>📄 Original Text</h3>
                <p>{result.original}</p>
              </div>
              <div className="arrow">→</div>
              <div className="text-box corrected">
                <h3>✅ Corrected Text</h3>
                <p>{result.corrected}</p>
              </div>
            </div>

            {/* Corrections & grammar (new) */}
            {(result.corrections?.length > 0 || result.grammar?.length > 0) && (
              <div className="review-panel">
                {result.corrections?.length > 0 && (
                  <>
                    <h3>🔤 Spelling ({result.corrections.length})</h3>
                    <ul className="review-list">
                      {result.corrections.map((c, i) => (
                        <li key={i}>
                          <span className="bad">{c.original}</span> → <span className="good">{c.suggestion}</span>
                          <span className={`badge ${c.applied ? 'applied' : 'review'}`}>
                            {c.applied ? 'fixed' : 'please review'} · {Math.round(c.confidence * 100)}%
                          </span>
                          {c.kind === 'context' && <span className="badge ctx">wrong word</span>}
                          {c.suggestions?.length > 1 && (
                            <small> also: {c.suggestions.slice(1, 4).join(', ')}</small>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {result.grammar?.length > 0 && (
                  <>
                    <h3>📐 Grammar ({result.grammar.length})</h3>
                    <ul className="review-list">
                      {result.grammar.map((g, i) => (
                        <li key={i}>
                          <span className="bad">{g.original}</span>
                          {g.suggestion && <> → <span className="good">{g.suggestion}</span></>}
                          <small> {g.message}</small>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {/* Download Button */}
            <button 
              className="download-btn"
              onClick={() => window.print()}
            >
              🖨️ Print Report
            </button>
          </div>
        )}
      </div>

      <footer className="footer">
        <p>© 2026 English Spelling Analyzer | Powered by FastAPI & React</p>
      </footer>
    </div>
  );
}

export default App;
