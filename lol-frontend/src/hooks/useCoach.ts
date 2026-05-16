import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { generateCoachReport, getCoachReport, sendCoachQuestion } from '../services/api';
import type { CoachReportResponse } from '../types';

export const coachReportQueryKey = (puuid: string) => ['coachReport', puuid] as const;

export const useCoachReport = (puuid: string) => {
  return useQuery({
    queryKey: coachReportQueryKey(puuid),
    queryFn: () => getCoachReport(puuid),
    enabled: !!puuid,
    staleTime: 5 * 60 * 1000,
  });
};

export const useGenerateCoachReport = (puuid: string) => {
  const queryClient = useQueryClient();

  return useMutation<CoachReportResponse, Error, boolean | undefined>({
    mutationFn: (force = false) => generateCoachReport(puuid, force),
    onSuccess: (data) => {
      queryClient.setQueryData(coachReportQueryKey(puuid), data);
    },
  });
};

export const useCoachChat = (puuid: string) => {
  return useMutation({
    mutationFn: (question: string) => sendCoachQuestion(puuid, question),
  });
};
