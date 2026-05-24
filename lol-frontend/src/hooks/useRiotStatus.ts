import { useQuery } from '@tanstack/react-query';
import { getRiotPlatformStatus } from '../services/api';

export const riotStatusQueryKey = (platform: string) => ['riotStatus', platform.toLowerCase()] as const;

export const useRiotStatus = (platform: string) => {
  const normalizedPlatform = platform.trim().toLowerCase();

  return useQuery({
    queryKey: riotStatusQueryKey(normalizedPlatform),
    queryFn: () => getRiotPlatformStatus(normalizedPlatform),
    enabled: normalizedPlatform.length > 0,
    staleTime: 5 * 60 * 1000,
  });
};
