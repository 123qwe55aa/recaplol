import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchHistory } from '../MatchHistory';

const getPlayerMatchesWithDetails = vi.fn();
const fetchPlayerMatches = vi.fn();
const fetchMatchTimeline = vi.fn();
const getMatchRecap = vi.fn();

vi.mock('../../services/api', () => ({
  getPlayerMatchesWithDetails: (...args: unknown[]) => getPlayerMatchesWithDetails(...args),
  fetchPlayerMatches: (...args: unknown[]) => fetchPlayerMatches(...args),
  fetchMatchTimeline: (...args: unknown[]) => fetchMatchTimeline(...args),
  getMatchRecap: (...args: unknown[]) => getMatchRecap(...args),
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
    getMatchRecap.mockResolvedValue({
      match_id: 'NA1_123',
      participant: {
        puuid: 'test-puuid',
        participant_id: 1,
        champion_name: 'Ahri',
        team_position: 'MID',
      },
      timeline_stats: {
        early_deaths: 1,
        resource_deaths: 1,
        cs_per_min_at_10: 5,
        gold_at_10: 3000,
      },
      match_phase_summary: {},
      resource_windows: [],
      key_events: {},
      insights: [
        {
          type: 'resource_death',
          severity: 'high',
          title: '关键资源前阵亡',
          evidence: ['资源前 90 秒内死亡 1 次'],
          recommendation: '资源前 90 秒先补视野。',
        },
      ],
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

    expect(screen.getByText(/最新战绩已同步/i)).toBeInTheDocument();
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
      expect(getMatchRecap).toHaveBeenCalledWith('NA1_123', 'test-puuid');
    });
    expect(await screen.findByText('关键资源前阵亡')).toBeInTheDocument();
    expect(screen.getByText('资源前 90 秒先补视野。')).toBeInTheDocument();
  });
});
