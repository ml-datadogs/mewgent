import type { CollarDef, TeamSlot, RosterEntry } from './types';

declare global {
  interface Window {
    qt?: { webChannelTransport: unknown };
    QWebChannel?: new (
      transport: unknown,
      callback: (channel: { objects: { bridge: BridgeObject } }) => void,
    ) => void;
  }
}

interface BridgeObject {
  get_roster: (cb: (json: string) => void) => void;
  get_collars: (cb: (json: string) => void) => void;
  get_team: (cb: (json: string) => void) => void;
  get_save_info: (cb: (json: string) => void) => void;
  set_team_slot: (slot: number, cat_db_key: number, collar_name: string) => void;
  remove_team_slot: (slot: number) => void;
  clear_team: () => void;
  autofill_team: () => void;
  autofill_team_llm: () => void;
  request_close: () => void;

  roster_updated: { connect: (fn: (json: string) => void) => void };
  team_updated: { connect: (fn: (json: string) => void) => void };
  save_info_updated: { connect: (fn: (json: string) => void) => void };
  llm_status_changed: { connect: (fn: (status: string) => void) => void };
  collars_updated: { connect: (fn: (json: string) => void) => void };
}

let bridge: BridgeObject | null = null;

export function initBridge(): Promise<void> {
  return new Promise((resolve) => {
    if (!window.qt?.webChannelTransport || !window.QWebChannel) {
      console.warn('QWebChannel not available — running in standalone mode');
      resolve();
      return;
    }
    new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
      bridge = channel.objects.bridge;
      resolve();
    });
  });
}

export function isConnected(): boolean {
  return bridge !== null;
}

function promiseSlot<T>(method: (cb: (json: string) => void) => void): Promise<T> {
  return new Promise((resolve) => {
    method((json: string) => {
      resolve(JSON.parse(json) as T);
    });
  });
}

export function getRoster(): Promise<RosterEntry[]> {
  if (!bridge) return Promise.resolve([]);
  return promiseSlot<RosterEntry[]>(bridge.get_roster.bind(bridge));
}

export function getCollars(): Promise<CollarDef[]> {
  if (!bridge) return Promise.resolve([]);
  return promiseSlot<CollarDef[]>(bridge.get_collars.bind(bridge));
}

export function getTeam(): Promise<(TeamSlot | null)[]> {
  if (!bridge) return Promise.resolve([null, null, null, null]);
  return promiseSlot<(TeamSlot | null)[]>(bridge.get_team.bind(bridge));
}

export function getSaveInfo(): Promise<{ day: number; cat_count: number; status: string }> {
  if (!bridge) return Promise.resolve({ day: 0, cat_count: 0, status: 'disconnected' });
  return promiseSlot(bridge.get_save_info.bind(bridge));
}

export function setTeamSlot(slot: number, catDbKey: number, collarName: string) {
  bridge?.set_team_slot(slot, catDbKey, collarName);
}

export function removeTeamSlot(slot: number) {
  bridge?.remove_team_slot(slot);
}

export function clearTeam() {
  bridge?.clear_team();
}

export function autofillTeam() {
  bridge?.autofill_team();
}

export function autofillTeamLlm() {
  bridge?.autofill_team_llm();
}

export function requestClose() {
  bridge?.request_close();
}

export function onRosterUpdated(fn: (roster: RosterEntry[]) => void) {
  bridge?.roster_updated.connect((json: string) => fn(JSON.parse(json)));
}

export function onTeamUpdated(fn: (team: (TeamSlot | null)[]) => void) {
  bridge?.team_updated.connect((json: string) => fn(JSON.parse(json)));
}

export function onSaveInfoUpdated(fn: (info: { day: number; cat_count: number; status: string }) => void) {
  bridge?.save_info_updated.connect((json: string) => fn(JSON.parse(json)));
}

export function onLlmStatusChanged(fn: (status: string) => void) {
  bridge?.llm_status_changed.connect(fn);
}

export function onCollarsUpdated(fn: (collars: CollarDef[]) => void) {
  bridge?.collars_updated.connect((json: string) => fn(JSON.parse(json)));
}
