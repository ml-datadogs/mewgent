import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { AiCircleProgress } from '@/components/AiCircleProgress';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import { STAT_ORDER, STAT_LABELS, STAT_COLORS } from '@/types';
import type { SaveCat, RoomStats, StatKey } from '@/types';
import {
  getBreedingAdvice,
  getRoomDistribution,
  getOverallRankings,
  suggestDistributionLlm,
  onDistributionResult,
  type BreedingAdvice,
  type PairRanking,
  type RoomAssignment,
  type RoomDistribution,
  type DistributionResult,
} from '@/bridge';

interface BreedingPanelProps {
  cats: SaveCat[];
  roomStats: Record<string, RoomStats>;
  llmAvailable: boolean;
  bridgeConnected: boolean;
}

const ROOM_DISPLAY: Record<string, string> = {
  Floor1_Large: 'Ground Floor Left',
  Floor1_Small: 'Ground Floor Right',
  Floor2_Large: '2nd Floor Right',
  Floor2_Small: '2nd Floor Left',
  Attic: 'Attic',
};

const CARD_TILTS = [-0.8, 0.6, -0.4, 0.7, -0.5];

function roomDisplayName(room: string): string {
  return ROOM_DISPLAY[room] ?? (room || 'Unknown');
}

// ── Sub-components ──────────────────────────────────────────────────

function ScoreBadge({ value }: { value: number }) {
  const animated = useAnimatedNumber(value);
  return (
    <div
      className="sketchy-frame flex items-center justify-center rounded-sm px-1.5 py-0.5"
      style={{ background: 'rgba(255,255,255,0.35)' }}
    >
      <span className="font-mono text-[11px] font-bold text-accent tabular-nums leading-none">
        {animated}
      </span>
    </div>
  );
}

function InbreedingBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    none: 'text-good',
    low: 'text-medium',
    moderate: 'text-accent',
    high: 'text-poor',
  };
  return (
    <span className={`font-mono text-[10px] font-bold ${colors[level] ?? 'text-text-dim'}`}>
      {level === 'none' ? 'Clean' : level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  );
}

function StatInheritanceGrid({ advice }: { advice: BreedingAdvice }) {
  const left = STAT_ORDER.slice(0, 4);
  const right = STAT_ORDER.slice(4);

  function renderStat(key: string, i: number) {
    const prob = advice.stat_high_probs[key] ?? 0.5;
    const expected = advice.expected_stats[key] ?? 0;
    const color = STAT_COLORS[key as StatKey];
    const isHigh = prob > 0.6;

    return (
      <motion.div
        key={key}
        initial={{ opacity: 0, x: -4 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.15, delay: i * 0.03 }}
        className="flex items-center justify-between gap-1 px-1 py-px rounded-sm"
        style={{
          backgroundColor: isHigh ? `color-mix(in srgb, ${color} 12%, transparent)` : undefined,
        }}
      >
        <span
          className="text-[8px] font-mono font-bold leading-none tracking-wider"
          style={{ color: isHigh ? color : 'var(--color-text-dim)', opacity: isHigh ? 1 : 0.55 }}
        >
          {STAT_LABELS[i]}
        </span>
        <div className="flex items-center gap-1">
          <span
            className="text-[10px] font-mono font-bold tabular-nums leading-none"
            style={{ color: isHigh ? color : 'var(--color-text)' }}
          >
            {expected.toFixed(1)}
          </span>
          <span className="text-[8px] font-mono text-text-dim tabular-nums">
            {Math.round(prob * 100)}%
          </span>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-0">
      <div className="flex flex-col gap-0.5">
        {left.map((key, i) => renderStat(key, i))}
      </div>
      <div className="flex flex-col gap-0.5">
        {right.map((key, i) => renderStat(key, i + 4))}
      </div>
    </div>
  );
}

function AbilityChances({ advice }: { advice: BreedingAdvice }) {
  const items = [
    { label: '1st Active', value: advice.first_active_chance, guaranteed: advice.first_active_chance >= 1 },
    { label: 'Passive', value: advice.passive_chance, guaranteed: advice.passive_chance >= 1 },
    { label: '2nd Active', value: advice.second_active_chance, guaranteed: advice.second_active_chance >= 1 },
  ];

  return (
    <div className="flex gap-1.5">
      {items.map((item) => (
        <div
          key={item.label}
          className="sketchy-frame rounded-sm px-1.5 py-1 flex-1 text-center"
          style={{ background: item.guaranteed ? 'rgba(94,122,58,0.1)' : 'rgba(255,255,255,0.3)' }}
        >
          <div className="text-[8px] font-mono font-bold text-text-dim tracking-wider">{item.label}</div>
          <div className={`text-[11px] font-mono font-bold tabular-nums ${item.guaranteed ? 'text-good' : 'text-text'}`}>
            {Math.round(item.value * 100)}%
          </div>
        </div>
      ))}
      {advice.class_bias_chance > 0 && (
        <div
          className="sketchy-frame rounded-sm px-1.5 py-1 flex-1 text-center"
          style={{ background: advice.class_bias_chance >= 1 ? 'rgba(160,128,80,0.1)' : 'rgba(255,255,255,0.3)' }}
        >
          <div className="text-[8px] font-mono font-bold text-text-dim tracking-wider">Class Bias</div>
          <div className="text-[11px] font-mono font-bold tabular-nums text-accent">
            {Math.round(advice.class_bias_chance * 100)}%
          </div>
        </div>
      )}
    </div>
  );
}

function InbreedingDetail({ advice }: { advice: BreedingAdvice }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex items-center gap-1">
        <span className="text-[9px] text-text-dim">Risk:</span>
        <InbreedingBadge level={advice.inbreeding_warning} />
      </div>
      <div className="flex gap-1.5">
        <span className="text-[8px] font-mono text-text-dim">
          {advice.cat_a_name.split(' ')[0]}: {(advice.parent_a_coeff * 100).toFixed(1)}%
        </span>
        <span className="text-[8px] font-mono text-text-dim">
          {advice.cat_b_name.split(' ')[0]}: {(advice.parent_b_coeff * 100).toFixed(1)}%
        </span>
      </div>
      {advice.birth_defect_disorder_chance > 0.02 && (
        <span className="text-[8px] font-mono text-poor">
          Defect: {Math.round(advice.birth_defect_disorder_chance * 100)}%
        </span>
      )}
    </div>
  );
}

