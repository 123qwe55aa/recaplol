import { useQuery } from '@tanstack/react-query';
import { getLatestPatchAnnouncement } from '../services/api';

export const patchAnnouncementQueryKey = ['patchAnnouncement'] as const;

export const usePatchAnnouncement = () => {
  return useQuery({
    queryKey: patchAnnouncementQueryKey,
    queryFn: getLatestPatchAnnouncement,
    staleTime: 6 * 60 * 60 * 1000,
  });
};
