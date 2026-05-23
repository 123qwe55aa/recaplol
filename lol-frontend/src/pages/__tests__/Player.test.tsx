import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { PlayerPage } from '../Player';
import type { Player } from '../../types';

const mockUsePlayer = vi.fn();
const mockUseChampionMastery = vi.fn();
const mockUseLolVersion = vi.fn();
const mockUseCoachChat = vi.fn();

vi.mock('../../hooks/usePlayer', () => ({
  usePlayer: () => mockUsePlayer(),
  useChampionMastery: () => mockUseChampionMastery(),
}));

vi.mock('../../hooks/useLolVersion', () => ({
  useLolVersion: () => mockUseLolVersion(),
}));

vi.mock('../../hooks/useCoach', () => ({
  useCoachChat: () => mockUseCoachChat(),
}));

vi.mock('../../services/api', () => ({
  refreshPlayerByPuuid: vi.fn(),
}));

const player: Player = {
  puuid: 'test-puuid',
  gameName: 'TestPlayer',
  tagLine: 'NA1',
  level: 150,
  rank: 'II',
  tier: 'Gold',
  lp: 75,
  winRate: 52.5,
  wins: 105,
  losses: 95,
  recentChampions: [],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/player/TestPlayer/NA1']}>
      <Routes>
        <Route path="/player/:gameName/:tagLine" element={<PlayerPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('PlayerPage', () => {
  it('renders LoL version information and embedded AI coach chat', () => {
    mockUsePlayer.mockReturnValue({
      data: player,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseChampionMastery.mockReturnValue({ data: { champion_masteries: [] } });
    mockUseLolVersion.mockReturnValue({
      data: '26.10.1',
      isLoading: false,
      error: null,
    });
    mockUseCoachChat.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      error: null,
    });

    renderPage();

    expect(screen.getByText('LoL 客户端版本')).toBeInTheDocument();
    expect(screen.getByText('26.10.1')).toBeInTheDocument();
    expect(screen.getByText('问 AI Coach')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开完整 AI 教练' })).toHaveAttribute(
      'href',
      '/coach/test-puuid'
    );
  });
});