function DisorderSection({ catA, catB }: { catA: SaveCat; catB: SaveCat }) {
  const aDisorders = catA.disorders ?? [];
  const bDisorders = catB.disorders ?? [];
  if (aDisorders.length === 0 && bDisorders.length === 0) return null;

  return (
    <div className="space-y-0.5">
      <div className="text-[8px] font-mono font-bold text-text-dim tracking-wider">DISORDERS (15% inherit each)</div>
      {aDisorders.length > 0 && (
        <div className="text-[9px] text-text-dim">
          {catA.name}: {aDisorders.join(', ')}
        </div>
      )}
      {bDisorders.length > 0 && (
        <div className="text-[9px] text-text-dim">
          {catB.name}: {bDisorders.join(', ')}
        </div>
      )}
    </div>
  );
}

function RoomContext({ advice }: { advice: BreedingAdvice }) {
  if (!advice.room_context) return null;
  const ctx = advice.room_context as { room_name: string; stimulation: number; comfort: number };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-[8px] font-mono font-bold text-text-dim tracking-wider">ROOM</span>
      <span className="text-[9px] font-mono text-text">{roomDisplayName(ctx.room_name)}</span>
      <span className="text-[8px] font-mono text-text-dim">Stim={ctx.stimulation}</span>
      <span className="text-[8px] font-mono text-text-dim">Comfort={ctx.comfort}</span>
      {advice.comfort_breeding_odds && (
        <span className="text-[8px] font-mono text-accent">Breed odds: {advice.comfort_breeding_odds}</span>
      )}
    </div>
  );
}

function FamilyInfo({ cat, allCats }: { cat: SaveCat; allCats: SaveCat[] }) {
  const parentA = cat.parent_a_key ? allCats.find((c) => c.db_key === cat.parent_a_key) : null;
  const parentB = cat.parent_b_key ? allCats.find((c) => c.db_key === cat.parent_b_key) : null;
  const childCount = cat.children_keys?.length ?? 0;
  if (!parentA && !parentB && childCount === 0) return null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {(parentA || parentB) && (
        <span className="text-[8px] font-mono text-text-dim">
          Parents: {parentA?.name ?? '?'} + {parentB?.name ?? '?'}
        </span>
      )}
      {childCount > 0 && (
        <span className="text-[8px] font-mono text-text-dim">
          Children: {childCount}
        </span>
      )}
      <span className="text-[8px] font-mono text-text-dim">
        Gen {cat.generation}
      </span>
    </div>
  );
}

// ── Advice detail card ───────────────────────────────────────────────

