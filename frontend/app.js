const SAMPLES = [
  "Did Trump accurately describe the Medicare payments and premiums?",
  "What did The Guardian report that the official statements left out?",
  "How do the US and China statements differ on military crisis communication?",
];

const SIDE_NAME = {
  us: "US (White House)",
  china: "China (Foreign Ministry)",
  press: "The Guardian",
};

const SIDE_SHORT = { us: "US", china: "China", press: "Guardian" };
const SIDE_HEADER = { us: "US", china: "China", press: "The Guardian" };

const LABEL_TEXT = {
  same: "Same",
  different_framing: "Different framing",
  contradiction: "Contradiction",
  only_us: "Only in US statement",
  only_china: "Only in China statement",
  only_press: "Only in The Guardian",
};

const ONLY_NOTE = {
  only_us: "Only the US says this",
  only_china: "Only China says this",
  only_press: "Only The Guardian says this",
};

const FOLLOW_UP = {
  us: "Compare with the US instead",
  china: "Compare with China instead",
  press: "Compare with The Guardian instead",
};

const VERDICT_TEXT = {
  supported: "Supported",
  imprecise: "Imprecise",
  contradicted: "Contradicted",
  not_checkable: "Not checkable",
};

const messages = document.querySelector("#messages");
const empty = document.querySelector("#empty");
const samples = document.querySelector("#samples");
const form = document.querySelector("#composer");
const input = document.querySelector("#question");
const sendButton = document.querySelector("#send");
const panelQuestion = document.querySelector("#panel-question");
const panelKicker = document.querySelector("#panel-kicker");
const panelBody = document.querySelector("#panel-body");

let sessionId = null;
let busy = false;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function formatDate(value) {
  if (!value) return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value));
  if (!match) return String(value);
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function commaIntegers(value) {
  return String(value).replace(/\d{4,}/g, (digits) => Number(digits).toLocaleString("en-US"));
}

function parseResult(call) {
  try {
    const parsed = JSON.parse(call.result);
    return parsed && typeof parsed === "object" ? parsed : { error: "The tool returned a result that could not be read." };
  } catch (err) {
    return { error: "The tool returned a result that could not be read." };
  }
}

function sideName(side) {
  return SIDE_NAME[side] || side || "Source";
}

function topicLabel(topic) {
  const text = (topic || "").trim();
  return text || "all topics";
}

function trailLabel(call, parsed) {
  const args = call.args || {};
  if (call.name === "compare_statements") {
    const left = SIDE_SHORT[args.left] || args.left || "?";
    const right = SIDE_SHORT[args.right] || args.right || "?";
    return `compare_statements · ${left} vs ${right} · ${topicLabel(args.topic)}`;
  }
  if (call.name === "check_claim") return `check_claim · ${args.claim_id || "claim"}`;
  if (call.name === "get_official_source") return `get_official_source · ${SIDE_SHORT[args.source] || args.source || "source"}`;
  if (call.name === "get_press_coverage") return "get_press_coverage · Guardian articles";
  if (call.name === "list_cases") {
    const count = Array.isArray(parsed.cases) ? parsed.cases.length : 0;
    return `list_cases · ${count} cases`;
  }
  return call.name || "tool";
}

function compareTitle(result, args) {
  const left = SIDE_HEADER[result.left || args.left] || result.left || "Left";
  const right = SIDE_HEADER[result.right || args.right] || result.right || "Right";
  const topic = topicLabel(result.topic != null ? result.topic : args.topic);
  return `${left} vs ${right} · ${topic}`;
}

function renderMarkdown(text) {
  const html = window.marked.parse(text || "", { gfm: true, breaks: true });
  return window.DOMPurify.sanitize(html);
}

function appendLink(parent, href, text) {
  if (!href) return;
  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener";
  link.textContent = text || href;
  parent.appendChild(link);
}

function liveTag(live) {
  if (typeof live !== "boolean") return null;
  return el("span", live ? "tag live" : "tag snapshot", live ? "LIVE" : "SNAPSHOT");
}

function changedNote(parent, changed) {
  if (changed !== true) return;
  parent.appendChild(el("p", "note", "Live page changed or unavailable; showing saved copy"));
}

function highlight(parent, text, phrase) {
  parent.replaceChildren();
  const body = text || "";
  const start = phrase ? body.indexOf(phrase) : -1;
  if (!phrase || start < 0) {
    parent.textContent = body;
    return;
  }
  parent.appendChild(document.createTextNode(body.slice(0, start)));
  parent.appendChild(el("mark", null, phrase));
  parent.appendChild(document.createTextNode(body.slice(start + phrase.length)));
}

