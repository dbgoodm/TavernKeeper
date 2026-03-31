const playerData = [
  {
    name: "Iri Thorn",
    pronouns: "she/they",
    style: "Heavy roleplay",
    comfort: "Prefers low-gore horror",
    hook: "Estranged mentor tied to the observatory",
  },
  {
    name: "Bram Cask",
    pronouns: "he/him",
    style: "Tactical with social scenes",
    comfort: "No betrayal within party",
    hook: "Debt owed to the river syndicate",
  },
  {
    name: "Sel Vale",
    pronouns: "they/them",
    style: "Lore and mystery",
    comfort: "Wants lines/veils check-ins",
    hook: "Searching for a lost saint map",
  },
];

const insights = [
  "Three players asked for investigation-heavy sessions with room for character drama.",
  "Safety preferences overlap around avoiding party betrayal and surprise body horror.",
  "Two players created hooks connected to the same ruined observatory, which is a strong early-campaign anchor.",
  "The group likes letters and prop drops between sessions, especially when they reveal rumors or secret agendas.",
];

const surveyQuestions = [
  "What mix of combat, roleplay, exploration, and mystery feels best for you?",
  "Are there any lines, veils, or content boundaries you want the DM to know?",
  "What kind of spotlight moments do you enjoy for your character?",
  "What schedule, recap format, and reminder style help you stay engaged between sessions?",
  "Share one rumor, fear, relationship, or unresolved problem tied to your character.",
];

const announcements = [
  {
    title: "Letter from the Glass Archivist",
    type: "Typed Letter",
    audience: "All players",
    body:
      "A sealed note warns the party that the bells beneath Blackglass Harbor rang before dawn, even though the cathedral sank ninety years ago.",
  },
  {
    title: "Session 04 Schedule Shift",
    type: "Announcement",
    audience: "All players",
    body:
      "This week starts thirty minutes later. Please bring one rumor your character has heard about the drowned chapel.",
  },
  {
    title: "Smuggler's Token",
    type: "Image Prop",
    audience: "Rogue + DM",
    body:
      "A worn brass token appears in your inventory with the tide-mark sigil scratched into the center.",
  },
];

const notes = [
  {
    title: "Session 03: The Harbor Bells",
    author: "Sel Vale",
    visibility: "Shared with campaign",
    body:
      "We confirmed the bells can be heard only by those marked with ash. Bram pocketed a brass token and Iri recognized the hymn from her mentor's field notes.",
  },
  {
    title: "Loose Threads After Session 02",
    author: "Bram Cask",
    visibility: "Shared with campaign",
    body:
      "Questions still open: who is paying the ferryman, why does the saint statue face inland, and what did the innkeeper mean by 'the fourth tide'?",
  },
];

const wikiEntries = [
  {
    title: "Blackglass Harbor",
    category: "Place",
    body: "A storm-bitten port city built around mirrored volcanic stone and old saint roads.",
  },
  {
    title: "Order of the Lantern Wake",
    category: "Faction",
    body: "Caretakers of burial rites, fog shrines, and records concerning drowned miracles.",
  },
  {
    title: "The Drowned Chapel",
    category: "Mystery",
    body: "A submerged cathedral ruin said to ring its bells only for the guilty or the chosen.",
  },
  {
    title: "Ferryman's Debt",
    category: "Lore",
    body: "Local superstition claiming every safe crossing owes a memory to the river in return.",
  },
];

const playerDrafts = [
  {
    title: "House Thorn Genealogy",
    author: "Iri Thorn",
    summary: "A family record tying three generations of scholars to vanished lighthouse surveys.",
  },
  {
    title: "Brass Diving Harness",
    author: "Bram Cask",
    summary: "A player-created invention page with diagrams, limitations, and salvage notes.",
  },
];

const playerFocusItems = [
  {
    title: "Lost Saint Map",
    body: "You believe the hymn from the harbor bells matches marginalia in your saint archive.",
  },
  {
    title: "Mentor's Warning",
    body: "A private clue suggests your old mentor entered the drowned chapel willingly.",
  },
];

