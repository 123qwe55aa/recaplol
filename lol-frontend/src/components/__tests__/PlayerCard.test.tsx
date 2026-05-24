import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlayerCard } from '../PlayerCard';
import type { Player } from '../../types';

describe('PlayerCard', () => {
  const mockPlayer: Player = {
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
    recentChampions: [1, 2, 3],
  };

  it('renders player name and tagLine', () => {
    render(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('TestPlayer')).toBeInTheDocument();
    expect(screen.getByText('#NA1')).toBeInTheDocument();
  });

  it('renders player level', () => {
    render(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('等级 150')).toBeInTheDocument();
  });

  it('renders wins and losses', () => {
    render(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('105W')).toBeInTheDocument();
    expect(screen.getByText('95L')).toBeInTheDocument();
  });

  it('renders win rate with correct color class for >= 50%', () => {
    const { container } = render(<PlayerCard player={mockPlayer} />);
    const winRateEl = container.querySelector('.text-green-400');
    expect(winRateEl).toBeInTheDocument();
    expect(winRateEl?.textContent).toBe('52.5%');
  });

  it('renders win rate with red color for < 50%', () => {
    const lowWinRatePlayer: Player = {
      ...mockPlayer,
      winRate: 45.0,
    };
    const { container } = render(<PlayerCard player={lowWinRatePlayer} />);
    const winRateEl = container.querySelector('.text-red-400');
    expect(winRateEl).toBeInTheDocument();
    expect(winRateEl?.textContent).toBe('45.0%');
  });

  it('renders recent champions when present', () => {
    render(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('最近使用')).toBeInTheDocument();
  });

  it('does not render recent champions section when empty', () => {
    const playerNoRecent: Player = {
      ...mockPlayer,
      recentChampions: [],
    };
    const { queryByText } = render(<PlayerCard player={playerNoRecent} />);
    expect(queryByText('最近使用')).toBeNull();
  });

  it('renders RankBadge component', () => {
    render(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('Gold II')).toBeInTheDocument();
    expect(screen.getByText('75 LP')).toBeInTheDocument();
  });

  it('shows solo unavailable placeholders when ranked data is unavailable', () => {
    const unavailablePlayer: Player = {
      ...mockPlayer,
      tier: 'UNRANKED',
      rank: 'UNRANKED',
      lp: 0,
      wins: 0,
      losses: 0,
      winRate: 0,
      rankedStatus: 'ranked_empty_from_riot',
    };
    render(<PlayerCard player={unavailablePlayer} />);
    expect(screen.getByText('SOLO 暂不可用')).toBeInTheDocument();
    expect(screen.getByText('-- LP')).toBeInTheDocument();
  });

});
