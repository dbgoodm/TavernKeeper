const { v4: uuidv4 } = require('uuid')
const { createHash } = require('crypto')
const { getDb } = require('./database')

function hashPassword(password) {
  return createHash('sha256').update(password + 'tavernkeeper-salt').digest('hex')
}
function now() { return new Date().toISOString() }
function generateInviteCode() {
  return Math.random().toString(36).substring(2, 8).toUpperCase()
}
function sanitizeUser(user) {
  var copy = Object.assign({}, user)
  delete copy.password_hash
  return copy
}

let currentUser = null
let saveFn = null

function rows(sql, params) {
  var db = getDb()
  if (!params) params = []
  var stmt = db.prepare(sql)
  var result = []
  while (stmt.step()) {
    result.push(stmt.getAsObject())
  }
  stmt.free()
  return result
}

function run(sql, params) {
  var db = getDb()
  db.run(sql, params || [])
  if (saveFn) saveFn()
}

function registerHandlers(ipcMain, saveFnParam) {
  saveFn = saveFnParam
  var wrap = function(channel, fn) {
    ipcMain.handle(channel, async function(_, args) {
      try { return await fn(args) }
      catch (err) { console.error("[" + channel + "]", err); return { success: false, error: err.message } }
    })
  }

  wrap("auth:login", async function(data) {
    var results = rows("SELECT * FROM users WHERE email = ?", [data.email])
    var user = results[0]
    if (!user || user.password_hash !== hashPassword(data.password))
      return { success: false, error: "Invalid email or password" }
    currentUser = user
    return { success: true, user: sanitizeUser(user) }
  })

  wrap("auth:register", async function(data) {
    var existing = rows("SELECT id FROM users WHERE email = ?", [data.email])
    if (existing.length) return { success: false, error: "Email already in use" }
    var user = {
      id: uuidv4(), email: data.email, display_name: data.displayName,
      password_hash: hashPassword(data.password), role: data.role || "player",
      profile_image_url: "", pronouns: "", default_note_visibility: "private",
      ui_density: "comfortable", timezone: "America/New_York", created_at: now()
    }
    run("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?)",
      [user.id, user.email, user.display_name, user.password_hash, user.role, user.profile_image_url, user.pronouns, user.default_note_visibility, user.ui_density, user.timezone, user.created_at])
    currentUser = user
    return { success: true, user: sanitizeUser(user) }
  })

  wrap("auth:logout", async function() { currentUser = null; return { success: true } })

  wrap("campaigns:list", async function() {
    if (!currentUser) return []
    if (currentUser.role === "dm")
      return rows("SELECT * FROM campaigns WHERE dm_user_id = ? ORDER BY created_at DESC", [currentUser.id])
    return rows("SELECT c.* FROM campaigns c JOIN memberships m ON m.campaign_id = c.id WHERE m.user_id = ? ORDER BY c.created_at DESC", [currentUser.id])
  })

  wrap("campaigns:get", async function(id) {
    var results = rows("SELECT * FROM campaigns WHERE id = ?", [id])
    return results[0] || null
  })

  wrap("campaigns:create", async function(data) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    var campaign = {
      id: uuidv4(), name: data.name, premise: data.premise || "",
      invite_code: generateInviteCode(), dm_user_id: currentUser.id,
      world_atlas_title: "World Atlas", world_atlas_intro: "",
      emporium_hide_uncommon_plus: 1, created_at: now()
    }
    run("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?)",
      [campaign.id, campaign.name, campaign.premise, campaign.invite_code, campaign.dm_user_id, campaign.world_atlas_title, campaign.world_atlas_intro, campaign.emporium_hide_uncommon_plus, campaign.created_at])
    run("INSERT INTO memberships (id, campaign_id, user_id, joined_at) VALUES (?,?,?,?)",
      [uuidv4(), campaign.id, currentUser.id, now()])
    return { success: true, campaign }
  })

  wrap("campaigns:join", async function(inviteCode) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    var results = rows("SELECT * FROM campaigns WHERE invite_code = ?", [inviteCode])
    var campaign = results[0]
    if (!campaign) return { success: false, error: "Invalid invite code" }
    var existing = rows("SELECT id FROM memberships WHERE campaign_id = ? AND user_id = ?", [campaign.id, currentUser.id])
    if (existing.length) return { success: false, error: "Already in this campaign" }
    run("INSERT INTO memberships (id, campaign_id, user_id, joined_at) VALUES (?,?,?,?)",
      [uuidv4(), campaign.id, currentUser.id, now()])
    return { success: true, campaign }
  })

  wrap("characters:get", async function(campaignId) {
    if (!currentUser) return null
    var results = rows("SELECT * FROM memberships WHERE campaign_id = ? AND user_id = ?", [campaignId, currentUser.id])
    return results[0] || null
  })

  wrap("characters:update", async function(payload) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    var cid = payload.campaignId
    var d = payload.data
    var keys = Object.keys(d)
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i]
      var v = d[k]
      run("UPDATE memberships SET " + k + " = ? WHERE campaign_id = ? AND user_id = ?", [v, cid, currentUser.id])
    }
    return { success: true }
  })

  wrap("notes:list", async function(campaignId) {
    if (!currentUser) return []
    if (currentUser.role === "dm")
      return rows("SELECT * FROM notes WHERE campaign_id = ? ORDER BY created_at DESC", [campaignId])
    return rows("SELECT * FROM notes WHERE campaign_id = ? AND (author_user_id = ? OR visibility = 'all_players') ORDER BY created_at DESC", [campaignId, currentUser.id])
  })

  wrap("notes:create", async function(payload) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    var note = {
      id: uuidv4(), campaign_id: payload.campaignId, author_user_id: currentUser.id,
      author_name: currentUser.display_name, title: payload.data.title, body: payload.data.body || "",
      visibility: payload.data.visibility || "private", created_at: now(), updated_at: now()
    }
    run("INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?)",
      [note.id, note.campaign_id, note.author_user_id, note.author_name, note.title, note.body, note.visibility, note.created_at, note.updated_at])
    return { success: true, note }
  })

  wrap("notes:update", async function(payload) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    run("UPDATE notes SET title = ?, body = ?, visibility = ?, updated_at = ? WHERE id = ? AND author_user_id = ?",
      [payload.data.title, payload.data.body, payload.data.visibility, now(), payload.id, currentUser.id])
    return { success: true }
  })

  wrap("notes:delete", async function(id) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    run("DELETE FROM notes WHERE id = ? AND author_user_id = ?", [id, currentUser.id])
    return { success: true }
  })

  wrap("wiki:list", async function(payload) {
    if (payload.category)
      return rows("SELECT * FROM wiki_pages WHERE campaign_id = ? AND world_category = ? ORDER BY title ASC", [payload.campaignId, payload.category])
    return rows("SELECT * FROM wiki_pages WHERE campaign_id = ? ORDER BY title ASC", [payload.campaignId])
  })

  wrap("wiki:get", async function(id) {
    var results = rows("SELECT * FROM wiki_pages WHERE id = ?", [id])
    return results[0] || null
  })

  wrap("wiki:create", async function(payload) {
    if (!currentUser) return { success: false, error: "Not logged in" }
    var page = {
      id: uuidv4(), campaign_id: payload.campaignId, title: payload.data.title, content: payload.data.content || "",
      world_category: payload.data.world_category || "lore", subtitle: payload.data.subtitle || "",
      summary: payload.data.summary || "", image_url: payload.data.image_url || "",
      tags: payload.data.tags || "", status: "published", visibility: payload.data.visibility || "all_players",
      source: "manual", created_at: now(), updated_at: now()
    }
    run("INSERT INTO wiki_pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
      [page.id, page.campaign_id, page.title, page.content, page.world_category, page.subtitle, page.summary, page.image_url, page.tags, page.status, page.visibility, page.source, page.created_at, page.updated_at])
    return { success: true, page }
  })

  wrap("wiki:update", async function(payload) {
    run("UPDATE wiki_pages SET title = ?, content = ?, world_category = ?, subtitle = ?, summary = ?, image_url = ?, tags = ?, visibility = ?, updated_at = ? WHERE id = ?",
      [payload.data.title, payload.data.content, payload.data.world_category, payload.data.subtitle, payload.data.summary, payload.data.image_url, payload.data.tags, payload.data.visibility, now(), payload.id])
    return { success: true }
  })

  wrap("wiki:delete", async function(id) {
    run("DELETE FROM wiki_pages WHERE id = ?", [id])
    return { success: true }
  })

  wrap("members:list", async function(campaignId) {
    return rows("SELECT m.*, u.email, u.display_name, u.role FROM memberships m JOIN users u ON u.id = m.user_id WHERE m.campaign_id = ?", [campaignId])
  })
}

module.exports = { registerHandlers }
