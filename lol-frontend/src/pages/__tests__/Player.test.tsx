import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { PlayerPage } from '../Player';
import type { Player } from '../../types';

const mockUsePlayer = vi.fn();
const mockUseChampionMastery = vi.fn();
const mockUseLolVersion = vi.fn();
const mockUsePatchAnnouncement = vi.fn();
const mockUseCoachChat = vi.fn();

vi.mock('../../hooks/usePlayer', () => ({
  usePlayer: () => mockUsePlayer(),
  useChampionMastery: () => mockUseChampionMastery(),
}));

vi.mock('../../hooks/useLolVersion', () => ({
  useLolVersion: () => mockUseLolVersion(),
}));

vi.mock('../../hooks/usePatchAnnouncement', () => ({
  usePatchAnnouncement: () => mockUsePatchAnnouncement(),
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
    mockUsePatchAnnouncement.mockReturnValue({
      data: {
        version: '26.10',
        title: '《英雄聯盟》26.10版本更新公告',
        url: 'https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/',
        published_at: '2026-05-12T18:00:00.000Z',
        summary: '26.10版本登場，群魔繼續亂舞！',
        overview: '我們針對近期第二賽季的改動做了一些後續調整。',
        analysis: {
          headline: '26.10 版本重點解析',
          sections: ['版本概要', '英雄', '道具'],
          takeaways: ['英雄：安比薩獲得上路和打野方向調整。'],
        },
      },
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
    expect(screen.getByText('LoL 版本公告')).toBeInTheDocument();
    expect(screen.getByText('《英雄聯盟》26.10版本更新公告')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '问 AI Coach' })).toBeInTheDocument();
  });
});
