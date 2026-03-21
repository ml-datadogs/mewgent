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
  status: string;
  breed_coefficient: number;
  retired: boolean;
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
