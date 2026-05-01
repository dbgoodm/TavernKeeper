const path = require('path')
const { app } = require('electron')
const createDatabase = require('@databases/sqlite')

let db

function getDb() {
  return db
}

async function setupDatabase() {
  const userDataPath = app.getPath('userData')
  const dbPath = path.join(userDataPath, 'tavernkeeper.db')

  db = createDatabase(dbPath)

  await db.query("PRAGMA journal_mode = WAL")
  await db.query("PRAGMA foreign_keys = ON")

  await db.query(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
      display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'player', profile_image_url TEXT DEFAULT '',
      pronouns TEXT DEFAULT '', default_note_visibility TEXT DEFAULT 'private',
      ui_density TEXT DEFAULT 'comfortable', timezone TEXT DEFAULT 'America/New_York',
      created_at TEXT NOT NULL
    )
  `)

  await db.query(`
    CREATE TABLE IF NOT EXISTS campaigns (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, premise TEXT DEFAULT '',
      invite_code TEXT UNIQUE NOT NULL, dm_user_id TEXT NOT NULL,
      world_atlas_title TEXT DEFAULT 'World Atlas', world_atlas_intro TEXT DEFAULT '',
      emporium_hide_uncommon_plus INTEGER DEFAULT 1, created_at TEXT NOT NULL
    )
  `)

  await db.query(`
    CREATE TABLE IF NOT EXISTS memberships (
      id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, user_id TEXT NOT NULL,
      character_name TEXT DEFAULT '', class_name TEXT DEFAULT '',
      subclass TEXT DEFAULT '', level TEXT DEFAULT '1', species TEXT DEFAULT '',
      background TEXT DEFAULT '', alignment TEXT DEFAULT '',
      armor_class TEXT DEFAULT '10', speed TEXT DEFAULT '30',
      max_hit_points TEXT DEFAULT '0', current_hit_points TEXT DEFAULT '0',
      temp_hit_points TEXT DEFAULT '0', proficiency_bonus TEXT DEFAULT '2',
      initiative_bonus TEXT DEFAULT '0', strength TEXT DEFAULT '10',
      dexterity TEXT DEFAULT '10', constitution TEXT DEFAULT '10',
      intelligence TEXT DEFAULT '10', wisdom TEXT DEFAULT '10', charisma TEXT DEFAULT '10',
      inventory_items TEXT DEFAULT '[]', attacks TEXT DEFAULT '',
      spellcasting_ability TEXT DEFAULT '', known_spells TEXT DEFAULT '',
      prepared_spell_names TEXT DEFAULT '', currency_purse TEXT DEFAULT '',
      features_traits TEXT DEFAULT '', character_notes TEXT DEFAULT '',
      portrait_url TEXT DEFAULT '', joined_at TEXT NOT NULL,
      UNIQUE(campaign_id, user_id)
    )
  `)

  await db.query(`
    CREATE TABLE IF NOT EXISTS notes (
      id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL,
      author_user_id TEXT NOT NULL, author_name TEXT NOT NULL,
      title TEXT NOT NULL, body TEXT DEFAULT '', visibility TEXT DEFAULT 'private',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )
  `)

  await db.query(`
    CREATE TABLE IF NOT EXISTS wiki_pages (
      id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, title TEXT NOT NULL,
      content TEXT DEFAULT '', world_category TEXT DEFAULT 'lore',
      subtitle TEXT DEFAULT '', summary TEXT DEFAULT '', image_url TEXT DEFAULT '',
      tags TEXT DEFAULT '', status TEXT DEFAULT 'published',
      visibility TEXT DEFAULT 'all_players', source TEXT DEFAULT 'manual',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )
  `)

  await db.query(`
    CREATE TABLE IF NOT EXISTS announcements (
      id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL,
      author_user_id TEXT NOT NULL, title TEXT NOT NULL,
      body TEXT DEFAULT '', kind TEXT DEFAULT 'general', created_at TEXT NOT NULL
    )
  `)

  console.log('Database ready at:', dbPath)
  return db
}

module.exports = { setupDatabase, getDb }
