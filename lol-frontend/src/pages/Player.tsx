import { useParams, Link } from 'react-router-dom';
import { useState } from 'react';
import axios from 'axios';
import { usePlayer, useChampionMastery } from '../hooks/usePlayer';
import { useChampionBuild } from '../hooks/useChampionBuild';
import { refreshPlayerByPuuid } from '../services/api';
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
  const primaryChampionName = masteryData?.champion_masteries?.[0]?.championName ?? '';
  const { data: opggBuildResp } = useChampionBuild(
    primaryChampionName,
    !!primaryChampionName,
    { region: 'kr', queue: 'RANKED_SOLO_5x5', tier: 'overall' }
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

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="text-gray-400 hover:text-white mb-4 inline-block">
          ← 返回
        </Link>

        <PlayerCard player={player} opggBuild={opggBuildResp?.data ?? null} />
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
