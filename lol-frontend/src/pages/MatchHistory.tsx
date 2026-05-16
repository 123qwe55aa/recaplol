import { useEffect, useRef } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchPlayerMatches, getPlayerMatchesWithDetails } from '../services/api';
import { MatchCard } from '../components/MatchCard';
import { usePlayerStore } from '../stores/playerStore';

export function MatchHistory() {
  const { puuid } = useParams<{ puuid: string }>();
  const [searchParams] = useSearchParams();
  const { currentPlayer } = usePlayerStore();

  const resolvedPuuid = puuid || currentPlayer?.puuid || '';
  const region = searchParams.get('region') || 'americas';

  const { data: matchData, isLoading, error, refetch } = useQuery({
    queryKey: ['matches-with-details', resolvedPuuid],
    queryFn: () => getPlayerMatchesWithDetails(resolvedPuuid, 20),
    enabled: !!resolvedPuuid,
    staleTime: 5 * 60 * 1000,
  });
  const hasSyncedRef = useRef(false);
  const syncMatches = useMutation({
    mutationFn: () => fetchPlayerMatches(resolvedPuuid, 20, region),
  });

  useEffect(() => {
    if (!resolvedPuuid || hasSyncedRef.current) return;
    hasSyncedRef.current = true;
    syncMatches.mutate(undefined, {
      onSuccess: () => {
        void refetch();
      },
    });
  }, [resolvedPuuid, region, refetch, syncMatches]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-yellow-400 text-xl">加载中...</div>
      </div>
    );
  }

  if (error || !matchData) {
    return (
      <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-8">
        <p className="text-red-400 text-xl mb-4">加载比赛记录失败</p>
        <Link to="/" className="text-yellow-400 hover:underline">
          返回首页
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="text-gray-400 hover:text-white mb-4 inline-block">
          ← 返回
        </Link>

        <h1 className="text-2xl font-bold text-white mb-6">
          比赛记录 {matchData.total > 0 && `(${matchData.total})`}
        </h1>

        <div className="mb-4 text-sm">
          {syncMatches.isPending && (
            <span className="text-yellow-400">正在同步最新战绩...</span>
          )}
          {syncMatches.isSuccess && (
            <span className="text-green-400">最新战绩已同步</span>
          )}
          {syncMatches.isError && (
            <span className="text-red-400">同步最新战绩失败，当前显示本地已有记录</span>
          )}
        </div>

        <div className="space-y-3">
          {matchData.matches.map((match) => (
            <MatchCard
              key={match.matchId}
              match={match}
              puuid={resolvedPuuid}
            />
          ))}
        </div>

        {matchData.matches.length === 0 && (
          <p className="text-gray-400 text-center py-8">暂无比赛记录</p>
        )}
      </div>
    </div>
  );
}
