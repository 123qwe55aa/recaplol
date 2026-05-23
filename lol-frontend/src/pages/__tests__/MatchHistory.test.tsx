import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchHistory } from '../MatchHistory';

const getPlayerMatchesWithDetails = vi.fn();
const fetchPlayerMatches = vi.fn();
const fetchMatchTimeline = vi.fn();
const generateAiMatchRecap = vi.fn();
const getSavedAiMatchRecap = vi.fn();

vi.mock('../../services/api', () => ({
  getPlayerMatchesWithDetails: (...args: unknown[]) => getPlayerMatchesWithDetails(...args),
  fetchPlayerMatches: (...args: unknown[]) => fetchPlayerMatches(...args),
  fetchMatchTimeline: (...args: unknown[]) => fetchMatchTimeline(...args),
  generateAiMatchRecap: (...args: unknown[]) => generateAiMatchRecap(...args),
  getSavedAiMatchRecap: (...args: unknown[]) => getSavedAiMatchRecap(...args),
}));

function renderPage(route = '/matches/test-puuid') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/matches/:puuid" element={<MatchHistory />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('MatchHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getPlayerMatchesWithDetails.mockResolvedValue({ matches: [], total: 0 });
    fetchPlayerMatches.mockResolvedValue({ fetched: 10, match_count: 10 });
    fetchMatchTimeline.mockResolvedValue({ match_id: 'NA1_123', frame_interval: 60000, frames: [] });
    getSavedAiMatchRecap.mockResolvedValue(null);
    generateAiMatchRecap.mockResolvedValue({
      match_id: 'NA1_123',
      puuid: 'test-puuid',
      model: 'fake-match-ai',
      timeline_stats: {
        early_deaths: 1,
        resource_deaths: 1,
        cs_per_min_at_10: 5,
        gold_at_10: 3000,
      },
      deterministic_insights: [
        {
          type: 'resource_death',
          severity: 'high',
          title: '关键资源前阵亡',
          evidence: ['资源前 90 秒内死亡 1 次'],
          recommendation: '资源前 90 秒先补视野。',
        },
      ],
      recap: {
        summary: '这局阿狸的问题集中在小龙前阵亡。',
        turning_points: [
          {
            title: '关键资源前阵亡',
            timestamp: 600000,
            explanation: '你在小龙前阵亡，队伍无法正面争夺。',
          },
        ],
        strengths: ['对线补刀还能接受'],
        mistakes: ['资源前没有先处理视野和站位'],
        next_game_focus: '资源前 90 秒先补视野。',
        follow_up_questions: ['这波小龙前应该怎么站位？'],
      },
    });
  });

  it('syncs latest matches when opened and then refreshes match details', async () => {
    renderPage();

    await waitFor(() => {
      expect(fetchPlayerMatches).toHaveBeenCalledWith('test-puuid', 20, 'americas');
    });

    await waitFor(() => {
      expect(getPlayerMatchesWithDetails).toHaveBeenCalledTimes(2);
    });

    expect(screen.getByText(/最新战绩已同步（新增 10 场）/i)).toBeInTheDocument();
  });

  it('shows up-to-date message when sync returns no new matches', async () => {
    fetchPlayerMatches.mockResolvedValue({ fetched: 0, match_count: 10 });
    renderPage();

    await waitFor(() => {
      expect(fetchPlayerMatches).toHaveBeenCalledWith('test-puuid', 20, 'americas');
    });

    expect(screen.getByText(/战绩已是最新，无需同步/i)).toBeInTheDocument();
  });

  it('uses route region query when syncing latest matches', async () => {
    renderPage('/matches/test-puuid?region=sea');

    await waitFor(() => {
      expect(fetchPlayerMatches).toHaveBeenCalledWith('test-puuid', 20, 'sea');
    });
  });

  it('loads deep recap for a match', async () => {
    getPlayerMatchesWithDetails.mockResolvedValue({
      total: 1,
      matches: [
        {
          matchId: 'NA1_123',
          queueType: 'CLASSIC',
          gameCreation: Date.now(),
          gameDuration: 1800,
          participants: [
            {
              puuid: 'test-puuid',
              gameName: 'Tester',
              tagLine: 'NA1',
              teamId: 100,
              championId: 103,
              championName: 'Ahri',
              kills: 3,
              deaths: 4,
              assists: 5,
              goldEarned: 10000,
              items: [],
              itemImages: [],
              summonerSpells: [],
              win: false,
              position: 'MID',
            },
          ],
        },
      ],
    });

    renderPage();

    const button = await screen.findByRole('button', { name: '深度复盘' });
    fireEvent.click(button);

    await waitFor(() => {
      expect(fetchMatchTimeline).toHaveBeenCalledWith('NA1_123');
      expect(generateAiMatchRecap).toHaveBeenCalledWith('NA1_123', 'test-puuid');
    });
    await waitFor(() => {
      expect(screen.getAllByText('关键资源前阵亡').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('这局阿狸的问题集中在小龙前阵亡。')).toBeInTheDocument();
    expect(screen.getByText('资源前 90 秒先补视野。')).toBeInTheDocument();
  });

  it('shows saved AI recap when match history is opened again', async () => {
    getPlayerMatchesWithDetails.mockResolvedValue({
      total: 1,
      matches: [
        {
          matchId: 'NA1_123',
          queueType: 'CLASSIC',
          gameCreation: Date.now(),
          gameDuration: 1800,
          participants: [
            {
              puuid: 'test-puuid',
              gameName: 'Tester',
              tagLine: 'NA1',
              teamId: 100,
              championId: 103,
              championName: 'Ahri',
              kills: 3,
              deaths: 4,
              assists: 5,
              goldEarned: 10000,
              items: [],
              itemImages: [],
              summonerSpells: [],
              win: false,
              position: 'MID',
            },
          ],
        },
      ],
    });
    getSavedAiMatchRecap.mockResolvedValue({
      match_id: 'NA1_123',
      puuid: 'test-puuid',
      model: 'fake-match-ai',
      timeline_stats: {
        early_deaths: 0,
        resource_deaths: 0,
        cs_per_min_at_10: 7,
        gold_at_10: 3200,
      },
      deterministic_insights: [],
      recap: {
        summary: '这是已经保存过的 AI 复盘。',
        turning_points: [],
        strengths: ['对线稳定'],
        mistakes: ['资源前站位还可以更早'],
        next_game_focus: '提前布置小龙视野。',
        follow_up_questions: [],
      },
    });

    renderPage();

    await waitFor(() => {
      expect(getSavedAiMatchRecap).toHaveBeenCalledWith('NA1_123', 'test-puuid');
    });
    expect(await screen.findByText('这是已经保存过的 AI 复盘。')).toBeInTheDocument();
  });
});
