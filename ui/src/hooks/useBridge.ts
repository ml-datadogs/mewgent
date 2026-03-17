import { useEffect, useRef, useState } from 'react';
import {
  initBridge,
  isConnected,
  getRoster,
  getCollars,
  getTeam,
  getSaveInfo,
  onRosterUpdated,
  onTeamUpdated,
  onSaveInfoUpdated,
  onLlmStatusChanged,
  onCollarsUpdated,
} from '@/bridge';
import type { RosterEntry, CollarDef, TeamSlot } from '@/types';

export interface BridgeState {
  connected: boolean;
  roster: RosterEntry[];
  collars: CollarDef[];
  team: (TeamSlot | null)[];
  saveInfo: { day: number; cat_count: number; status: string };
  llmStatus: string;
}

export function useBridge(): BridgeState {
  const [connected, setConnected] = useState(false);
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [collars, setCollars] = useState<CollarDef[]>([]);
  const [team, setTeam] = useState<(TeamSlot | null)[]>([null, null, null, null]);
  const [saveInfo, setSaveInfo] = useState({ day: 0, cat_count: 0, status: 'Waiting for save data...' });
  const [llmStatus, setLlmStatus] = useState('');
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    initBridge().then(async () => {
      setConnected(isConnected());
      if (!isConnected()) return;

      const [r, c, t, s] = await Promise.all([
        getRoster(),
        getCollars(),
        getTeam(),
        getSaveInfo(),
      ]);
      setRoster(r);
      setCollars(c);
      setTeam(t);
      setSaveInfo(s);

      onRosterUpdated(setRoster);
      onTeamUpdated(setTeam);
      onSaveInfoUpdated(setSaveInfo);
      onLlmStatusChanged(setLlmStatus);
      onCollarsUpdated(setCollars);
    });
  }, []);

  return { connected, roster, collars, team, saveInfo, llmStatus };
}
