export interface Player {
  puuid: string;
  gameName: string;
  tagLine: string;
  level: number;
  rank: string;
  tier: string;
  lp: number;
  winRate: number;
  wins: number;
  losses: number;
  recentChampions: number[];
}

export interface Match {
  matchId: string;
  queueType: string;
  gameCreation: number;
  gameDuration: number;
  participants: Participant[];
}

export interface Participant {
  puuid: string;
  gameName: string;
  tagLine: string;
  teamId: number;
  championId: number;
  championName: string;
  kills: number;
  deaths: number;
  assists: number;
  goldEarned: number;
  items: number[];
  itemImages: string[];
  summonerSpells: number[];
  win: boolean;
  position: string;
}

export interface Stats {
  kda: number;
  winRate: number;
  avgKills: number;
  avgDeaths: number;
  avgAssists: number;
  gamesPlayed: number;
}

export interface ChampionMastery {
  championId: number;
  championName: string;
  level: number;
  points: number;
  lastPlayed: number;
}

// OP.GG Champion Build Types
export interface OpggItem {
  id: string;
  name: string;
}

export interface OpggCounter {
  champion_name: string;
  win_rate: number | null;
  games: number;
  advantage?: number | null;  // Positive = good for this champ
}

export interface OpggMatchups {
  counters: OpggCounter[];    // Champions that beat this champ (克制该英雄)
  countered_by: OpggCounter[]; // Champions this champ beats (该英雄克制)
}

export interface OpggBuild {
  champion_name: string;
  win_rate: number | null;
  pick_rate: number | null;
  games_played: number | null;
  roles: string[];
  items: {
    start: OpggItem[];
    core: OpggItem[];
    final: OpggItem[];
  };
  skills: string[];
  runes: { name: string }[];
  matchups: OpggMatchups;
  last_updated: string;
  source: string;
  cached: boolean;
  stale?: boolean;
}

export interface ChampionBuildResponse {
  success: boolean;
  data: OpggBuild | null;
  error: string | null;
  cached: boolean;
}

export interface CoachDataWindow {
  match_count: number;
  days?: number | null;
  start_timestamp?: number | null;
  end_timestamp?: number | null;
  started_at?: string | null;
  ended_at?: string | null;
}

export interface CoachPriority {
  area?: string;
  category?: string;
  title: string;
  severity: string;
  evidence: string[];
  recommendation?: string;
  rationale?: string;
  action_items?: string[];
}

export interface CoachReportPayload {
  summary: string;
  data_window: CoachDataWindow;
  priorities: CoachPriority[];
  confidence: number | string;
  notes?: string | null;
}

export interface CoachReportResponse {
  id?: number;
  puuid?: string;
  has_report?: boolean;
  report: CoachReportPayload | null;
  data_fingerprint?: string;
  model?: string | null;
  status?: string;
  error_message?: string | null;
  stale: boolean;
  generated_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CoachChatResponse {
  answer: string;
  model?: string | null;
  report_id?: number | null;
  cited_priorities?: string[];
}

export type QueueType = 'RANKED_SOLO_5x5' | 'RANKED_FLEX_SR' | 'RANKED_TFT' | 'ARKANE';
export type RegionCode = 'kr' | 'na' | 'euw' | 'eune' | 'jp' | 'oce' | 'ru' | 'br' | 'las' | 'lan' | 'tr' | 'sg' | 'my' | 'ph' | 'th' | 'tw' | 'vn';
