import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RiotStatusCard } from '../RiotStatusCard';

const mockUseRiotStatus = vi.fn();

vi.mock('../../hooks/useRiotStatus', () => ({
  useRiotStatus: (platform: string) => mockUseRiotStatus(platform),
}));

describe('RiotStatusCard', () => {
  it('shows normal platform status when there are no maintenances or incidents', () => {
    mockUseRiotStatus.mockReturnValue({
      data: {
        id: 'TW2',
        name: 'Taiwan',
        maintenances: [],
        incidents: [],
      },
      isLoading: false,
      error: null,
    });

    render(<RiotStatusCard platform="tw2" />);

    expect(mockUseRiotStatus).toHaveBeenCalledWith('tw2');
    expect(screen.getByText('Riot 服务状态')).toBeInTheDocument();
    expect(screen.getByText('TW2')).toBeInTheDocument();
    expect(screen.getByText('服务正常')).toBeInTheDocument();
  });

  it('shows maintenance and incident counts', () => {
    mockUseRiotStatus.mockReturnValue({
      data: {
        id: 'NA1',
        name: 'North America',
        maintenances: [{ id: 1, titles: [{ locale: 'en_US', content: 'Maintenance' }] }],
        incidents: [{ id: 2, titles: [{ locale: 'en_US', content: 'Login issue' }] }],
      },
      isLoading: false,
      error: null,
    });

    render(<RiotStatusCard platform="na1" />);

    expect(screen.getByText('维护 1 项 · 异常 1 项')).toBeInTheDocument();
    expect(screen.getByText('Login issue')).toBeInTheDocument();
  });
});
