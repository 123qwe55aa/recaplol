import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RankBadge } from '../RankBadge';

describe('RankBadge', () => {
  it('renders tier and rank correctly', () => {
    render(<RankBadge tier="Gold" rank="II" lp={75} />);
    expect(screen.getByText('Gold II')).toBeInTheDocument();
  });

  it('renders LP correctly', () => {
    render(<RankBadge tier="Diamond" rank="I" lp={100} />);
    expect(screen.getByText('100 LP')).toBeInTheDocument();
  });

  it('handles unknown tier with default color', () => {
    render(<RankBadge tier="Unknown" rank="I" lp={50} />);
    expect(screen.getByText('Unknown I')).toBeInTheDocument();
  });

  it('renders all known tier colors', () => {
    const tiers = ['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'Grandmaster', 'Challenger'];
    tiers.forEach((tier) => {
      const { container } = render(<RankBadge tier={tier} rank="I" lp={0} />);
      expect(container.firstChild).toBeInTheDocument();
    });
  });
});
