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
  win: boolean | null;
  outcome?: 'WIN' | 'LOSS' | 'REMAKE' | 'UNKNOWN';
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

export interface OpggSynergy {
  champion_name: string;
  win_rate: number | null;
  pick_rate: number | null;
  games: number;
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
  rune_setup?: {
    primary_runes: string[];
    secondary_runes: string[];
    stat_shards?: string[];
  } | null;
  rune_setups?: Array<{
    primary_runes: string[];
    secondary_runes: string[];
    stat_shards?: string[];
  }>;
  rune_setup_valid?: boolean;
  matchups: OpggMatchups;
  synergies: OpggSynergy[];
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
  primary_role?: string | null;
  primary_champions?: Array<Record<string, unknown>>;
}

export interface CoachDashboard {
  match_count?: number;
  win_rate?: number | null;
  primary_role?: string | null;
  averages?: {
    kills?: number;
    deaths?: number;
    assists?: number;
    cs_per_minute?: number;
    vision_score?: number;
    gold_earned?: number;
  };
  lane_opponent_comparison?: CoachLaneOpponentComparison;
  primary_champions?: Array<Record<string, unknown>>;
}

export interface CoachLaneOpponentComparison {
  sample_size?: number;
  player?: CoachComparisonStats;
  opponent?: CoachComparisonStats;
  delta?: CoachComparisonStats;
}

export interface CoachComparisonStats {
  kills?: number;
  deaths?: number;
  assists?: number;
  cs?: number;
  cs_per_minute?: number;
  vision_score?: number;
  gold_earned?: number;
}

export interface CoachLaneOpponent {
  champion_name?: string | null;
  kills?: number | null;
  deaths?: number | null;
  assists?: number | null;
  cs?: number | null;
  vision_score?: number | null;
  gold_earned?: number | null;
}

export interface CoachRecentMatch {
  match_id: string;
  champion_name?: string | null;
  role?: string | null;
  win?: boolean | null;
  kills?: number | null;
  deaths?: number | null;
  assists?: number | null;
  cs?: number | null;
  vision_score?: number | null;
  game_duration?: number | null;
  lane_opponent?: CoachLaneOpponent | null;
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
  dashboard?: CoachDashboard;
  recent_matches?: CoachRecentMatch[];
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

export interface PatchNoteAnnouncement {
  version: string;
  title: string;
  url: string;
  published_at?: string | null;
  summary: string;
  overview: string;
  analysis: {
    headline: string;
    sections: string[];
    takeaways: string[];
    details: Record<string, string[]>;
  };
}

export interface MatchTimelineResponse {
  match_id: string;
  frame_interval: number;
  frames: Record<string, unknown>[];
}

export interface MatchRecapInsight {
  type: string;
  severity: string;
  title: string;
  evidence: string[];
  recommendation: string;
}

export interface MatchRecapParticipant {
  puuid: string;
  participant_id: number;
  team_id?: number | null;
  champion_name?: string | null;
  team_position?: string | null;
}

export interface MatchRecapResponse {
  match_id: string;
  participant: MatchRecapParticipant;
  timeline_stats: {
    kills?: number;
    deaths?: number;
    assists?: number;
    early_deaths?: number;
    resource_deaths?: number;
    gold_at_10?: number | null;
    cs_at_10?: number | null;
    cs_per_min_at_10?: number | null;
    gold_at_14?: number | null;
    cs_at_14?: number | null;
    cs_per_min_at_14?: number | null;
  };
  match_phase_summary: Record<string, unknown>;
  resource_windows: Array<Record<string, unknown>>;
  key_events: Record<string, unknown>;
  insights: MatchRecapInsight[];
}

export interface CoachMatchTurningPoint {
  title: string;
  timestamp: number;
  explanation: string;
}

export interface CoachMatchRecapResponse {
  match_id: string;
  puuid: string;
  model?: string | null;
  timeline_stats: MatchRecapResponse['timeline_stats'];
  deterministic_insights: MatchRecapInsight[];
  recap: {
    summary: string;
    turning_points: CoachMatchTurningPoint[];
    strengths: string[];
    mistakes: string[];
    next_game_focus: string;
    follow_up_questions: string[];
  };
}

export type QueueType = 'RANKED_SOLO_5x5' | 'RANKED_FLEX_SR' | 'RANKED_TFT' | 'ARKANE';
export type RegionCode = 'kr' | 'na' | 'euw' | 'eune' | 'jp' | 'oce' | 'ru' | 'br' | 'las' | 'lan' | 'tr' | 'sg' | 'my' | 'ph' | 'th' | 'tw' | 'vn';
