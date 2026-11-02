// Calendar dates are plain "YYYY-MM-DD" strings. They are never converted through UTC or time
// zones: local Date objects are only used as a calendar to do day arithmetic.

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function pad(value, length = 2) {
  return String(value).padStart(length, "0");
}

export function parseIso(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function toIso(date) {
  return `${pad(date.getFullYear(), 4)}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function today() {
  return toIso(new Date());
}

export function addDays(iso, count) {
  const date = parseIso(iso);
  date.setDate(date.getDate() + count);
  return toIso(date);
}

/** Move by whole months, clamping the day (Jan 31 + 1 month = Feb 28/29). */
export function addMonths(iso, count) {
  const date = parseIso(iso);
  const day = date.getDate();
  date.setDate(1);
  date.setMonth(date.getMonth() + count);
  const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  date.setDate(Math.min(day, lastDay));
  return toIso(date);
}

export function startOfMonth(iso) {
  return `${iso.slice(0, 8)}01`;
}

/** Monday of the week containing `iso`. */
export function startOfWeek(iso) {
  const date = parseIso(iso);
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7));
  return toIso(date);
}

export function weekDays(iso) {
  const start = startOfWeek(iso);
  return Array.from({ length: 7 }, (_, index) => addDays(start, index));
}

/** The 6 weeks (42 days, Monday first) shown for the month containing `iso`. */
export function monthGrid(iso) {
  const start = startOfWeek(startOfMonth(iso));
  return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

export function sameMonth(a, b) {
  return a.slice(0, 7) === b.slice(0, 7);
}

export function dayOfMonth(iso) {
  return Number(iso.slice(8, 10));
}

export function weekdayName(iso) {
  return WEEKDAYS[parseIso(iso).getDay()];
}

export function formatMonth(iso) {
  return `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(0, 4))}`;
}

export function formatDay(iso) {
  const month = MONTHS[Number(iso.slice(5, 7)) - 1];
  return `${weekdayName(iso)} ${dayOfMonth(iso)} ${month} ${Number(iso.slice(0, 4))}`;
}

/** "2 – 8 Nov 2026", "28 Dec 2026 – 3 Jan 2027" or "30 Mar – 5 Apr 2026" for the week of `iso`. */
export function formatWeek(iso) {
  const days = weekDays(iso);
  const first = days[0];
  const last = days[6];
  const short = (value) => MONTHS[Number(value.slice(5, 7)) - 1].slice(0, 3);
  const year = (value) => Number(value.slice(0, 4));

  if (year(first) !== year(last)) {
    return `${dayOfMonth(first)} ${short(first)} ${year(first)} – ${dayOfMonth(last)} ${short(last)} ${year(last)}`;
  }
  if (first.slice(5, 7) !== last.slice(5, 7)) {
    return `${dayOfMonth(first)} ${short(first)} – ${dayOfMonth(last)} ${short(last)} ${year(last)}`;
  }
  return `${dayOfMonth(first)} – ${dayOfMonth(last)} ${short(last)} ${year(last)}`;
}
