import type { Player } from '../types';
import { RankBadge } from './RankBadge';
import { ChampionPortrait } from './ChampionPortrait';

interface PlayerCardProps {
  player: Player;
}

export function PlayerCard({ player }: PlayerCardProps) {
  const isSoloUnavailable =
    player.rankedStatus === 'ranked_empty_from_riot' ||
    player.rankedStatus === 'ranked_fetch_failed_fallback';
  const winRateColor = player.winRate >= 50 ? 'text-green-400' : 'text-red-400';
  const rankedStatusText = player.rankedStatus === 'ranked_from_riot'
    ? '排位来源: Riot 实时'
    : player.rankedStatus === 'ranked_empty_from_riot'
      ? '排位来源: Riot 返回空（当前无单排数据）'
      : player.rankedStatus === 'ranked_fetch_failed_fallback'
        ? '排位来源: Riot 拉取失败，已使用降级数据'
        : player.rankedStatus === 'ranked_from_cache'
          ? '排位来源: 本地缓存'
          : null;

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {player.gameName}
            <span className="text-gray-400 text-lg ml-1">#{player.tagLine}</span>
          </h2>
          <p className="text-gray-400 mt-1">等级 {player.level}</p>
          {rankedStatusText ? (
            <p className="text-xs text-gray-500 mt-1">{rankedStatusText}</p>
          ) : null}
        </div>
        {isSoloUnavailable ? (
          <div className="text-right">
            <div className="bg-gray-600 text-gray-100 font-bold px-3 py-1 rounded">
              SOLO 暂不可用
            </div>
            <span className="text-gray-400 text-sm">-- LP</span>
          </div>
        ) : (
          <RankBadge tier={player.tier} rank={player.rank} lp={player.lp} />
        )}
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-3xl font-bold text-white">{isSoloUnavailable ? '--' : `${player.wins}W`}</p>
          <p className="text-gray-400">胜</p>
        </div>
        <div className="text-center">
          <p className="text-3xl font-bold text-white">{isSoloUnavailable ? '--' : `${player.losses}L`}</p>
          <p className="text-gray-400">负</p>
        </div>
        <div className="text-center">
          <p className={`text-3xl font-bold ${winRateColor}`}>
            {isSoloUnavailable ? '--' : `${player.winRate.toFixed(1)}%`}
          </p>
          <p className="text-gray-400">胜率</p>
        </div>
      </div>

      {player.rankedFlex ? (
        <div className="mt-4 rounded-lg border border-gray-700 p-3">
          <p className="text-xs text-gray-400">灵活组排 (RANKED_FLEX_SR)</p>
          <p className="text-sm text-white mt-1">
            {player.rankedFlex.tier} {player.rankedFlex.rank} · {player.rankedFlex.lp} LP ·
            {' '}{player.rankedFlex.wins}W {player.rankedFlex.losses}L · {player.rankedFlex.winRate.toFixed(1)}%
          </p>
        </div>
      ) : null}

      {player.recentChampions.length > 0 && (
        <div className="mt-6">
          <p className="text-gray-400 mb-2">最近使用</p>
          <div className="flex gap-2">
            {player.recentChampions.map((champId, idx) => (
              <ChampionPortrait
                key={`${champId}-${idx}`}
                championId={champId}
                championName=""
                size="sm"
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