function AdviceDetail({ advice, cats }: { advice: BreedingAdvice; cats: SaveCat[] }) {
  const catA = cats.find((c) => c.db_key === advice.cat_a_key);
  const catB = cats.find((c) => c.db_key === advice.cat_b_key);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="parchment-card card-tape sketchy-border rounded-lg overflow-hidden"
    >
      <div className="px-2.5 pt-3 pb-2 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-serif font-bold text-text">
            {advice.cat_a_name} &times; {advice.cat_b_name}
          </span>
          <span className="text-[9px] font-mono text-accent">Stim {advice.stimulation}</span>
        </div>

        <StatInheritanceGrid advice={advice} />

        <AbilityChances advice={advice} />

        <div
          className="h-px mx-1"
          style={{
            background: 'repeating-linear-gradient(90deg, var(--color-border-subtle) 0px, var(--color-border-subtle) 3px, transparent 3px, transparent 6px)',
          }}
        />

        <InbreedingDetail advice={advice} />

        {catA && catB && <DisorderSection catA={catA} catB={catB} />}

        <RoomContext advice={advice} />

        {catA && <FamilyInfo cat={catA} allCats={cats} />}
        {catB && <FamilyInfo cat={catB} allCats={cats} />}

        {advice.tips && advice.tips.length > 0 && (
          <>
            <div
              className="h-px mx-1"
              style={{
                background: 'repeating-linear-gradient(90deg, var(--color-border-subtle) 0px, var(--color-border-subtle) 3px, transparent 3px, transparent 6px)',
              }}
            />
            <div className="space-y-0.5">
              {advice.tips.map((tip, i) => (
                <div key={i} className="text-[9px] text-text-dim italic leading-tight px-0.5">
                  &bull; {tip}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}

// ── Cat mini badge for room cards ────────────────────────────────────

function CatBadge({ cat }: { cat: SaveCat }) {
  const genderIcon = cat.gender === 'male' ? '\u2642' : '\u2640';
  const genderColor = cat.gender === 'male' ? 'var(--color-stat-int)' : 'var(--color-stat-cha)';
  const inbredLevel = cat.breed_coefficient <= 0.05 ? 'none'
    : cat.breed_coefficient < 0.15 ? 'low'
    : cat.breed_coefficient < 0.4 ? 'moderate' : 'high';

  return (
    <div
      className="sketchy-frame rounded-sm px-1.5 py-1 flex items-center gap-1.5"
      style={{ background: 'rgba(255,255,255,0.3)' }}
    >
      <span className="text-[10px] leading-none" style={{ color: genderColor }}>
        {genderIcon}
      </span>
      <span className="text-[10px] font-serif font-bold text-text truncate max-w-[80px]">
        {cat.name}
      </span>
      <span className="text-[8px] font-mono text-text-dim">G{cat.generation}</span>
      {inbredLevel !== 'none' && (
        <InbreedingBadge level={inbredLevel} />
      )}
    </div>
  );
}

// ── Room stat icons ──────────────────────────────────────────────────

const ROOM_STAT_ICONS: { key: keyof RoomStats; label: string; color: string }[] = [
  { key: 'stimulation', label: 'STM', color: 'var(--color-stat-int)' },
  { key: 'comfort', label: 'CMF', color: 'var(--color-stat-con)' },
  { key: 'health', label: 'HLT', color: 'var(--color-stat-lck)' },
  { key: 'mutation', label: 'MUT', color: 'var(--color-stat-dex)' },
];

// ── Room card ────────────────────────────────────────────────────────

function RoomCard({
  roomName,
  stats,
  assignment,
  cats,
  index,
  isSelectedRoom,
  onPairClick,
}: {
  roomName: string;
  stats: RoomStats;
  assignment?: RoomAssignment;
  cats: SaveCat[];
  index: number;
  isSelectedRoom: boolean;
  onPairClick: (aKey: number, bKey: number) => void;
}) {
  const tilt = CARD_TILTS[index % CARD_TILTS.length];
  const roomCats = cats.filter((c) => c.room === roomName);
  const assignedKeys = assignment?.cat_keys ?? [];
  const displayCats = assignedKeys.length > 0
    ? assignedKeys.map((k) => cats.find((c) => c.db_key === k)).filter(Boolean) as SaveCat[]
    : roomCats;

  const hasPair = assignment?.best_pair != null;
  const comfortWarning = stats.cat_count > 4;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 26, delay: index * 0.06 }}
      className={`parchment-card sketchy-border rounded-lg overflow-hidden ${
        isSelectedRoom ? 'ring-1 ring-good/40' : ''
      }`}
      style={{ transform: `rotate(${tilt * 0.3}deg)` }}
    >
      <div className="px-2.5 py-2 space-y-1.5">
        {/* Room header */}
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-serif font-bold text-text truncate">
            {roomDisplayName(roomName)}
          </span>
          <div className="flex items-center gap-1.5">
            <span className={`text-[8px] font-mono ${comfortWarning ? 'text-poor font-bold' : 'text-text-dim'}`}>
              {stats.cat_count} cat{stats.cat_count !== 1 ? 's' : ''}
              {comfortWarning && ' \u26a0'}
            </span>
          </div>
        </div>

        {/* Room stats */}
        <div className="flex gap-1">
          {ROOM_STAT_ICONS.map(({ key, label, color }) => (
            <div key={key} className="text-center flex-1">
              <div className="text-[7px] font-mono font-bold tracking-wider" style={{ color }}>{label}</div>
              <div className="text-[10px] font-mono font-bold tabular-nums text-text">
                {stats[key]}
              </div>
            </div>
          ))}
        </div>

        {/* Comfort breeding odds */}
        {assignment?.comfort_breeding_odds && (
          <div className="text-[8px] font-mono text-text-dim">
            Breed odds: <span className="text-accent">{assignment.comfort_breeding_odds}</span>
          </div>
        )}

        {/* Cat list */}
        {displayCats.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {displayCats.map((cat) => (
              <CatBadge key={cat.db_key} cat={cat} />
            ))}
          </div>
        ) : (
          <div className="text-[9px] font-mono text-text-dim opacity-50 py-1">
            No cats
          </div>
        )}

        {/* Best pair highlight */}
        {hasPair && assignment?.best_pair && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            whileHover={{
              scale: 1.01,
              boxShadow: '0 3px 10px rgba(0,0,0,0.08)',
              transition: { duration: 0.15 },
            }}
            onClick={() => onPairClick(assignment.best_pair![0], assignment.best_pair![1])}
            className="w-full sketchy-frame rounded-sm px-2 py-1.5 cursor-pointer text-left transition-colors"
            style={{
              background: isSelectedRoom
                ? 'rgba(94,122,58,0.1)'
                : 'rgba(255,255,255,0.4)',
            }}
          >
            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1 min-w-0">
                <span className="text-[8px] font-mono font-bold text-good tracking-wider shrink-0">BEST</span>
                <span className="text-[10px] font-serif font-bold text-text truncate">
                  {cats.find((c) => c.db_key === assignment.best_pair![0])?.name ?? '?'}
                </span>
                <span className="text-[8px] text-text-dim">&times;</span>
                <span className="text-[10px] font-serif font-bold text-text truncate">
                  {cats.find((c) => c.db_key === assignment.best_pair![1])?.name ?? '?'}
                </span>
              </div>
              <ScoreBadge value={assignment.pair_score} />
            </div>
            {assignment.pair_reason && (
              <p className="text-[8px] text-text-dim italic leading-snug mt-0.5">
                {assignment.pair_reason}
              </p>
            )}
          </motion.button>
        )}
      </div>
    </motion.div>
  );
}

