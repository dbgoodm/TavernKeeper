const { v4: uuidv4 } = require('uuid')
const { createHash } = require('crypto')
const { getDb } = require('./database')

function hashPassword(password) {
  return createHash('sha256').update(password + 'tavernkeeper-salt').digest('hex')
}

function now() {
  return new Date().toISOString()
}

function generateInviteCode() {
  return Math.random().toString(36).substring(2, 8).toUpperCase()
}

function sanitizeUser(user) {
  const { password_hash, ...safe } = user
  return safe
}

let currentUser = null

function registerHandlers(ipcMain) {
  const wrap = (channel, fn) => {
    ipcMain.handle(channel, async (_, ...args) => {
      try {
        return await fn(...args)
      } catch (err) {
        console.error(`[${channel}]`, err)
        return { success: false, error: err.message }
      }
    })
  }

  const db = () => getDb()
  const sql = (...args) => getDb().sql(...args)

  // ── AUTH ──────────────────────────────────────────────────────────
  wrap('auth:login', async ({ email, password }) => {
    const [user] = await db().query(sql`SELECT * FROM users WHERE email = ${email}`)
    if (!user || user.password_hash !== hashPassword(password)) {
      return { success: false, error: 'Invalid email or password' }
    }
    currentUser = user
    return { success: true, user: sanitizeUser(user) }
  })

  wrap('auth:register', async ({ email, password, displayName, role }) => {
    const [existing] = await db().query(sql`SELECT id FROM users WHERE email = ${email}`)
    if (existing) return { success: false, error: 'Email already in use' }
    const user = {
      id: uuidv4(),
      email,
      display_name: displayName,
      password_hash: hashPassword(password),
      role: role || 'player',
      profile_image_url: '',
      pronouns: '',
      default_note_visibility: 'private',
      ui_density: 'comfortable',
      timezone: 'America/New_York',
      created_at: now(),
    }
    await db().query(sql`
      INSERT INTO users VALUES (
        ${user.id}, ${user.email}, ${user.display_name}, ${user.password_hash},
        ${user.role}, ${user.profile_image_url}, ${user.pronouns},
        ${user.default_note_visibility}, ${user.ui_density}, ${user.timezone}, ${user.created_at}
      )
    `)
    currentUser = user
    return { success: true, user: sanitizeUser(user) }
  })

  wrap('auth:logout', async () => {
    currentUser = null
    return { success: true }
  })

  // ── CAMPAIGNS ─────────────────────────────────────────────────────
  wrap('campaigns:list', async () => {
    if (!currentUser) return []
    if (currentUser.role === 'dm') {
      return db().query(sql`SELECT * FROM campaigns WHERE dm_user_id = ${currentUser.id} ORDER BY created_at DESC`)
    }
    return db().query(sql`
      SELECT c.* FROM campaigns c
      JOIN memberships m ON m.campaign_id = c.id
      WHERE m.user_id = ${currentUser.id}
      ORDER BY c.created_at DESC
    `)
  })

  wrap('campaigns:get', async (id) => {
    const [c] = await db().query(sql`SELECT * FROM campaigns WHERE id = ${id}`)
    return c || null
  })

  wrap('campaigns:create', async (data) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    const campaign = {
      id: uuidv4(),
      name: data.name,
      premise: data.premise || '',
      invite_code: generateInviteCode(),
      dm_user_id: currentUser.id,
      world_atlas_title: 'World Atlas',
      world_atlas_intro: '',
      emporium_hide_uncommon_plus: 1,
      created_at: now(),
    }
    await db().query(sql`
      INSERT INTO campaigns VALUES (
        ${campaign.id}, ${campaign.name}, ${campaign.premise}, ${campaign.invite_code},
        ${campaign.dm_user_id}, ${campaign.world_atlas_title}, ${campaign.world_atlas_intro},
        ${campaign.emporium_hide_uncommon_plus}, ${campaign.created_at}
      )
    `)
    // DM auto-joins
    await db().query(sql`
      INSERT INTO memberships (id, campaign_id, user_id, joined_at)
      VALUES (${uuidv4()}, ${campaign.id}, ${currentUser.id}, ${now()})
    `)
    return { success: true, campaign }
  })

  wrap('campaigns:update', async ({ id, data }) => {
    const entries = Object.entries(data)
    for (const [key, value] of entries) {
      // Safe field update (key is internal, not user input)
      await db().query(sql`UPDATE campaigns SET ${db().sql([`${key} = ?`], [value])} WHERE id = ${id}`)
    }
    return { success: true }
  })

  wrap('campaigns:join', async (inviteCode) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    const [campaign] = await db().query(sql`SELECT * FROM campaigns WHERE invite_code = ${inviteCode}`)
    if (!campaign) return { success: false, error: 'Invalid invite code' }
    const [existing] = await db().query(sql`
      SELECT id FROM memberships WHERE campaign_id = ${campaign.id} AND user_id = ${currentUser.id}
    `)
    if (existing) return { success: false, error: 'Already in this campaign' }
    await db().query(sql`
      INSERT INTO memberships (id, campaign_id, user_id, joined_at)
      VALUES (${uuidv4()}, ${campaign.id}, ${currentUser.id}, ${now()})
    `)
    return { success: true, campaign }
  })

  // ── CHARACTERS ────────────────────────────────────────────────────
  wrap('characters:get', async (campaignId) => {
    if (!currentUser) return null
    const [m] = await db().query(sql`
      SELECT * FROM memberships WHERE campaign_id = ${campaignId} AND user_id = ${currentUser.id}
    `)
    return m || null
  })

  wrap('characters:update', async ({ campaignId, data }) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    const allowed = [
      'character_name','class_name','subclass','level','species','background','alignment',
      'armor_class','speed','max_hit_points','current_hit_points','temp_hit_points',
      'proficiency_bonus','initiative_bonus','strength','dexterity','constitution',
      'intelligence','wisdom','charisma','inventory_items','attacks','spellcasting_ability',
      'known_spells','prepared_spell_names','currency_purse','features_traits','character_notes','portrait_url'
    ]
    for (const [key, value] of Object.entries(data)) {
      if (!allowed.includes(key)) continue
      await db().query(db().sql([`UPDATE memberships SET ${key} = ? WHERE campaign_id = ? AND user_id = ?`], [value, campaignId, currentUser.id]))
    }
    return { success: true }
  })

  // ── NOTES ─────────────────────────────────────────────────────────
  wrap('notes:list', async (campaignId) => {
    if (!currentUser) return []
    if (currentUser.role === 'dm') {
      return db().query(sql`SELECT * FROM notes WHERE campaign_id = ${campaignId} ORDER BY created_at DESC`)
    }
    return db().query(sql`
      SELECT * FROM notes
      WHERE campaign_id = ${campaignId}
        AND (author_user_id = ${currentUser.id} OR visibility = 'all_players')
      ORDER BY created_at DESC
    `)
  })

  wrap('notes:create', async ({ campaignId, data }) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    const note = {
      id: uuidv4(),
      campaign_id: campaignId,
      author_user_id: currentUser.id,
      author_name: currentUser.display_name,
      title: data.title,
      body: data.body || '',
      visibility: data.visibility || 'private',
      created_at: now(),
      updated_at: now(),
    }
    await db().query(sql`
      INSERT INTO notes VALUES (
        ${note.id}, ${note.campaign_id}, ${note.author_user_id}, ${note.author_name},
        ${note.title}, ${note.body}, ${note.visibility}, ${note.created_at}, ${note.updated_at}
      )
    `)
    return { success: true, note }
  })

  wrap('notes:update', async ({ id, data }) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    await db().query(sql`
      UPDATE notes SET title = ${data.title}, body = ${data.body}, visibility = ${data.visibility}, updated_at = ${now()}
      WHERE id = ${id} AND author_user_id = ${currentUser.id}
    `)
    return { success: true }
  })

  wrap('notes:delete', async (id) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    await db().query(sql`DELETE FROM notes WHERE id = ${id} AND author_user_id = ${currentUser.id}`)
    return { success: true }
  })

  // ── WIKI ──────────────────────────────────────────────────────────
  wrap('wiki:list', async ({ campaignId, category }) => {
    if (category) {
      return db().query(sql`SELECT * FROM wiki_pages WHERE campaign_id = ${campaignId} AND world_category = ${category} ORDER BY title ASC`)
    }
    return db().query(sql`SELECT * FROM wiki_pages WHERE campaign_id = ${campaignId} ORDER BY title ASC`)
  })

  wrap('wiki:get', async (id) => {
    const [p] = await db().query(sql`SELECT * FROM wiki_pages WHERE id = ${id}`)
    return p || null
  })

  wrap('wiki:create', async ({ campaignId, data }) => {
    if (!currentUser) return { success: false, error: 'Not logged in' }
    const page = {
      id: uuidv4(),
      campaign_id: campaignId,
      title: data.title,
      content: data.content || '',
      world_category: data.world_category || 'lore',
      subtitle: data.subtitle || '',
      summary: data.summary || '',
      image_url: data.image_url || '',
      tags: data.tags || '',
      status: 'published',
      visibility: data.visibility || 'all_players',
      source: 'manual',
      created_at: now(),
      updated_at: now(),
    }
    await db().query(sql`
      INSERT INTO wiki_pages VALUES (
        ${page.id}, ${page.campaign_id}, ${page.title}, ${page.content},
        ${page.world_category}, ${page.subtitle}, ${page.summary}, ${page.image_url},
        ${page.tags}, ${page.status}, ${page.visibility}, ${page.source},
        ${page.created_at}, ${page.updated_at}
      )
    `)
    return { success: true, page }
  })

  wrap('wiki:update', async ({ id, data }) => {
    await db().query(sql`
      UPDATE wiki_pages SET
        title = ${data.title}, content = ${data.content}, world_category = ${data.world_category},
        subtitle = ${data.subtitle}, summary = ${data.summary}, image_url = ${data.image_url},
        tags = ${data.tags}, visibility = ${data.visibility}, updated_at = ${now()}
      WHERE id = ${id}
    `)
    return { success: true }
  })

  wrap('wiki:delete', async (id) => {
    await db().query(sql`DELETE FROM wiki_pages WHERE id = ${id}`)
    return { success: true }
  })

  // ── MEMBERS ───────────────────────────────────────────────────────
  wrap('members:list', async (campaignId) => {
    return db().query(sql`
      SELECT m.*, u.email, u.display_name, u.role
      FROM memberships m
      JOIN users u ON u.id = m.user_id
      WHERE m.campaign_id = ${campaignId}
    `)
  })
}

module.exports = { registerHandlers }
