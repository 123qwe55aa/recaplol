import { useQuery } from '@tanstack/react-query';
import { getPlayerStats } from '../services/api';

export const useStats = (puuid: string) => {
  return useQuery({
    queryKey: ['stats', puuid],
    queryFn: () => getPlayerStats(puuid),
    enabled: !!puuid,
  });
};
