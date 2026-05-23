import { beforeEach, describe, expect, it, vi } from 'vitest';

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
  beforeEach(() => {
    vi.resetModules();
    axiosMocks.get.mockReset();
    axiosMocks.post.mockReset();
    axiosMocks.create.mockReset();
  });

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

  it('allows AI match recap requests enough time for slow coach providers', async () => {
    axiosMocks.post.mockResolvedValue({ data: { match_id: 'TW2_414414169' } });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { generateAiMatchRecap } = await import('../api');

    await generateAiMatchRecap('TW2_414414169', 'test-puuid');

    expect(axiosMocks.post).toHaveBeenCalledWith(
      '/coach/matches/TW2_414414169/recap/test-puuid',
      null,
      {
        timeout: 600000,
      }
    );
  });

  it('allows AI coach report generation enough time for slow coach providers', async () => {
    axiosMocks.post.mockResolvedValue({ data: { has_report: true, report: null } });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { generateCoachReport } = await import('../api');

    await generateCoachReport('test-puuid', true);

    expect(axiosMocks.post).toHaveBeenCalledWith(
      '/coach/players/test-puuid/report',
      { force: true },
      {
        timeout: 600000,
      }
    );
  });

  it('allows AI coach chat enough time for slow coach providers', async () => {
    axiosMocks.post.mockResolvedValue({ data: { answer: 'ok' } });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { sendCoachQuestion } = await import('../api');

    await sendCoachQuestion('test-puuid', 'How do I die less?');

    expect(axiosMocks.post).toHaveBeenCalledWith(
      '/coach/players/test-puuid/chat',
      { question: 'How do I die less?' },
      {
        timeout: 600000,
      }
    );
  });

  it('fetches the latest League of Legends Data Dragon version', async () => {
    axiosMocks.get.mockResolvedValue({ data: ['26.10.1', '26.9.1'] });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { getLatestLolVersion } = await import('../api');

    await expect(getLatestLolVersion()).resolves.toBe('26.10.1');
    expect(axiosMocks.get).toHaveBeenCalledWith(
      'https://ddragon.leagueoflegends.com/api/versions.json'
    );
  });
});
