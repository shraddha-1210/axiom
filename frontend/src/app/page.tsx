"use client";

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Search, FileText, Activity, Link2, Download, TerminalSquare, Moon, Sun, MoreVertical, LogOut, ChevronRight } from 'lucide-react';

export default function AppRouter() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [theme, setTheme] = useState('light');
  
  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  if (!isAuthenticated) {
    return <LoginScreen onLogin={() => setIsAuthenticated(true)} />;
  }

  return <EnterpriseDashboard onLogout={() => setIsAuthenticated(false)} theme={theme} setTheme={setTheme} />;
}

/* -------------------------------------------------------------------------- */
/* LOGIN SCREEN COMPONENT */
/* -------------------------------------------------------------------------- */
function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (email && password) onLogin();
  };

  return (
    <div className="auth-layout">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }} 
        transition={{ duration: 0.4 }}
        className="auth-card"
      >
        <div className="auth-header">
          <TerminalSquare size={32} style={{ color: 'var(--text-main)', margin: '0 auto 1rem auto' }} />
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, letterSpacing: '1px' }}>AXIOM CORE</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>Enterprise SOC Portal</p>
        </div>
        
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>Analyst ID / Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="analyst@axiom.internal" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>Security Passphrase</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••••••" />
          </div>
          
          <button type="submit" className="btn-primary" style={{ marginTop: '1rem' }}>
            Authenticate Session
          </button>
        </form>
      </motion.div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* DASHBOARD COMPONENT */
/* -------------------------------------------------------------------------- */
function EnterpriseDashboard({ onLogout, theme, setTheme }: { onLogout: () => void, theme: string, setTheme: (v: string) => void }) {
  const [activeTab, setActiveTab] = useState('command_center');
  
  return (
    <div className="enterprise-layout">
      <aside className="sidebar">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="brand">
            <TerminalSquare size={20} />
            AXIOM
          </div>
        </div>
        
        <div className="nav-group" style={{ flex: 1 }}>
          <div className="kpi-label" style={{ marginBottom: '0.5rem' }}>Modules</div>
          <div className={`nav-item ${activeTab === 'command_center' ? 'active' : ''}`} onClick={() => setActiveTab('command_center')}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}><Activity size={16} /> Overview</span>
          </div>
          <div className={`nav-item ${activeTab === 'interrogation' ? 'active' : ''}`} onClick={() => setActiveTab('interrogation')}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}><Search size={16} /> Triage Sandbox</span>
          </div>
          <div className={`nav-item ${activeTab === 'provenance' ? 'active' : ''}`} onClick={() => setActiveTab('provenance')}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}><FileText size={16} /> Audit Ledger</span>
          </div>
          <div className={`nav-item ${activeTab === 'scrapers' ? 'active' : ''}`} onClick={() => setActiveTab('scrapers')}>
           <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}><Link2 size={16} /> Pipeline Hooks</span>
          </div>
        </div>

        <div style={{ padding: '1rem 0', borderTop: '1px solid var(--border-muted)', display: 'flex', justifyContent: 'space-between' }}>
           <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--threat-low)' }}></div>
              SOC_ADMIN_01
           </div>
           <LogOut size={16} style={{ color: 'var(--text-muted)', cursor: 'pointer' }} onClick={onLogout} />
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Root <ChevronRight size={14}/> <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>{activeTab.replace('_', ' ').toUpperCase()}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button className="btn-secondary" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} style={{ border: 'none', padding: '0.5rem' }}>
               {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </div>

        <div className="content-scroll">
          {activeTab === 'command_center' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="page-header">
                <h1 className="page-title">Command Center</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '0.5rem 0 0 0' }}>Real-time telemetry and ingestion queue.</p>
              </div>

              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Volume Indexed (24h)</div>
                  <div className="kpi-value">14,290</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Cache Intercepts</div>
                  <div className="kpi-value">1,902</div>
                </div>
                <div className="kpi-card" style={{ borderLeft: '2px solid var(--threat-high)' }}>
                  <div className="kpi-label">Critical Incidents</div>
                  <div className="kpi-value" style={{ color: 'var(--threat-high)' }}>47</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
                <div className="panel">
                  <div className="panel-header">Pipeline Event Feed</div>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Resource ID</th>
                        <th>Origin Context</th>
                        <th>Status</th>
                        <th>Routing</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ fontFamily: 'monospace' }}>vid_xt9918</td>
                        <td>Reddit Scraper</td>
                        <td><span className="status-badge status-green">VERIFIED</span></td>
                        <td>L2 Cache Hit</td>
                      </tr>
                      <tr>
                        <td style={{ fontFamily: 'monospace' }}>vid_jk0192</td>
                        <td>Organic YouTube</td>
                        <td><span className="status-badge status-red">FRAUD HIT</span></td>
                        <td>Gemini 94% Match</td>
                      </tr>
                      <tr>
                        <td style={{ fontFamily: 'monospace' }}>vid_manual_8</td>
                        <td>Admin Upload</td>
                        <td><span className="status-badge" style={{ background: 'var(--border-muted)' }}>PROCESSING</span></td>
                        <td>FFmpeg Pipeline</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="panel">
                  <div className="panel-header">Direct Escalation</div>
                  <div style={{ padding: '1.5rem' }}>
                    <div className="upload-box">
                      <Download size={24} style={{ color: 'var(--accent)', marginBottom: '1rem' }} />
                      <div style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-main)' }}>Upload Suspicious Asset</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>MP4/AVI maximum 50MB</div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          {activeTab === 'interrogation' && (
             <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                 <div className="page-header">
                     <h1 className="page-title">Deep Interrogation</h1>
                 </div>
                 <div className="panel" style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                     <Search size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
                     <p>Select a flagged asset from the Overview table to expand forensic telemetry mapping.</p>
                 </div>
             </motion.div>
          )}

          {activeTab === 'provenance' && (
             <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                 <div className="page-header">
                     <h1 className="page-title">Provenance Ledger</h1>
                 </div>
                 <div className="panel">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Object Hash (SHA-256)</th>
                        <th>C2PA Standard</th>
                        <th>Issuer</th>
                        <th>Signature Integrity</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>a126...78f4</td>
                        <td>Local-RSA-2048-MVP</td>
                        <td>shivaa</td>
                        <td><span className="status-badge status-green">VALID</span></td>
                      </tr>
                    </tbody>
                  </table>
                 </div>
             </motion.div>
          )}

          {activeTab === 'scrapers' && (
             <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                 <div className="page-header">
                     <h1 className="page-title">Pipeline Settings</h1>
                 </div>
                 <div className="kpi-grid">
                    <div className="panel" style={{ padding: '1.5rem' }}>
                       <div className="kpi-label">YouTube Sync</div>
                       <br/>
                       <span className="status-badge status-green">ACTIVE</span>
                    </div>
                    <div className="panel" style={{ padding: '1.5rem' }}>
                       <div className="kpi-label">Reddit Crawler</div>
                       <br/>
                       <span className="status-badge status-green">ACTIVE</span>
                    </div>
                 </div>
             </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
