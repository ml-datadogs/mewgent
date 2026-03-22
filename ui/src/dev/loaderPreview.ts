/** Vite-only: simulate team LLM status so TeamPanel loader can be previewed without QWebChannel. */

let mockTeamLlmStatus = '';
const listeners = new Set<() => void>();

function notify(): void {
  for (const fn of listeners) fn();
}

export function getMockTeamLlmStatus(): string {
  return mockTeamLlmStatus;
}

export function setMockTeamLlmStatus(status: string): void {
  mockTeamLlmStatus = status;
  notify();
}

export function subscribeMockTeamLlmStatus(fn: () => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
