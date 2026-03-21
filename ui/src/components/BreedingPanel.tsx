import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ClassIcon } from '@/components/ClassIcon';
import {
  getBreedingAdvice,
  getBreedingRankings,
  suggestBreedingLlm,
  onBreedingResult,
  type BreedingAdvice,
  type PairRanking,
} from '@/bridge';
import type { SaveCat, CollarDef } from '@/types';

interface BreedingPanelProps {
  cats: SaveCat[];
  collars: CollarDef[];
  llmAvailable: boolean;
  bridgeConnected: boolean;
}

const STAT_LABELS: Record<string, string> = {
  str: 'STR', dex: 'DEX', con: 'CON', int: 'INT',
  spd: 'SPD', cha: 'CHA', lck: 'LCK',
};

const STIM_PRESETS = [0, 32, 95, 100, 196] as const;

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

function PctBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-bg-dim overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.round(value * 100)}%` }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />
    </div>
  );
}

function AdviceDetail({ advice }: { advice: BreedingAdvice }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-2"
    >
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-text-dim">Inbreeding risk:</span>
        <InbreedingBadge level={advice.inbreeding_warning} />
      </div>

      <div>
        <div className="text-[10px] font-mono font-bold text-text-dim mb-1">
          Stat inheritance (higher parent)
        </div>
        <div className="grid grid-cols-7 gap-1">
          {Object.entries(advice.stat_high_probs).map(([key, prob]) => (
            <div key={key} className="text-center">
              <div className="text-[9px] font-mono text-text-dim">{STAT_LABELS[key]}</div>
              <div className="text-[10px] font-mono font-bold text-text">
                {Math.round(prob * 100)}%
              </div>
              <PctBar value={prob} color={`var(--color-stat-${key})`} />
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-[10px] font-mono font-bold text-text-dim mb-1">
          Expected offspring stats
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {Object.entries(advice.expected_stats).map(([key, val]) => (
            <Badge key={key} variant="default">
              <span style={{ color: `var(--color-stat-${key})` }}>{STAT_LABELS[key]}</span>
              {' '}
              {val.toFixed(1)}
            </Badge>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-md bg-bg-dim p-1.5 text-center">
          <div className="text-[9px] text-text-dim">1st Active</div>
          <div className="text-[11px] font-mono font-bold text-text">
            {Math.round(advice.first_active_chance * 100)}%
          </div>
        </div>
        <div className="rounded-md bg-bg-dim p-1.5 text-center">
          <div className="text-[9px] text-text-dim">Passive</div>
          <div className="text-[11px] font-mono font-bold text-text">
            {Math.round(advice.passive_chance * 100)}%
          </div>
        </div>
        <div className="rounded-md bg-bg-dim p-1.5 text-center">
          <div className="text-[9px] text-text-dim">2nd Active</div>
          <div className="text-[11px] font-mono font-bold text-text">
            {Math.round(advice.second_active_chance * 100)}%
          </div>
        </div>
      </div>

      {advice.tips && advice.tips.length > 0 && (
        <div className="space-y-0.5">
          {advice.tips.map((tip, i) => (
            <div key={i} className="text-[9px] text-text-dim leading-tight">
              &bull; {tip}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

export function BreedingPanel({ cats, collars, llmAvailable, bridgeConnected }: BreedingPanelProps) {
  const [selectedCollar, setSelectedCollar] = useState<string>(collars[0]?.name ?? '');
  const [stimulation, setStimulation] = useState(0);
  const [rankings, setRankings] = useState<PairRanking[]>([]);
  const [selectedPair, setSelectedPair] = useState<{ a: number; b: number } | null>(null);
  const [advice, setAdvice] = useState<BreedingAdvice | null>(null);
  const [loading, setLoading] = useState(false);
  const signalConnected = useRef(false);

  useEffect(() => {
    if (signalConnected.current) return;
    signalConnected.current = true;
    onBreedingResult((result) => {
      setLoading(false);
      if (result.pairs.length > 0) {
        const mapped: PairRanking[] = result.pairs.map((p) => ({
          cat_a_key: p.cat_a_key,
          cat_a_name: p.cat_a_name,
          cat_b_key: p.cat_b_key,
          cat_b_name: p.cat_b_name,
          expected_score: 'expected_score' in p ? (p as PairRanking).expected_score : 0,
          reason: p.reason,
        }));
        setRankings(mapped);
      }
    });
  }, []);

  const handleSearch = useCallback(async () => {
    if (!selectedCollar) return;
    setLoading(true);
    setAdvice(null);
    setSelectedPair(null);
    try {
      const result = await getBreedingRankings(selectedCollar, stimulation);
      setRankings(result);
    } finally {
      setLoading(false);
    }
  }, [selectedCollar, stimulation]);

  const handleAiSuggest = useCallback(() => {
    if (!selectedCollar) return;
    setLoading(true);
    setAdvice(null);
    setSelectedPair(null);
    suggestBreedingLlm(selectedCollar, stimulation);
  }, [selectedCollar, stimulation]);

  const handlePairClick = useCallback(async (aKey: number, bKey: number) => {
    setSelectedPair({ a: aKey, b: bKey });
    const result = await getBreedingAdvice(aKey, bKey, stimulation);
    setAdvice(result);
  }, [stimulation]);

  if (cats.length < 2 || collars.length === 0) {
    return (
      <div className="flex items-center justify-center h-[160px] text-text-dim text-xs">
        Need at least 2 cats to analyze breeding
      </div>
    );
  }

  const collarDef = collars.find((c) => c.name === selectedCollar);

  return (
    <ScrollArea className="h-[280px]">
      <div className="space-y-2 pr-2">
        {/* Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1">
            <span className="text-[10px] font-mono text-text-dim">Target:</span>
            <select
              value={selectedCollar}
              onChange={(e) => setSelectedCollar(e.target.value)}
              className="h-6 rounded-md border border-border bg-card px-1.5 text-[10px] font-mono text-text cursor-pointer focus:outline-none"
            >
              {collars.map((c) => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1">
            <span className="text-[10px] font-mono text-text-dim">Stim:</span>
            <div className="flex gap-0.5">
              {STIM_PRESETS.map((s) => (
                <button
                  key={s}
                  onClick={() => setStimulation(s)}
                  className={`h-5 min-w-[28px] rounded text-[9px] font-mono border transition-colors cursor-pointer ${
                    stimulation === s
                      ? 'bg-good/20 border-good/40 text-good font-bold'
                      : 'bg-bg-dim border-border text-text-dim hover:text-text'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <input
              type="number"
              min={0}
              max={300}
              value={stimulation}
              onChange={(e) => setStimulation(Math.max(0, Math.min(300, Number(e.target.value) || 0)))}
              className="h-5 w-10 rounded border border-border bg-card text-center text-[9px] font-mono text-text focus:outline-none focus:border-accent"
            />
          </div>

          <div className="flex-1" />

          <Button
            size="sm"
            onClick={handleSearch}
            disabled={loading || !bridgeConnected}
            title={!bridgeConnected ? 'Requires Mewgent app' : undefined}
          >
            Rank Pairs
          </Button>
          {llmAvailable && (
            <Button
              size="sm"
              variant="primary"
              onClick={handleAiSuggest}
              disabled={loading || !bridgeConnected}
              title={!bridgeConnected ? 'Requires Mewgent app' : undefined}
            >
              AI Suggest
            </Button>
          )}
        </div>

        {/* Rankings */}
        <AnimatePresence mode="wait">
          {rankings.length > 0 && (
            <motion.div
              key="rankings"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-1"
            >
              <div className="text-[10px] font-mono font-bold text-text-dim flex items-center gap-1.5">
                {collarDef && <ClassIcon name={collarDef.name} size={12} />}
                Top pairs for {selectedCollar}
              </div>

              {rankings.map((r, i) => {
                const isSelected = selectedPair?.a === r.cat_a_key && selectedPair?.b === r.cat_b_key;
                return (
                  <motion.button
                    key={`${r.cat_a_key}-${r.cat_b_key}`}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => handlePairClick(r.cat_a_key, r.cat_b_key)}
                    className={`w-full flex items-center gap-2 rounded-md border px-2 py-1 text-left cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-selected border-good/40'
                        : 'bg-card border-border/50 hover:bg-card-hover'
                    }`}
                  >
                    <span className="text-[10px] font-mono text-text-dim w-4">{i + 1}.</span>
                    <span className="text-[11px] font-serif text-text truncate">
                      {r.cat_a_name}
                    </span>
                    <span className="text-[9px] text-text-dim">&times;</span>
                    <span className="text-[11px] font-serif text-text truncate">
                      {r.cat_b_name}
                    </span>
                    <span className="flex-1" />
                    <Badge
                      variant="accent"
                      className="shrink-0"
                      style={collarDef ? { borderColor: `${collarDef.color}33`, color: collarDef.color } : undefined}
                    >
                      {r.expected_score.toFixed(1)}
                    </Badge>
                  </motion.button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Detail panel */}
        <AnimatePresence>
          {advice && (
            <motion.div
              key="advice"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="rounded-lg border border-border bg-card-solid p-2 overflow-hidden"
            >
              <div className="text-[10px] font-mono font-bold text-accent mb-1.5">
                {advice.cat_a_name} &times; {advice.cat_b_name} &mdash; Stim {advice.stimulation}
              </div>
              <AdviceDetail advice={advice} />
            </motion.div>
          )}
        </AnimatePresence>

        {rankings.length === 0 && !loading && (
          <div className="text-center text-text-dim text-[10px] py-4">
            Select a target class and click "Rank Pairs" to find optimal breeding pairs
          </div>
        )}

        {loading && (
          <div className="text-center text-text-dim text-[10px] py-4">
            <span className="animate-pulse-dot inline-block w-1.5 h-1.5 rounded-full bg-accent mr-1" />
            Analyzing...
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
