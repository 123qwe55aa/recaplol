import { useParams, Link } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { usePlayer, useChampionMastery } from '../hooks/usePlayer';
import { useChampionBuild } from '../hooks/useChampionBuild';
import { getPlayerMatchesWithDetails, refreshPlayerByPuuid } from '../services/api';
import { PlayerCard } from '../components/PlayerCard';
import { ChampionPortrait } from '../components/ChampionPortrait';
import { LoLVersionCard } from '../components/LoLVersionCard';
import { LoLPatchAnnouncementCard } from '../components/LoLPatchAnnouncementCard';
import { PlayerCoachChatPanel } from '../components/PlayerCoachChatPanel';
import type { ChampionMastery } from '../types';

function getRegionalRouting(tagLine = '') {
  const tag = tagLine.toLowerCase();
  if (['kr', 'kr1', 'jp', 'jp1'].includes(tag)) return 'asia';
  if (['euw1', 'eune1', 'tr1', 'ru'].includes(tag)) return 'europe';
  if (['tw2', 'sg2', 'ph2', 'th2', 'vn2', 'my2', 'id2'].includes(tag)) return 'sea';
  return 'americas';
}

export function PlayerPage() {
  const { gameName, tagLine } = useParams<{ gameName: string; tagLine: string }>();
  const { data: player, isLoading, error, refetch } = usePlayer(gameName!, tagLine!, !!gameName && !!tagLine);
  const { data: masteryData } = useChampionMastery(player?.puuid ?? '', !!player?.puuid);
  const masteryPrimaryChampionName = masteryData?.champion_masteries?.[0]?.championName ?? '';
  const { data: matchesWithDetails } = useQuery({
    queryKey: ['player-fallback-primary', player?.puuid],
    queryFn: () => getPlayerMatchesWithDetails(player!.puuid, 20),
    enabled: !!player?.puuid && !masteryPrimaryChampionName,
    staleTime: 2 * 60 * 1000,
  });
  const fallbackPrimaryChampionName = useMemo(() => {
    if (!matchesWithDetails?.matches?.length || !player?.puuid) return '';
    const counts = new Map<string, number>();
    for (const match of matchesWithDetails.matches) {
      const me = match.participants.find((p) => p.puuid === player.puuid);
      const name = me?.championName?.trim();
      if (!name) continue;
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    let bestName = '';
    let bestCount = 0;
    for (const [name, count] of counts.entries()) {
      if (count > bestCount) {
        bestName = name;
        bestCount = count;
      }
    }
    return bestName;
  }, [matchesWithDetails, player?.puuid]);
  const primaryChampionName = masteryPrimaryChampionName || fallbackPrimaryChampionName;
  const {
    data: opggBuildResp,
    isLoading: isOpggBuildLoading,
    isError: isOpggBuildError,
  } = useChampionBuild(
    primaryChampionName,
    !!primaryChampionName,
    {
      region: 'kr',
      queue: 'RANKED_SOLO_5x5',
      tier: 'overall',
    }
  );
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const handleRefresh = async () => {
    if (!player?.puuid || isRefreshing) return;
    setIsRefreshing(true);
    setRefreshMessage(null);
    try {
      await refreshPlayerByPuuid(player.puuid);
      await refetch();
      setRefreshMessage('刷新成功');
    } catch (refreshError) {
      let message = '刷新失败，请稍后重试';
      if (axios.isAxiosError(refreshError)) {
        const detail = refreshError.response?.data?.detail;
        message = typeof detail === 'string' ? detail : (refreshError.message || message);
      } else if (refreshError instanceof Error) {
        message = refreshError.message;
      }
      setRefreshMessage(message);
    } finally {
      setIsRefreshing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-yellow-400 text-xl">加载中...</div>
      </div>
    );
  }

  if (error || !player) {
    return (
      <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-8">
        <p className="text-red-400 text-xl mb-4">未找到玩家</p>
        <Link to="/" className="text-yellow-400 hover:underline">
          返回首页
        </Link>
      </div>
    );
  }

  const masteries = masteryData?.champion_masteries ?? [];
  const matchRegion = getRegionalRouting(player.tagLine);
  const opggBuild = opggBuildResp?.data ?? null;
  const opggStatusText = !primaryChampionName
    ? 'OP.GG: 暂无可查询英雄（缺少熟练度与比赛数据）'
    : isOpggBuildLoading
      ? `OP.GG: 正在查询 ${primaryChampionName}`
      : isOpggBuildError
        ? `OP.GG: ${primaryChampionName} 查询失败`
        : !masteryPrimaryChampionName
          ? `OP.GG: ${primaryChampionName}（最近比赛回退）`
        : opggBuild?.rune_setup?.primary_runes?.length
          ? `OP.GG: ${primaryChampionName} 已返回可应用符文`
          : opggBuild?.runes?.length
            ? `OP.GG: ${primaryChampionName} 仅返回符文名称列表`
            : `OP.GG: ${primaryChampionName} 未返回符文数据`;

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="text-gray-400 hover:text-white mb-4 inline-block">
          ← 返回
        </Link>

        <PlayerCard player={player} opggBuild={opggBuild} opggStatusText={opggStatusText} />
        <div className="mt-4 grid grid-cols-1 gap-4">
          <LoLVersionCard />
          <LoLPatchAnnouncementCard />
          <PlayerCoachChatPanel puuid={player.puuid} />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-600 disabled:opacity-50 transition-colors"
          >
            {isRefreshing ? '刷新中...' : '强制刷新资料'}
          </button>
          {refreshMessage && (
            <span className="text-sm text-gray-300">{refreshMessage}</span>
          )}
        </div>

        {masteries.length > 0 && (
          <div className="mt-8">
            <h3 className="text-xl font-bold text-white mb-4">英雄成就</h3>
            <div className="grid grid-cols-5 gap-4">
              {masteries.slice(0, 10).map((champ: ChampionMastery) => (
                <div key={champ.championId} className="flex flex-col items-center">
                  <ChampionPortrait
                    championName={champ.championName}
                    size="lg"
                    showName
                  />
                  <span className="text-yellow-400 text-sm mt-1">
                    Lv.{champ.level} · {champ.points.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-8 flex gap-4">
          <Link
            to={`/matches/${player.puuid}?region=${matchRegion}`}
            className="inline-block px-6 py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors"
          >
            查看比赛记录
          </Link>
          <Link
            to={`/analysis/${player.puuid}`}
            className="inline-block px-6 py-3 bg-gray-700 text-white font-bold rounded-lg hover:bg-gray-600 transition-colors"
          >
            数据分析
          </Link>
        </div>
      </div>
    </div>
  );
}
