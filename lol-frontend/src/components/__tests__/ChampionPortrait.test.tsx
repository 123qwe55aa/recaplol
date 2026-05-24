import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ChampionPortrait } from '../ChampionPortrait';

vi.mock('../../services/championIcon', () => ({
  resolveChampionIconUrl: vi.fn(async (name: string) => `https://ddragon.leagueoflegends.com/cdn/16.10.1/img/champion/${name.replace(/[^A-Za-z0-9]/g, '') || 'Aatrox'}.png`),
  resolveChampionIconUrlByKey: vi.fn(async (key: string) => `https://ddragon.leagueoflegends.com/cdn/16.10.1/img/champion/${key.replace(/[^A-Za-z0-9]/g, '') || 'Aatrox'}.png`),
  getLatestDdragonVersion: vi.fn(async () => '16.10.1'),
  getFallbackChampionIconUrl: vi.fn((version: string) => `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/Aatrox.png`),
}));

describe('ChampionPortrait', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  it('uses resolved CDN URL from champion icon service', async () => {
    const { container } = render(<ChampionPortrait championName="Lee Sin" />);
    await waitFor(() => {
      const img = container.querySelector('img');
      expect(img?.getAttribute('src')).toContain('ddragon.leagueoflegends.com/cdn/16.10.1/img/champion/LeeSin.png');
    });
  });

  it('handles champion name with special characters via resolver', async () => {
    const { container } = render(<ChampionPortrait championName="Kai'Sa" />);
    await waitFor(() => {
      const img = container.querySelector('img');
      expect(img?.getAttribute('src')).toContain('KaiSa.png');
    });
  });
});
