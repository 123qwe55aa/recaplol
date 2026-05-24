import axios from 'axios';
import type {
  Player,
  Match,
  ChampionMastery as ClientChampionMastery,
  Stats,
  ChampionBuildResponse,
  CoachChatResponse,
  CoachMatchRecapResponse,
  PatchNoteAnnouncement,
  CoachReportResponse,
  MatchRecapResponse,
  MatchTimelineResponse,
  RiotPlatformStatus,
  QueueType,
  RegionCode,
} from '../types';
import {
  buildItemIconUrl,
  DDRAGON_VERSIONS_URL,
  loadChampionByIdMap,
} from './ddragon';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

const MATCH_SYNC_TIMEOUT_MS = 60000;
const AI_MATCH_RECAP_TIMEOUT_MS = 600000;
const AI_COACH_REPORT_TIMEOUT_MS = 600000;
const AI_COACH_CHAT_TIMEOUT_MS = 600000;

// API response types (snake_case from backend)
interface ApiPlayerResponse {
  puuid: string;
  summoner_name: string;
  tag_line: string;
  summoner_id: string;
  profile_icon_id: number;
  summoner_level: number;
  ranked_status?: string | null;
  ranked_stats?: {
    tier: string;
    rank: string;
    league_points: number;
    wins: number;
    losses: number;
    queue_type: string;
  };
  ranked_flex_stats?: {
    tier: string;
    rank: string;
    league_points: number;
    wins: number;
    losses: number;
    queue_type: string;
  };
}

interface ApiMatchListResponse {
  matches: string[];
  start_index: number;
  total_count: number;
  puuid: string;
}

interface ApiParticipantSummary {
  puuid: string | null;
  summoner_name: string | null;
  team_id: number | null;
  team_position: string | null;
  champion_id: number | null;
  champion_name: string | null;
  champion_level: number;
  kills: number;
  deaths: number;
  assists: number;
  kda: number;
  total_damage_dealt: number;
  total_damage_dealt_to_champions: number;
  total_damage_taken: number;
  neutral_minions_killed: number;
  total_minions_killed: number;
  cs_per_minute: number;
  vision_score: number;
  wards_placed: number;
  wards_destroyed: number;
  gold_earned: number;
  items: number[];
  double_kills: number;
  triple_kills: number;
  quadra_kills: number;
  pentakills: number;
  win: boolean;
  outcome?: 'WIN' | 'LOSS' | 'REMAKE' | 'UNKNOWN';
}

interface ApiMatchSummary {
  match_id: string;
  game_mode: string | null;
  game_type: string | null;
  game_version: string | null;
  game_duration: number;
  game_start_timestamp: number | null;
  game_end_timestamp: number | null;
  blue_team_win: boolean | null;
  participants: ApiParticipantSummary[];
}

interface ApiMatchListWithDetailsResponse {
  matches: ApiMatchSummary[];
  start_index: number;
  total_count: number;
  puuid: string;
}

interface ApiMatchDetail {
  match_id: string;
  // Additional fields from backend
}

interface ApiChampionMastery {
  champion_id: number;
  champion_level: number;
  champion_points: number;
  champion_points_since_last_level?: number;
  champion_points_until_next_level?: number;
  chest_granted?: boolean;
  last_played_time?: number;
  tokens_earned?: number;
}

interface ApiPlayerMasteryResponse {
  puuid: string;
  summoner_name: string;
  total_champion_levels: number;
  total_champion_points: number;
  champion_masteries: ApiChampionMastery[];
}

interface ApiPlayerStatsResponse {
  puuid: string;
  summoner_name: string;
  career: {
    total_matches: number;
    total_wins: number;
    total_losses: number;
    win_rate: number;
    overall_kda: number;
    avg_kills: number;
    avg_deaths: number;
    avg_assists: number;
    avg_cs_per_minute?: number;
    avg_vision_score?: number;
    avg_gold_earned?: number;
    total_double_kills?: number;
    total_triple_kills?: number;
    total_quadra_kills?: number;
    total_pentakills?: number;
  };
  champion_stats: Array<{
    champion_id: number;
    champion_name?: string;
    games_played: number;
    wins: number;
    losses: number;
    win_rate: number;
    kills: number;
    deaths: number;
    assists: number;
    kda: number;
    avg_cs_per_minute?: number;
  }>;
  role_stats?: Array<{
    role: string;
    games_played: number;
    win_rate: number;
    avg_kda: number;
    avg_cs_per_minute?: number;
  }>;
}

