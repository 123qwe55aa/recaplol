import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { PlayerCoachChatPanel } from '../PlayerCoachChatPanel';

const mockUseCoachChat = vi.fn();

vi.mock('../../hooks/useCoach', () => ({
  useCoachChat: () => mockUseCoachChat(),
}));

describe('PlayerCoachChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends a question to AI coach and renders the answer', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ answer: '先减少无视野压线死亡。' });
    mockUseCoachChat.mockReturnValue({
      mutateAsync,
      isPending: false,
      error: null,
    });

    render(
      <MemoryRouter>
        <PlayerCoachChatPanel puuid="test-puuid" />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('问 AI Coach 一个问题...'), {
      target: { value: '我该先练什么？' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith('我该先练什么？');
    });
    expect(await screen.findByText('先减少无视野压线死亡。')).toBeInTheDocument();
  });

  it('links to the full coach page for report generation and detail review', () => {
    mockUseCoachChat.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      error: null,
    });

    render(
      <MemoryRouter>
        <PlayerCoachChatPanel puuid="test-puuid" />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: '打开完整 AI 教练' })).toHaveAttribute(
      'href',
      '/coach/test-puuid'
    );
  });
});