const playerChecklist = [
  "Review the archivist's letter before Thursday's session.",
  "Add one rumor or omen your character heard after the bells rang.",
  "Check the shared notes for names tied to the ferryman and the saint roads.",
  "Decide whether to share your family genealogy page with the DM for canon review.",
];

const playerWikiEntries = [
  {
    title: "Sel Vale",
    category: "Character",
    body: "A scholar of drowned saints collecting half-banned maps, hymns, and burial customs.",
  },
  {
    title: "Archive Fragments",
    category: "Research",
    body: "Loose notes connecting bell hymns, ash marks, and missing harbor processions.",
  },
];

const playerCards = document.querySelector("#playerCards");
const insightList = document.querySelector("#insightList");
const surveyList = document.querySelector("#surveyQuestions");
const announcementFeed = document.querySelector("#announcementFeed");
const notesFeed = document.querySelector("#notesFeed");
const wikiGrid = document.querySelector("#wikiGrid");
const draftList = document.querySelector("#draftList");
const noteForm = document.querySelector("#noteForm");
const playerAnnouncementFeed = document.querySelector("#playerAnnouncementFeed");
const playerInboxFeed = document.querySelector("#playerInboxFeed");
const playerNotesFeed = document.querySelector("#playerNotesFeed");
const playerWikiGrid = document.querySelector("#playerWikiGrid");
const playerSubmissionList = document.querySelector("#playerSubmissionList");
const playerFocusList = document.querySelector("#playerFocusList");
const playerChecklistList = document.querySelector("#playerChecklist");
const playerNoteForm = document.querySelector("#playerNoteForm");
const navButtons = document.querySelectorAll(".nav-link");
const viewPanels = document.querySelectorAll(".view-panel");
const authScreen = document.querySelector("#authScreen");
const dmScreen = document.querySelector("#dmScreen");
const playerScreen = document.querySelector("#playerScreen");
const authForm = document.querySelector("#authForm");
const authLabel = document.querySelector(".auth-card .label");
const authHeading = document.querySelector(".auth-card h2");
const entryTabs = document.querySelectorAll(".entry-tab");
const entryPanels = document.querySelectorAll(".entry-panel");
const roleCards = document.querySelectorAll(".role-card");
const registerEmailInput = document.querySelector("#registerEmail");
const displayNameInput = document.querySelector("#displayName");
const registerPasswordInput = document.querySelector("#registerPassword");
const loginEmailInput = document.querySelector("#loginEmail");
const loginPasswordInput = document.querySelector("#loginPassword");
const loginDisplayNameInput = document.querySelector("#loginDisplayName");
const shareInviteBtn = document.querySelector("#shareInviteBtn");
const enterPortalBtn = document.querySelector("#enterPortalBtn");
const backToLoginFromDm = document.querySelector("#backToLoginFromDm");
const backToLoginFromPlayer = document.querySelector("#backToLoginFromPlayer");
const joinCampaignBtn = document.querySelector("#joinCampaignBtn");
const dmHeroEyebrow = document.querySelector("#dmHeroEyebrow");
const playerHeroEyebrow = document.querySelector("#playerHeroEyebrow");
const toast = document.querySelector("#toast");

let selectedRole = "dm";
let currentUserName = "Mara Voss";
let currentEntryMode = "register";

function renderPlayers() {
  playerCards.innerHTML = playerData
    .map(
      (player) => `
        <article class="player-card">
          <header>
            <div>
              <h4>${player.name}</h4>
              <p>${player.pronouns}</p>
            </div>
            <span class="announcement-type">${player.style}</span>
          </header>
          <p><strong>Comfort:</strong> ${player.comfort}</p>
          <p><strong>Hook:</strong> ${player.hook}</p>
        </article>
      `
    )
    .join("");
}

function renderInsights() {
  insightList.innerHTML = insights.map((item) => `<li>${item}</li>`).join("");
}

function renderSurvey() {
  surveyList.innerHTML = surveyQuestions
    .map(
      (question, index) => `
        <article class="survey-question">
          <span class="label">Question ${index + 1}</span>
          <strong>${question}</strong>
        </article>
      `
    )
    .join("");
}

