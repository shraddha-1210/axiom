"use client";

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, FileText, Activity, Link2, Download, TerminalSquare, Moon, Sun, LogOut, RefreshCw, AlertTriangle, CheckCircle, Zap, Shield } from 'lucide-react';

/* ─── Nav Config ─────────────────────────────────────────────────────────── */
const NAV_ITEMS = [
  { key: 'command_center', label: 'Overview', icon: <Activity size={15} />, shortcut: '⌘1' },
  { key: 'interrogation', label: 'Triage Sandbox', icon: <Search size={15} />, shortcut: '⌘2' },
  { key: 'provenance', label: 'Audit Ledger', icon: <FileText size={15} />, shortcut: '⌘3' },
  { key: 'scrapers', label: 'Pipeline Hooks', icon: <Link2 size={15} />, shortcut: '⌘4' },
];

const MODULE_NAMES: Record<string, string> = {
  command_center: 'Command Center',
  interrogation: 'Deep Interrogation',
  provenance: 'Provenance Ledger',
  scrapers: 'Pipeline Settings',
};

/* ─── Interfaces ─────────────────────────────────────────────────────────── */
interface TriageData {
  pHashScore: string;
  aHashScore: string;
  audioFingerprint: string;
  routingDecision: string;
}
interface GeminiData {
  confidence: string;
  classification: string;
  recommendedAction: string;
  forensicSignals: string[];
}
interface FeedRow {
  id: string;
  origin: string;
  timestamp: string;
  status: 'VERIFIED' | 'FRAUD HIT' | 'PROCESSING' | 'ARCHIVED';
  routing: string;
  triageData: TriageData;
  geminiData: GeminiData;
}
type Asset = FeedRow;

interface WorkerStatus {
  id: string;
  name: string;
  status: 'ACTIVE' | 'IDLE' | 'ERROR';
  lastRun: string;
  loading: boolean;
  error: string | null;
}

interface ProvenanceRecord {
  hash: string;
  standard: string;
  issuer: string;
  timestamp: string;
  integrity: 'VALID' | 'INVALID' | 'PENDING';
  claimGenerator: string;
  signingTimestamp: string;
  assetHash: string;
}

/* ─── Mock Data ──────────────────────────────────────────────────────────── */
const MOCK_FEED: FeedRow[] = [
  { id: 'vid_xt9918', origin: 'Reddit Scraper', timestamp: '2026-04-28 09:14:22', status: 'VERIFIED', routing: 'L2 Cache Hit', triageData: { pHashScore: '0.02', aHashScore: '0.01', audioFingerprint: 'No Match', routingDecision: 'Cache Hit — No Further Analysis' }, geminiData: { confidence: '98%', classification: 'Original Content', recommendedAction: 'Archive', forensicSignals: ['No deepfake markers', 'Consistent metadata'] } },
  { id: 'vid_jk0192', origin: 'Organic YouTube', timestamp: '2026-04-28 09:11:05', status: 'FRAUD HIT', routing: 'Gemini 94% Match', triageData: { pHashScore: '0.87', aHashScore: '0.91', audioFingerprint: 'Match — 94.2%', routingDecision: 'Escalated to Layer 3' }, geminiData: { confidence: '94%', classification: 'Deepfake Detected', recommendedAction: 'Issue Takedown', forensicSignals: ['Face swap detected', 'Audio-visual desync', 'GAN artifacts in frame 142'] } },
  { id: 'vid_manual_8', origin: 'Admin Upload', timestamp: '2026-04-28 09:08:47', status: 'PROCESSING', routing: 'FFmpeg Pipeline', triageData: { pHashScore: 'Pending', aHashScore: 'Pending', audioFingerprint: 'Pending', routingDecision: 'In Progress' }, geminiData: { confidence: 'Pending', classification: 'Pending', recommendedAction: 'Await Results', forensicSignals: [] } },
  { id: 'vid_tg_0041', origin: 'Telegram Monitor', timestamp: '2026-04-28 09:05:33', status: 'FRAUD HIT', routing: 'Gemini 88% Match', triageData: { pHashScore: '0.79', aHashScore: '0.82', audioFingerprint: 'Match — 88.1%', routingDecision: 'Escalated to Layer 3' }, geminiData: { confidence: '88%', classification: 'Manipulated Media', recommendedAction: 'Issue Takedown', forensicSignals: ['Logo replacement detected', 'Inconsistent lighting'] } },
  { id: 'vid_yt_2291', origin: 'YouTube Sync', timestamp: '2026-04-28 09:02:11', status: 'VERIFIED', routing: 'L2 Cache Hit', triageData: { pHashScore: '0.03', aHashScore: '0.02', audioFingerprint: 'No Match', routingDecision: 'Cache Hit — No Further Analysis' }, geminiData: { confidence: '99%', classification: 'Original Content', recommendedAction: 'Archive', forensicSignals: ['Clean metadata', 'No manipulation markers'] } },
];

