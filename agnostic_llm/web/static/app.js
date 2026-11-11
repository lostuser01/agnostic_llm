// Agnostic AI - macOS Web Client & Voice Controller
let currentEmployee = "supervisor";
let employeesData = [];
let isRecording = false;
let recognition = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initEmployees();
  initVoiceRecognition();
  initChat();
  initAgendaWorkspace();
  initCRMWorkspace();
  initMarketingWorkspace();
  initEmpathyWorkspace();
});

// --- Tab Switching ---
function initTabs() {
  const tabBtns = document.querySelectorAll(".nav-tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");

      // Auto-load tab data
      if (targetId === "tab-agenda") loadAgendaData();
      if (targetId === "tab-crm") loadCRMData();
      if (targetId === "tab-marketing") loadMarketingData();
      if (targetId === "tab-manuscript") loadManuscriptData();
    });
  });
}

// --- Load Employees & Sidebar ---
async function initEmployees() {
  try {
    const res = await fetch("/api/employees");
    const data = await res.json();
    employeesData = data.employees || [];

    const listEl = document.getElementById("employee-list");
    listEl.innerHTML = "";

    employeesData.forEach(emp => {
      const card = document.createElement("div");
      card.className = `employee-card ${emp.name.toLowerCase() === currentEmployee.toLowerCase() ? "active" : ""}`;
      card.setAttribute("data-name", emp.name.toLowerCase());
      card.innerHTML = `
        <div class="emp-avatar">${emp.avatar}</div>
        <div class="emp-info">
          <div class="emp-name-row">
            <span class="emp-name">${emp.name}</span>
            <span class="emp-voice-tag">${emp.voice}</span>
          </div>
          <div class="emp-role-desc">${emp.title}</div>
        </div>
      `;

      card.addEventListener("click", () => {
        selectEmployee(emp);
      });
      listEl.appendChild(card);
    });
  } catch (e) {
    console.error("Failed to load employees:", e);
  }

  // Standup button
  document.getElementById("standup-btn").addEventListener("click", () => {
    switchTab("tab-chat");
    sendChatMessage("Run morning team standup and summarize operational status across all departments");
  });
}

function selectEmployee(emp) {
  currentEmployee = emp.name.toLowerCase();
  document.querySelectorAll(".employee-card").forEach(c => c.classList.remove("active"));
  const activeCard = document.querySelector(`.employee-card[data-name="${currentEmployee}"]`);
  if (activeCard) activeCard.classList.add("active");

  document.getElementById("current-emp-name").textContent = emp.name;
  document.getElementById("current-emp-title").textContent = emp.title;
  document.getElementById("current-emp-avatar").textContent = emp.avatar;
  document.getElementById("model-route-info").textContent = `Route: ${emp.route} (${emp.voice})`;
}

function switchTab(tabId) {
  const btn = document.querySelector(`.nav-tab-btn[data-tab="${tabId}"]`);
  if (btn) btn.click();
}

// --- Web Speech API: Voice Input Recognition ---
function initVoiceRecognition() {
  const micBtn = document.getElementById("mic-btn");
  const waveContainer = document.getElementById("waveform-container");
  const waveStatus = document.getElementById("waveform-status");
  const chatInput = document.getElementById("chat-input");

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    console.warn("Web Speech API not supported in this browser; falling back to typed interaction.");
    micBtn.title = "Microphone requires Chrome or Safari with SpeechRecognition";
    return;
  }

  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    isRecording = true;
    micBtn.classList.add("recording");
    waveContainer.classList.add("active");
    waveStatus.textContent = `Listening... speak to ${document.getElementById("current-emp-name").textContent}`;
  };

  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    chatInput.value = transcript;
    waveStatus.textContent = `"${transcript}"`;
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    stopRecording();
  };

  recognition.onend = () => {
    stopRecording();
    const val = chatInput.value.trim();
    if (val) {
      sendChatMessage(val);
    }
  };

  function stopRecording() {
    isRecording = false;
    micBtn.classList.remove("recording");
    waveContainer.classList.remove("active");
  }

  micBtn.addEventListener("click", () => {
    if (isRecording) {
      recognition.stop();
    } else {
      chatInput.value = "";
      recognition.start();
    }
  });

  // Stop speaking button
  const stopSpeechBtn = document.getElementById("stop-speech-btn");
  stopSpeechBtn.addEventListener("click", async () => {
    await fetch("/api/voice/stop", { method: "POST" });
    stopSpeechBtn.style.display = "none";
  });
}

