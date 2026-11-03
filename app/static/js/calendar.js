import { listEntries, listEventTypes } from "./api.js";
import {
  WEEKDAY_LABELS,
  addDays,
  addMonths,
  dayOfMonth,
  formatDay,
  formatMonth,
  formatWeek,
  monthGrid,
  sameMonth,
  today,
  weekDays,
  weekdayName,
} from "./dates.js";
import { element } from "./dom.js";
import { createMarker } from "./markers.js";
import { onSwipe } from "./swipe.js";

const MONTH_MARKER_SLOTS = 3;

/**
 * Calendar with Day, Week and Month views for one Track at a time.
 * Tapping a day dispatches `trakko:day-tap` on the window with `{ date }`.
 */
export function createCalendar() {
  const body = document.getElementById("cal-body");
  const title = document.getElementById("cal-title");
  const viewButtons = document.querySelectorAll("[data-cal-view]");

  const state = {
    view: "month",
    anchor: today(),
    trackId: null,
    eventTypes: new Map(),
    entries: [],
    error: null,
  };
  let latestRequest = 0;

  function visibleDays() {
    if (state.view === "day") return [state.anchor];
    if (state.view === "week") return weekDays(state.anchor);
    return monthGrid(state.anchor);
  }

  function periodTitle() {
    if (state.view === "day") return formatDay(state.anchor);
    if (state.view === "week") return formatWeek(state.anchor);
    return formatMonth(state.anchor);
  }

  async function load() {
    if (state.trackId === null) return;
    const request = ++latestRequest;
    const trackId = state.trackId;
    const days = visibleDays();
    try {
      const [eventTypes, entries] = await Promise.all([
        listEventTypes(trackId),
        listEntries({ trackId, from: days[0], to: days[days.length - 1] }),
      ]);
      if (request !== latestRequest) return;
      state.eventTypes = new Map(eventTypes.map((type) => [type.id, type]));
      state.entries = entries;
      state.error = null;
    } catch (error) {
      if (request !== latestRequest) return;
      state.error = error.message || "Could not load entries.";
    }
    render();
  }

  function entriesByDate() {
    const byDate = new Map();
    for (const entry of state.entries) {
      const type = state.eventTypes.get(entry.event_type_id);
      if (!type) continue;
      if (!byDate.has(entry.date)) byDate.set(entry.date, []);
      byDate.get(entry.date).push({ entry, type });
    }
    for (const list of byDate.values()) {
      list.sort((a, b) => a.type.position - b.type.position || a.entry.id - b.entry.id);
    }
    return byDate;
  }

  function dayButton(date, items, className) {
    const button = element("button", className);
    button.type = "button";
    button.dataset.date = date;
    const count = items.length;
    const label = `${formatDay(date)}, ${count} ${count === 1 ? "entry" : "entries"}`;
    button.setAttribute("aria-label", label);
    if (date === today()) {
      button.classList.add("is-today");
      button.setAttribute("aria-current", "date");
    }
    button.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("trakko:day-tap", { detail: { date } }));
    });
    return button;
  }

  function renderMonth(byDate) {
    const grid = element("div", "month");
    for (const label of WEEKDAY_LABELS) {
      const header = element("span", "month-weekday", label);
      header.setAttribute("aria-hidden", "true");
      grid.append(header);
    }
    for (const date of monthGrid(state.anchor)) {
      const items = byDate.get(date) ?? [];
      const cell = dayButton(date, items, "month-day");
      if (!sameMonth(date, state.anchor)) cell.classList.add("is-outside");
      cell.append(element("span", "month-number", dayOfMonth(date)));

      const markers = element("span", "markers");
      const overflow = items.length > MONTH_MARKER_SLOTS;
      const shown = overflow ? items.slice(0, MONTH_MARKER_SLOTS - 1) : items;
      for (const { type } of shown) markers.append(createMarker(type));
      if (overflow) {
        markers.append(element("span", "marker-more", `+${items.length - shown.length}`));
      }
      cell.append(markers);
      grid.append(cell);
    }
    return grid;
  }

  function renderWeek(byDate) {
    const list = element("div", "week");
    for (const date of weekDays(state.anchor)) {
      const items = byDate.get(date) ?? [];
      const row = dayButton(date, items, "week-row");
      const label = element("span", "week-label");
      label.append(
        element("span", "week-weekday", weekdayName(date).slice(0, 3)),
        element("span", "week-number", dayOfMonth(date)),
      );
      const markers = element("span", "markers markers-large");
      for (const { type } of items) markers.append(createMarker(type));
      row.append(label, markers);
      list.append(row);
    }
    return list;
  }

  function renderDay(byDate) {
    const items = byDate.get(state.anchor) ?? [];
    const panel = dayButton(state.anchor, items, "day-panel");
    panel.removeAttribute("aria-label");
    if (items.length === 0) panel.append(element("span", "day-empty", "No entries"));
    for (const { entry, type } of items) {
      const row = element("span", "day-entry");
      row.append(createMarker(type), element("span", "day-entry-name", type.name));
      if (entry.note) row.append(element("span", "day-entry-note", entry.note));
      panel.append(row);
    }
    return panel;
  }

  function render() {
    title.textContent = periodTitle();
    for (const button of viewButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.calView === state.view));
    }

    if (state.error) {
      body.replaceChildren(element("p", "cal-error", state.error));
      return;
    }
    const byDate = entriesByDate();
    const views = { month: renderMonth, week: renderWeek, day: renderDay };
    body.replaceChildren(views[state.view](byDate));
  }

  function moveTo(anchor) {
    state.anchor = anchor;
    render();
    load();
  }

  function step(direction) {
    if (state.view === "month") moveTo(addMonths(state.anchor, direction));
    else moveTo(addDays(state.anchor, state.view === "week" ? 7 * direction : direction));
  }

  for (const button of viewButtons) {
    button.addEventListener("click", () => {
      state.view = button.dataset.calView;
      render();
      load();
    });
  }
  document.getElementById("cal-prev").addEventListener("click", () => step(-1));
  document.getElementById("cal-next").addEventListener("click", () => step(1));
  document.getElementById("cal-today").addEventListener("click", () => moveTo(today()));
  onSwipe(body, { onLeft: () => step(1), onRight: () => step(-1) });

  render();

  return {
    setTrack(track) {
      state.trackId = track.id;
      state.entries = [];
      state.eventTypes = new Map();
      state.error = null;
      render();
      load();
    },
    /** Show Day, Week or Month (the user's default view is applied this way at startup). */
    setView(view) {
      if (!["day", "week", "month"].includes(view) || view === state.view) return;
      state.view = view;
      render();
      load();
    },
    /** Reload the visible period, e.g. after entries were changed. */
    refresh: load,
  };
}