// ── Main panel ────────────────────────────────────────────────────

export function BreedingPanel({ cats, roomStats, llmAvailable, bridgeConnected }: BreedingPanelProps) {
  const [distribution, setDistribution] = useState<RoomDistribution | null>(null);
  const [selectedPair, setSelectedPair] = useState<{ a: number; b: number } | null>(null);
  const [advice, setAdvice] = useState<BreedingAdvice | null>(null);
  const [loading, setLoading] = useState(false);
  const [rankings, setRankings] = useState<PairRanking[]>([]);
  const signalConnected = useRef(false);

  useEffect(() => {
    if (signalConnected.current) return;
    signalConnected.current = true;
    onDistributionResult((result: DistributionResult) => {
      setLoading(false);
      if (result.distribution) {
        setDistribution(result.distribution);
      }
    });
  }, []);

  const handleOptimize = useCallback(async () => {
    setLoading(true);
    setAdvice(null);
    setSelectedPair(null);
    try {
      const [dist, ranks] = await Promise.all([
        getRoomDistribution(),
        getOverallRankings(),
      ]);
      setDistribution(dist);
      setRankings(ranks);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAiOptimize = useCallback(() => {
    setLoading(true);
    setAdvice(null);
    setSelectedPair(null);
    suggestDistributionLlm();
  }, []);

  const handlePairClick = useCallback(async (aKey: number, bKey: number) => {
    setSelectedPair({ a: aKey, b: bKey });
    const result = await getBreedingAdvice(aKey, bKey, 0);
    setAdvice(result);
  }, []);

  if (cats.length < 2) {
    return (
      <div className="parchment-empty rounded-lg flex items-center justify-center h-[160px]">
        <span className="text-[10px] font-mono font-bold text-text-dim tracking-wider opacity-50">
          Need at least 2 cats to analyze breeding
        </span>
      </div>
    );
  }

  const roomNames = Object.keys(roomStats);
  const assignmentByRoom: Record<string, RoomAssignment> = {};
  if (distribution) {
    for (const ra of distribution.rooms) {
      assignmentByRoom[ra.room_name] = ra;
    }
  }

  return (
    <div className="flex flex-col gap-3 py-1">
      {/* Header + actions */}
      <div className="flex items-center gap-2 px-1">
        <span className="font-mono text-xs font-bold text-accent tracking-wider">
          BREEDING
        </span>
        <div className="flex-1" />
        <Button
          size="sm"
          onClick={handleOptimize}
          disabled={loading || !bridgeConnected}
          title={!bridgeConnected ? 'Requires Mewgent app' : undefined}
        >
          Optimize
        </Button>
        {llmAvailable && (
          <Button
            size="sm"
            variant="primary"
            onClick={handleAiOptimize}
            disabled={loading || !bridgeConnected}
            title={!bridgeConnected ? 'Requires Mewgent app' : undefined}
          >
            AI Optimize
          </Button>
        )}
      </div>

      {/* Distribution total score */}
      <AnimatePresence>
        {distribution && !loading && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 px-1"
          >
            <span className="text-[9px] font-mono font-bold text-text-dim tracking-wider">
              TOTAL BREEDING SCORE
            </span>
            <ScoreBadge value={distribution.total_score} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <AiCircleProgress active={loading} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Room cards */}
      {roomNames.length > 0 && !loading && (
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {roomNames.map((rname, i) => (
              <RoomCard
                key={rname}
                roomName={rname}
                stats={roomStats[rname]!}
                assignment={assignmentByRoom[rname]}
                cats={cats}
                index={i}
                isSelectedRoom={
                  selectedPair != null &&
                  assignmentByRoom[rname]?.best_pair != null &&
                  assignmentByRoom[rname]!.best_pair![0] === selectedPair.a &&
                  assignmentByRoom[rname]!.best_pair![1] === selectedPair.b
                }
                onPairClick={handlePairClick}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Overall pair rankings (shown after optimize) */}
      <AnimatePresence>
        {rankings.length > 0 && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-1.5"
          >
            <div className="text-[10px] font-mono font-bold text-text-dim px-1 tracking-wider">
              TOP PAIRS (ALL ROOMS)
            </div>
            {rankings.map((r, i) => (
              <motion.button
                key={`${r.cat_a_key}-${r.cat_b_key}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                whileHover={{
                  y: -1,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                  transition: { duration: 0.15 },
                }}
                onClick={() => handlePairClick(r.cat_a_key, r.cat_b_key)}
                className={`w-full parchment-card sketchy-border rounded-lg overflow-hidden text-left cursor-pointer transition-colors ${
                  selectedPair?.a === r.cat_a_key && selectedPair?.b === r.cat_b_key
                    ? 'ring-1 ring-good/40'
                    : ''
                }`}
                style={{ transform: `rotate(${CARD_TILTS[i % CARD_TILTS.length]! * 0.3}deg)` }}
              >
                <div className="px-2.5 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-text-dim w-4 shrink-0">{i + 1}.</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        <span className="text-[11px] font-serif font-bold text-text truncate">
                          {r.cat_a_name}
                        </span>
                        <span className="text-[9px] text-text-dim">&times;</span>
                        <span className="text-[11px] font-serif font-bold text-text truncate">
                          {r.cat_b_name}
                        </span>
                      </div>
                      {r.same_room && r.room_name && (
                        <span className="text-[8px] font-mono text-text-dim">
                          {roomDisplayName(r.room_name)}
                        </span>
                      )}
                    </div>
                    <ScoreBadge value={r.expected_score} />
                  </div>
                  <p className="text-[8px] text-text-dim italic leading-snug mt-0.5 pl-4">
                    {r.reason}
                  </p>
                </div>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Advice detail for selected pair */}
      <AnimatePresence>
        {advice && !loading && (
          <AdviceDetail advice={advice} cats={cats} />
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!distribution && rankings.length === 0 && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="parchment-empty rounded-lg flex items-center justify-center py-8"
        >
          <span className="text-[10px] font-mono text-text-dim opacity-60">
            Click "Optimize" to find the best cat distribution across rooms
          </span>
        </motion.div>
      )}
    </div>
  );
}