// --- Chat & Messaging ---
function initChat() {
  const sendBtn = document.getElementById("send-btn");
  const chatInput = document.getElementById("chat-input");

  sendBtn.addEventListener("click", () => {
    const text = chatInput.value.trim();
    if (text) {
      sendChatMessage(text);
      chatInput.value = "";
    }
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (text) {
        sendChatMessage(text);
        chatInput.value = "";
      }
    }
  });

  // Quick prompt chips
  document.querySelectorAll(".quick-prompt-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      // Map prompt to appropriate employee
      if (prompt.includes("day")) selectEmployeeByName("alex");
      else if (prompt.includes("pitch") || prompt.includes("freelance")) selectEmployeeByName("morgan");
      else if (prompt.includes("campaign") || prompt.includes("LinkedIn")) selectEmployeeByName("taylor");
      else if (prompt.includes("empathetic") || prompt.includes("Book") || prompt.includes("email")) selectEmployeeByName("elena");

      sendChatMessage(prompt);
    });
  });

  document.getElementById("clear-chat-btn").addEventListener("click", () => {
    document.getElementById("messages-container").innerHTML = "";
  });
}

function selectEmployeeByName(name) {
  const emp = employeesData.find(e => e.name.toLowerCase() === name.toLowerCase());
  if (emp) selectEmployee(emp);
}

