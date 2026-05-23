import { fireEvent, render, screen } from '@testing-library/react';
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
          details: {
            英雄: ['安妮：Q 傷害提升', '安比薩：傷害提升', '安比薩：治療百分比提升', '艾希：W 傷害提升', '加里欧：Q 冷卻調整'],
            道具: ['道具 多兰之盔：生命 ：110 ⇒ 140', '多蘭之盔：價格調整'],
            符文: ['冥火之触：傷害降低', '冥火之觸：冷卻時間調整'],
          },
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
    expect(screen.getByText('平衡性变更概览')).toBeInTheDocument();
    expect(screen.getAllByText('英雄').length).toBeGreaterThan(0);
    expect(screen.getAllByText('道具').length).toBeGreaterThan(0);
    expect(screen.getAllByText('符文').length).toBeGreaterThan(0);
    expect(screen.getByText('⚔')).toBeInTheDocument();
    expect(screen.getByText('🛡')).toBeInTheDocument();
    expect(screen.getByText('✦')).toBeInTheDocument();
    expect(screen.queryByText('安比薩：傷害提升')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '展开完整版本清单' }));
    expect(screen.getByAltText('安妮 图标')).toHaveAttribute(
      'src',
      'https://ddragon.leagueoflegends.com/cdn/16.10.1/img/champion/Annie.png'
    );
    expect(screen.getByAltText('艾希 图标')).toHaveAttribute(
      'src',
      'https://ddragon.leagueoflegends.com/cdn/16.10.1/img/champion/Ashe.png'
    );
    expect(screen.getByAltText('加里欧 图标')).toHaveAttribute(
      'src',
      'https://ddragon.leagueoflegends.com/cdn/16.10.1/img/champion/Galio.png'
    );
    expect(screen.getByAltText('道具 多兰之盔 图标')).toHaveAttribute(
      'src',
      'https://ddragon.leagueoflegends.com/cdn/16.10.1/img/item/1120.png'
    );
    expect(screen.getByAltText('冥火之触 图标')).toHaveAttribute(
      'src',
      'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Scorch/Scorch.png'
    );
    expect(screen.getByText(/安妮：Q 傷害提升/)).toBeInTheDocument();
    expect(screen.getByText(/安比薩：傷害提升/)).toBeInTheDocument();
    expect(screen.getByText(/安比薩：治療百分比提升/)).toBeInTheDocument();
    expect(screen.getByText(/艾希：W 傷害提升/)).toBeInTheDocument();
    expect(screen.getByText(/加里欧：Q 冷卻調整/)).toBeInTheDocument();
    expect(screen.getByText(/道具 多兰之盔：生命 ：110 ⇒ 140/)).toBeInTheDocument();
    expect(screen.getByText(/多蘭之盔：價格調整/)).toBeInTheDocument();
    expect(screen.getByText(/冥火之触：傷害降低/)).toBeInTheDocument();
    expect(screen.getByText(/冥火之觸：冷卻時間調整/)).toBeInTheDocument();
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
