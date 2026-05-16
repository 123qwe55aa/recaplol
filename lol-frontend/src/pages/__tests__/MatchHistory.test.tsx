import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchHistory } from '../MatchHistory';

const getPlayerMatchesWithDetails = vi.fn();
const fetchPlayerMatches = vi.fn();

vi.mock('../../services/api', () => ({
  getPlayerMatchesWithDetails: (...args: unknown[]) => getPlayerMatchesWithDetails(...args),
  fetchPlayerMatches: (...args: unknown[]) => fetchPlayerMatches(...args),
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
});
