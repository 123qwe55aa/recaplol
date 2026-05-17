import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CoachPage } from '../Coach';
import type { CoachChatResponse, CoachReportResponse } from '../../types';

const mockUseCoachReport = vi.fn();
const mockUseGenerateCoachReport = vi.fn();
const mockUseCoachChat = vi.fn();

vi.mock('../../hooks/useCoach', () => ({
  useCoachReport: () => mockUseCoachReport(),
  useGenerateCoachReport: () => mockUseGenerateCoachReport(),
  useCoachChat: () => mockUseCoachChat(),
}));

const reportResponse: CoachReportResponse = {
  has_report: true,
  stale: false,
  generated_at: '2026-05-16T08:30:00Z',
  model: 'fake-coach',
  report: {
    summary: 'Your early deaths are slowing down otherwise playable games.',
    confidence: 0.82,
    data_window: {
      match_count: 20,
      started_at: '2026-05-10T00:00:00Z',
      ended_at: '2026-05-16T00:00:00Z',
      primary_role: 'MIDDLE',
    },
    dashboard: {
      match_count: 20,
      win_rate: 0.55,
      primary_role: 'MIDDLE',
      averages: {
        kills: 6.1,
        deaths: 7.8,
        assists: 8.4,
        cs_per_minute: 5.4,
        vision_score: 14,
      },
      lane_opponent_comparison: {
        sample_size: 2,
        player: {
          kills: 5.5,
          deaths: 6,
          assists: 10.5,
          cs_per_minute: 5.8,
          vision_score: 16,
          gold_earned: 10100,
        },
        opponent: {
          kills: 6,
          deaths: 5,
          assists: 8,
          cs_per_minute: 6.2,
          vision_score: 18,
          gold_earned: 10550,
        },
        delta: {
          kills: -0.5,
          deaths: 1,
          assists: 2.5,
          cs_per_minute: -0.4,
          vision_score: -2,
          gold_earned: -450,
        },
      },
    },
    recent_matches: [
      {
        match_id: 'NA1_1',
        champion_name: 'Ahri',
        role: 'MIDDLE',
        win: false,
        kills: 6,
        deaths: 8,
        assists: 9,
        cs: 164,
        vision_score: 14,
        game_duration: 1800,
        lane_opponent: {
          champion_name: 'Syndra',
          kills: 8,
          deaths: 6,
          assists: 7,
          cs: 181,
          vision_score: 17,
          gold_earned: 10600,
        },
      },
      {
        match_id: 'NA1_2',
        champion_name: 'Orianna',
        role: 'MIDDLE',
        win: true,
        kills: 5,
        deaths: 4,
        assists: 12,
        cs: 198,
        vision_score: 18,
        game_duration: 1900,
        lane_opponent: {
          champion_name: 'Viktor',
          kills: 4,
          deaths: 5,
          assists: 9,
          cs: 205,
          vision_score: 19,
          gold_earned: 10500,
        },
      },
    ],
    priorities: [
      {
        title: 'Reduce avoidable deaths',
        category: 'survivability',
        severity: 'high',
        rationale: 'You average 7.8 deaths in recent ranked games.',
        evidence: ['7.8 avg deaths', '42% win rate when behind'],
        action_items: ['Track enemy jungler before pushing', 'Reset after first objective'],
      },
      {
        title: 'Improve CS floor',
        category: 'economy',
        severity: 'medium',
        rationale: 'Your CS per minute trails role baseline.',
        evidence: ['5.4 CS/min'],
        action_items: ['Practice first 10 waves'],
      },
      {
        title: 'Ward around objectives',
        category: 'vision',
        severity: 'medium',
        rationale: 'Vision score dips before dragons.',
        evidence: ['14 avg vision score'],
        action_items: ['Place control ward before dragon setup'],
      },
    ],
  },
};

