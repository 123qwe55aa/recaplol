import { useQuery } from '@tanstack/react-query';
import { getPlayerMatches, getMatchDetail } from '../services/api';

export const useMatchHistory = (puuid: string, limit = 20) => {
  return useQuery({
    queryKey: ['matches', puuid, limit],
    queryFn: () => getPlayerMatches(puuid, limit),
    enabled: !!puuid,
    staleTime: 2 * 60 * 1000,
  });
};

export const useMatchDetail = (matchId: string) => {
  return useQuery({
    queryKey: ['match', matchId],
    queryFn: () => getMatchDetail(matchId),
    enabled: !!matchId,
  });
};
