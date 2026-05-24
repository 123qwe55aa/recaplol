import { useQuery } from '@tanstack/react-query';
import { getChampionBuild } from '../services/api';
import type { RegionCode, QueueType } from '../types';

interface UseChampionBuildOptions {
  region?: RegionCode;
  queue?: QueueType;
  tier?: string;
  countersCount?: number;
  role?: string;
  refresh?: boolean;
}

export const useChampionBuild = (
  champName: string,
  enabled: boolean,
  options: UseChampionBuildOptions = {}
) => {
  const {
    region = 'kr',
    queue = 'RANKED_SOLO_5x5',
    tier = 'overall',
    countersCount = 5,
    role = '',
    refresh = false,
  } = options;

  return useQuery({
    queryKey: ['championBuild', champName, region, queue, tier, countersCount, role, refresh],
    queryFn: () => getChampionBuild(champName, region, queue, tier, countersCount, role, refresh),
    enabled: enabled && !!champName,
    staleTime: 6 * 60 * 60 * 1000, // 6 hours - matches backend cache TTL
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
};
