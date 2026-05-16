import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { Analysis } from '../Analysis';

vi.mock('../../hooks/useStats', () => ({
  useStats: () => ({
    data: {
      gamesPlayed: 20,
      winRate: 52.5,
      kda: 3.1,
      avgKills: 7.2,
      avgDeaths: 4.4,
      avgAssists: 8.1,
    },
    isLoading: false,
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/analysis/test-puuid']}>
      <Routes>
        <Route path="/analysis/:puuid" element={<Analysis />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('Analysis', () => {
  it('links to the AI coach page for the current player', () => {
    renderPage();

    const link = screen.getByRole('link', { name: /打开 AI 教练/i });
    expect(screen.getByText('AI 教练')).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/coach/test-puuid');
  });
});