function publishedFor(result, which) {
  const meta = result[`${which}_source`] || {};
  if (meta.published) return [meta.published];
  const seen = [];
  for (const row of result.rows || []) {
    const value = row[`${which}_published`];
    if (value && !seen.includes(value)) seen.push(value);
  }
  return seen;
}

function fillQuote(cell, result, row, which) {
  const side = result[which];
  cell.classList.add(side || "source");
  const quote = row[`${which}_quote`];
  const headline = row[`${which}_headline`];
  const byline = row[`${which}_byline`];
  const url = row[`${which}_url`] || (result[`${which}_source`] || {}).url;
  const published = row[`${which}_published`] || (result[`${which}_source`] || {}).published;

  if (side === "press" && headline) cell.appendChild(el("p", "headline", headline));
  if (side === "press" && byline) cell.appendChild(el("p", "byline", byline));

  if (quote) cell.appendChild(el("blockquote", "words", quote));
  else cell.appendChild(el("p", "missing", "Not mentioned in this source"));

  const cite = el("p", "cite");
  cite.appendChild(document.createTextNode(sideName(side)));
  if (published) cite.appendChild(document.createTextNode(`, ${formatDate(published)}`));
  if (url) {
    cite.appendChild(document.createTextNode(" · "));
    appendLink(cite, url, "Link");
  }
  cell.appendChild(cite);

  if (side === "press" && row.attributed_to) {
    cell.appendChild(el("p", "note", `Attributed by the AI to: ${row.attributed_to}`));
  }
}

function renderComparison(parent, result, args) {
  const block = el("section", "evidence-block");
  block.appendChild(el("h3", "evidence-title", compareTitle(result, args || {})));

  const dates = el("p", "meta-line");
  ["left", "right"].forEach((which, index) => {
    const datesForSide = publishedFor(result, which);
    if (!datesForSide.length && !(result[`${which}_source`])) return;
    if (index && dates.childNodes.length) dates.appendChild(document.createTextNode(" · "));
    dates.appendChild(document.createTextNode(sideName(result[which])));
    if (datesForSide.length) {
      dates.appendChild(document.createTextNode(`, ${datesForSide.map(formatDate).join(" and ")}`));
    }
    const meta = result[`${which}_source`] || {};
    const tag = liveTag(meta.live);
    if (tag) dates.appendChild(tag);
  });
  if (dates.childNodes.length) block.appendChild(dates);
  const leftChanged = (result.left_source || {}).live_changed === true;
  const rightChanged = (result.right_source || {}).live_changed === true;
  changedNote(block, leftChanged || rightChanged);

  const columns = el("div", "columns");
  columns.appendChild(el("div", null, sideName(result.left)));
  columns.appendChild(el("div"));
  columns.appendChild(el("div", null, sideName(result.right)));
  block.appendChild(columns);

  let termRow = null;
  for (const row of result.rows || []) {
    if (row.label === "term_check") {
      termRow = row;
      continue;
    }
    const pair = el("div", "pair");
    if (ONLY_NOTE[row.label]) pair.classList.add(row.label);
    const left = el("div", "quote");
    const right = el("div", "quote");
    fillQuote(left, result, row, "left");
    fillQuote(right, result, row, "right");
    const badge = el("div", "label-cell");
    badge.appendChild(el("span", "badge", LABEL_TEXT[row.label] || row.label || "Row"));
    pair.append(left, badge, right);
    if (ONLY_NOTE[row.label]) {
      const note = el("p", "only-note", ONLY_NOTE[row.label]);
      note.style.gridColumn = "1 / -1";
      pair.appendChild(note);
    }
    if (row.source_note) {
      const note = el("p", "note", row.source_note);
      pair.appendChild(note);
    }
    block.appendChild(pair);
  }

  if (termRow && termRow.terms) {
    const terms = el("div", "terms");
    Object.entries(termRow.terms).forEach(([term, found]) => {
      terms.appendChild(el("p", "term-line", found ? `${term} ✓ found` : `${term} ✗ not found`));
    });
    terms.appendChild(el("p", "term-note", "Checked in China's own Chinese text."));
    block.appendChild(terms);
  }

  if (result.dropped > 0) {
    const count = result.dropped;
    const noun = count === 1 ? "quote" : "quotes";
    block.appendChild(el("p", "note", `${count} ${noun} hidden because they couldn't be verified`));
  }
  if (result.cap_hit === true) {
    block.appendChild(el("p", "cap-note", "This comparison is capped at 12 rows."));
  }

  const shown = new Set([result.left, result.right]);
  const follow = el("div", "followups");
  ["us", "china", "press"].forEach((side) => {
    if (shown.has(side) || !FOLLOW_UP[side]) return;
    const button = el("button", null, FOLLOW_UP[side]);
    button.type = "button";
    button.addEventListener("click", () => send(FOLLOW_UP[side]));
    follow.appendChild(button);
  });
  if (follow.childNodes.length) block.appendChild(follow);
  parent.appendChild(block);
}

