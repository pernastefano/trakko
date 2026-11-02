import {
  addDays,
  addMonths,
  diffDays,
  formatDay,
  formatShortDate,
  formatShortMonth,
  startOfMonth,
  startOfWeek,
  weekdayIndex,
} from "./dates.js";
import { svg } from "./dom.js";

const BAR_WIDTH = 360;
const BAR_HEIGHT = 170;
const BAR_TOP = 20;
const BAR_BOTTOM = 24;
const BAR_SIDE = 8;
const MAX_BAR_PX = 40;
const MAX_LABELS = 8;
const MAX_VALUE_LABELS = 16;

const HEAT_CELL = 10;
const HEAT_STEP = 12;
const HEAT_LABEL_HEIGHT = 14;
const HEAT_LABELS_FROM_COLUMNS = 8;
const HEAT_MIN_CELL_PX = 9;
const HEAT_MAX_CELL_PX = 28;

/**
 * Bar chart of `buckets` ({ start, count }) as inline SVG.
 * `granularity` is "week" or "month"; `withYear` adds the year to month labels.
 */
export function createBarChart(buckets, granularity, { withYear = false } = {}) {
  const plotHeight = BAR_HEIGHT - BAR_TOP - BAR_BOTTOM;
  const baseline = BAR_TOP + plotHeight;
  const maxCount = Math.max(1, ...buckets.map((bucket) => bucket.count));
  const step = (BAR_WIDTH - 2 * BAR_SIDE) / buckets.length;
  const barWidth = Math.min(step * 0.7, MAX_BAR_PX);
  const labelEvery = Math.ceil(buckets.length / MAX_LABELS);
  const label = (bucket) =>
    granularity === "week"
      ? formatShortDate(bucket.start)
      : formatShortMonth(bucket.start, withYear);

  const summary = buckets.map((bucket) => `${label(bucket)}: ${bucket.count}`).join(", ");
  const chart = svg("svg", {
    class: "chart",
    viewBox: `0 0 ${BAR_WIDTH} ${BAR_HEIGHT}`,
    role: "img",
    "aria-label": `Entries per ${granularity}. ${summary}`,
  });
  chart.append(
    svg("line", {
      class: "chart-axis",
      x1: BAR_SIDE,
      x2: BAR_WIDTH - BAR_SIDE,
      y1: baseline,
      y2: baseline,
    }),
  );

  buckets.forEach((bucket, index) => {
    const centre = BAR_SIDE + step * (index + 0.5);
    const height = (bucket.count / maxCount) * plotHeight;
    if (bucket.count > 0) {
      chart.append(
        svg("rect", {
          class: "chart-bar",
          x: centre - barWidth / 2,
          y: baseline - height,
          width: barWidth,
          height,
          rx: 2,
        }),
      );
      if (buckets.length <= MAX_VALUE_LABELS) {
        chart.append(
          svg(
            "text",
            { class: "chart-value", x: centre, y: baseline - height - 4, "text-anchor": "middle" },
            String(bucket.count),
          ),
        );
      }
    }
    if (index % labelEvery === 0) {
      chart.append(
        svg(
          "text",
          { class: "chart-text", x: centre, y: BAR_HEIGHT - 8, "text-anchor": "middle" },
          label(bucket),
        ),
      );
    }
  });
  return chart;
}

function heatLevel(count, maxCount) {
  if (count === 0) return 0;
  const ratio = count / maxCount;
  if (ratio <= 0.25) return 1;
  if (ratio <= 0.5) return 2;
  if (ratio <= 0.75) return 3;
  return 4;
}

/**
 * Activity heatmap: one square per day from `start` to `end`, a column per week (Monday first),
 * shaded by the number of entries (`days` is a list of { date, count }).
 */
export function createHeatmap(days, start, end) {
  const counts = new Map(days.map((day) => [day.date, day.count]));
  const maxCount = Math.max(1, ...days.map((day) => day.count));
  const firstMonday = startOfWeek(start);
  const columns = Math.floor(diffDays(firstMonday, end) / 7) + 1;
  const total = diffDays(start, end) + 1;

  const showMonths = columns >= HEAT_LABELS_FROM_COLUMNS;
  const top = showMonths ? HEAT_LABEL_HEIGHT : 0;
  const gap = HEAT_STEP - HEAT_CELL;
  const chart = svg("svg", {
    class: "chart",
    viewBox: `0 0 ${columns * HEAT_STEP - gap} ${top + 7 * HEAT_STEP - gap}`,
    role: "img",
    "aria-label": `Activity heatmap: ${days.length} active ${days.length === 1 ? "day" : "days"}`,
  });
  chart.style.minWidth = `${columns * HEAT_MIN_CELL_PX}px`;
  chart.style.maxWidth = `${columns * HEAT_MAX_CELL_PX}px`;

  for (let offset = 0; offset < total; offset += 1) {
    const date = addDays(start, offset);
    const count = counts.get(date) ?? 0;
    const level = heatLevel(count, maxCount);
    const cell = svg("rect", {
      class: level === 0 ? "heat heat-0" : `heat heat-${level}`,
      x: Math.floor(diffDays(firstMonday, date) / 7) * HEAT_STEP,
      y: top + weekdayIndex(date) * HEAT_STEP,
      width: HEAT_CELL,
      height: HEAT_CELL,
      rx: 2,
    });
    cell.append(svg("title", {}, `${formatDay(date)}: ${count} ${count === 1 ? "entry" : "entries"}`));
    chart.append(cell);
  }
  if (showMonths) {
    for (const first of monthStarts(start, end)) {
      const column = Math.floor(diffDays(firstMonday, first) / 7);
      chart.append(
        svg("text", { class: "chart-text", x: column * HEAT_STEP, y: 9 }, formatShortMonth(first)),
      );
    }
  }
  return chart;
}

/** First day of every month that starts within [start, end]. */
function monthStarts(start, end) {
  const starts = [];
  let cursor = start.slice(8) === "01" ? start : addMonths(startOfMonth(start), 1);
  while (cursor <= end) {
    starts.push(cursor);
    cursor = addMonths(cursor, 1);
  }
  return starts;
}
