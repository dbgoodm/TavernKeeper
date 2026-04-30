import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const TABS_DM = ['Dashboard', 'Members', 'Notes', 'World Atlas']
const TABS_PLAYER = ['Character', 'Notes', 'World Atlas']

export default function CampaignPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState(null)
  const [activeTab, setActiveTab] = useState(user?.role === 'dm' ? 'Dashboard' : 'Character')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    window.tk.getCampaign(id).then(c => {
      setCampaign(c)
      setLoading(false)
    })
  }, [id])

  if (loading) return <div style={{ padding: 32, color: 'var(--text-secondary)' }}>Loading...</div>
  if (!campaign) return <div style={{ padding: 32, color: 'var(--text-secondary)' }}>Campaign not found.</div>

  const isDM = user?.role === 'dm'
  const tabs = isDM ? TABS_DM : TABS_PLAYER

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">⚔️ TavernKeeper</div>
          <div className="sidebar-subtitle">{campaign.name}</div>
        </div>

        <nav className="sidebar-nav">
          {tabs.map(tab => (
            <div
              key={tab}
              className={`nav-item ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tabIcon(tab)} {tab}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
            {user?.display_name} · {isDM ? 'DM' : 'Player'}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ width: '100%', justifyContent: 'flex-start', padding: '6px 0' }}>
            ← All Campaigns
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="main-content">
        {activeTab === 'Dashboard' && <DashboardTab campaign={campaign} />}
        {activeTab === 'Members' && <MembersTab campaignId={id} />}
        {activeTab === 'Notes' && <NotesTab campaignId={id} user={user} />}
        {activeTab === 'World Atlas' && <WikiTab campaignId={id} isDM={isDM} />}
        {activeTab === 'Character' && <CharacterTab campaignId={id} />}
      </div>
    </div>
  )
}

function tabIcon(tab) {
  const icons = {
    Dashboard: '🏰',
    Members: '👥',
    Notes: '📝',
    'World Atlas': '🗺️',
    Character: '⚔️',
  }
  return icons[tab] || '•'
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
function DashboardTab({ campaign }) {
  return (
    <div>
      <div className="page-header">
        <h1>{campaign.name}</h1>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace', letterSpacing: 1 }}>
          Invite: {campaign.invite_code}
        </span>
      </div>
      {campaign.premise && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>Campaign Premise</div>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>{campaign.premise}</p>
        </div>
      )}
      <div className="grid-2">
        <div className="card">
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>QUICK TIPS</div>
          <ul style={{ paddingLeft: 16, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 2 }}>
            <li>Share the invite code with your players</li>
            <li>Build out your World Atlas with lore</li>
            <li>Add notes during sessions</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

// ── MEMBERS ───────────────────────────────────────────────────────────────────
function MembersTab({ campaignId }) {
  const [members, setMembers] = useState([])

  useEffect(() => {
    window.tk.getMembers(campaignId).then(setMembers)
  }, [campaignId])

  return (
    <div>
      <div className="page-header">
        <h1>Party Members</h1>
        <span className="badge badge-gray">{members.length} members</span>
      </div>
      {members.length === 0 ? (
        <div className="empty-state">
          <h3>No members yet</h3>
          <p>Share your invite code to bring players in.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {members.map(m => (
            <div key={m.id} className="card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{
                width: 44, height: 44, borderRadius: '50%',
                background: 'var(--bg-secondary)',
                border: '2px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, flexShrink: 0
              }}>
                {m.portrait_url ? <img src={m.portrait_url} style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : '🧙'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{m.character_name || m.display_name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {[m.class_name, m.subclass].filter(Boolean).join(' – ')}
                  {m.level ? ` · Level ${m.level}` : ''}
                  {m.species ? ` · ${m.species}` : ''}
                </div>
              </div>
              <span className={`badge ${m.role === 'dm' ? 'badge-gold' : 'badge-gray'}`}>
                {m.role === 'dm' ? 'DM' : 'Player'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── NOTES ─────────────────────────────────────────────────────────────────────
function NotesTab({ campaignId, user }) {
  const [notes, setNotes] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ title: '', body: '', visibility: 'private' })

  useEffect(() => {
    window.tk.getNotes(campaignId).then(setNotes)
  }, [campaignId])

  const handleSave = async (e) => {
    e.preventDefault()
    if (editing) {
      await window.tk.updateNote(editing.id, form)
      setNotes(prev => prev.map(n => n.id === editing.id ? { ...n, ...form } : n))
      setEditing(null)
    } else {
      const result = await window.tk.createNote(campaignId, form)
      if (result.success) setNotes(prev => [result.note, ...prev])
    }
    setShowForm(false)
    setForm({ title: '', body: '', visibility: 'private' })
  }

  const handleEdit = (note) => {
    setEditing(note)
    setForm({ title: note.title, body: note.body, visibility: note.visibility })
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    await window.tk.deleteNote(id)
    setNotes(prev => prev.filter(n => n.id !== id))
  }

  return (
    <div>
      <div className="page-header">
        <h1>Notes</h1>
        <button className="btn btn-primary btn-sm" onClick={() => { setShowForm(!showForm); setEditing(null); setForm({ title: '', body: '', visibility: 'private' }) }}>
          + New Note
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 16, color: 'var(--accent)' }}>{editing ? 'Edit Note' : 'New Note'}</h3>
          <form onSubmit={handleSave}>
            <div className="form-group">
              <label>Title</label>
              <input type="text" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required placeholder="Note title..." />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))} placeholder="Write your note..." style={{ minHeight: 120 }} />
            </div>
            <div className="form-group">
              <label>Visibility</label>
              <select value={form.visibility} onChange={e => setForm(f => ({ ...f, visibility: e.target.value }))}>
                <option value="private">Private (only me)</option>
                <option value="all_players">All Players</option>
                <option value="dm_only">DM Only</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary btn-sm">{editing ? 'Save Changes' : 'Create Note'}</button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setShowForm(false); setEditing(null) }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {notes.length === 0 ? (
        <div className="empty-state">
          <h3>No notes yet</h3>
          <p>Create a note to keep track of important information.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {notes.map(n => (
            <div key={n.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{n.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {n.author_name} · <span className={`badge ${n.visibility === 'private' ? 'badge-gray' : 'badge-green'}`}>{n.visibility}</span>
                  </div>
                </div>
                {n.author_user_id === user?.id && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(n)}>Edit</button>
                    <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(n.id)}>Delete</button>
                  </div>
                )}
              </div>
              {n.body && <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{n.body}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── WORLD ATLAS ───────────────────────────────────────────────────────────────
function WikiTab({ campaignId, isDM }) {
  const [pages, setPages] = useState([])
  const [category, setCategory] = useState('all')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', content: '', world_category: 'lore', subtitle: '', summary: '', visibility: 'all_players' })

  const CATEGORIES = ['all', 'lore', 'locations', 'factions', 'npcs', 'items', 'gods', 'history']

  useEffect(() => {
    window.tk.getWikiPages(campaignId, category === 'all' ? null : category).then(setPages)
  }, [campaignId, category])

  const handleCreate = async (e) => {
    e.preventDefault()
    const result = await window.tk.createWikiPage(campaignId, form)
    if (result.success) {
      setPages(prev => [...prev, result.page].sort((a, b) => a.title.localeCompare(b.title)))
      setShowForm(false)
      setForm({ title: '', content: '', world_category: 'lore', subtitle: '', summary: '', visibility: 'all_players' })
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>World Atlas</h1>
        {isDM && <button className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>+ New Page</button>}
      </div>

      {/* Category filter */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
        {CATEGORIES.map(c => (
          <button
            key={c}
            className={`btn btn-sm ${category === c ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCategory(c)}
            style={{ textTransform: 'capitalize' }}
          >
            {c}
          </button>
        ))}
      </div>

      {showForm && isDM && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 16, color: 'var(--accent)' }}>New Wiki Page</h3>
          <form onSubmit={handleCreate}>
            <div className="grid-2">
              <div className="form-group">
                <label>Title</label>
                <input type="text" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required placeholder="Page title..." />
              </div>
              <div className="form-group">
                <label>Category</label>
                <select value={form.world_category} onChange={e => setForm(f => ({ ...f, world_category: e.target.value }))}>
                  {CATEGORIES.filter(c => c !== 'all').map(c => <option key={c} value={c} style={{ textTransform: 'capitalize' }}>{c}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Subtitle</label>
              <input type="text" value={form.subtitle} onChange={e => setForm(f => ({ ...f, subtitle: e.target.value }))} placeholder="e.g. Ancient Dragon, City of Mages..." />
            </div>
            <div className="form-group">
              <label>Summary</label>
              <input type="text" value={form.summary} onChange={e => setForm(f => ({ ...f, summary: e.target.value }))} placeholder="One-line description..." />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} placeholder="Full lore entry..." style={{ minHeight: 160 }} />
            </div>
            <div className="form-group">
              <label>Visibility</label>
              <select value={form.visibility} onChange={e => setForm(f => ({ ...f, visibility: e.target.value }))}>
                <option value="all_players">All Players</option>
                <option value="dm_only">DM Only</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary btn-sm">Create Page</button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {pages.length === 0 ? (
        <div className="empty-state">
          <h3>No pages yet</h3>
          <p>{isDM ? 'Create your first lore entry.' : 'Your DM hasn\'t added any world lore yet.'}</p>
        </div>
      ) : (
        <div className="grid-2">
          {pages.map(p => (
            <div key={p.id} className="card card-hover">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ textTransform: 'capitalize', fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>{p.world_category}</span>
                {p.visibility === 'dm_only' && <span className="badge badge-gold" style={{ fontSize: 10 }}>DM Only</span>}
              </div>
              <div style={{ fontWeight: 700, fontSize: 15 }}>{p.title}</div>
              {p.subtitle && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{p.subtitle}</div>}
              {p.summary && <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>{p.summary}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── CHARACTER SHEET ───────────────────────────────────────────────────────────
function CharacterTab({ campaignId }) {
  const [char, setChar] = useState(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})

  useEffect(() => {
    window.tk.getCharacter(campaignId).then(c => {
      setChar(c)
      if (c) setForm(c)
    })
  }, [campaignId])

  const handleSave = async (e) => {
    e.preventDefault()
    await window.tk.updateCharacter(campaignId, form)
    setChar(prev => ({ ...prev, ...form }))
    setEditing(false)
  }

  const f = editing ? form : (char || {})
  const Field = ({ label, field, type = 'text', style = {} }) => (
    <div className="form-group" style={style}>
      <label>{label}</label>
      {editing ? (
        <input type={type} value={f[field] || ''} onChange={e => setForm(prev => ({ ...prev, [field]: e.target.value }))} />
      ) : (
        <div style={{ padding: '9px 12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', color: f[field] ? 'var(--text-primary)' : 'var(--text-muted)', minHeight: 38 }}>
          {f[field] || <em style={{ fontSize: 12 }}>—</em>}
        </div>
      )}
    </div>
  )

  const StatBox = ({ label, field }) => (
    <div style={{ textAlign: 'center', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px 8px' }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>{label}</div>
      {editing ? (
        <input type="text" value={f[field] || ''} onChange={e => setForm(prev => ({ ...prev, [field]: e.target.value }))}
          style={{ width: '100%', textAlign: 'center', fontWeight: 700, fontSize: 18, background: 'transparent', border: 'none', color: 'var(--text-primary)', outline: 'none' }} />
      ) : (
        <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent)' }}>{f[field] || '—'}</div>
      )}
    </div>
  )

  if (!char) return <div className="empty-state"><h3>Character not found</h3></div>

  return (
    <div>
      <div className="page-header">
        <h1>{char.character_name || 'Your Character'}</h1>
        <button className="btn btn-secondary btn-sm" onClick={() => setEditing(!editing)}>
          {editing ? '✕ Cancel' : '✏️ Edit'}
        </button>
      </div>

      <form onSubmit={handleSave}>
        {/* Identity */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 }}>Identity</div>
          <div className="grid-3">
            <Field label="Character Name" field="character_name" />
            <Field label="Class" field="class_name" />
            <Field label="Subclass" field="subclass" />
            <Field label="Level" field="level" />
            <Field label="Species" field="species" />
            <Field label="Background" field="background" />
          </div>
        </div>

        {/* Ability Scores */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 }}>Ability Scores</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 10 }}>
            {[['STR','strength'],['DEX','dexterity'],['CON','constitution'],['INT','intelligence'],['WIS','wisdom'],['CHA','charisma']].map(([label, field]) => (
              <StatBox key={field} label={label} field={field} />
            ))}
          </div>
        </div>

        {/* Combat */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 }}>Combat</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
            <StatBox label="HP Max" field="max_hit_points" />
            <StatBox label="HP Current" field="current_hit_points" />
            <StatBox label="Armor Class" field="armor_class" />
            <StatBox label="Speed" field="speed" />
            <StatBox label="Initiative" field="initiative_bonus" />
            <StatBox label="Prof. Bonus" field="proficiency_bonus" />
          </div>
        </div>

        {/* Notes */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 }}>Character Notes</div>
          {editing ? (
            <textarea value={f.character_notes || ''} onChange={e => setForm(prev => ({ ...prev, character_notes: e.target.value }))}
              style={{ width: '100%', minHeight: 120, background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-primary)', padding: '9px 12px', fontSize: 14, resize: 'vertical' }} />
          ) : (
            <p style={{ color: f.character_notes ? 'var(--text-secondary)' : 'var(--text-muted)', whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>
              {f.character_notes || <em>No notes yet.</em>}
            </p>
          )}
        </div>

        {editing && (
          <button type="submit" className="btn btn-primary">Save Character</button>
        )}
      </form>
    </div>
  )
}