function renderClaim(parent, result) {
  const block = el("section", "evidence-block");
  const top = el("div", "claim-top");
  const heading = el("div");
  const titleRow = el("div", "title-row");
  titleRow.appendChild(el("h3", "evidence-title", `Claim ${result.claim_id || ""}`.trim()));
  const tag = liveTag(result.live);
  if (tag) titleRow.appendChild(tag);
  heading.appendChild(titleRow);
  const post = result.post || {};
  const who = [post.speaker, post.platform, formatDate(post.date)].filter(Boolean).join(", ");
  if (who) heading.appendChild(el("p", "meta-line", who));
  if (post.is_excerpt) heading.appendChild(el("p", "meta-line", "excerpt"));
  if (post.original_url === "TODO") heading.appendChild(el("p", "pending-link", "Original link pending"));
  top.appendChild(heading);
  const verdict = result.verdict || "not_checkable";
  top.appendChild(el("span", `stamp ${verdict}`, VERDICT_TEXT[verdict] || verdict));
  block.appendChild(top);
  changedNote(block, result.live_changed);

  if (post.verbatim_text) {
    const excerpt = el("p", "post-text");
    highlight(excerpt, post.verbatim_text, result.claimed_phrase);
    block.appendChild(excerpt);
  }
  if (result.evidence_quote) block.appendChild(el("blockquote", "record", result.evidence_quote));
  if (result.arithmetic) block.appendChild(el("p", "arithmetic", commaIntegers(result.arithmetic)));
  if (result.reason) block.appendChild(el("p", "rule", result.reason));
  if (result.checked_against) {
    const line = el("p", "checked");
    if (result.source_url) appendLink(line, result.source_url, result.checked_against);
    else line.textContent = result.checked_against;
    block.appendChild(line);
  }
  if (result.context_note) {
    const box = el("div", "context");
    box.appendChild(el("p", "rule", result.context_note));
    block.appendChild(box);
  }
  parent.appendChild(block);
}

function renderOfficial(parent, result) {
  const block = el("section", "evidence-block");
  block.appendChild(el("h3", "evidence-title", sideName(result.side)));
  const meta = el("p", "meta-line");
  meta.textContent = [formatDate(result.published)].filter(Boolean).join("");
  const tag = liveTag(result.live);
  if (tag) meta.appendChild(tag);
  if (meta.childNodes.length) block.appendChild(meta);
  if (result.url) {
    const line = el("p", "source-line");
    appendLink(line, result.url, "Link");
    block.appendChild(line);
  }
  changedNote(block, result.live_changed);
  const paragraphs = Array.isArray(result.paragraphs) ? result.paragraphs : [];
  paragraphs.forEach((paragraph) => {
    const text = typeof paragraph === "string" ? paragraph : paragraph && paragraph.text;
    if (text) block.appendChild(el("p", "words", text));
  });
  parent.appendChild(block);
}

function renderPress(parent, result) {
  const block = el("section", "evidence-block");
  block.appendChild(el("h3", "evidence-title", "The Guardian"));
  (result.articles || []).forEach((article) => {
    const piece = el("article", "article");
    if (article.headline) piece.appendChild(el("p", "headline", article.headline));
    if (article.byline) piece.appendChild(el("p", "byline", article.byline));
    const meta = el("p", "meta-line");
    if (article.published) meta.appendChild(document.createTextNode(formatDate(article.published)));
    if (article.url) {
      if (meta.childNodes.length) meta.appendChild(document.createTextNode(" · "));
      appendLink(meta, article.url, "Link");
    }
    if (meta.childNodes.length) piece.appendChild(meta);
    (article.paragraphs || []).forEach((paragraph) => {
      const text = typeof paragraph === "string" ? paragraph : paragraph && paragraph.text;
      if (text) piece.appendChild(el("p", "words", text));
    });
    block.appendChild(piece);
  });
  parent.appendChild(block);
}

function renderError(parent, call, parsed) {
  const block = el("section", "evidence-block");
  block.appendChild(el("h3", "evidence-title", call.name || "Tool"));
  block.appendChild(el("p", "calm-error", parsed.error || "This source could not be loaded."));
  parent.appendChild(block);
}

