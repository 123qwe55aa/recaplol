import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LoLPatchAnnouncementCard } from '../LoLPatchAnnouncementCard';

const mockUsePatchAnnouncement = vi.fn();

vi.mock('../../hooks/usePatchAnnouncement', () => ({
  usePatchAnnouncement: () => mockUsePatchAnnouncement(),
}));

describe('LoLPatchAnnouncementCard', () => {
  it('renders the latest patch note announcement and parsed takeaways', () => {
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

    render(<LoLPatchAnnouncementCard />);

    expect(screen.getByText('LoL 版本公告')).toBeInTheDocument();
    expect(screen.getByText('《英雄聯盟》26.10版本更新公告')).toBeInTheDocument();
    expect(screen.getByText('26.10 版本重點解析')).toBeInTheDocument();
    expect(screen.getByText(/英雄：安比薩獲得上路和打野方向調整。/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看官方原文' })).toHaveAttribute(
      'href',
      'https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/'
    );
  });

  it('renders a loading state', () => {
    mockUsePatchAnnouncement.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<LoLPatchAnnouncementCard />);

    expect(screen.getByText('正在读取台服最新版本公告...')).toBeInTheDocument();
  });
});
