import type { CollarDef, TeamSlot, RosterEntry, RoomStats, SaveCat } from './types';

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
  get_catalog: (cb: (json: string) => void) => void;
  get_collars: (cb: (json: string) => void) => void;
  get_team: (cb: (json: string) => void) => void;
  get_save_info: (cb: (json: string) => void) => void;
  set_team_slot: (slot: number, cat_db_key: number, collar_name: string) => void;
  remove_team_slot: (slot: number) => void;
  clear_team: () => void;
  autofill_team_llm: () => void;
  request_close: () => void;
  begin_drag: (screen_x: number, screen_y: number) => void;
  update_drag: (screen_x: number, screen_y: number) => void;
  end_drag: () => void;
  get_breeding_advice: (cat_a_key: number, cat_b_key: number, stimulation: number, cb: (json: string) => void) => void;
  get_breeding_rankings: (collar_name: string, stimulation: number, cb: (json: string) => void) => void;
  suggest_breeding_llm: (collar_name: string, stimulation: number) => void;
  get_room_stats: (cb: (json: string) => void) => void;
  get_room_distribution: (cb: (json: string) => void) => void;
  get_overall_rankings: (cb: (json: string) => void) => void;
  suggest_distribution_llm: () => void;

  get_update_info: (cb: (json: string) => void) => void;
  open_url: (url: string) => void;
  check_for_updates: () => void;
  get_llm_settings: (cb: (json: string) => void) => void;
  apply_llm_settings: (payload_json: string, cb: (json: string) => void) => void;
  test_llm_connection: () => void;

  roster_updated: { connect: (fn: (json: string) => void) => void };
  catalog_updated: { connect: (fn: (json: string) => void) => void };
  team_updated: { connect: (fn: (json: string) => void) => void };
  team_synergy_updated: { connect: (fn: (json: string) => void) => void };
  save_info_updated: { connect: (fn: (json: string) => void) => void };
  llm_status_changed: { connect: (fn: (status: string) => void) => void };
  collars_updated: { connect: (fn: (json: string) => void) => void };
  breeding_result: { connect: (fn: (json: string) => void) => void };
  distribution_result: { connect: (fn: (json: string) => void) => void };
  room_stats_updated: { connect: (fn: (json: string) => void) => void };
  update_available: { connect: (fn: (json: string) => void) => void };
  update_check_status: { connect: (fn: (json: string) => void) => void };
  llm_settings_changed: { connect: (fn: (json: string) => void) => void };
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

export function getCatalog(): Promise<SaveCat[]> {
  if (!bridge) return Promise.resolve([]);
  return promiseSlot<SaveCat[]>(bridge.get_catalog.bind(bridge));
}

export function getCollars(): Promise<CollarDef[]> {
  if (!bridge) return Promise.resolve([]);
  return promiseSlot<CollarDef[]>(bridge.get_collars.bind(bridge));
}

export function getTeam(): Promise<(TeamSlot | null)[]> {
  if (!bridge) return Promise.resolve([null, null, null, null]);
  return promiseSlot<(TeamSlot | null)[]>(bridge.get_team.bind(bridge));
}

export interface InventoryEntry {
  item_id: string;
  effect: string | null;
  icon_url: string | null;
  slot: string | null;
}

export interface SaveInfoInventory {
  backpack: InventoryEntry[];
  storage: InventoryEntry[];
  trash: InventoryEntry[];
}

export interface SaveInfo {
  day: number;
  cat_count: number;
  status: string;
  inventory: SaveInfoInventory;
}

const EMPTY_SAVE_INVENTORY: SaveInfoInventory = { backpack: [], storage: [], trash: [] };

