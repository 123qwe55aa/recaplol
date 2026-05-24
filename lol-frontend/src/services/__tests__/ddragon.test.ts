import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('Data Dragon service', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('normalizes Riot client versions before building item icon URLs', async () => {
    const { buildDdragonAssetUrl, buildItemIconUrl, normalizeDdragonVersion } = await import('../ddragon');

    expect(normalizeDdragonVersion('16.10.760.9485')).toBe('16.10.1');
    expect(buildItemIconUrl(3089, '16.10.760.9485')).toBe(
      'https://ddragon.leagueoflegends.com/cdn/16.10.1/img/item/3089.png'
    );
    expect(buildDdragonAssetUrl('perk-images/Styles/Sorcery/Scorch/Scorch.png')).toBe(
      'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Scorch/Scorch.png'
    );
  });

  it('loads champion id metadata from Data Dragon and caches by version and locale', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        data: {
          Aatrox: { id: 'Aatrox', key: '266', name: 'Aatrox' },
          LeeSin: { id: 'LeeSin', key: '64', name: 'Lee Sin' },
        },
      }),
    }));
    vi.stubGlobal('fetch', fetchMock);

    const { loadChampionByIdMap } = await import('../ddragon');

    await expect(loadChampionByIdMap('16.10.760.9485')).resolves.toEqual({
      64: { id: 'LeeSin', key: 64, name: 'Lee Sin' },
      266: { id: 'Aatrox', key: 266, name: 'Aatrox' },
    });
    await loadChampionByIdMap('16.10.1');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      'https://ddragon.leagueoflegends.com/cdn/16.10.1/data/en_US/champion.json'
    );
  });
});
