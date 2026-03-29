import { useEffect, useRef, useState } from 'react';
import {
  initBridge,
  isConnected,
  getRoster,
  getCatalog,
  getCollars,
  getTeam,
  getSaveInfo,
  getUpdateInfo,
  getRoomStats,
  getLlmSettings,
  onRosterUpdated,
  onCatalogUpdated,
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
import type {
  UpdateInfo,
  DistributionResult,
  LlmSettings,
  SaveInfo,
  TeamSynergyPayload,
} from '@/bridge';
import { EMPTY_TEAM_SYNERGY_PAYLOAD } from '@/bridge';
import type { RosterEntry, CollarDef, TeamSlot, RoomStats, SaveCat } from '@/types';
import {
  STANDALONE_COLLARS,
  STANDALONE_ROSTER,
  STANDALONE_CATALOG,
  STANDALONE_ROOM_STATS,
  STANDALONE_SAVE_INFO,
  STANDALONE_TEAM_SYNERGY,
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
  /** Every cat in the save (all statuses); empty until a save is loaded. */
  catalog: SaveCat[];
  collars: CollarDef[];
  team: (TeamSlot | null)[];
  teamSynergy: TeamSynergyPayload;
  saveInfo: SaveInfo;
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
  const [catalog, setCatalog] = useState<SaveCat[]>([]);
  const [collars, setCollars] = useState<CollarDef[]>([]);
  const [team, setTeam] = useState<(TeamSlot | null)[]>([null, null, null, null]);
  const [teamSynergy, setTeamSynergy] = useState<TeamSynergyPayload>(EMPTY_TEAM_SYNERGY_PAYLOAD);
  const [saveInfo, setSaveInfo] = useState<SaveInfo>({
    day: 0,
    cat_count: 0,
    status: 'Waiting for save data...',
    inventory: { backpack: [], storage: [], trash: [] },
  });
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
          setCatalog(STANDALONE_CATALOG);
          setCollars(STANDALONE_COLLARS);
          setTeam(STANDALONE_TEAM);
          setTeamSynergy({ ...STANDALONE_TEAM_SYNERGY });
          setSaveInfo(STANDALONE_SAVE_INFO);
          setRoomStats(STANDALONE_ROOM_STATS);
          setLlmSettings(standaloneLlmPreviewSettings());
        }
        return;
      }

      const [r, catalogData, c, t, s, rs, llm] = await Promise.all([
        getRoster(),
        getCatalog(),
        getCollars(),
        getTeam(),
        getSaveInfo(),
        getRoomStats(),
        getLlmSettings(),
      ]);
      setRoster(r);
      setCatalog(catalogData);
      setCollars(c);
      setTeam(t);
      setSaveInfo(s);
      setRoomStats(rs);
      if (llm) setLlmSettings(llm);

      getUpdateInfo().then((info) => {
        if (info) setUpdateInfo(info);
      });

      onRosterUpdated(setRoster);
      onCatalogUpdated(setCatalog);
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
    catalog,
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