// Response transformers: API -> Client types
function transformPlayer(apiPlayer: ApiPlayerResponse): Player {
  const ranked = apiPlayer.ranked_stats;
  const totalGames = ranked ? ranked.wins + ranked.losses : 0;
  const winRate = ranked && totalGames > 0 ? (ranked.wins / totalGames) * 100 : 0;

  return {
    puuid: apiPlayer.puuid,
    gameName: apiPlayer.summoner_name,
    tagLine: apiPlayer.tag_line,
    level: apiPlayer.summoner_level,
    rankedStatus: apiPlayer.ranked_status ?? null,
    rank: ranked?.rank ?? 'UNRANKED',
    tier: ranked?.tier ?? 'UNRANKED',
    lp: ranked?.league_points ?? 0,
    winRate: winRate,
    wins: ranked?.wins ?? 0,
    losses: ranked?.losses ?? 0,
    recentChampions: [], // Not provided by player endpoint
    rankedFlex: apiPlayer.ranked_flex_stats
      ? {
          tier: apiPlayer.ranked_flex_stats.tier,
          rank: apiPlayer.ranked_flex_stats.rank,
          lp: apiPlayer.ranked_flex_stats.league_points,
          wins: apiPlayer.ranked_flex_stats.wins,
          losses: apiPlayer.ranked_flex_stats.losses,
          winRate:
            (apiPlayer.ranked_flex_stats.wins + apiPlayer.ranked_flex_stats.losses) > 0
              ? (apiPlayer.ranked_flex_stats.wins / (apiPlayer.ranked_flex_stats.wins + apiPlayer.ranked_flex_stats.losses)) * 100
              : 0,
        }
      : null,
  };
}

function transformMatchList(apiResponse: ApiMatchListResponse): { matchIds: string[]; total: number } {
  return {
    matchIds: apiResponse.matches,
    total: apiResponse.total_count,
  };
}

const CHAMPION_ID_TO_NAME_FALLBACK: Record<number, string> = {
  1: 'Annie', 10: 'Kayle', 11: 'MasterYi', 16: 'Soraka', 18: 'Tristana',
  19: 'Warwick', 2: 'Olaf', 20: 'Nunu', 21: 'MissFortune', 22: 'Ashe',
};

let championIdToNameCache: Record<number, string> | null = null;

async function loadChampionIdToNameMap(): Promise<Record<number, string>> {
  if (championIdToNameCache) return championIdToNameCache;

  try {
    const versionsRes = await fetch(DDRAGON_VERSIONS_URL);
    if (!versionsRes.ok) throw new Error('versions fetch failed');
    const versions = (await versionsRes.json()) as string[];
    const latestVersion = versions?.[0];
    if (!latestVersion) throw new Error('version missing');

    const map: Record<number, string> = {};
    const championById = await loadChampionByIdMap(latestVersion);
    for (const champ of Object.values(championById)) {
      map[champ.key] = champ.id;
    }

    championIdToNameCache = Object.keys(map).length > 0 ? map : CHAMPION_ID_TO_NAME_FALLBACK;
  } catch {
    championIdToNameCache = CHAMPION_ID_TO_NAME_FALLBACK;
  }

  return championIdToNameCache;
}

function getChampionName(championId: number): string {
  return CHAMPION_ID_TO_NAME_FALLBACK[championId] ?? `Champion_${championId}`;
}

export const searchPlayer = async (gameName: string, tagLine: string): Promise<Player> => {
  const { data } = await api.get<ApiPlayerResponse>(
    `/players/by-summoner/${encodeURIComponent(gameName)}`,
    { params: { tag_line: tagLine } }
  );
  return transformPlayer(data);
};

