/** Equipped item with wiki-sourced effect text when known. */
export interface EquipmentEntry {
  item_id: string;
  effect: string | null;
  /** Wiki-hosted ITEM_*.svg URL when known. */
  icon_url: string | null;
  /** Wiki Items table Slot column when known (Weapon, Head, Trinket, …). */
  slot: string | null;
}

export interface SaveCat {
  db_key: number;
  name: string;
  level: number;
  age: number;
  gender: string;
  active_class: string;
  base_str: number;
  base_dex: number;
  base_con: number;
  base_int: number;
  base_spd: number;
  base_cha: number;
  base_lck: number;
  abilities: string[];
  passives: string[];
  /** Up to five equipped item ids from the save (heuristic parse; DefaultMove layout leaves empty). */
  equipment: EquipmentEntry[];
  status: string;
  breed_coefficient: number;
  retired: boolean;
  aggression: number | null;
  libido: number | null;
  inbredness: number | null;
  disorders: string[];
  visual_mutation_ids: number[];
  parent_a_key: number;
  parent_b_key: number;
  children_keys: number[];
  lover_keys: number[];
  hater_keys: number[];
  generation: number;
  room: string;
}

export interface RoomStats {
  appeal: number;
  comfort: number;
  effective_comfort: number;
  stimulation: number;
  health: number;
  mutation: number;
  cat_count: number;
  furniture_count: number;
}

export interface SaveData {
  cats: SaveCat[];
  house_cat_keys: number[];
  unlocked_classes: string[];
  current_day: number;
  house_gold: number;
}

export interface CollarDef {
  name: string;
  color: string;
  modifiers: Record<string, number>;
  score_weights: number[];
}

export interface TeamSlot {
  cat: SaveCat;
  collar_name: string;
  score: number;
  explanation?: string;
}

export interface RosterEntry {
  cat: SaveCat;
  scores: number[];
  best_idx: number;
  best_score: number;
}

export const STAT_ORDER = ['str', 'dex', 'con', 'int', 'spd', 'cha', 'lck'] as const;
export const STAT_LABELS = ['STR', 'DEX', 'CON', 'INT', 'SPD', 'CHA', 'LCK'] as const;

export type StatKey = (typeof STAT_ORDER)[number];

export const STAT_COLORS: Record<StatKey, string> = {
  str: '#C13128',
  dex: '#E8A524',
  con: '#3B7A57',
  int: '#4A90E2',
  spd: '#D4A017',
  cha: '#C17070',
  lck: '#5E7A3A',
};