function renderPage(route = '/coach/test-puuid') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/coach/:puuid" element={<CoachPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('CoachPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGenerateCoachReport.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseCoachChat.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      error: null,
    });
  });

  it('renders no-report state with generate button', () => {
    mockUseCoachReport.mockReturnValue({
      data: { has_report: false, stale: false, report: null },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText('AI 教练')).toBeInTheDocument();
    expect(screen.getByText('还没有训练报告')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成训练报告' })).toBeInTheDocument();
  });

  it('renders report summary and three priority cards', () => {
    mockUseCoachReport.mockReturnValue({
      data: reportResponse,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText(reportResponse.report!.summary)).toBeInTheDocument();
    expect(screen.getByText('Reduce avoidable deaths')).toBeInTheDocument();
    expect(screen.getByText('Improve CS floor')).toBeInTheDocument();
    expect(screen.getByText('Ward around objectives')).toBeInTheDocument();
  });

  it('renders dashboard metrics and recent match table', () => {
    mockUseCoachReport.mockReturnValue({
      data: reportResponse,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText('训练仪表盘')).toBeInTheDocument();
    expect(screen.getByText('55%')).toBeInTheDocument();
    expect(screen.getByText('7.8')).toBeInTheDocument();
    expect(screen.getByText('最近比赛样本')).toBeInTheDocument();
    expect(screen.getByText('Ahri')).toBeInTheDocument();
    expect(screen.getByText('Orianna')).toBeInTheDocument();
  });

  it('renders same-role enemy comparison from the coach report', () => {
    mockUseCoachReport.mockReturnValue({
      data: reportResponse,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText('对位横向对比')).toBeInTheDocument();
    expect(screen.getByText('2 局同位置样本')).toBeInTheDocument();
    expect(screen.getByText('Syndra')).toBeInTheDocument();
    expect(screen.getByText('Viktor')).toBeInTheDocument();
    expect(screen.getByText('-0.4')).toBeInTheDocument();
    expect(screen.getByText('-450')).toBeInTheDocument();
  });

  it('renders empty comparison state when no same-role enemy sample exists', () => {
    const zeroSample: CoachReportResponse = {
      ...reportResponse,
      report: {
        ...reportResponse.report!,
        dashboard: {
          ...reportResponse.report!.dashboard!,
          lane_opponent_comparison: {
            sample_size: 0,
            player: {},
            opponent: {},
            delta: {},
          },
        },
      },
    };
    mockUseCoachReport.mockReturnValue({
      data: zeroSample,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText('对位横向对比')).toBeInTheDocument();
    expect(screen.getByText('当前样本里缺少可匹配的敌方同位置数据，暂时无法生成横向对比。')).toBeInTheDocument();
  });

  it('renders chat answer after submitting a follow-up question', async () => {
    const answer: CoachChatResponse = {
      answer: 'Start with wave state: crash, recall, and return with tempo.',
    };
    const mutateAsync = vi.fn().mockResolvedValue(answer);
    mockUseCoachReport.mockReturnValue({
      data: reportResponse,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCoachChat.mockReturnValue({
      mutateAsync,
      isPending: false,
      error: null,
    });

    renderPage();

    fireEvent.change(screen.getByPlaceholderText('问一个后续问题...'), {
      target: { value: 'How do I die less in lane?' },
    });
    fireEvent.submit(screen.getByTestId('coach-chat-form'));

    await waitFor(() => {
      expect(screen.getByText(answer.answer)).toBeInTheDocument();
    });
    expect(mutateAsync).toHaveBeenCalledWith('How do I die less in lane?');
  });

  it('shows thinking state while follow-up answer is pending', () => {
    mockUseCoachReport.mockReturnValue({
      data: reportResponse,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCoachChat.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: true,
      error: null,
    });

    renderPage();

    expect(screen.getByText('AI 正在思考...')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    const refetch = vi.fn();
    mockUseCoachReport.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: new Error('Report failed'),
      refetch,
    });

    renderPage();

    expect(screen.getByText('训练报告加载失败')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(refetch).toHaveBeenCalled();
  });
});
