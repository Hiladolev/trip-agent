const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");

// Hebrew + Arabic Unicode ranges, used to pick each bubble's text direction.
const RTL_CHAR_RE = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/;
const LTR_CHAR_RE = /[a-zA-Z]/;

function detectDirection(text) {
  for (const char of text) {
    if (LTR_CHAR_RE.test(char)) return "ltr";
    if (RTL_CHAR_RE.test(char)) return "rtl";
  }
  return "ltr";
}

function renderMarkdown(text) {
  const html = marked.parse(text);
  return DOMPurify.sanitize(html);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message message-${role}`;
  bubble.dir = detectDirection(content);
  bubble.innerHTML = renderMarkdown(content);
  messagesEl.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

function appendTypingIndicator() {
  const bubble = document.createElement("div");
  bubble.className = "message message-assistant typing-indicator";
  bubble.textContent = "...";
  messagesEl.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

function appendError(text) {
  const bubble = document.createElement("div");
  bubble.className = "message message-error";
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  scrollToBottom();
}

async function loadHistory() {
  const response = await fetch("/history");
  const history = await response.json();
  for (const message of history) {
    appendMessage(message.role, message.content);
  }
}

async function sendMessage(text) {
  appendMessage("user", text);
  inputEl.disabled = true;
  const indicator = appendTypingIndicator();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    indicator.remove();
    appendMessage("assistant", data.reply);
  } catch (err) {
    indicator.remove();
    appendError("Something went wrong, try again.");
  } finally {
    inputEl.disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  sendMessage(text);
});

loadHistory();