export const getPlayerByPuuid = async (puuid: string): Promise<Player> => {
  const { data } = await api.get<ApiPlayerResponse>(`/players/${puuid}`);
  return transformPlayer(data);
};

export const refreshPlayerByPuuid = async (puuid: string): Promise<Player> => {
  const { data } = await api.post<ApiPlayerResponse>(`/players/${encodeURIComponent(puuid)}/refresh`);
  return transformPlayer(data);
};

export const getPlayerRanked = async (puuid: string) => {
  const { data } = await api.get(`/players/${puuid}/ranked`);
  return data;
};

export const getPlayerMatches = async (puuid: string, limit = 20) => {
  const { data } = await api.get<ApiMatchListResponse>(`/matches/${puuid}`, {
    params: { limit },
  });
  return transformMatchList(data);
};

function getItemImages(itemIds: number[], gameVersion: string): string[] {
  return itemIds
    .filter(id => id > 0)
    .map(id => buildItemIconUrl(id, gameVersion || '16.1.1'));
}

function transformMatchSummary(apiMatch: ApiMatchSummary): Match {
  const gameVersion = apiMatch.game_version || '16.1';
  const participants = apiMatch.participants.map(p => {
    const itemImages = getItemImages(p.items || [], gameVersion);
    return {
      puuid: p.puuid || '',
      gameName: p.summoner_name || '',
      tagLine: '',
      teamId: p.team_id || 0,
      championId: p.champion_id || 0,
      championName: p.champion_name || 'Unknown',
      kills: p.kills,
      deaths: p.deaths,
      assists: p.assists,
      goldEarned: p.gold_earned,
      items: p.items || [],
      itemImages,
      summonerSpells: [],
      win: p.win,
      outcome: p.outcome ?? (p.win ? 'WIN' : 'LOSS'),
      position: p.team_position || '',
    };
  });

  return {
    matchId: apiMatch.match_id,
    queueType: apiMatch.game_type || apiMatch.game_mode || '',
    gameCreation: apiMatch.game_start_timestamp || Date.now(),
    gameDuration: apiMatch.game_duration,
    participants,
  };
}

export const getPlayerMatchesWithDetails = async (puuid: string, limit = 20) => {
  const { data } = await api.get<ApiMatchListWithDetailsResponse>(
    `/matches/${puuid}/details`,
    { params: { limit } }
  );
  return {
    matches: data.matches.map(m => transformMatchSummary(m)),
    total: data.total_count,
  };
};

export const fetchPlayerMatches = async (puuid: string, limit = 20, region = 'americas') => {
  const { data } = await api.post(`/matches/fetch/${encodeURIComponent(puuid)}`, null, {
    params: { limit, region },
    timeout: MATCH_SYNC_TIMEOUT_MS,
  });
  return data;
};

export const fetchMatchTimeline = async (matchId: string): Promise<MatchTimelineResponse> => {
  const { data } = await api.post<MatchTimelineResponse>(
    `/matches/timeline/fetch/${encodeURIComponent(matchId)}`
  );
  return data;
};

export const getMatchRecap = async (
  matchId: string,
  puuid: string
): Promise<MatchRecapResponse> => {
  const { data } = await api.get<MatchRecapResponse>(
    `/matches/${encodeURIComponent(matchId)}/recap/${encodeURIComponent(puuid)}`
  );
  return data;
};

export const generateAiMatchRecap = async (
  matchId: string,
  puuid: string
): Promise<CoachMatchRecapResponse> => {
  const { data } = await api.post<CoachMatchRecapResponse>(
    `/coach/matches/${encodeURIComponent(matchId)}/recap/${encodeURIComponent(puuid)}`,
    null,
    { timeout: AI_MATCH_RECAP_TIMEOUT_MS }
  );
  return data;
};

