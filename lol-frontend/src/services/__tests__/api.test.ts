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

  it('fetches the latest League of Legends patch announcement', async () => {
    const announcement = {
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
    };
    axiosMocks.get.mockResolvedValue({ data: announcement });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { getLatestPatchAnnouncement } = await import('../api');

    await expect(getLatestPatchAnnouncement()).resolves.toEqual(announcement);
    expect(axiosMocks.get).toHaveBeenCalledWith('/patch-notes/latest');
  });

  it('fetches Riot platform status through the backend proxy', async () => {
    const status = {
      id: 'TW2',
      name: 'Taiwan',
      maintenances: [],
      incidents: [],
    };
    axiosMocks.get.mockResolvedValue({ data: status });
    axiosMocks.create.mockReturnValue({
      get: axiosMocks.get,
      post: axiosMocks.post,
    });

    const { getRiotPlatformStatus } = await import('../api');

    await expect(getRiotPlatformStatus('tw2')).resolves.toEqual(status);
    expect(axiosMocks.get).toHaveBeenCalledWith('/riot/status/tw2');
  });
});