export function getSaveInfo(): Promise<SaveInfo> {
  if (!bridge) {
    return Promise.resolve({
      day: 0,
      cat_count: 0,
      status: 'disconnected',
      inventory: EMPTY_SAVE_INVENTORY,
    });
  }
  return promiseSlot<SaveInfo>(bridge.get_save_info.bind(bridge));
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

export function autofillTeamLlm() {
  bridge?.autofill_team_llm();
}

export function requestClose() {
  bridge?.request_close();
}

export function beginDrag(screenX: number, screenY: number) {
  bridge?.begin_drag(Math.round(screenX), Math.round(screenY));
}

export function updateDrag(screenX: number, screenY: number) {
  bridge?.update_drag(Math.round(screenX), Math.round(screenY));
}

export function endDrag() {
  bridge?.end_drag();
}

export function onRosterUpdated(fn: (roster: RosterEntry[]) => void) {
  bridge?.roster_updated.connect((json: string) => fn(JSON.parse(json)));
}

export function onCatalogUpdated(fn: (cats: SaveCat[]) => void) {
  bridge?.catalog_updated.connect((json: string) => fn(JSON.parse(json) as SaveCat[]));
}

export function onTeamUpdated(fn: (team: (TeamSlot | null)[]) => void) {
  bridge?.team_updated.connect((json: string) => fn(JSON.parse(json)));
}

/** LLM team paragraph + suggested stash items (with wiki icon URLs from Python). */
export interface TeamStashTip {
  item_id: string;
  equip_on: string;
  reason: string;
  icon_url: string | null;
  slot: string | null;
  effect: string | null;
}

export interface TeamSynergyPayload {
  synergy: string;
  stash_tips: TeamStashTip[];
}

export const EMPTY_TEAM_SYNERGY_PAYLOAD: TeamSynergyPayload = {
  synergy: '',
  stash_tips: [],
};

export function parseTeamSynergyPayload(raw: string): TeamSynergyPayload {
  const trimmed = raw.trim();
  if (!trimmed) return EMPTY_TEAM_SYNERGY_PAYLOAD;
  try {
    const p = JSON.parse(trimmed) as Record<string, unknown>;
    if (p && typeof p === 'object' && typeof p.synergy === 'string') {
      const tips = p.stash_tips;
      const stash_tips: TeamStashTip[] = Array.isArray(tips)
        ? tips
            .filter((x): x is Record<string, unknown> => x !== null && typeof x === 'object')
            .map((x) => ({
              item_id: String(x.item_id ?? ''),
              equip_on: String(x.equip_on ?? ''),
              reason: String(x.reason ?? ''),
              icon_url: typeof x.icon_url === 'string' ? x.icon_url : null,
              slot: typeof x.slot === 'string' ? x.slot : null,
              effect: typeof x.effect === 'string' ? x.effect : null,
            }))
            .filter((t) => t.item_id.length > 0)
        : [];
      return { synergy: p.synergy, stash_tips };
    }
  } catch {
    /* legacy: plain text before JSON payload */
  }
  return { synergy: raw, stash_tips: [] };
}

export function onTeamSynergyUpdated(fn: (payload: TeamSynergyPayload) => void) {
  bridge?.team_synergy_updated.connect((json: string) => {
    fn(parseTeamSynergyPayload(json));
  });
}

export function onSaveInfoUpdated(fn: (info: SaveInfo) => void) {
  bridge?.save_info_updated.connect((json: string) => fn(JSON.parse(json) as SaveInfo));
}

export function onLlmStatusChanged(fn: (status: string) => void) {
  bridge?.llm_status_changed.connect(fn);
}

// ── LLM (BYOK + model) ───────────────────────────────────────────

export type LlmConnectionCheck = 'idle' | 'pending' | 'ok' | 'failed';

export interface LlmSettings {
  model: string;
  default_model: string;
  models: string[];
  has_saved_key: boolean;
  available: boolean;
  mock: boolean;
  enabled: boolean;
  connection_check: LlmConnectionCheck;
  connection_message: string;
}

export interface LlmApplyPayload {
  model: string;
  key_action: 'unchanged' | 'set' | 'clear';
  api_key: string;
}

const STANDALONE_LLM_MODELS = [
  'gpt-4o-mini',
  'gpt-4o',
  'gpt-4.1',
  'gpt-4.1-mini',
  'gpt-4.1-nano',
  'gpt-5.4',
  'o4-mini',
  'o3-mini',
];

export function getLlmSettings(): Promise<LlmSettings | null> {
  if (!bridge) return Promise.resolve(null);
  return new Promise((resolve) => {
    bridge!.get_llm_settings((json: string) => {
      resolve(JSON.parse(json) as LlmSettings);
    });
  });
}

export function applyLlmSettings(payload: LlmApplyPayload): Promise<{ ok: boolean; error?: string }> {
  if (!bridge) return Promise.resolve({ ok: false, error: 'disconnected' });
  return new Promise((resolve) => {
    bridge!.apply_llm_settings(JSON.stringify(payload), (json: string) => {
      resolve(JSON.parse(json) as { ok: boolean; error?: string });
    });
  });
}

export function testLlmConnection(): void {
  bridge?.test_llm_connection();
}

export function onLlmSettingsChanged(fn: (settings: LlmSettings) => void) {
  bridge?.llm_settings_changed.connect((json: string) => fn(JSON.parse(json) as LlmSettings));
}

export function standaloneLlmPreviewSettings(): LlmSettings {
  return {
    model: 'gpt-4o-mini',
    default_model: 'gpt-4o-mini',
    models: STANDALONE_LLM_MODELS,
    has_saved_key: false,
    available: false,
    mock: false,
    enabled: true,
    connection_check: 'idle',
    connection_message: '',
  };
}

export function onCollarsUpdated(fn: (collars: CollarDef[]) => void) {
  bridge?.collars_updated.connect((json: string) => fn(JSON.parse(json)));
}

// ── Update check ─────────────────────────────────────────────────

export interface UpdateInfo {
  version: string;
  url: string;
  changelog: string;
}

export function getUpdateInfo(): Promise<UpdateInfo | null> {
  if (!bridge) return Promise.resolve(null);
  return new Promise((resolve) => {
    bridge!.get_update_info((json: string) => {
      if (!json) {
        resolve(null);
        return;
      }
      resolve(JSON.parse(json) as UpdateInfo);
    });
  });
}

export function onUpdateAvailable(fn: (info: UpdateInfo) => void) {
  bridge?.update_available.connect((json: string) => fn(JSON.parse(json)));
}

export type UpdateCheckPayload =
  | { state: 'checking' }
  | { state: 'disabled' }
  | { state: 'error'; message: string }
  | { state: 'current'; current: string; latest: string }
  | { state: 'available'; version: string; url: string; changelog: string; current?: string };

export function checkForUpdates(): void {
  bridge?.check_for_updates();
}

export function onUpdateCheckStatus(fn: (payload: UpdateCheckPayload) => void) {
  bridge?.update_check_status.connect((json: string) => {
    fn(JSON.parse(json) as UpdateCheckPayload);
  });
}

export function openUrl(url: string) {
  bridge?.open_url(url);
}

// ── Breeding ──────────────────────────────────────────────────────

export interface BreedingAdvice {
  cat_a_name: string;
  cat_a_key: number;
  cat_b_name: string;
  cat_b_key: number;
  stimulation: number;
  stat_high_probs: Record<string, number>;
  first_active_chance: number;
  second_active_chance: number;
  passive_chance: number;
  expected_stats: Record<string, number>;
  inbreeding_warning: string;
  parent_a_coeff: number;
  parent_b_coeff: number;
  disorder_chance_per_parent: number;
  birth_defect_disorder_chance: number;
  birth_defect_parts_chance: number;
  class_bias_chance: number;
  comfort_breeding_odds: string | null;
  room_context: { room_name: string; stimulation: number; comfort: number } | null;
  tips: string[] | null;
}

export interface PairRanking {
  cat_a_key: number;
  cat_a_name: string;
  cat_b_key: number;
  cat_b_name: string;
  expected_score: number;
  reason: string;
  same_room: boolean;
  room_name: string;
}

export interface BreedingResult {
  source: 'calculator' | 'llm';
  pairs: PairRanking[] | Array<{ cat_a_name: string; cat_a_key: number; cat_b_name: string; cat_b_key: number; reason: string }>;
}

export function getBreedingAdvice(catAKey: number, catBKey: number, stimulation: number): Promise<BreedingAdvice | null> {
  if (!bridge) return Promise.resolve(null);
  return new Promise((resolve) => {
    bridge!.get_breeding_advice(catAKey, catBKey, stimulation, (json: string) => {
      resolve(JSON.parse(json) as BreedingAdvice | null);
    });
  });
}

export function getBreedingRankings(collarName: string, stimulation: number): Promise<PairRanking[]> {
  if (!bridge) return Promise.resolve([]);
  return new Promise((resolve) => {
    bridge!.get_breeding_rankings(collarName, stimulation, (json: string) => {
      resolve(JSON.parse(json) as PairRanking[]);
    });
  });
}

export function suggestBreedingLlm(collarName: string, stimulation: number) {
  bridge?.suggest_breeding_llm(collarName, stimulation);
}

export function onBreedingResult(fn: (result: BreedingResult) => void) {
  bridge?.breeding_result.connect((json: string) => fn(JSON.parse(json)));
}

// ── Room stats ────────────────────────────────────────────────────

export function getRoomStats(): Promise<Record<string, RoomStats>> {
  if (!bridge) return Promise.resolve({});
  return promiseSlot<Record<string, RoomStats>>(bridge.get_room_stats.bind(bridge));
}

export function onRoomStatsUpdated(fn: (stats: Record<string, RoomStats>) => void) {
  bridge?.room_stats_updated.connect((json: string) => fn(JSON.parse(json)));
}

// ── Room distribution ─────────────────────────────────────────────

export interface RoomAssignment {
  room_name: string;
  cat_keys: number[];
  best_pair: [number, number] | null;
  pair_score: number;
  pair_reason: string;
  room_stimulation: number;
  room_comfort: number;
  effective_comfort: number;
  comfort_breeding_odds: string;
}

export interface RoomDistribution {
  rooms: RoomAssignment[];
  total_score: number;
}

/** Emitted on `distribution_result`. `source` is `llm` on success, `error` when the advisor failed or was unavailable. */
export interface DistributionResult {
  source: 'calculator' | 'llm' | 'error';
  distribution: RoomDistribution | null;
  error?: string | null;
}

export function getRoomDistribution(): Promise<RoomDistribution | null> {
  if (!bridge) return Promise.resolve(null);
  return promiseSlot<RoomDistribution | null>(bridge.get_room_distribution.bind(bridge));
}

export function getOverallRankings(): Promise<PairRanking[]> {
  if (!bridge) return Promise.resolve([]);
  return promiseSlot<PairRanking[]>(bridge.get_overall_rankings.bind(bridge));
}

export function suggestDistributionLlm() {
  bridge?.suggest_distribution_llm();
}

export function onDistributionResult(fn: (result: DistributionResult) => void) {
  bridge?.distribution_result.connect((json: string) => fn(JSON.parse(json)));
}