function renderEvidence(parent, calls) {
  parent.replaceChildren();
  let shown = 0;
  (calls || []).forEach((call) => {
    const parsed = parseResult(call);
    if (parsed.error) {
      renderError(parent, call, parsed);
      shown += 1;
      return;
    }
    if (call.name === "compare_statements") {
      renderComparison(parent, parsed, call.args || {});
      shown += 1;
    } else if (call.name === "check_claim") {
      renderClaim(parent, parsed);
      shown += 1;
    } else if (call.name === "get_official_source") {
      renderOfficial(parent, parsed);
      shown += 1;
    } else if (call.name === "get_press_coverage") {
      renderPress(parent, parsed);
      shown += 1;
    }
  });
  if (!shown) {
    const text = (calls || []).length
      ? "This answer didn't quote a source."
      : "This answer didn't use any sources";
    parent.appendChild(el("p", "note", text));
  }
}

function renderTrail(parent, calls, onSelect) {
  parent.replaceChildren();
  const list = calls || [];
  const count = list.length;
  const caption = count === 0
    ? "No sources used"
    : `How I got this · ${count} ${count === 1 ? "step" : "steps"} · tap a step to inspect`;
  parent.appendChild(el("p", "trail-caption", caption));
  if (!count) return;

  const steps = el("div", "trail-steps");
  const dumps = el("div", "trail-dumps");
  list.forEach((call, index) => {
    if (index) steps.appendChild(el("span", "arrow", "→"));
    const parsed = parseResult(call);
    const button = el("button", "chip");
    button.type = "button";
    button.title = "View arguments and result";
    const failed = Boolean(parsed.error);
    button.appendChild(el("span", failed ? "mark bad" : "mark ok", failed ? "!" : "✓"));
    button.appendChild(document.createTextNode(trailLabel(call, parsed)));
    button.appendChild(el("span", "chevron", "›"));
    const dump = el("pre", "dump");
    dump.hidden = true;
    const argsText = JSON.stringify(call.args || {}, null, 2);
    let resultText = call.result;
    try {
      resultText = JSON.stringify(JSON.parse(call.result), null, 2);
    } catch (err) {
      resultText = String(call.result);
    }
    dump.textContent = `${argsText}\n\n${resultText}`;
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = dump.hidden;
      dump.hidden = !open;
      button.classList.toggle("open", open);
      onSelect();
    });
    steps.appendChild(button);
    dumps.appendChild(dump);
  });
  parent.append(steps, dumps);
}

function selectTurn(turn) {
  document.querySelectorAll(".turn.selected").forEach((node) => node.classList.remove("selected"));
  turn.classList.add("selected");
  panelKicker.textContent = "Showing evidence for";
  panelQuestion.textContent = turn.dataset.question || "";
  renderEvidence(panelBody, turn._calls || []);
}

function appendTurn(question, data) {
  const turn = el("article", "turn");
  turn.dataset.question = question;
  turn._calls = data.tool_calls || [];
  turn.appendChild(el("p", "user-line", question));
  const assistant = el("div", "assistant");
  const body = el("div", "markdown");
  body.innerHTML = renderMarkdown(data.response || "");
  const trail = el("div", "trail");
  assistant.append(trail, body);
  assistant.addEventListener("click", () => selectTurn(turn));
  const inline = el("div", "inline-evidence");
  renderTrail(trail, turn._calls, () => selectTurn(turn));
  renderEvidence(inline, turn._calls);
  turn.append(assistant, inline);
  messages.appendChild(turn);
  selectTurn(turn);
  messages.scrollTop = messages.scrollHeight;
}

function setBusy(isBusy) {
  busy = isBusy;
  sendButton.disabled = isBusy;
  input.disabled = isBusy;
}

async function send(message) {
  const question = (message || "").trim();
  if (!question || busy) return;
  if (empty) empty.remove();
  input.value = "";
  const pending = el("p", "pending", "Checking sources...");
  messages.appendChild(pending);
  messages.scrollTop = messages.scrollHeight;
  setBusy(true);
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, session_id: sessionId }),
    });
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json();
    sessionId = data.session_id || sessionId;
    pending.remove();
    appendTurn(question, data);
  } catch (err) {
    pending.remove();
    const turn = el("article", "turn");
    turn.appendChild(el("p", "user-line", question));
    turn.appendChild(el("p", "calm-error", "The request failed. Try sending it again."));
    messages.appendChild(turn);
    messages.scrollTop = messages.scrollHeight;
  } finally {
    setBusy(false);
    input.focus();
  }
}

SAMPLES.forEach((question) => {
  const button = el("button", null, question);
  button.type = "button";
  button.addEventListener("click", () => send(question));
  samples.appendChild(button);
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  send(input.value);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send(input.value);
  }
});