function renderAnnouncements() {
  const markup = announcements
    .map(
      (item) => `
        <article class="announcement-card">
          <header>
            <div>
              <h4>${item.title}</h4>
              <p>${item.audience}</p>
            </div>
            <span class="announcement-type">${item.type}</span>
          </header>
          <p>${item.body}</p>
        </article>
      `
    )
    .join("");

  announcementFeed.innerHTML = markup;
  playerAnnouncementFeed.innerHTML = markup;
  playerInboxFeed.innerHTML = markup;
}

function renderNotes() {
  const markup = notes
    .map(
      (note) => `
        <article class="note-card">
          <header>
            <div>
              <h4>${note.title}</h4>
              <p>By ${note.author}</p>
            </div>
            <span class="announcement-type">${note.visibility}</span>
          </header>
          <p>${note.body}</p>
        </article>
      `
    )
    .join("");

  notesFeed.innerHTML = markup;
  playerNotesFeed.innerHTML = markup;
}

function renderWiki() {
  wikiGrid.innerHTML = wikiEntries
    .map(
      (entry) => `
        <article class="wiki-card">
          <p class="label">${entry.category}</p>
          <h4>${entry.title}</h4>
          <p>${entry.body}</p>
        </article>
      `
    )
    .join("");
}

function renderDrafts() {
  const markup = playerDrafts
    .map(
      (draft, index) => `
        <article class="draft-card">
          <header>
            <div>
              <h4>${draft.title}</h4>
              <p>By ${draft.author}</p>
            </div>
            <span class="announcement-type">Player Draft</span>
          </header>
          <p>${draft.summary}</p>
          <div class="draft-actions">
            <button class="mini-btn approve" data-import-index="${index}">Import to Canon</button>
            <button class="mini-btn">Leave as Draft</button>
          </div>
        </article>
      `
    )
    .join("");

  draftList.innerHTML = markup;
  playerSubmissionList.innerHTML = markup;
}

function renderPlayerFocus() {
  playerFocusList.innerHTML = playerFocusItems
    .map(
      (item) => `
        <article class="player-focus-card">
          <p class="label">Character thread</p>
          <h4>${item.title}</h4>
          <p>${item.body}</p>
        </article>
      `
    )
    .join("");
}

function renderPlayerChecklist() {
  playerChecklistList.innerHTML = playerChecklist.map((item) => `<li>${item}</li>`).join("");
}

function renderPlayerWiki() {
  playerWikiGrid.innerHTML = playerWikiEntries
    .map(
      (entry) => `
        <article class="wiki-card">
          <p class="label">${entry.category}</p>
          <h4>${entry.title}</h4>
          <p>${entry.body}</p>
        </article>
      `
    )
    .join("");
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    toast.classList.remove("show");
  }, 2200);
}

function showScreen(screenName) {
  authScreen.classList.toggle("active-screen", screenName === "auth");
  dmScreen.classList.toggle("active-screen", screenName === "dm");
  playerScreen.classList.toggle("active-screen", screenName === "player");
}

function setEntryMode(mode) {
  currentEntryMode = mode;

  entryTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.entry === mode);
  });

  entryPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.entryPanel === mode);
  });

  if (mode === "register") {
    authLabel.textContent = "Account Access";
    authHeading.textContent = "Create your account";
    enterPortalBtn.textContent = selectedRole === "dm" ? "Create DM Account" : "Create Player Account";
  } else {
    authLabel.textContent = "Welcome Back";
    authHeading.textContent = "Log into your account";
    enterPortalBtn.textContent = "Log In";
  }

  roleCards.forEach((item) => {
    item.classList.toggle("selected", mode === "register" && item.dataset.role === selectedRole);
  });
}

function switchView(screenName, viewName) {
  navButtons.forEach((button) => {
    const isMatch = button.dataset.screen === screenName && button.dataset.view === viewName;
    button.classList.toggle("active", isMatch);
  });

  viewPanels.forEach((panel) => {
    const isMatch = panel.dataset.screenPanel === screenName && panel.dataset.panel === viewName;
    panel.classList.toggle("active", isMatch);
  });
}

navButtons.forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.screen, button.dataset.view));
});

entryTabs.forEach((tab) => {
  tab.addEventListener("click", () => setEntryMode(tab.dataset.entry));
});