export const getSavedAiMatchRecap = async (
  matchId: string,
  puuid: string
): Promise<CoachMatchRecapResponse | null> => {
  try {
    const { data } = await api.get<CoachMatchRecapResponse>(
      `/coach/matches/${encodeURIComponent(matchId)}/recap/${encodeURIComponent(puuid)}`
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
};

export const getMatchDetail = async (matchId: string): Promise<Match | null> => {
  try {
    const { data } = await api.get<ApiMatchDetail>(`/matches/detail/${matchId}`);
    // Transform to client type - simplified for now
    return {
      matchId: data.match_id,
      queueType: '',
      gameCreation: Date.now(),
      gameDuration: 0,
      participants: [],
    };
  } catch {
    return null;
  }
};

export const getPlayerStats = async (puuid: string): Promise<Stats | null> => {
  try {
    const { data } = await api.get<ApiPlayerStatsResponse>(`/stats/players/${puuid}/overview`);
    return {
      kda: data.career.overall_kda,
      winRate: data.career.win_rate,
      avgKills: data.career.avg_kills,
      avgDeaths: data.career.avg_deaths,
      avgAssists: data.career.avg_assists,
      gamesPlayed: data.career.total_matches,
    };
  } catch {
    return null;
  }
};

export const getChampionMastery = async (
  puuid: string,
  limit = 10
): Promise<{ champion_masteries: ClientChampionMastery[] }> => {
  const championIdToName = await loadChampionIdToNameMap();
  const { data } = await api.get<ApiPlayerMasteryResponse>(`/players/${puuid}/mastery`, {
    params: { limit },
  });

  return {
    champion_masteries: data.champion_masteries.map((m) => ({
      championId: m.champion_id,
      championName: championIdToName[m.champion_id] ?? getChampionName(m.champion_id),
      level: m.champion_level,
      points: m.champion_points,
      lastPlayed: m.last_played_time ?? 0,
    })),
  };
};

export const getChampionBuild = async (
  champName: string,
  region: RegionCode = 'kr',
  queue: QueueType = 'RANKED_SOLO_5x5',
  tier = 'overall',
  countersCount = 5,
  role = '',
  refresh = false
): Promise<ChampionBuildResponse> => {
  const { data } = await api.get<ChampionBuildResponse>(
    `/opgg/champions/${encodeURIComponent(champName)}/build`,
    {
      params: { region, queue, tier, counters_count: countersCount, role, refresh },
    }
  );
  return data;
};

export const getOpggRegions = async () => {
  const { data } = await api.get('/opgg/regions');
  return data;
};

export const getCoachReport = async (puuid: string): Promise<CoachReportResponse> => {
  const { data } = await api.get<CoachReportResponse>(
    `/coach/players/${encodeURIComponent(puuid)}/report`
  );
  return data;
};

export const generateCoachReport = async (
  puuid: string,
  force = false
): Promise<CoachReportResponse> => {
  const { data } = await api.post<CoachReportResponse>(
    `/coach/players/${encodeURIComponent(puuid)}/report`,
    { force },
    { timeout: AI_COACH_REPORT_TIMEOUT_MS }
  );
  return data;
};

export const sendCoachQuestion = async (
  puuid: string,
  question: string
): Promise<CoachChatResponse> => {
  const { data } = await api.post<CoachChatResponse>(
    `/coach/players/${encodeURIComponent(puuid)}/chat`,
    { question },
    { timeout: AI_COACH_CHAT_TIMEOUT_MS }
  );
  return data;
};

export const getLatestLolVersion = async (): Promise<string> => {
  const { data } = await api.get<string[]>(DDRAGON_VERSIONS_URL);
  return data[0] ?? '';
};

export const getLatestPatchAnnouncement = async (): Promise<PatchNoteAnnouncement> => {
  const { data } = await api.get<PatchNoteAnnouncement>('/patch-notes/latest');
  return data;
};

export const getRiotPlatformStatus = async (platform: string): Promise<RiotPlatformStatus> => {
  const { data } = await api.get<RiotPlatformStatus>(
    `/riot/status/${encodeURIComponent(platform)}`
  );
  return data;
};
