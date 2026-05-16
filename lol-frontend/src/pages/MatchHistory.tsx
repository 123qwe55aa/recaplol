import { useEffect, useRef, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchMatchTimeline, fetchPlayerMatches, generateAiMatchRecap, getPlayerMatchesWithDetails } from '../services/api';
import { MatchCard } from '../components/MatchCard';
import { usePlayerStore } from '../stores/playerStore';
import type { CoachMatchRecapResponse } from '../types';

function statText(value: number | null | undefined, suffix = '') {
  if (value === null || value === undefined) return '-';
  return `${value}${suffix}`;
}

export function MatchHistory() {
  const { puuid } = useParams<{ puuid: string }>();
  const [searchParams] = useSearchParams();
  const { currentPlayer } = usePlayerStore();
  const [recaps, setRecaps] = useState<Record<string, CoachMatchRecapResponse>>({});

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
  const recapMutation = useMutation({
    mutationFn: async (matchId: string) => {
      await fetchMatchTimeline(matchId);
      return generateAiMatchRecap(matchId, resolvedPuuid);
    },
    onSuccess: (recap) => {
      setRecaps((current) => ({ ...current, [recap.match_id]: recap }));
    },
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
          {matchData.matches.map((match) => {
            const recap = recaps[match.matchId];
            const isLoadingRecap = recapMutation.isPending && recapMutation.variables === match.matchId;
            return (
              <div key={match.matchId} className="space-y-2">
                <MatchCard
                  match={match}
                  puuid={resolvedPuuid}
                />
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => recapMutation.mutate(match.matchId)}
                    disabled={isLoadingRecap || !resolvedPuuid}
                    className="px-3 py-2 bg-gray-800 text-yellow-300 border border-gray-700 rounded-md text-sm hover:bg-gray-700 disabled:opacity-50"
                  >
                    {isLoadingRecap ? '分析中...' : '深度复盘'}
                  </button>
                </div>
                {recap && (
                  <section className="border border-gray-700 bg-gray-800/60 rounded-lg p-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <p className="text-gray-500">10 分钟补刀</p>
                        <p className="text-white font-semibold">
                          {statText(recap.timeline_stats.cs_per_min_at_10, '/分钟')}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">10 分钟经济</p>
                        <p className="text-white font-semibold">
                          {statText(recap.timeline_stats.gold_at_10)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">前期死亡</p>
                        <p className="text-white font-semibold">
                          {statText(recap.timeline_stats.early_deaths, ' 次')}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">资源前死亡</p>
                        <p className="text-white font-semibold">
                          {statText(recap.timeline_stats.resource_deaths, ' 次')}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 space-y-3">
                      <div className="border-t border-gray-700 pt-3">
                        <p className="text-gray-500 text-xs uppercase">AI 结论</p>
                        <p className="text-white leading-7 mt-1">{recap.recap.summary}</p>
                      </div>

                      {recap.recap.turning_points.length > 0 && (
                        <div className="border-t border-gray-700 pt-3">
                          <p className="text-gray-500 text-xs uppercase">关键转折</p>
                          <div className="mt-2 space-y-2">
                            {recap.recap.turning_points.map((point) => (
                              <article key={`${recap.match_id}-${point.title}-${point.timestamp}`}>
                                <p className="text-white font-semibold">{point.title}</p>
                                <p className="text-gray-300 text-sm mt-1">{point.explanation}</p>
                              </article>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-gray-700 pt-3">
                        <div>
                          <p className="text-gray-500 text-xs uppercase">做得好的地方</p>
                          <ul className="mt-2 space-y-1 text-sm text-gray-300">
                            {recap.recap.strengths.map((item) => (
                              <li key={item}>• {item}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs uppercase">主要问题</p>
                          <ul className="mt-2 space-y-1 text-sm text-gray-300">
                            {recap.recap.mistakes.map((item) => (
                              <li key={item}>• {item}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="border-t border-gray-700 pt-3">
                        <p className="text-gray-500 text-xs uppercase">下局只练这个</p>
                        <p className="text-yellow-200 text-sm mt-2">{recap.recap.next_game_focus}</p>
                      </div>

                      {recap.deterministic_insights.length > 0 && (
                        <details className="border-t border-gray-700 pt-3">
                          <summary className="text-gray-400 text-sm cursor-pointer">查看规则证据</summary>
                          <div className="mt-3 space-y-2">
                            {recap.deterministic_insights.map((insight) => (
                              <article key={`${recap.match_id}-${insight.type}`}>
                                <p className="text-white text-sm font-semibold">{insight.title}</p>
                                {insight.evidence.length > 0 && (
                                  <p className="text-gray-300 text-sm mt-1">{insight.evidence.join('；')}</p>
                                )}
                              </article>
                            ))}
                          </div>
                        </details>
                      )}

                      {recap.recap.follow_up_questions.length > 0 && (
                        <div className="border-t border-gray-700 pt-3">
                          <p className="text-gray-500 text-xs uppercase">可以继续问</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {recap.recap.follow_up_questions.map((question) => (
                              <span key={question} className="px-2 py-1 rounded bg-gray-700 text-gray-200 text-xs">
                                {question}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </section>
                )}
                {recapMutation.isError && recapMutation.variables === match.matchId && (
                  <p className="text-red-400 text-sm text-right">
                    深度复盘加载失败，请确认这局 timeline 已可从 Riot API 获取。
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {matchData.matches.length === 0 && (
          <p className="text-gray-400 text-center py-8">暂无比赛记录</p>
        )}
      </div>
    </div>
  );
}
