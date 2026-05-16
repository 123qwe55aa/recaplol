import { describe, expect, it, vi } from 'vitest';

const axiosMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  create: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: axiosMocks.create,
  },
}));

describe('api service', () => {
  it('allows match sync requests enough time to fetch and store recent Riot matches', async () => {
    axiosMocks.post.mockResolvedValue({ data: { fetched: 190, match_count: 20 } });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { fetchPlayerMatches } = await import('../api');

    await fetchPlayerMatches('test-puuid', 20, 'sea');

    expect(axiosMocks.post).toHaveBeenCalledWith(
      '/matches/fetch/test-puuid',
      null,
      {
        params: { limit: 20, region: 'sea' },
        timeout: 60000,
      }
    );
  });
});
