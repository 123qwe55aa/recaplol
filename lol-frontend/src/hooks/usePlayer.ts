import { useQuery } from '@tanstack/react-query';
import { searchPlayer, getPlayerStats, getChampionMastery } from '../services/api';

export const usePlayer = (gameName: string, tagLine: string, enabled: boolean) => {
  return useQuery({
    queryKey: ['player', gameName, tagLine],
    queryFn: () => searchPlayer(gameName, tagLine),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
};

export const usePlayerStats = (puuid: string, enabled: boolean) => {
  return useQuery({
    queryKey: ['stats', puuid],
    queryFn: () => getPlayerStats(puuid),
    enabled,
  });
};

export const useChampionMastery = (puuid: string, enabled: boolean) => {
  return useQuery({
    queryKey: ['mastery', puuid],
    queryFn: () => getChampionMastery(puuid),
    enabled,
  });
};