const INITIAL_WORKERS: WorkerStatus[] = [
  { id: 'youtube', name: 'YouTube Sync', status: 'ACTIVE', lastRun: '2026-04-28 09:10:00', loading: false, error: null },
  { id: 'reddit', name: 'Reddit Crawler', status: 'ACTIVE', lastRun: '2026-04-28 09:08:30', loading: false, error: null },
  { id: 'telegram', name: 'Telegram Monitor', status: 'IDLE', lastRun: '2026-04-28 08:55:12', loading: false, error: null },
];

const MOCK_PROVENANCE: ProvenanceRecord[] = Array.from({ length: 25 }, (_, i) => ({
  hash: `${['a126', 'b291', 'c384', 'd471', 'e512', 'f603', 'g714', 'h825'][i % 8]}...${['78f4', '91a2', '03b5', '14c8', '25d1', '36e4', '47f7', '58a0'][i % 8]}`,
  standard: i % 3 === 0 ? 'C2PA-1.3' : i % 3 === 1 ? 'Local-RSA-2048-MVP' : 'C2PA-1.2',
  issuer: ['axiom-soc', 'shivaa', 'admin-01', 'pipeline-auto'][i % 4],
  timestamp: `2026-04-${String(28 - (i % 10)).padStart(2, '0')} ${String(9 - (i % 9)).padStart(2, '0')}:${String(i * 3 % 60).padStart(2, '0')}:00`,
  integrity: i % 7 === 0 ? 'PENDING' : i % 11 === 0 ? 'INVALID' : 'VALID',
  claimGenerator: `axiom-pipeline/v${1 + (i % 3)}.${i % 10}.0`,
  signingTimestamp: `2026-04-${String(28 - (i % 10)).padStart(2, '0')}T${String(9 - (i % 9)).padStart(2, '0')}:${String(i * 3 % 60).padStart(2, '0')}:00Z`,
  assetHash: `sha256:${['a1b2c3d4e5f6', 'b2c3d4e5f6a1', 'c3d4e5f6a1b2', 'd4e5f6a1b2c3'][i % 4]}...${String(i).padStart(4, '0')}`,
}));

/* ─── Status Badge Helper ────────────────────────────────────────────────── */
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    'VERIFIED': 'status-green', 'VALID': 'status-green', 'ACTIVE': 'status-green',
    'FRAUD HIT': 'status-red', 'INVALID': 'status-red', 'ERROR': 'status-red',
    'PROCESSING': 'status-warn', 'PENDING': 'status-warn',
    'ARCHIVED': 'status-neutral', 'IDLE': 'status-neutral',
  };
  return <span className={`status-badge ${map[status] ?? 'status-neutral'}`}>{status}</span>;
}

/* ─── App Router ─────────────────────────────────────────────────────────── */
export default function AppRouter() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [theme, setTheme] = useState('light');
  const [analystEmail, setAnalystEmail] = useState('');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  if (!isAuthenticated) {
    return <LoginScreen onLogin={(email) => { setAnalystEmail(email); setIsAuthenticated(true); }} />;
  }
  return <EnterpriseDashboard onLogout={() => setIsAuthenticated(false)} theme={theme} setTheme={setTheme} analystEmail={analystEmail || 'analyst@axiom.internal'} />;
}