roleCards.forEach((card) => {
  card.addEventListener("click", () => {
    selectedRole = card.dataset.role;
    roleCards.forEach((item) => item.classList.toggle("selected", item === card));
    if (currentEntryMode === "register") {
      enterPortalBtn.textContent = selectedRole === "dm" ? "Create DM Account" : "Create Player Account";
    }
  });
});

shareInviteBtn.addEventListener("click", async () => {
  const code = document.querySelector("#inviteCode").textContent;

  try {
    await navigator.clipboard.writeText(code);
    showToast(`Invite code copied: ${code}`);
  } catch (error) {
    showToast(`Invite code: ${code}`);
  }
});

authForm.addEventListener("submit", (event) => {
  event.preventDefault();

  let role = selectedRole;
  let message = "";

  if (currentEntryMode === "register") {
    currentUserName = displayNameInput.value.trim() || (selectedRole === "dm" ? "Mara Voss" : "Sel Vale");
    registerEmailInput.value.trim();
    registerPasswordInput.value.trim();
    message = `Created a new ${selectedRole === "dm" ? "DM" : "player"} account for ${currentUserName}.`;
  } else {
    currentUserName = loginDisplayNameInput.value.trim() || "Sel Vale";
    loginEmailInput.value.trim();
    loginPasswordInput.value.trim();
    role = currentUserName.toLowerCase().includes("mara") || currentUserName.toLowerCase().includes("dm") ? "dm" : "player";
    selectedRole = role;
    message = `Logged in as ${currentUserName}.`;
  }

  dmHeroEyebrow.textContent = `${currentUserName} · Dungeon Master Dashboard`;
  playerHeroEyebrow.textContent = `${currentUserName} · Player Dashboard`;

  if (role === "player") {
    document.querySelector(".player-sidebar .campaign-meta").children[0].textContent = `Current Character: ${currentUserName}`;
    playerWikiEntries[0].title = currentUserName;
    renderPlayerWiki();
  }

  if (role === "dm") {
    showScreen("dm");
    switchView("dm", "overview");
  } else {
    showScreen("player");
    switchView("player", "home");
  }

  showToast(message);
});

backToLoginFromDm.addEventListener("click", () => {
  showScreen("auth");
  setEntryMode("register");
  showToast("Returned to role selection.");
});

backToLoginFromPlayer.addEventListener("click", () => {
  showScreen("auth");
  setEntryMode("register");
  showToast("Returned to role selection.");
});

joinCampaignBtn.addEventListener("click", () => {
  showToast("Campaign joining will live after account login in a later flow.");
});

noteForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(noteForm);
  notes.unshift({
    title: formData.get("title"),
    author: currentUserName || "Guest Player",
    visibility: "Shared with campaign",
    body: formData.get("summary"),
  });

  renderNotes();
  noteForm.reset();
  showToast("New sample note added to the campaign feed.");
});

playerNoteForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(playerNoteForm);
  notes.unshift({
    title: formData.get("title"),
    author: currentUserName || "You",
    visibility: "Shared with campaign",
    body: formData.get("summary"),
  });

  renderNotes();
  playerNoteForm.reset();
  showToast("Your note was added to the shared session log.");
});

function handleDraftImport(event) {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }

  const importIndex = target.dataset.importIndex;
  if (importIndex === undefined) {
    showToast("Draft left unchanged.");
    return;
  }

  const draft = playerDrafts[Number(importIndex)];
  wikiEntries.unshift({
    title: draft.title,
    category: "Imported from Player",
    body: draft.summary,
  });
  playerDrafts.splice(Number(importIndex), 1);
  renderDrafts();
  renderWiki();
  showToast(`Imported "${draft.title}" into the campaign wiki.`);
}

draftList.addEventListener("click", handleDraftImport);
playerSubmissionList.addEventListener("click", handleDraftImport);

renderPlayers();
renderInsights();
renderSurvey();
renderAnnouncements();
renderNotes();
renderWiki();
renderDrafts();
renderPlayerFocus();
renderPlayerChecklist();
renderPlayerWiki();
setEntryMode("register");
