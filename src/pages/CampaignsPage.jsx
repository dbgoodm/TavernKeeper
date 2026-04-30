import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function CampaignsPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [campaigns, setCampaigns] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin, setShowJoin] = useState(false)
  const [form, setForm] = useState({ name: '', premise: '' })
  const [joinCode, setJoinCode] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    window.tk.getCampaigns().then(setCampaigns)
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    const result = await window.tk.createCampaign(form)
    if (result.success) {
      setCampaigns(prev => [result.campaign, ...prev])
      setShowCreate(false)
      setForm({ name: '', premise: '' })
    } else {
      setError(result.error)
    }
  }

  const handleJoin = async (e) => {
    e.preventDefault()
    setError('')
    const result = await window.tk.joinCampaign(joinCode.trim().toUpperCase())
    if (result.success) {
      setCampaigns(prev => [result.campaign, ...prev])
      setShowJoin(false)
      setJoinCode('')
    } else {
      setError(result.error)
    }
  }

  const isDM = user?.role === 'dm'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Top bar */}
      <div style={{
        background: 'var(--bg-sidebar)',
        borderBottom: '1px solid var(--border)',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent)' }}>⚔️ TavernKeeper</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            {user?.display_name} · <span className="badge badge-gold">{isDM ? 'DM' : 'Player'}</span>
          </span>
          <button className="btn btn-ghost btn-sm" onClick={logout}>Sign out</button>
        </div>
      </div>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
        <div className="page-header">
          <div>
            <h1>Your Campaigns</h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 13 }}>
              {campaigns.length === 0 ? 'No campaigns yet — create or join one to get started.' : `${campaigns.length} campaign${campaigns.length !== 1 ? 's' : ''}`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {isDM && (
              <button className="btn btn-primary" onClick={() => { setShowCreate(true); setShowJoin(false); setError('') }}>
                + New Campaign
              </button>
            )}
            {!isDM && (
              <button className="btn btn-secondary" onClick={() => { setShowJoin(true); setShowCreate(false); setError('') }}>
                Join Campaign
              </button>
            )}
          </div>
        </div>

        {/* Create form */}
        {showCreate && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 16, color: 'var(--accent)' }}>Create New Campaign</h3>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Campaign Name</label>
                <input
                  type="text"
                  placeholder="e.g. Lost Mine of Phandelver"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label>Premise (optional)</label>
                <textarea
                  placeholder="A brief description of the campaign setting and tone..."
                  value={form.premise}
                  onChange={e => setForm(f => ({ ...f, premise: e.target.value }))}
                />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="submit" className="btn btn-primary">Create</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Join form */}
        {showJoin && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 16, color: 'var(--accent)' }}>Join a Campaign</h3>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={handleJoin}>
              <div className="form-group">
                <label>Invite Code</label>
                <input
                  type="text"
                  placeholder="e.g. XK9A2F"
                  value={joinCode}
                  onChange={e => setJoinCode(e.target.value)}
                  required
                  style={{ textTransform: 'uppercase', letterSpacing: 2, fontWeight: 600 }}
                />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="submit" className="btn btn-primary">Join</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowJoin(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Campaign list */}
        {campaigns.length === 0 ? (
          <div className="empty-state">
            <h3>{isDM ? 'No campaigns yet' : 'Not in any campaigns'}</h3>
            <p>{isDM ? 'Create your first campaign to get started.' : 'Ask your DM for an invite code.'}</p>
          </div>
        ) : (
          <div className="grid-2">
            {campaigns.map(c => (
              <div key={c.id} className="card card-hover" onClick={() => navigate(`/campaign/${c.id}`)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 700 }}>{c.name}</h3>
                  {isDM && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-secondary)', padding: '2px 8px', borderRadius: 99, fontFamily: 'monospace', letterSpacing: 1 }}>
                      {c.invite_code}
                    </span>
                  )}
                </div>
                {c.premise && (
                  <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.5 }}>
                    {c.premise.length > 120 ? c.premise.slice(0, 120) + '...' : c.premise}
                  </p>
                )}
                <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                  Click to open →
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
