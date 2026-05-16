import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChampionLookupPage } from '../ChampionLookup';

vi.mock('../../hooks/useChampionBuild', () => ({
  useChampionBuild: vi.fn((_champion: string, enabled: boolean) => ({
    data: null,
    isLoading: enabled,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

function renderPage(initialEntries = ['/champion-lookup']) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/champion-lookup" element={<ChampionLookupPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ChampionLookupPage', () => {
  it('renders lookup entry page', () => {
    renderPage();
    expect(screen.getByText('OP.GG 聚合查询')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/输入英雄名字/i)).toBeInTheDocument();
  });

  it('submits champion search from input', async () => {
    renderPage();

    const input = screen.getByPlaceholderText(/输入英雄名字/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Ahri' } });
    fireEvent.click(screen.getByRole('button', { name: '立即抓取' }));

    expect(await screen.findByText(/正在抓取/i)).toBeInTheDocument();
  });
});
