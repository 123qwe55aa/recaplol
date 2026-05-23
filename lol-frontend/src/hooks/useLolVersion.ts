import { useQuery } from '@tanstack/react-query';
import { getLatestLolVersion } from '../services/api';

export const lolVersionQueryKey = ['lolVersion'] as const;

export const useLolVersion = () => {
  return useQuery({
    queryKey: lolVersionQueryKey,
    queryFn: getLatestLolVersion,
    staleTime: 6 * 60 * 60 * 1000,
  });
};
