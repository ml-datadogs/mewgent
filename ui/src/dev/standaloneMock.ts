/**
 * Sample data for Vite-only dev (no QWebChannel). Matches shapes from the Python bridge.
 */
import type { CollarDef, RosterEntry, TeamSlot } from '@/types';

const MOCK_COLLARS: CollarDef[] = [
  {
    name: 'Fighter',
    color: '#C13128',
    modifiers: { STR: 2, SPD: 1, INT: -1 },
    score_weights: [2, 0, 0.5, 0, 1, 0, 0.25],
  },
  {
    name: 'Mage',
    color: '#4A90E2',
    modifiers: { INT: 2, CHA: 2, CON: -1, STR: -1 },
    score_weights: [0, 0, 0.25, 1.5, 0.5, 1.5, 0.25],
  },
  {
    name: 'Hunter',
    color: '#3B7A57',
    modifiers: { DEX: 3, LCK: 2, CON: -1, SPD: -2 },
    score_weights: [0, 2, 0.25, 0, 0, 0, 1.5],
  },
  {
    name: 'Cleric',
    color: '#D4A017',
    modifiers: { CHA: 2, CON: 1, STR: -1 },
    score_weights: [0, 0, 1, 0.5, 0, 2, 0.5],
  },
];

function mockCat(
  db_key: number,
  name: string,
  active_class: string,
  age: number,
  stats: [number, number, number, number, number, number, number],
): RosterEntry['cat'] {
  return {
    db_key,
    name,
    level: 8 + db_key * 2,
    age,
    gender: db_key % 2 === 0 ? 'female' : 'male',
    active_class,
    base_str: stats[0],
    base_dex: stats[1],
    base_con: stats[2],
    base_int: stats[3],
    base_spd: stats[4],
    base_cha: stats[5],
    base_lck: stats[6],
    abilities: ['Fireball', 'HealingTouch'],
    passives: ['NineLives'],
    status: 'OK',
    breed_coefficient: 0.12,
    retired: false,
  };
}

const cats: RosterEntry['cat'][] = [
  mockCat(1, 'Mittens', 'Mage', 4, [3, 2, 4, 9, 5, 8, 4]),
  mockCat(2, 'Whiskers', 'Fighter', 5, [8, 5, 7, 2, 6, 3, 3]),
  mockCat(3, 'Chairman Meow', 'Hunter', 3, [4, 9, 3, 3, 4, 2, 8]),
  mockCat(4, 'Purrlock', 'Cleric', 6, [2, 3, 6, 5, 3, 9, 5]),
  mockCat(5, 'Noodle', 'Fighter', 2, [7, 6, 5, 4, 7, 4, 5]),
];

function scoresFor(cat: RosterEntry['cat']): number[] {
  return MOCK_COLLARS.map((collar) => {
    let total = 0;
    let norm = 0;
    const stats = [
      cat.base_str, cat.base_dex, cat.base_con,
      cat.base_int, cat.base_spd, cat.base_cha, cat.base_lck,
    ];
    for (let i = 0; i < stats.length; i++) {
      const w = collar.score_weights[i] ?? 0;
      total += stats[i] * w;
      norm += Math.abs(w);
    }
    return norm > 0 ? Math.round((total / norm) * 10) / 10 : 0;
  });
}

export const STANDALONE_ROSTER: RosterEntry[] = cats.map((cat) => {
  const scores = scoresFor(cat);
  const best_idx = scores.indexOf(Math.max(...scores));
  return {
    cat,
    scores,
    best_idx,
    best_score: scores[best_idx]!,
  };
});

export const STANDALONE_COLLARS = MOCK_COLLARS;

export const STANDALONE_TEAM: (TeamSlot | null)[] = [
  {
    cat: cats[0]!,
    collar_name: 'Mage',
    score: 72,
    explanation: 'Highest INT and CHA in the roster make Mittens the ideal Mage. Strong synergy with Cleric support.',
  },
  {
    cat: cats[1]!,
    collar_name: 'Fighter',
    score: 68,
    explanation: 'Top STR and solid CON give Whiskers the best frontline durability. Pairs well with Hunter flanking.',
  },
  {
    cat: cats[2]!,
    collar_name: 'Hunter',
    score: 74,
    explanation: 'Outstanding DEX and LCK — Chairman Meow is a natural Hunter. Fills the ranged DPS role the team needs.',
  },
  {
    cat: cats[3]!,
    collar_name: 'Cleric',
    score: 65,
    explanation: 'Highest CHA plus good CON makes Purrlock a reliable healer. Completes the four-role composition.',
  },
];

export const STANDALONE_SYNERGY =
  'Balanced four-role composition: Fighter tanks, Hunter deals ranged damage, Mage controls the field, and Cleric sustains. No stat overlap between members — each cat fills a unique niche.';

export const STANDALONE_SAVE_INFO = {
  day: 42,
  cat_count: cats.length,
  status: 'Browser preview — open via Mewgent for real save + AI',
};
