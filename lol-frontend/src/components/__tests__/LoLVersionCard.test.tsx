import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LoLVersionCard } from '../LoLVersionCard';

const mockUseLolVersion = vi.fn();

vi.mock('../../hooks/useLolVersion', () => ({
  useLolVersion: () => mockUseLolVersion(),
}));

describe('LoLVersionCard', () => {
  it('shows the latest LoL client version with mirror and Taiwan official links', () => {
    mockUseLolVersion.mockReturnValue({
      data: '26.10.1',
      isLoading: false,
      error: null,
    });

    render(<LoLVersionCard />);

    expect(screen.getByText('LoL 客户端版本')).toBeInTheDocument();
    expect(screen.getByText('26.10.1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看版本更新（镜像）' })).toHaveAttribute(
      'href',
      'https://leagueoflegends.fandom.com/wiki/Patch_(League_of_Legends)'
    );
    expect(screen.getByRole('link', { name: '台服官方链接' })).toHaveAttribute(
      'href',
      'https://www.leagueoflegends.com/zh-tw/news/tags/patch-notes/'
    );
  });

  it('shows a loading state while checking the version', () => {
    mockUseLolVersion.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<LoLVersionCard />);

    expect(screen.getByText('正在检查版本...')).toBeInTheDocument();
  });

  it('shows a fallback message when the version request fails', () => {
    mockUseLolVersion.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('network failed'),
    });

    render(<LoLVersionCard />);

    expect(screen.getByText('暂时无法获取版本')).toBeInTheDocument();
  });
});
