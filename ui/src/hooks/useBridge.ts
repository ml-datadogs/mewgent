import { useEffect, useRef, useState } from 'react';
import {
  initBridge,
  isConnected,
  getRoster,
  getCollars,
  getTeam,
  getSaveInfo,
  getUpdateInfo,
  getRoomStats,
  getLlmSettings,
  onRosterUpdated,
  onTeamUpdated,
  onTeamSynergyUpdated,
  onSaveInfoUpdated,
  onLlmStatusChanged,
  onLlmSettingsChanged,
  onCollarsUpdated,
  onUpdateAvailable,
  onRoomStatsUpdated,
  onDistributionResult,
  standaloneLlmPreviewSettings,
} from '@/bridge';
import type { UpdateInfo, DistributionResult, LlmSettings } from '@/bridge';
import type { RosterEntry, CollarDef, TeamSlot, RoomStats } from '@/types';
import {
  STANDALONE_COLLARS,
  STANDALONE_ROSTER,
  STANDALONE_ROOM_STATS,
  STANDALONE_SAVE_INFO,
  STANDALONE_SYNERGY,
  STANDALONE_TEAM,
} from '@/dev/standaloneMock';
import {
  getMockTeamLlmStatus,
  subscribeMockTeamLlmStatus,
} from '@/dev/loaderPreview';

export interface BridgeState {
  connected: boolean;
  /** True when showing Vite-only mock data (no QWebChannel, import.meta.env.DEV) */
  uiPreview: boolean;
  roster: RosterEntry[];
  collars: CollarDef[];
  team: (TeamSlot | null)[];
  teamSynergy: string;
  saveInfo: { day: number; cat_count: number; status: string };
  llmStatus: string;
  updateInfo: UpdateInfo | null;
  roomStats: Record<string, RoomStats>;
  lastDistribution: DistributionResult | null;
  llmSettings: LlmSettings | null;
}

export function useBridge(): BridgeState {
  const [connected, setConnected] = useState(false);
  const [uiPreview, setUiPreview] = useState(false);
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [collars, setCollars] = useState<CollarDef[]>([]);
  const [team, setTeam] = useState<(TeamSlot | null)[]>([null, null, null, null]);
  const [teamSynergy, setTeamSynergy] = useState('');
  const [saveInfo, setSaveInfo] = useState({ day: 0, cat_count: 0, status: 'Waiting for save data...' });
  const [llmStatusFromBridge, setLlmStatusFromBridge] = useState('');
  const [mockTeamLlmStatus, setMockTeamLlmStatus] = useState('');
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [roomStats, setRoomStats] = useState<Record<string, RoomStats>>({});
  const [lastDistribution, setLastDistribution] = useState<DistributionResult | null>(null);
  const [llmSettings, setLlmSettings] = useState<LlmSettings | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    initBridge().then(async () => {
      setConnected(isConnected());
      if (!isConnected()) {
        if (import.meta.env.DEV) {
          setUiPreview(true);
          setRoster(STANDALONE_ROSTER);
          setCollars(STANDALONE_COLLARS);
          setTeam(STANDALONE_TEAM);
          setTeamSynergy(STANDALONE_SYNERGY);
          setSaveInfo(STANDALONE_SAVE_INFO);
          setRoomStats(STANDALONE_ROOM_STATS);
          setLlmSettings(standaloneLlmPreviewSettings());
        }
        return;
      }

      const [r, c, t, s, rs, llm] = await Promise.all([
        getRoster(),
        getCollars(),
        getTeam(),
        getSaveInfo(),
        getRoomStats(),
        getLlmSettings(),
      ]);
      setRoster(r);
      setCollars(c);
      setTeam(t);
      setSaveInfo(s);
      setRoomStats(rs);
      if (llm) setLlmSettings(llm);

      getUpdateInfo().then((info) => {
        if (info) setUpdateInfo(info);
      });

      onRosterUpdated(setRoster);
      onTeamUpdated(setTeam);
      onTeamSynergyUpdated(setTeamSynergy);
      onSaveInfoUpdated(setSaveInfo);
      onLlmStatusChanged(setLlmStatusFromBridge);
      onLlmSettingsChanged(setLlmSettings);
      onCollarsUpdated(setCollars);
      onUpdateAvailable(setUpdateInfo);
      onRoomStatsUpdated(setRoomStats);
      onDistributionResult(setLastDistribution);
    });
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV || !uiPreview) return;
    setMockTeamLlmStatus(getMockTeamLlmStatus());
    return subscribeMockTeamLlmStatus(() => setMockTeamLlmStatus(getMockTeamLlmStatus()));
  }, [uiPreview]);

  const llmStatus = connected ? llmStatusFromBridge : mockTeamLlmStatus;

  return {
    connected,
    uiPreview,
    roster,
    collars,
    team,
    teamSynergy,
    saveInfo,
    llmStatus,
    updateInfo,
    roomStats,
    lastDistribution,
    llmSettings,
  };
}
