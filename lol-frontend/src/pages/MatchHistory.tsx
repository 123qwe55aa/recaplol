import { useEffect, useRef, useState } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  fetchMatchTimeline,
  fetchPlayerMatches,
  generateAiMatchRecap,
  getPlayerMatchesWithDetails,
  getSavedAiMatchRecap,
  sendCoachQuestion,
} from '../services/api';
import { MatchCard } from '../components/MatchCard';
import { usePlayerStore } from '../stores/playerStore';
import { useRiotStatus } from '../hooks/useRiotStatus';
import type { CoachChatResponse, CoachMatchRecapResponse } from '../types';

function statText(value: number | null | undefined, suffix = '') {
  if (value === null || value === undefined) return '-';
  return `${value}${suffix}`;
}

function signedStatText(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return value > 0 ? `+${value}` : `${value}`;
}

export function MatchHistory() {
  const { puuid } = useParams<{ puuid: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentPlayer } = usePlayerStore();
  const [recaps, setRecaps] = useState<Record<string, CoachMatchRecapResponse>>({});
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'coach'; text: string }>>([]);

  const resolvedPuuid = puuid || currentPlayer?.puuid || '';
  const region = searchParams.get('region') || 'americas';
  const statusPlatform = (
    currentPlayer?.tagLine
    || (region === 'europe' ? 'euw1' : region === 'asia' ? 'kr' : region === 'sea' ? 'tw2' : 'na1')
  ).toLowerCase();
  const { data: riotStatus } = useRiotStatus(statusPlatform);

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
  const syncedNewMatches = syncMatches.data?.fetched ?? 0;
  const syncedTotalMatches = syncMatches.data?.match_count ?? 0;
  const hasRiotPlatformIssues = ((riotStatus?.incidents?.length ?? 0) + (riotStatus?.maintenances?.length ?? 0)) > 0;
  const recapMutation = useMutation({
    mutationFn: async (matchId: string) => {
      await fetchMatchTimeline(matchId);
      return generateAiMatchRecap(matchId, resolvedPuuid);
    },
    onSuccess: (recap) => {
      setRecaps((current) => ({ ...current, [recap.match_id]: recap }));
    },
  });
  const chatMutation = useMutation({
    mutationFn: (question: string) => sendCoachQuestion(resolvedPuuid, question),
  });

  const appendMention = (matchId: string) => {
    setChatInput((current) => (current.trim() ? `${current} @${matchId} ` : `@${matchId} `));
  };

  const submitChat = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = chatInput.trim();
    if (!trimmed || chatMutation.isPending) return;
    setChatInput('');
    setChatMessages((current) => [...current, { role: 'user', text: trimmed }]);
    const answer: CoachChatResponse = await chatMutation.mutateAsync(trimmed);
    setChatMessages((current) => [...current, { role: 'coach', text: answer.answer }]);
  };

  useEffect(() => {
    if (!resolvedPuuid || hasSyncedRef.current) return;
    hasSyncedRef.current = true;
    syncMatches.mutate(undefined, {
      onSuccess: (result) => {
        if (result?.puuid && result.puuid !== resolvedPuuid) {
          navigate(`/matches/${encodeURIComponent(result.puuid)}?region=${encodeURIComponent(region)}`, {
            replace: true,
          });
          return;
        }
        void refetch();
      },
    });
  }, [navigate, resolvedPuuid, region, refetch, syncMatches]);

  useEffect(() => {
    if (!resolvedPuuid || !matchData?.matches.length) return;
    let cancelled = false;
    const missingMatches = matchData.matches.filter((match) => !recaps[match.matchId]);
    if (!missingMatches.length) return;

    void Promise.all(
      missingMatches.map((match) => getSavedAiMatchRecap(match.matchId, resolvedPuuid))
    ).then((savedRecaps) => {
      if (cancelled) return;
      const nextRecaps = savedRecaps.filter((recap): recap is CoachMatchRecapResponse => !!recap);
      if (!nextRecaps.length) return;
      setRecaps((current) => {
        const updated = { ...current };
        nextRecaps.forEach((recap) => {
          updated[recap.match_id] = recap;
        });
        return updated;
      });
    });

    return () => {
      cancelled = true;
    };
  }, [matchData?.matches, recaps, resolvedPuuid]);

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
            <span className="text-yellow-400">正在同步最新战绩，可能需要半分钟...</span>
          )}
          {syncMatches.isSuccess && syncedNewMatches > 0 && (
            <span className="text-green-400">最新战绩已同步（新增 {syncedNewMatches} 场）</span>
          )}
          {syncMatches.isSuccess && syncedNewMatches === 0 && syncedTotalMatches > 0 && (
            <span className="text-gray-300">战绩已是最新，无需同步</span>
          )}
          {syncMatches.isSuccess && syncedTotalMatches === 0 && (
            <span className="text-gray-300">未获取到可同步战绩</span>
          )}
          {syncMatches.isError && (
            <span className="text-red-400">
              {hasRiotPlatformIssues
                ? '同步最新战绩失败，Riot 当前平台可能有维护或异常，先显示本地已有记录'
                : '同步最新战绩失败，当前显示本地已有记录'}
            </span>
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
                  onDeepRecap={() => recapMutation.mutate(match.matchId)}
                  isDeepRecapLoading={isLoadingRecap}
                  hasDeepRecap={!!recap}
                />
                {recap && (
                  <section className="border border-gray-700 bg-gray-800/60 rounded-lg p-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-sm">
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
                        <p className="text-gray-500">10 分钟队伍经济差</p>
                        <p className="text-white font-semibold">
                          {signedStatText(recap.timeline_stats.team_gold_delta_at_10)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">14 分钟队伍经济差</p>
                        <p className="text-white font-semibold">
                          {signedStatText(recap.timeline_stats.team_gold_delta_at_14)}
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
                      <div className="border-t border-gray-700 pt-3">
                        <button
                          type="button"
                          onClick={() => appendMention(recap.match_id)}
                          className="px-3 py-1 rounded bg-yellow-500 text-black text-xs font-semibold hover:bg-yellow-400 transition-colors"
                        >
                          提问这场 @{recap.match_id}
                        </button>
                      </div>
                    </div>
                  </section>
                )}
                {recapMutation.isError && recapMutation.variables === match.matchId && (
                  <p className="text-red-400 text-sm text-right">
                    深度复盘加载失败，可能是 Riot timeline 或 AI 复盘服务暂时不可用。
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

      <section className="fixed bottom-4 right-4 w-[360px] max-w-[calc(100vw-2rem)] bg-gray-900 border border-gray-700 rounded-xl shadow-xl z-20">
        <header className="px-4 py-3 border-b border-gray-700">
          <p className="text-white font-semibold">AI 教练对话</p>
          <p className="text-gray-400 text-xs mt-1">可 mention 比赛 ID，例如 @TW2_415032107</p>
        </header>
        <div className="h-64 overflow-y-auto px-4 py-3 space-y-2">
          {chatMessages.length === 0 && (
            <p className="text-gray-500 text-sm">先点击任一比赛下方“提问这场”，或直接输入问题。</p>
          )}
          {chatMessages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={message.role === 'user' ? 'text-right' : 'text-left'}>
              <p
                className={`inline-block max-w-[90%] rounded-lg px-3 py-2 text-sm ${
                  message.role === 'user' ? 'bg-yellow-500 text-black' : 'bg-gray-800 text-gray-100'
                }`}
              >
                {message.text}
              </p>
            </div>
          ))}
          {chatMutation.isPending && (
            <p className="text-gray-400 text-sm">AI 正在思考...</p>
          )}
        </div>
        <form onSubmit={submitChat} className="p-3 border-t border-gray-700 flex gap-2">
          <input
            type="text"
            value={chatInput}
            onChange={(event) => setChatInput(event.target.value)}
            placeholder="输入问题，或 @matchId 后提问"
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-yellow-500"
          />
          <button
            type="submit"
            disabled={!chatInput.trim() || chatMutation.isPending}
            className="px-3 py-2 bg-yellow-500 text-black font-semibold text-sm rounded hover:bg-yellow-400 disabled:opacity-50"
          >
            发送
          </button>
        </form>
        {chatMutation.isError && (
          <p className="px-3 pb-3 text-red-400 text-xs">
            {chatMutation.error instanceof Error ? chatMutation.error.message : '提问失败，请稍后再试'}
          </p>
        )}
      </section>
    </div>
  );
}