async function sendChatMessage(promptText) {
  const container = document.getElementById("messages-container");
  const voiceEnabled = document.getElementById("voice-toggle").checked;

  // Append User message
  const userMsgEl = document.createElement("div");
  userMsgEl.className = "message user-message";
  userMsgEl.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-body">
      <div class="msg-author">You</div>
      <div class="msg-text">${escapeHtml(promptText)}</div>
    </div>
  `;
  container.appendChild(userMsgEl);
  container.scrollTop = container.scrollHeight;

  // Append Thinking Indicator
  const currentEmpObj = employeesData.find(e => e.name.toLowerCase() === currentEmployee.toLowerCase()) || { name: "Supervisor", avatar: "👑" };
  const thinkingEl = document.createElement("div");
  thinkingEl.className = "message assistant-message thinking-msg";
  thinkingEl.innerHTML = `
    <div class="msg-avatar">${currentEmpObj.avatar}</div>
    <div class="msg-body">
      <div class="msg-author">${currentEmpObj.name}</div>
      <div class="msg-text" style="color: var(--text-muted); font-style: italic;">Thinking & executing tools...</div>
    </div>
  `;
  container.appendChild(thinkingEl);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee: currentEmployee,
        prompt: promptText,
        voice_out: voiceEnabled
      })
    });
    const data = await res.json();
    thinkingEl.remove();

    const empMsgEl = document.createElement("div");
    empMsgEl.className = "message assistant-message";

    let toolsHtml = "";
    if (data.tool_calls && data.tool_calls.length > 0) {
      toolsHtml = data.tool_calls.map(tc => `<div class="tool-badge">⚙️ Tool: ${tc.name}</div>`).join(" ");
    }

    empMsgEl.innerHTML = `
      <div class="msg-avatar">${data.avatar || currentEmpObj.avatar}</div>
      <div class="msg-body">
        <div class="msg-author">${data.employee} (${data.title})</div>
        <div class="msg-text">${escapeHtml(data.text)}</div>
        ${toolsHtml}
        <div class="msg-actions">
          <button class="action-btn-sm" onclick="copyText(this, \`${escapeJs(data.text)}\`)">📋 Copy to macOS</button>
          <button class="action-btn-sm" onclick="speakText(\`${escapeJs(data.text)}\`, '${data.voice}', '${data.employee}')">🔊 Replay Voice</button>
        </div>
      </div>
    `;
    container.appendChild(empMsgEl);
    container.scrollTop = container.scrollHeight;

    if (voiceEnabled) {
      document.getElementById("stop-speech-btn").style.display = "inline-flex";
    }
  } catch (err) {
    thinkingEl.remove();
    console.error("Chat error:", err);
  }
}

// --- Workspace: Agenda & Calendar ---
function initAgendaWorkspace() {
  document.getElementById("add-event-toggle-btn").addEventListener("click", () => {
    toggleVisibility("add-event-form");
  });

  document.getElementById("add-task-toggle-btn").addEventListener("click", () => {
    toggleVisibility("add-task-form");
  });

  document.getElementById("ev-submit-btn").addEventListener("click", async () => {
    const title = document.getElementById("ev-title").value.trim();
    const start_time = document.getElementById("ev-time").value.trim();
    const duration = document.getElementById("ev-dur").value.trim();
    const location = document.getElementById("ev-loc").value.trim();

    if (!title || !start_time) return alert("Title and start time are required.");

    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, start_time, duration_minutes: duration, location })
    });
    document.getElementById("add-event-form").style.display = "none";
    loadAgendaData();
  });

  document.getElementById("task-submit-btn").addEventListener("click", async () => {
    const title = document.getElementById("task-title").value.trim();
    const priority = document.getElementById("task-prio").value;
    const category = document.getElementById("task-cat").value.trim();

    if (!title) return alert("Task title required.");

    await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, priority, category })
    });
    document.getElementById("add-task-form").style.display = "none";
    loadAgendaData();
  });

  document.getElementById("quick-plan-btn").addEventListener("click", () => {
    selectEmployeeByName("alex");
    switchTab("tab-chat");
    sendChatMessage("Alex, generate an optimized time-blocking plan for my day based on my calendar and pending tasks");
  });
}

async function loadAgendaData() {
  try {
    const res = await fetch("/api/agenda");
    const data = await res.json();

    const evList = document.getElementById("events-list");
    if (!data.events || data.events.length === 0) {
      evList.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No calendar events yet. Click + New Event to schedule.</div>`;
    } else {
      evList.innerHTML = data.events.map(ev => `
        <div class="item-row">
          <div>
            <strong>${escapeHtml(ev.title)}</strong><br>
            <span style="color: var(--text-muted); font-size: 11px;">⏰ ${ev.start_time} (${ev.duration_minutes} min) ${ev.location ? '• ' + ev.location : ''}</span>
          </div>
          <span class="badge badge-low">Scheduled</span>
        </div>
      `).join("");
    }

    const tList = document.getElementById("tasks-list");
    if (!data.tasks || data.tasks.length === 0) {
      tList.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No pending tasks. You are all caught up!</div>`;
    } else {
      tList.innerHTML = data.tasks.map(t => `
        <div class="item-row">
          <div>
            <span style="${t.status === 'completed' ? 'text-decoration: line-through; color: var(--text-muted);' : ''}">${escapeHtml(t.title)}</span><br>
            <span style="color: var(--text-muted); font-size: 11px;">Category: ${t.category || 'General'}</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge badge-${t.priority}">${t.priority.toUpperCase()}</span>
            ${t.status === 'pending' ? `<button class="action-btn-sm" onclick="completeTask(${t.id})">✓ Done</button>` : ''}
          </div>
        </div>
      `).join("");
    }
  } catch (e) {
    console.error("Failed to load agenda:", e);
  }
}

async function completeTask(id) {
  await fetch("/api/tasks/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id })
  });
  loadAgendaData();
}

// --- Workspace: CRM & Deals ---
function initCRMWorkspace() {
  document.getElementById("add-lead-toggle-btn").addEventListener("click", () => {
    toggleVisibility("add-lead-form");
  });

  document.getElementById("lead-submit-btn").addEventListener("click", async () => {
    const client_name = document.getElementById("lead-name").value.trim();
    const company = document.getElementById("lead-company").value.trim();
    const project_scope = document.getElementById("lead-scope").value.trim();
    const estimated_value = document.getElementById("lead-value").value.trim();
    const status = document.getElementById("lead-status").value;

    if (!client_name) return alert("Client name required.");

    await fetch("/api/crm/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_name, company, project_scope, estimated_value, status })
    });
    document.getElementById("add-lead-form").style.display = "none";
    loadCRMData();
  });

  document.getElementById("calc-btn").addEventListener("click", () => {
    const rate = parseFloat(document.getElementById("calc-rate").value) || 100;
    const hours = parseFloat(document.getElementById("calc-hours").value) || 40;
    const markup = parseFloat(document.getElementById("calc-markup").value) || 25;

    const base = rate * hours;
    const valAligned = base * (1 + markup / 100);
    const premium = valAligned * 1.5;

    document.getElementById("calc-result").textContent =
`Structured Pricing Tiers:
-------------------------------------------
1. Cost-Plus Base:      $${base.toLocaleString('en-US', {minimumFractionDigits: 2})}
2. Value-Aligned:       $${valAligned.toLocaleString('en-US', {minimumFractionDigits: 2})} (RECOMMENDED)
3. Turnkey Premium:     $${premium.toLocaleString('en-US', {minimumFractionDigits: 2})}
-------------------------------------------
Deliverable: Production deployment with full handoff & documentation.`;
  });

  document.getElementById("pitch-helper-btn").addEventListener("click", () => {
    selectEmployeeByName("morgan");
    switchTab("tab-chat");
    sendChatMessage("Morgan, draft a persuasive $10,000 cold pitch proposal targeting a funded startup for automated AI systems");
  });
}

async function loadCRMData() {
  try {
    const res = await fetch("/api/crm/leads");
    const data = await res.json();
    const list = document.getElementById("leads-list");

    if (!data.leads || data.leads.length === 0) {
      list.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No deals in CRM yet. Click + Add Lead to track prospects.</div>`;
    } else {
      list.innerHTML = data.leads.map(l => `
        <div class="item-row">
          <div>
            <strong>${escapeHtml(l.client_name)}</strong> ${l.company ? '(' + escapeHtml(l.company) + ')' : ''}<br>
            <span style="color: var(--text-muted); font-size: 11px;">Scope: ${escapeHtml(l.project_scope || 'General')} • Val: ${l.estimated_value}</span>
          </div>
          <span class="badge ${l.status === 'won' ? 'badge-low' : 'badge-medium'}">${l.status.toUpperCase()}</span>
        </div>
      `).join("");
    }
  } catch (e) {
    console.error("Failed to load CRM leads:", e);
  }
}