/* ─── Login Screen ───────────────────────────────────────────────────────── */
function LoginScreen({ onLogin }: { onLogin: (email: string) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (email && password) onLogin(email);
  };

  return (
    <div className="auth-layout">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="auth-card">
        <div className="auth-header">
          <div className="auth-logo-ring">
            <TerminalSquare size={22} />
          </div>
          <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, letterSpacing: '1.5px', color: 'var(--text-main)' }}>AXIOM CORE</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '0.375rem' }}>Enterprise SOC Portal</p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-subtle)', marginBottom: '0.375rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Analyst ID / Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="analyst@axiom.internal" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-subtle)', marginBottom: '0.375rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Security Passphrase</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••••••" />
          </div>
          <button type="submit" className="btn-primary" style={{ marginTop: '0.5rem', width: '100%', justifyContent: 'center', padding: '0.625rem' }}>
            <Shield size={14} /> Authenticate Session
          </button>
        </form>
      </motion.div>
    </div>
  );
}

/* ─── Enterprise Dashboard ───────────────────────────────────────────────── */
function EnterpriseDashboard({ onLogout, theme, setTheme, analystEmail }: {
  onLogout: () => void; theme: string; setTheme: (v: string) => void; analystEmail: string;
}) {
  const [activeTab, setActiveTab] = useState('command_center');
  const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'error' | 'success'>('idle');
  const [wafError, setWafError] = useState('');
  const [manifestData, setManifestData] = useState<any>(null);
  const [latency, setLatency] = useState('...');
  const [feedRows, setFeedRows] = useState<FeedRow[]>(MOCK_FEED);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [actionBarError, setActionBarError] = useState('');
  const [actionBarDisabled, setActionBarDisabled] = useState(false);
  const [workerStatuses, setWorkerStatuses] = useState<WorkerStatus[]>(INITIAL_WORKERS);
  const [provenanceRecords] = useState<ProvenanceRecord[]>(MOCK_PROVENANCE);
  const [provenancePage, setProvenancePage] = useState(1);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

  useEffect(() => { setActionBarError(''); setActionBarDisabled(false); }, [selectedAsset]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        const idx = parseInt(e.key, 10);
        if (idx >= 1 && idx <= 4) { e.preventDefault(); setActiveTab(NAV_ITEMS[idx - 1].key); }
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const t = Date.now();
        await fetch('http://localhost:8000/health');
        setLatency(`${Date.now() - t}ms`);
      } catch { setLatency('N/A'); }
    })();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadState('uploading'); setWafError('');
    const fd = new FormData(); fd.append('file', file);
    try {
      const res = await fetch(`http://localhost:8000/api/upload-source?asset_id=ui_${Date.now()}&uploader=soc_admin`, { method: 'POST', body: fd });
      const data = await res.json();
      if (res.status === 429) { setWafError('WAF Blocked: Rate Limit Exceeded'); setUploadState('error'); }
      else if (res.status === 403) { setWafError(`WAF Blocked: ${data.detail}`); setUploadState('error'); }
      else if (res.ok) { setManifestData(data.manifest); setUploadState('success'); }
      else { setWafError(data.error || 'Server Error'); setUploadState('error'); }
    } catch { setWafError('Network Error'); setUploadState('error'); }
  };

  const invokeWorker = async (workerId: string) => {
    setWorkerStatuses(p => p.map(w => w.id === workerId ? { ...w, loading: true, error: null } : w));
    try {
      const res = await fetch(`http://localhost:8000/api/scrapers/trigger?platform=${workerId}`);
      if (res.ok) {
        setWorkerStatuses(p => p.map(w => w.id === workerId ? { ...w, loading: false, status: 'ACTIVE', lastRun: new Date().toISOString().replace('T', ' ').slice(0, 19) } : w));
      } else {
        const d = await res.json().catch(() => ({}));
        setWorkerStatuses(p => p.map(w => w.id === workerId ? { ...w, loading: false, status: 'ERROR', error: d.detail || d.error || `Error ${res.status}` } : w));
      }
    } catch {
      setWorkerStatuses(p => p.map(w => w.id === workerId ? { ...w, loading: false, status: 'ERROR', error: 'Network error — could not reach backend.' } : w));
    }
  };

  const avatarInitials = analystEmail.slice(0, 2).toUpperCase();

  return (
    <div className="enterprise-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><TerminalSquare size={16} /></div>
          AXIOM
        </div>

        <div className="nav-group">
          <div className="nav-section-label">Modules</div>
          {NAV_ITEMS.map(item => (
            <div key={item.key} className={`nav-item ${activeTab === item.key ? 'active' : ''}`} onClick={() => setActiveTab(item.key)}>
              <span className="nav-item-left">{item.icon}{item.label}</span>
              <span className="nav-shortcut">{item.shortcut}</span>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">{avatarInitials}</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-email">{analystEmail}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.15rem' }}>
                <div className="sidebar-status-dot" />
                <span style={{ fontSize: '0.65rem', color: 'var(--threat-low)' }}>Online</span>
              </div>
            </div>
          </div>
          <button className="logout-btn" onClick={onLogout} title="Sign out"><LogOut size={15} /></button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="main">
        <div className="topbar">
          <div className="topbar-breadcrumb">
            <span className="topbar-breadcrumb-root">AXIOM</span>
            <span className="topbar-breadcrumb-sep">›</span>
            <span className="topbar-breadcrumb-current">{MODULE_NAMES[activeTab]}</span>
          </div>
          <div className="topbar-actions">
            <button className="icon-btn" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} title="Toggle theme">
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
          </div>
        </div>

        <div className="content-scroll">
          {activeTab === 'command_center' && <CommandCenterTab feedRows={feedRows} setFeedRows={setFeedRows} latency={latency} uploadState={uploadState} wafError={wafError} manifestData={manifestData} handleUpload={handleUpload} onRowClick={(row) => { setSelectedAsset(row); setActiveTab('interrogation'); }} />}
          {activeTab === 'interrogation' && <InterrogationTab selectedAsset={selectedAsset} actionBarError={actionBarError} actionBarDisabled={actionBarDisabled} setActionBarError={setActionBarError} setActionBarDisabled={setActionBarDisabled} setSelectedAsset={setSelectedAsset} />}
          {activeTab === 'provenance' && <ProvenanceTab provenanceRecords={provenanceRecords} provenancePage={provenancePage} setProvenancePage={setProvenancePage} expandedRowId={expandedRowId} setExpandedRowId={setExpandedRowId} />}
          {activeTab === 'scrapers' && <ScrapersTab workerStatuses={workerStatuses} invokeWorker={invokeWorker} />}
        </div>
      </main>
    </div>
  );
}

/* ─── Command Center Tab ─────────────────────────────────────────────────── */
function CommandCenterTab({ feedRows, setFeedRows, latency, uploadState, wafError, manifestData, handleUpload, onRowClick }: {
  feedRows: FeedRow[]; setFeedRows: (r: FeedRow[]) => void; latency: string;
  uploadState: string; wafError: string; manifestData: any;
  handleUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRowClick: (row: FeedRow) => void;
}) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="page-header">
        <h1 className="page-title">Command Center</h1>
        <p className="page-subtitle">Real-time telemetry and ingestion queue.</p>
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
        <div className="kpi-card kpi-card-accent">
          <div className="kpi-label">Critical Incidents</div>
          <div className="kpi-value kpi-value-danger">47</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">System Latency</div>
          <div className="kpi-value" style={{ fontSize: '1.5rem' }}>{latency}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '1.25rem' }}>
        <div className="panel">
          <div className="panel-header">
            <span className="panel-header-title"><Zap size={14} style={{ color: 'var(--accent)' }} />Pipeline Event Feed</span>
            <button className="btn-secondary" onClick={() => setFeedRows([...MOCK_FEED])} style={{ gap: '0.3rem' }}>
              <RefreshCw size={12} />Refresh
            </button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Resource ID</th>
                <th>Origin</th>
                <th>Timestamp</th>
                <th>Status</th>
                <th>Routing</th>
              </tr>
            </thead>
            <tbody>
              {feedRows.map(row => (
                <tr key={row.id} onClick={() => onRowClick(row)} style={{ cursor: 'pointer', background: row.status === 'FRAUD HIT' ? 'rgba(var(--threat-high-rgb), 0.06)' : undefined }}>
                  <td style={{ fontFamily: 'monospace', fontWeight: 500 }}>{row.id}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{row.origin}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-subtle)' }}>{row.timestamp}</td>
                  <td><StatusBadge status={row.status} /></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{row.routing}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <span className="panel-header-title"><Download size={14} style={{ color: 'var(--accent)' }} />Direct Escalation</span>
          </div>
          <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <label className="upload-box">
              <input type="file" style={{ display: 'none' }} onChange={handleUpload} accept="video/mp4,video/avi" />
              <div className="upload-icon-wrap">
                <Download size={18} />
              </div>
              <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-main)' }}>
                {uploadState === 'uploading' ? 'Analyzing via WAF...' : 'Upload Suspicious Asset'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', marginTop: '0.25rem' }}>MP4 / AVI · max 50MB</div>
            </label>
            {uploadState === 'error' && (
              <div className="alert alert-error"><AlertTriangle size={14} />{wafError}</div>
            )}
            {uploadState === 'success' && manifestData && (
              <div className="alert alert-success">
                <CheckCircle size={14} />
                <div>WAF passed. Manifest: <strong>{manifestData.signature_info?.issuer || manifestData.claim_generator}</strong></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ─── Interrogation Tab ──────────────────────────────────────────────────── */
function InterrogationTab({ selectedAsset, actionBarError, actionBarDisabled, setActionBarError, setActionBarDisabled, setSelectedAsset }: {
  selectedAsset: Asset | null; actionBarError: string; actionBarDisabled: boolean;
  setActionBarError: (v: string) => void; setActionBarDisabled: (v: boolean) => void;
  setSelectedAsset: (a: Asset | null) => void;
}) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="page-header">
        <h1 className="page-title">Deep Interrogation</h1>
        {selectedAsset && <p className="page-subtitle">Forensic workspace — <span style={{ fontFamily: 'monospace' }}>{selectedAsset.id}</span></p>}
      </div>

      {!selectedAsset ? (
        <div className="panel" style={{ padding: '5rem 2rem', textAlign: 'center' }}>
          <Search size={40} style={{ opacity: 0.15, display: 'block', margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.875rem' }}>Select a flagged asset from the Overview table to begin forensic analysis.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Asset Summary */}
          <div className="panel">
            <div className="panel-header"><span className="panel-header-title"><Shield size={14} style={{ color: 'var(--accent)' }} />Asset Summary</span></div>
            <div style={{ padding: '1.25rem 1.5rem', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
              {[
                { label: 'Asset ID', value: selectedAsset.id, mono: true },
                { label: 'Origin Context', value: selectedAsset.origin, mono: false },
                { label: 'Ingested At', value: selectedAsset.timestamp, mono: true },
              ].map(({ label, value, mono }) => (
                <div key={label}>
                  <div className="kpi-label">{label}</div>
                  <div style={{ fontFamily: mono ? 'monospace' : 'inherit', marginTop: '0.3rem', fontSize: '0.875rem', fontWeight: 500 }}>{value}</div>
                </div>
              ))}
              <div>
                <div className="kpi-label">Pipeline Status</div>
                <div style={{ marginTop: '0.3rem' }}><StatusBadge status={selectedAsset.status} /></div>
              </div>
            </div>
          </div>

          {/* Triage + Gemini */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
            <div className="panel">
              <div className="panel-header"><span className="panel-header-title">Triage Log</span></div>
              <div style={{ padding: '0.25rem 1.25rem 1rem' }}>
                {[
                  { label: 'pHash Match Score', value: selectedAsset.triageData.pHashScore },
                  { label: 'aHash Match Score', value: selectedAsset.triageData.aHashScore },
                  { label: 'Audio Fingerprint', value: selectedAsset.triageData.audioFingerprint },
                  { label: 'Routing Decision', value: selectedAsset.triageData.routingDecision },
                ].map(({ label, value }) => (
                  <div key={label} className="kv-row">
                    <span className="kv-label">{label}</span>
                    <span className="kv-value">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header"><span className="panel-header-title">Gemini Analysis</span></div>
              <div style={{ padding: '0.25rem 1.25rem 1rem' }}>
                {[
                  { label: 'Confidence Score', value: selectedAsset.geminiData.confidence },
                  { label: 'Classification', value: selectedAsset.geminiData.classification },
                  { label: 'Recommended Action', value: selectedAsset.geminiData.recommendedAction },
                ].map(({ label, value }) => (
                  <div key={label} className="kv-row">
                    <span className="kv-label">{label}</span>
                    <span className="kv-value">{value}</span>
                  </div>
                ))}
                {selectedAsset.geminiData.forensicSignals.length > 0 && (
                  <div style={{ marginTop: '0.75rem' }}>
                    <div className="kpi-label" style={{ marginBottom: '0.5rem' }}>Forensic Signals</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                      {selectedAsset.geminiData.forensicSignals.map((sig, i) => (
                        <div key={i} style={{ fontSize: '0.78rem', fontFamily: 'monospace', color: 'var(--text-muted)', paddingLeft: '0.625rem', borderLeft: '2px solid var(--accent-border)' }}>{sig}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="panel">
            <div className="panel-header"><span className="panel-header-title">Actions</span></div>
            <div style={{ padding: '1rem 1.25rem', display: 'flex', gap: '0.625rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <button className="btn-danger" disabled={actionBarDisabled} onClick={async () => {
                if (!window.confirm(`Issue takedown for ${selectedAsset.id}?`)) return;
                try {
                  const res = await fetch('http://localhost:8000/api/interrogate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ asset_id: selectedAsset.id, action: 'takedown' }) });
                  if (!res.ok) { const d = await res.json().catch(() => ({})); setActionBarError(d.detail || d.error || `Error ${res.status}`); }
                  else { setActionBarError(''); setActionBarDisabled(true); }
                } catch { setActionBarError('Network error — could not reach backend.'); }
              }}>
                <AlertTriangle size={13} /> Issue Takedown
              </button>
              <button className="btn-secondary" disabled={actionBarDisabled} onClick={() => { setSelectedAsset({ ...selectedAsset, status: 'ARCHIVED' }); setActionBarDisabled(true); setActionBarError(''); }}>
                Archive as False Positive
              </button>
              <button className="btn-secondary" disabled={actionBarDisabled} onClick={async () => {
                try {
                  const res = await fetch('http://localhost:8000/api/interrogate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ asset_id: selectedAsset.id, action: 'escalate' }) });
                  if (!res.ok) { const d = await res.json().catch(() => ({})); setActionBarError(d.detail || d.error || `Error ${res.status}`); }
                  else { setActionBarError(''); alert(`${selectedAsset.id} escalated to Tier 2.`); }
                } catch { setActionBarError('Network error — could not reach backend.'); }
              }}>
                Escalate to Tier 2
              </button>
            </div>
            {actionBarError && (
              <div style={{ margin: '0 1.25rem 1rem' }} className="alert alert-error"><AlertTriangle size={14} />{actionBarError}</div>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}

/* ─── Provenance Tab ─────────────────────────────────────────────────────── */
function ProvenanceTab({ provenanceRecords, provenancePage, setProvenancePage, expandedRowId, setExpandedRowId }: {
  provenanceRecords: ProvenanceRecord[]; provenancePage: number; setProvenancePage: (p: number) => void;
  expandedRowId: string | null; setExpandedRowId: (id: string | null) => void;
}) {
  const PAGE_SIZE = 20;
  const totalPages = Math.ceil(provenanceRecords.length / PAGE_SIZE);
  const pageRecords = provenanceRecords.slice((provenancePage - 1) * PAGE_SIZE, provenancePage * PAGE_SIZE);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="page-header">
        <h1 className="page-title">Provenance Ledger</h1>
        <p className="page-subtitle">Cryptographic chain of custody for all ingested assets.</p>
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-header-title"><FileText size={14} style={{ color: 'var(--accent)' }} />C2PA Manifest Records</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', fontWeight: 400 }}>{provenanceRecords.length} records</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Object Hash (SHA-256)</th>
              <th>C2PA Standard</th>
              <th>Issuer</th>
              <th>Timestamp</th>
              <th>Integrity</th>
            </tr>
          </thead>
          <tbody>
            {pageRecords.map((rec, idx) => {
              const rowKey = rec.hash + idx;
              const isExpanded = expandedRowId === rowKey;
              return (
                <>
                  <tr key={rowKey} onClick={() => setExpandedRowId(isExpanded ? null : rowKey)} style={{ cursor: 'pointer' }}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{rec.hash}</td>
                    <td style={{ fontSize: '0.8rem' }}>{rec.standard}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{rec.issuer}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-subtle)' }}>{rec.timestamp}</td>
                    <td><StatusBadge status={rec.integrity} /></td>
                  </tr>
                  {isExpanded && (
                    <tr key={rowKey + '_detail'}>
                      <td colSpan={5} style={{ padding: 0 }}>
                        <div className="expanded-detail">
                          {[
                            { label: 'Claim Generator', value: rec.claimGenerator },
                            { label: 'Signature Issuer', value: rec.issuer },
                            { label: 'Signing Timestamp', value: rec.signingTimestamp },
                            { label: 'Asset Hash', value: rec.assetHash },
                          ].map(({ label, value }) => (
                            <div key={label}>
                              <div className="expanded-field-label">{label}</div>
                              <div className="expanded-field-value">{value}</div>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="pagination-bar">
            <button className="btn-secondary" disabled={provenancePage <= 1} onClick={() => setProvenancePage(Math.max(1, provenancePage - 1))}>← Previous</button>
            <span className="pagination-info">Page {provenancePage} of {totalPages}</span>
            <button className="btn-secondary" disabled={provenancePage >= totalPages} onClick={() => setProvenancePage(Math.min(totalPages, provenancePage + 1))}>Next →</button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* ─── Scrapers Tab ───────────────────────────────────────────────────────── */
function ScrapersTab({ workerStatuses, invokeWorker }: { workerStatuses: WorkerStatus[]; invokeWorker: (id: string) => void }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Pipeline Settings</h1>
          <p className="page-subtitle">Scraper fleet management and dispatch controls.</p>
        </div>
        <button className="btn-primary" onClick={() => INITIAL_WORKERS.forEach(w => invokeWorker(w.id))}>
          <Zap size={13} /> Invoke All Scrapers
        </button>
      </div>

      <div className="worker-grid">
        {workerStatuses.map(worker => (
          <div key={worker.id} className="panel">
            <div className="panel-header">
              <span className="panel-header-title">{worker.name}</span>
              <StatusBadge status={worker.status} />
            </div>
            <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <div className="kpi-label">Last Successful Run</div>
                <div style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>{worker.lastRun}</div>
              </div>
              {worker.error && <div className="alert alert-error"><AlertTriangle size={13} />{worker.error}</div>}
              <button className="btn-secondary" disabled={worker.loading} onClick={() => invokeWorker(worker.id)} style={{ justifyContent: 'center' }}>
                {worker.loading ? <><RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} />Dispatching...</> : <><Zap size={12} />Invoke Scrape</>}
              </button>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
