const games = window.GAMEGEM_CATALOG || [];
const featuredIds = window.GAMEGEM_FEATURED_IDS || games.slice(0, 5).map(game => game.id);
const featuredGames = featuredIds.map(id => games.find(game => game.id === id)).filter(Boolean);
const config = window.GAMEGEM_CONFIG || { chatEndpoint: null };

const state = {
  activeFilter: "all",
  search: "",
  selectedGame: null,
  messages: [],
  chatBusy: false,
  heroIndex: 0,
  heroTimer: null,
  heroTransitioning: false,
  pointerStartX: null,
  pointerDeltaX: 0
};

const $ = id => document.getElementById(id);
const gamesGrid = $("gamesGrid");
const searchInput = $("searchInput");
const chips = document.querySelectorAll(".chip");
const openSearchBtn = $("openSearchBtn");
const detailModal = $("detailModal");
const detailBackdrop = $("detailBackdrop");
const closeDetailBtn = $("closeDetailBtn");
const detailCover = $("detailCover");
const detailGenre = $("detailGenre");
const detailTitle = $("detailTitle");
const detailDescription = $("detailDescription");
const detailMeta = $("detailMeta");
const detailAskAiBtn = $("detailAskAiBtn");
const chatWidget = $("chatWidget");
const chatLauncher = $("chatLauncher");
const closeChatBtn = $("closeChatBtn");
const chatMessages = $("chatMessages");
const chatForm = $("chatForm");
const chatInput = $("chatInput");
const sendBtn = chatForm.querySelector(".send-btn");
const chatSuggestions = $("chatSuggestions");
const carouselStage = $("carouselStage");
const carouselDots = $("carouselDots");
const carouselPrev = $("carouselPrev");
const carouselNext = $("carouselNext");
const carouselShell = $("carouselShell");
const carouselProgressBar = $("carouselProgressBar");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function coverFallbackDataUri(title = "GameGem") {
  const safe = String(title).slice(0, 28).replace(/[<>&"]/g, "");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1350" viewBox="0 0 900 1350"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset=".52" stop-color="#23345a"/><stop offset="1" stop-color="#6d4bd1"/></linearGradient></defs><rect width="900" height="1350" fill="url(#g)"/><circle cx="720" cy="220" r="280" fill="#22d3ee" opacity=".12"/><text x="70" y="1140" fill="#fff" font-family="Arial,sans-serif" font-size="72" font-weight="700">${safe}</text><text x="72" y="1215" fill="#a9b8ce" font-family="Arial,sans-serif" font-size="28" letter-spacing="8">GAMEGEM</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function heroFallbackDataUri(title = "GameGem") {
  const safe = String(title).slice(0, 36).replace(/[<>&"]/g, "");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#07101d"/><stop offset=".48" stop-color="#132b52"/><stop offset="1" stop-color="#4f36a5"/></linearGradient><radialGradient id="r"><stop stop-color="#25d9ef" stop-opacity=".30"/><stop offset="1" stop-color="#25d9ef" stop-opacity="0"/></radialGradient></defs><rect width="1600" height="900" fill="url(#g)"/><circle cx="1260" cy="260" r="460" fill="url(#r)"/><text x="95" y="635" fill="#fff" font-family="Arial,sans-serif" font-size="96" font-weight="700">${safe}</text><text x="102" y="708" fill="#a8bad3" font-family="Arial,sans-serif" font-size="30" letter-spacing="10">GAMEGEM FEATURED</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function createHeroSlide(game, index) {
  const slide = document.createElement("article");
  slide.className = "hero-slide";
  slide.dataset.heroIndex = String(index);
  slide.innerHTML = `
    <img class="hero-art" src="${escapeHtml(game.heroImage || game.image)}" data-cover="${escapeHtml(game.image)}" alt="" draggable="false" />
    <div class="hero-slide-content">
      <span class="hero-badge">Featured game</span>
      <h1 class="hero-game-title">${escapeHtml(game.title)}</h1>
      <p class="hero-game-description">${escapeHtml(game.description)}</p>
      <div class="hero-meta">
        <span>${escapeHtml(game.genre)}</span>
        <span>${escapeHtml(game.price)}</span>
        <span>${escapeHtml(game.time)}</span>
        <span>${escapeHtml(game.platforms.slice(0, 2).join(" · "))}</span>
      </div>
      <div class="hero-cta-row">
        <button class="primary-btn hero-action" type="button" data-hero-details="${game.id}">View details <span>↗</span></button>
        <button class="ghost-btn hero-action" type="button" data-hero-ai="${game.id}">Ask GameGem AI</button>
      </div>
    </div>`;

  const image = slide.querySelector(".hero-art");
  let fallbackStage = 0;
  image.addEventListener("error", () => {
    if (fallbackStage === 0 && image.dataset.cover) {
      fallbackStage = 1;
      image.src = image.dataset.cover;
    } else if (fallbackStage === 1) {
      fallbackStage = 2;
      image.src = heroFallbackDataUri(game.title);
    }
  });

  return slide;
}

function updateDots() {
  carouselDots.querySelectorAll(".carousel-dot").forEach((dot, index) => {
    const active = index === state.heroIndex;
    dot.classList.toggle("active", active);
    dot.setAttribute("aria-current", active ? "true" : "false");
  });
}

function resetProgressAnimation() {
  carouselProgressBar.classList.remove("running");
  void carouselProgressBar.offsetWidth;
  carouselProgressBar.classList.add("running");
}

function renderCarousel() {
  if (!featuredGames.length) return;
  carouselStage.innerHTML = "";
  const initial = createHeroSlide(featuredGames[0], 0);
  initial.classList.add("is-current");
  carouselStage.appendChild(initial);

  carouselDots.innerHTML = featuredGames.map((game, index) => `
    <button class="carousel-dot ${index === 0 ? "active" : ""}" type="button" data-dot-index="${index}" aria-label="Show ${escapeHtml(game.title)}" aria-current="${index === 0 ? "true" : "false"}"></button>
  `).join("");
  resetProgressAnimation();
}

function goToHero(nextIndex, userInitiated = false, explicitDirection = null) {
  if (!featuredGames.length || state.heroTransitioning) return;
  const normalized = (nextIndex + featuredGames.length) % featuredGames.length;
  if (normalized === state.heroIndex) {
    if (userInitiated) restartHeroAutoplay();
    return;
  }

  const currentIndex = state.heroIndex;
  let direction = explicitDirection;
  if (!direction) {
    const forwardDistance = (normalized - currentIndex + featuredGames.length) % featuredGames.length;
    const backwardDistance = (currentIndex - normalized + featuredGames.length) % featuredGames.length;
    direction = forwardDistance <= backwardDistance ? 1 : -1;
  }

  state.heroTransitioning = true;
  const oldSlide = carouselStage.querySelector(".hero-slide.is-current") || carouselStage.querySelector(".hero-slide");
  const incoming = createHeroSlide(featuredGames[normalized], normalized);
  incoming.classList.add("is-entering", direction > 0 ? "enter-from-right" : "enter-from-left");
  carouselStage.appendChild(incoming);

  // Force the browser to commit the starting position before animating.
  void incoming.offsetWidth;
  oldSlide?.classList.add("is-leaving");
  oldSlide?.classList.remove("is-current");
  oldSlide?.classList.add(direction > 0 ? "leave-to-left" : "leave-to-right");
  incoming.classList.remove("enter-from-right", "enter-from-left");
  incoming.classList.add("is-current");

  state.heroIndex = normalized;
  updateDots();
  resetProgressAnimation();

  window.setTimeout(() => {
    oldSlide?.remove();
    incoming.classList.remove("is-entering");
    state.heroTransitioning = false;
  }, 690);

  if (userInitiated) restartHeroAutoplay();
}

function nextHero(userInitiated = false) { goToHero(state.heroIndex + 1, userInitiated, 1); }
function prevHero(userInitiated = false) { goToHero(state.heroIndex - 1, userInitiated, -1); }

function startHeroAutoplay() {
  stopHeroAutoplay();
  resetProgressAnimation();
  state.heroTimer = window.setInterval(() => nextHero(false), 7500);
}
function stopHeroAutoplay() {
  if (state.heroTimer) window.clearInterval(state.heroTimer);
  state.heroTimer = null;
  carouselProgressBar.classList.remove("running");
}
function restartHeroAutoplay() {
  startHeroAutoplay();
}

carouselPrev.addEventListener("click", () => prevHero(true));
carouselNext.addEventListener("click", () => nextHero(true));
carouselDots.addEventListener("click", event => {
  const dot = event.target.closest(".carousel-dot");
  if (!dot) return;
  const nextIndex = Number(dot.dataset.dotIndex);
  const direction = nextIndex > state.heroIndex ? 1 : -1;
  goToHero(nextIndex, true, direction);
});
carouselStage.addEventListener("click", event => {
  const detailsButton = event.target.closest("[data-hero-details]");
  const aiButton = event.target.closest("[data-hero-ai]");
  if (detailsButton) {
    const game = games.find(item => item.id === Number(detailsButton.dataset.heroDetails));
    if (game) openDetailModal(game);
  }
  if (aiButton) {
    const game = games.find(item => item.id === Number(aiButton.dataset.heroAi));
    if (game) {
      setChatOpen(true);
      chatInput.value = `Tell me about ${game.title}`;
      resizeChatInput();
      chatInput.focus();
    }
  }
});

carouselShell.addEventListener("mouseenter", stopHeroAutoplay);
carouselShell.addEventListener("mouseleave", startHeroAutoplay);
carouselShell.addEventListener("focusin", stopHeroAutoplay);
carouselShell.addEventListener("focusout", event => {
  if (!carouselShell.contains(event.relatedTarget)) startHeroAutoplay();
});

carouselShell.addEventListener("pointerdown", event => {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  if (event.target.closest("button")) return;
  state.pointerStartX = event.clientX;
  state.pointerDeltaX = 0;
  carouselShell.setPointerCapture?.(event.pointerId);
});
carouselShell.addEventListener("pointermove", event => {
  if (state.pointerStartX == null) return;
  state.pointerDeltaX = event.clientX - state.pointerStartX;
});
carouselShell.addEventListener("pointerup", () => {
  if (state.pointerStartX == null) return;
  if (Math.abs(state.pointerDeltaX) > 55) {
    state.pointerDeltaX < 0 ? nextHero(true) : prevHero(true);
  }
  state.pointerStartX = null;
  state.pointerDeltaX = 0;
});
carouselShell.addEventListener("pointercancel", () => {
  state.pointerStartX = null;
  state.pointerDeltaX = 0;
});

/* ===== Catalog ===== */
function renderGames(list) {
  gamesGrid.innerHTML = list.map(game => `
    <article class="game-card" data-id="${game.id}" tabindex="0" role="button" aria-label="Open details for ${escapeHtml(game.title)}">
      <img class="game-cover" src="${escapeHtml(game.image)}" alt="${escapeHtml(game.title)} cover" loading="lazy" />
      <div class="game-card-body">
        <div class="game-price-row"><small>${escapeHtml(game.genre)}</small><span class="game-price">${escapeHtml(game.price)}</span></div>
        <h3>${escapeHtml(game.title)}</h3>
        <p class="game-description">${escapeHtml(game.description)}</p>
        <div class="game-meta"><span class="badge">${escapeHtml(game.time)}</span><span>${escapeHtml(game.platforms.slice(0, 2).join(" · "))}</span></div>
        <div class="game-tags">${game.tags.slice(0, 3).map(tag => `<span>${escapeHtml(tag)}</span>`).join("")}</div>
      </div>
    </article>`).join("");

  gamesGrid.querySelectorAll(".game-cover").forEach(img => {
    img.addEventListener("error", () => {
      const card = img.closest(".game-card");
      const game = games.find(item => String(item.id) === card?.dataset.id);
      img.src = coverFallbackDataUri(game?.title || "GameGem");
    }, { once: true });
  });

  gamesGrid.querySelectorAll(".game-card").forEach(card => {
    const open = () => {
      const game = games.find(item => String(item.id) === card.dataset.id);
      if (game) openDetailModal(game);
    };
    card.addEventListener("click", open);
    card.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
  });
}

function filterGames() {
  const query = state.search.trim().toLowerCase();
  const list = games.filter(game => {
    const searchable = `${game.title} ${game.genre} ${game.description} ${game.tags.join(" ")} ${game.platforms.join(" ")}`.toLowerCase();
    const matchesSearch = !query || searchable.includes(query);
    let matchesFilter = true;
    switch (state.activeFilter) {
      case "rpg": matchesFilter = game.tags.includes("rpg"); break;
      case "action": matchesFilter = game.tags.includes("action"); break;
      case "co-op": matchesFilter = game.tags.includes("co-op"); break;
      case "story": matchesFilter = game.tags.includes("story"); break;
      case "budget": matchesFilter = game.priceValue <= 30; break;
      case "switch": matchesFilter = game.platforms.some(p => p.toLowerCase().includes("switch")); break;
      case "ps5": matchesFilter = game.platforms.some(p => p.toLowerCase().includes("ps5")); break;
    }
    return matchesSearch && matchesFilter;
  });
  renderGames(list);
}

/* ===== Detail modal ===== */
function openDetailModal(game) {
  state.selectedGame = game;
  detailCover.src = game.image;
  detailCover.onerror = () => { detailCover.onerror = null; detailCover.src = coverFallbackDataUri(game.title); };
  detailGenre.textContent = game.genre;
  detailTitle.textContent = game.title;
  detailDescription.textContent = game.description;
  detailMeta.innerHTML = `<span>Price: ${escapeHtml(game.price)}</span><span>Time: ${escapeHtml(game.time)}</span><span>${escapeHtml(game.platforms.join(" · "))}</span>${game.tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join("")}`;
  detailModal.classList.add("open");
  detailModal.setAttribute("aria-hidden", "false");
}
function closeDetailModal() {
  detailModal.classList.remove("open");
  detailModal.setAttribute("aria-hidden", "true");
}

/* ===== Chat ===== */
function setChatOpen(open) {
  chatWidget.classList.toggle("open", open);
  chatWidget.setAttribute("aria-hidden", String(!open));
  chatLauncher.setAttribute("aria-expanded", String(open));
  if (open) window.setTimeout(() => chatInput.focus(), 120);
}
function toggleChat() { setChatOpen(!chatWidget.classList.contains("open")); }

function addMessage(role, text) {
  const element = document.createElement("div");
  element.className = `message ${role}`;
  element.textContent = text;
  chatMessages.appendChild(element);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return element;
}
function addTypingIndicator() {
  const element = document.createElement("div");
  element.id = "typingIndicator";
  element.className = "message assistant typing";
  element.innerHTML = "<i></i><i></i><i></i>";
  chatMessages.appendChild(element);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function removeTypingIndicator() {
  $("typingIndicator")?.remove();
}
function setChatBusy(busy) {
  state.chatBusy = busy;
  chatInput.disabled = busy;
  sendBtn.disabled = busy;
  chatSuggestions.querySelectorAll("button").forEach(button => { button.disabled = busy; });
}
function resizeChatInput() {
  chatInput.style.height = "auto";
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 96)}px`;
}
chatInput.addEventListener("input", resizeChatInput);
chatInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

function getSessionId() {
  let id = localStorage.getItem("gamegem_session_id");
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : `gg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem("gamegem_session_id", id);
  }
  return id;
}

const SMOOTH_STREAM_CONFIG = {
  tickMs: 20,
  baseChars: 2,
  mediumChars: 4,
  fastChars: 8,
  catchUpChars: 14,
  mediumBacklog: 48,
  fastBacklog: 140,
  catchUpBacklog: 360,
  maxTailMs: 650
};

function safePrefixLength(text, requested) {
  let end = Math.min(requested, text.length);
  if (end > 0 && end < text.length) {
    const previous = text.charCodeAt(end - 1);
    const next = text.charCodeAt(end);
    const previousIsHighSurrogate = previous >= 0xD800 && previous <= 0xDBFF;
    const nextIsLowSurrogate = next >= 0xDC00 && next <= 0xDFFF;
    if (previousIsHighSurrogate && nextIsLowSurrogate) end += 1;
  }
  return end;
}

function createSmoothTextStreamer(element) {
  let pending = "";
  let displayed = "";
  let timer = null;
  let sourceDone = false;
  let settled = false;
  let resolveDone;
  const donePromise = new Promise(resolve => { resolveDone = resolve; });

  const scrollToLatest = () => {
    window.requestAnimationFrame(() => {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    });
  };

  const settleIfFinished = () => {
    if (!settled && sourceDone && pending.length === 0) {
      settled = true;
      element.classList.remove("streaming");
      resolveDone(displayed);
    }
  };

  const charsForThisTick = () => {
    const backlog = pending.length;
    let amount = SMOOTH_STREAM_CONFIG.baseChars;

    if (backlog >= SMOOTH_STREAM_CONFIG.catchUpBacklog) {
      amount = SMOOTH_STREAM_CONFIG.catchUpChars;
    } else if (backlog >= SMOOTH_STREAM_CONFIG.fastBacklog) {
      amount = SMOOTH_STREAM_CONFIG.fastChars;
    } else if (backlog >= SMOOTH_STREAM_CONFIG.mediumBacklog) {
      amount = SMOOTH_STREAM_CONFIG.mediumChars;
    }

    // Once the network/model stream has ended, gently catch up so the user
    // never waits several seconds just for the visual animation to finish.
    if (sourceDone && backlog > 0) {
      const ticksAvailable = Math.max(1, Math.floor(SMOOTH_STREAM_CONFIG.maxTailMs / SMOOTH_STREAM_CONFIG.tickMs));
      amount = Math.max(amount, Math.ceil(backlog / ticksAvailable));
    }

    return Math.max(1, amount);
  };

  const schedule = () => {
    if (timer !== null || settled) return;
    timer = window.setTimeout(step, SMOOTH_STREAM_CONFIG.tickMs);
  };

  const step = () => {
    timer = null;
    if (!pending.length) {
      settleIfFinished();
      return;
    }

    const count = safePrefixLength(pending, charsForThisTick());
    const piece = pending.slice(0, count);
    pending = pending.slice(count);
    displayed += piece;
    element.textContent = displayed;
    scrollToLatest();

    if (pending.length) schedule();
    else settleIfFinished();
  };

  return {
    add(text) {
      if (!text || settled) return;
      pending += text;

      // Paint the first couple of characters immediately for fast first-token
      // feedback, then switch to the controlled cadence.
      if (!displayed && timer === null) {
        step();
      } else {
        schedule();
      }
    },
    finish() {
      sourceDone = true;
      if (pending.length) schedule();
      else settleIfFinished();
      return donePromise;
    },
    cancel() {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
      sourceDone = true;
      pending = "";
      settleIfFinished();
    },
    get text() {
      return displayed + pending;
    }
  };
}

async function streamFromFastAPI(message) {
  const response = await fetch(config.chatEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: getSessionId() })
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);

  const returnedSession = response.headers.get("X-GameGem-Session-ID");
  if (returnedSession) localStorage.setItem("gamegem_session_id", returnedSession);

  let assistantBubble = null;
  let smoother = null;
  let rawText = "";

  const ensureAssistantBubble = () => {
    if (assistantBubble) return;
    removeTypingIndicator();
    assistantBubble = addMessage("assistant", "");
    assistantBubble.classList.add("streaming");
    smoother = createSmoothTextStreamer(assistantBubble);
  };

  const acceptChunk = text => {
    if (!text) return;
    rawText += text;
    ensureAssistantBubble();
    smoother.add(text);
  };

  if (!response.body) {
    acceptChunk(await response.text());
    ensureAssistantBubble();
    await smoother.finish();
    return rawText || assistantBubble.textContent;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      acceptChunk(decoder.decode(value, { stream: true }));
    }
    acceptChunk(decoder.decode());

    // An empty model response is rare, but keep the UI coherent if it occurs.
    if (!assistantBubble) {
      acceptChunk("GameGem didn't return any text. Please try again.");
    }

    await smoother.finish();
    return rawText || assistantBubble.textContent;
  } catch (error) {
    smoother?.cancel();
    throw error;
  } finally {
    reader.releaseLock?.();
  }
}

function demoReply(message) {
  const text = message.toLowerCase();
  if (text.includes("cheap") || text.includes("budget") || text.includes("under")) return "For budget-friendly picks, Hades, Hollow Knight, and Stardew Valley are strong choices in this demo catalog.";
  if (text.includes("co-op") || text.includes("coop")) return "For co-op, It Takes Two is the strongest dedicated choice here, while Stardew Valley and Baldur's Gate 3 also support cooperative play.";
  const match = games.find(game => text.includes(game.title.toLowerCase()));
  if (match) return `${match.title} is a ${match.genre} title at ${match.price}, available on ${match.platforms.join(", ")}. ${match.description}`;
  return "I can recommend games by genre, platform, budget, playtime, co-op support, or tell you more about a specific title.";
}

async function handleUserMessage(text) {
  const message = text.trim();
  if (!message || state.chatBusy) return;
  setChatOpen(true);
  setChatBusy(true);
  addMessage("user", message);
  state.messages.push({ role: "user", content: message });
  chatInput.value = "";
  resizeChatInput();
  addTypingIndicator();

  try {
    if (!config.chatEndpoint) {
      await new Promise(resolve => setTimeout(resolve, 600));
      removeTypingIndicator();
      const reply = demoReply(message);
      addMessage("assistant", reply);
      state.messages.push({ role: "assistant", content: reply });
      return;
    }

    const reply = await streamFromFastAPI(message);
    state.messages.push({ role: "assistant", content: reply });
  } catch (error) {
    removeTypingIndicator();
    const fallback = `I couldn't reach the GameGem backend right now. ${demoReply(message)}`;
    addMessage("assistant", fallback);
    state.messages.push({ role: "assistant", content: fallback });
    console.error("GameGem chat error:", error);
  } finally {
    setChatBusy(false);
    chatInput.focus();
  }
}

chips.forEach(chip => {
  chip.addEventListener("click", () => {
    chips.forEach(item => item.classList.remove("active"));
    chip.classList.add("active");
    state.activeFilter = chip.dataset.filter;
    filterGames();
  });
});
searchInput.addEventListener("input", event => { state.search = event.target.value; filterGames(); });
openSearchBtn.addEventListener("click", () => {
  document.querySelector(".filter-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
  window.setTimeout(() => searchInput.focus(), 420);
});
chatForm.addEventListener("submit", event => { event.preventDefault(); handleUserMessage(chatInput.value); });
chatSuggestions.addEventListener("click", event => {
  const button = event.target.closest(".suggestion-chip");
  if (!button || state.chatBusy) return;
  const map = {
    "Cheap PS5 co-op": "Recommend a cheap PS5 co-op game",
    "About Cyberpunk 2077": "Tell me about Cyberpunk 2077",
    "Short indie game": "I want a short indie game"
  };
  handleUserMessage(map[button.textContent.trim()] || button.textContent.trim());
});
chatLauncher.addEventListener("click", toggleChat);
closeChatBtn.addEventListener("click", () => setChatOpen(false));
detailBackdrop.addEventListener("click", closeDetailModal);
closeDetailBtn.addEventListener("click", closeDetailModal);
detailAskAiBtn.addEventListener("click", () => {
  if (!state.selectedGame) return;
  const prompt = `Tell me about ${state.selectedGame.title}`;
  closeDetailModal();
  setChatOpen(true);
  chatInput.value = prompt;
  resizeChatInput();
  chatInput.focus();
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    closeDetailModal();
    setChatOpen(false);
  }
  const tag = document.activeElement?.tagName;
  const typing = tag === "INPUT" || tag === "TEXTAREA" || document.activeElement?.isContentEditable;
  if (!typing && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
    event.preventDefault();
    event.key === "ArrowLeft" ? prevHero(true) : nextHero(true);
  }
});

function bootstrapChat() {
  addMessage("assistant", "Hi — I'm GameGem AI. Tell me what you feel like playing, your platform, budget, or a game you want to know more about.");
}

renderCarousel();
renderGames(games);
bootstrapChat();
startHeroAutoplay();
