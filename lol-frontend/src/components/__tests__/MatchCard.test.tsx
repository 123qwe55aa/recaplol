import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MatchCard } from '../MatchCard';
import type { Match } from '../../types';

function makeMatch(outcome: 'WIN' | 'LOSS' | 'REMAKE'): Match {
  return {
    matchId: 'NA1_123',
    queueType: 'CLASSIC',
    gameCreation: Date.now(),
    gameDuration: outcome === 'REMAKE' ? 210 : 1800,
    participants: [
      {
        puuid: 'player-puuid',
        gameName: 'Tester',
        tagLine: 'NA1',
        teamId: 100,
        championId: 103,
        championName: 'Ahri',
        kills: 0,
        deaths: 0,
        assists: 0,
        goldEarned: 1200,
        items: [],
        itemImages: [],
        summonerSpells: [],
        win: outcome === 'WIN',
        outcome,
        position: 'MID',
      },
    ],
  };
}

describe('MatchCard', () => {
  it('renders remake separately from losses', () => {
    render(<MatchCard match={makeMatch('REMAKE')} puuid="player-puuid" />);

    expect(screen.getByText('重开')).toBeInTheDocument();
    expect(screen.queryByText('失败')).not.toBeInTheDocument();
  });

  it('renders deep recap as an icon action inside the card', () => {
    const onDeepRecap = vi.fn();
    render(
      <MatchCard
        match={makeMatch('WIN')}
        puuid="player-puuid"
        onDeepRecap={onDeepRecap}
      />
    );

    const button = screen.getByRole('button', { name: '深度复盘' });
    expect(button).toHaveAttribute('title', '深度复盘');

    fireEvent.click(button);

    expect(onDeepRecap).toHaveBeenCalledTimes(1);
  });

  it('shows loading state for the deep recap icon action', () => {
    render(
      <MatchCard
        match={makeMatch('WIN')}
        puuid="player-puuid"
        onDeepRecap={() => undefined}
        isDeepRecapLoading
      />
    );

    const button = screen.getByRole('button', { name: '正在生成深度复盘' });
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent('...');
  });
});
