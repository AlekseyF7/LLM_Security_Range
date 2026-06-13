// Local challenge progress (won challenge ids) in localStorage.
// Components subscribe to the "swiki:progress" window event to re-render.

const KEY = "swiki:challenges:won";
export const PROGRESS_EVENT = "swiki:progress";

export function getWon(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]") as string[];
  } catch {
    return [];
  }
}

export function markWon(id: string): void {
  if (typeof window === "undefined") return;
  const s = new Set(getWon());
  if (s.has(id)) return;
  s.add(id);
  localStorage.setItem(KEY, JSON.stringify([...s]));
  window.dispatchEvent(new Event(PROGRESS_EVENT));
}
