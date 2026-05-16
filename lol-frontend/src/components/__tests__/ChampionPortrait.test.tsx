import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChampionPortrait } from '../ChampionPortrait';

describe('ChampionPortrait', () => {
  it('renders with correct size class for sm', () => {
    const { container } = render(<ChampionPortrait championName="Ahri" size="sm" />);
    const div = container.querySelector('.w-10');
    expect(div).toBeInTheDocument();
  });

  it('renders with correct size class for md', () => {
    const { container } = render(<ChampionPortrait championName="Ahri" size="md" />);
    const div = container.querySelector('.w-16');
    expect(div).toBeInTheDocument();
  });

  it('renders with correct size class for lg', () => {
    const { container } = render(<ChampionPortrait championName="Ahri" size="lg" />);
    const div = container.querySelector('.w-24');
    expect(div).toBeInTheDocument();
  });

  it('renders champion name when showName is true', () => {
    render(<ChampionPortrait championName="Ahri" showName={true} />);
    expect(screen.getByText('Ahri')).toBeInTheDocument();
  });

  it('does not render champion name when showName is false', () => {
    const { container } = render(<ChampionPortrait championName="Ahri" showName={false} />);
    expect(container.querySelector('.text-xs')).toBeNull();
  });

  it('constructs correct CDN URL', () => {
    const { container } = render(<ChampionPortrait championName="Lee Sin" />);
    const img = container.querySelector('img');
    expect(img?.getAttribute('src')).toContain('ddragon.leagueoflegends.com/cdn/16.5.1/img/champion/Lee%20Sin.png');
  });

  it('handles champion name with special characters', () => {
    const { container } = render(<ChampionPortrait championName="Kai'Sa" />);
    const img = container.querySelector('img');
    // The apostrophe is not encoded by encodeURIComponent
    expect(img?.getAttribute('src')).toContain("Kai'Sa.png");
  });
});
