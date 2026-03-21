import { useEffect, useRef, useState } from 'react';
import {
  initBridge,
  isConnected,
  getRoster,
  getCollars,
  getTeam,
  getSaveInfo,
  getUpdateInfo,
  onRosterUpdated,
  onTeamUpdated,
  onTeamSynergyUpdated,
  onSaveInfoUpdated,
  onLlmStatusChanged,
  onCollarsUpdated,
  onUpdateAvailable,
} from '@/bridge';
import type { UpdateInfo } from '@/bridge';
import type { RosterEntry, CollarDef, TeamSlot } from '@/types';

export interface BridgeState {
  connected: boolean;
  roster: RosterEntry[];
  collars: CollarDef[];
  team: (TeamSlot | null)[];
  teamSynergy: string;
  saveInfo: { day: number; cat_count: number; status: string };
  llmStatus: string;
  updateInfo: UpdateInfo | null;
}

export function useBridge(): BridgeState {
  const [connected, setConnected] = useState(false);
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [collars, setCollars] = useState<CollarDef[]>([]);
  const [team, setTeam] = useState<(TeamSlot | null)[]>([null, null, null, null]);
  const [teamSynergy, setTeamSynergy] = useState('');
  const [saveInfo, setSaveInfo] = useState({ day: 0, cat_count: 0, status: 'Waiting for save data...' });
  const [llmStatus, setLlmStatus] = useState('');
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
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

      getUpdateInfo().then((info) => {
        if (info) setUpdateInfo(info);
      });

      onRosterUpdated(setRoster);
      onTeamUpdated(setTeam);
      onTeamSynergyUpdated(setTeamSynergy);
      onSaveInfoUpdated(setSaveInfo);
      onLlmStatusChanged(setLlmStatus);
      onCollarsUpdated(setCollars);
      onUpdateAvailable(setUpdateInfo);
    });
  }, []);

  return { connected, roster, collars, team, teamSynergy, saveInfo, llmStatus, updateInfo };
}