// --- Workspace: Marketing ---
function initMarketingWorkspace() {
  document.getElementById("analyze-hook-btn").addEventListener("click", () => {
    const hook = document.getElementById("hook-input").value.trim();
    if (!hook) return alert("Please enter a hook to analyze.");

    selectEmployeeByName("taylor");
    switchTab("tab-chat");
    sendChatMessage(`Taylor, analyze this hook and give me 3 high-converting viral variations: "${hook}"`);
  });
}

async function loadMarketingData() {
  try {
    const res = await fetch("/api/marketing/campaigns");
    const data = await res.json();
    const list = document.getElementById("campaigns-list");

    if (!data.campaigns || data.campaigns.length === 0) {
      list.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No campaigns logged yet. Ask Taylor in chat to generate campaigns.</div>`;
    } else {
      list.innerHTML = data.campaigns.map(c => `
        <div class="item-row">
          <div>
            <strong>${escapeHtml(c.title)}</strong><br>
            <span style="color: var(--text-muted); font-size: 11px;">Platform: ${c.platform.toUpperCase()}</span>
          </div>
          <button class="action-btn-sm" onclick="copyText(this, \`${escapeJs(c.content)}\`)">Copy Post</button>
        </div>
      `).join("");
    }
  } catch (e) {
    console.error("Failed to load marketing campaigns:", e);
  }
}

// --- Workspace: Empathy & Manuscripts ---
function initEmpathyWorkspace() {
  document.getElementById("calibrate-empathy-btn").addEventListener("click", () => {
    const text = document.getElementById("empathy-input").value.trim();
    const context = document.getElementById("empathy-recipient").value.trim();
    if (!text) return alert("Please enter text to calibrate.");

    selectEmployeeByName("elena");
    switchTab("tab-chat");
    sendChatMessage(`Elena, using your high-empathy calibration (Claude Haiku 4.5), rewrite this sensitive message for the recipient context '${context}':\n\n"${text}"`);
  });

  document.getElementById("open-mail-btn").addEventListener("click", async () => {
    const text = document.getElementById("empathy-input").value.trim();
    const recipient = document.getElementById("empathy-recipient").value.trim() || "client@example.com";
    if (!text) return alert("Please enter an email draft first.");

    selectEmployeeByName("elena");
    switchTab("tab-chat");
    sendChatMessage(`Elena, compose this email with high empathy, copy it to clipboard, and open it in Apple Mail for ${recipient}`);
  });
}

async function loadManuscriptData() {
  try {
    const res = await fetch("/api/manuscripts");
    const data = await res.json();
    const list = document.getElementById("manuscripts-list");

    if (!data.manuscripts || data.manuscripts.length === 0) {
      list.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No manuscript chapters logged yet. Ask Elena in chat to outline a book or draft chapters.</div>`;
    } else {
      list.innerHTML = data.manuscripts.map(m => `
        <div class="item-row">
          <div>
            <strong>Chapter ${m.chapter_number}: ${escapeHtml(m.title)}</strong><br>
            <span style="color: var(--text-muted); font-size: 11px;">Tone: ${m.tone} • Word Count: ${m.word_count} words</span>
          </div>
          <span class="badge badge-low">Draft</span>
        </div>
      `).join("");
    }
  } catch (e) {
    console.error("Failed to load manuscripts:", e);
  }
}

// --- Voice & Speech Audio Playback ---
async function speakText(text, voiceName, empName) {
  try {
    await fetch("/api/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice: voiceName, employee: empName })
    });
    document.getElementById("stop-speech-btn").style.display = "inline-flex";
  } catch (e) {
    console.error("Voice playback error:", e);
  }
}

// --- Utility Helpers ---
async function copyText(btnEl, text) {
  try {
    await navigator.clipboard.writeText(text);
    await fetch("/api/clipboard/copy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const orig = btnEl.textContent;
    btnEl.textContent = "✓ Copied!";
    setTimeout(() => { btnEl.textContent = orig; }, 1800);
  } catch (e) {
    console.error("Copy failed:", e);
  }
}

function toggleVisibility(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = el.style.display === "none" ? "flex" : "none";
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function escapeJs(str) {
  if (!str) return "";
  return str.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$/g, "\\$");
}

