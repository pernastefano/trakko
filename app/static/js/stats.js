import { getStats } from "./api.js";
import { createBarChart, createHeatmap } from "./charts.js";
import { addMonths, formatMonth, today } from "./dates.js";
import { element } from "./dom.js";
import { createMarker } from "./markers.js";

function plural(count, singular, pluralForm) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

function daysAgo(days) {
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

function formatInterval(days) {
  return `${Number(days.toFixed(1))} days`;
}

function fact(label, value) {
  const wrapper = element("div");
  wrapper.append(element("dt", "", label), element("dd", "", value));
  return wrapper;
}

function eventTypeCard(stats) {
  const card = element("article", "stat-card");

  const head = element("header", "stat-head");
  const total = element("div", "stat-total");
  total.append(
    element("span", "stat-count", stats.count),
    element("span", "stat-count-label", stats.count === 1 ? "entry" : "entries"),
  );
  head.append(createMarker(stats), element("h4", "stat-name", stats.name), total);

  const facts = element("dl", "stat-facts");
  facts.append(
    fact("Last entry", stats.days_since_last === null ? "—" : daysAgo(stats.days_since_last)),
    fact("Current streak", plural(stats.current_streak, "day", "days")),
    fact("Longest streak", plural(stats.longest_streak, "day", "days")),
    fact(
      "Average interval",
      stats.average_interval_days === null ? "—" : formatInterval(stats.average_interval_days),
    ),
  );
  card.append(head, facts);
  return card;
}

function section(title) {
  const node = element("section");
  node.append(element("h3", "stats-section-title", title));
  return node;
}

function emptyMessage(text) {
  return element("p", "stats-empty", text);
}

function renderEventTypes(data) {
  const node = section("Event types");
  if (data.event_types.length === 0) {
    node.append(emptyMessage("This Track has no event types yet."));
  } else {
    node.append(...data.event_types.map(eventTypeCard));
  }
  return node;
}

function renderBars(data) {
  const node = section(`Entries per ${data.granularity}`);
  const hasEntries = data.buckets.some((bucket) => bucket.count > 0);
  node.append(
    hasEntries
      ? createBarChart(data.buckets, data.granularity, { withYear: data.period === "all" })
      : emptyMessage("No entries in this period."),
  );
  return node;
}

function renderHeatmap(data) {
  const node = section("Activity");
  if (data.heatmap.length === 0) {
    node.append(emptyMessage("No entries in this period."));
    return node;
  }
  const container = element("div", "heatmap");
  container.append(createHeatmap(data.heatmap, data.start, data.end));
  node.append(container);
  return node;
}

/**
 * Statistics screen for the current Track: a period (month, year or all time) with counts,
 * streaks, intervals, a bar chart and a heatmap. Loads only while the screen is shown.
 */
export function createStats() {
  const body = document.getElementById("stats-body");
  const title = document.getElementById("stats-title");
  const previous = document.getElementById("stats-prev");
  const next = document.getElementById("stats-next");
  const periodButtons = document.querySelectorAll("[data-stats-period]");

  const state = { period: "month", anchor: today(), trackId: null, dirty: false };
  let latestRequest = 0;

  const isShown = () => location.hash.startsWith("#/stats");

  function periodTitle() {
    if (state.period === "month") return formatMonth(state.anchor);
    if (state.period === "year") return state.anchor.slice(0, 4);
    return "All time";
  }

  function renderControls() {
    title.textContent = periodTitle();
    previous.disabled = next.disabled = state.period === "all";
    for (const button of periodButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.statsPeriod === state.period));
    }
  }

  async function load() {
    state.dirty = false;
    const request = ++latestRequest;
    try {
      const data = await getStats({
        trackId: state.trackId,
        period: state.period,
        ref: state.anchor,
        today: today(),
      });
      if (request !== latestRequest) return;
      body.replaceChildren(renderEventTypes(data), renderBars(data), renderHeatmap(data));
      // A heatmap wider than the screen scrolls; start at the most recent weeks.
      const heatmap = body.querySelector(".heatmap");
      if (heatmap) heatmap.scrollLeft = heatmap.scrollWidth;
    } catch (failure) {
      if (request !== latestRequest) return;
      const message = element("p", "cal-error", failure.message || "Could not load statistics.");
      message.setAttribute("role", "alert");
      body.replaceChildren(message);
    }
  }

  function loadIfNeeded() {
    if (state.trackId !== null && state.dirty && isShown()) load();
  }

  function invalidate() {
    state.dirty = true;
    loadIfNeeded();
  }

  function change(update) {
    Object.assign(state, update);
    renderControls();
    invalidate();
  }

  for (const button of periodButtons) {
    button.addEventListener("click", () => change({ period: button.dataset.statsPeriod }));
  }
  const step = (direction) =>
    change({ anchor: addMonths(state.anchor, state.period === "year" ? 12 * direction : direction) });
  previous.addEventListener("click", () => step(-1));
  next.addEventListener("click", () => step(1));
  window.addEventListener("hashchange", loadIfNeeded);

  renderControls();

  return {
    setTrack(track) {
      if (state.trackId !== track.id) {
        // Never leave the previous Track's numbers on screen while the new ones load, and ignore
        // an answer for the previous Track that is still on its way.
        latestRequest++;
        body.replaceChildren();
      }
      state.trackId = track.id;
      invalidate();
    },
    /** Entries or Event Types changed: reload next time the screen is (or already is) shown. */
    invalidate,
  };
}
