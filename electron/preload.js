const { contextBridge, ipcRenderer } = require('electron')

// Expose a safe API to the renderer (React app)
// Every database/system call goes through here
contextBridge.exposeInMainWorld('tk', {
  // Auth
  login: (email, password) => ipcRenderer.invoke('auth:login', { email, password }),
  register: (data) => ipcRenderer.invoke('auth:register', data),
  logout: () => ipcRenderer.invoke('auth:logout'),

  // Campaigns
  getCampaigns: () => ipcRenderer.invoke('campaigns:list'),
  createCampaign: (data) => ipcRenderer.invoke('campaigns:create', data),
  getCampaign: (id) => ipcRenderer.invoke('campaigns:get', id),
  updateCampaign: (id, data) => ipcRenderer.invoke('campaigns:update', { id, data }),
  joinCampaign: (inviteCode) => ipcRenderer.invoke('campaigns:join', inviteCode),

  // Characters
  getCharacter: (campaignId) => ipcRenderer.invoke('characters:get', campaignId),
  updateCharacter: (campaignId, data) => ipcRenderer.invoke('characters:update', { campaignId, data }),

  // Notes
  getNotes: (campaignId) => ipcRenderer.invoke('notes:list', campaignId),
  createNote: (campaignId, data) => ipcRenderer.invoke('notes:create', { campaignId, data }),
  updateNote: (id, data) => ipcRenderer.invoke('notes:update', { id, data }),
  deleteNote: (id) => ipcRenderer.invoke('notes:delete', id),

  // Wiki / World Atlas
  getWikiPages: (campaignId, category) => ipcRenderer.invoke('wiki:list', { campaignId, category }),
  getWikiPage: (id) => ipcRenderer.invoke('wiki:get', id),
  createWikiPage: (campaignId, data) => ipcRenderer.invoke('wiki:create', { campaignId, data }),
  updateWikiPage: (id, data) => ipcRenderer.invoke('wiki:update', { id, data }),
  deleteWikiPage: (id) => ipcRenderer.invoke('wiki:delete', id),

  // Members (DM view)
  getMembers: (campaignId) => ipcRenderer.invoke('members:list', campaignId),
})
