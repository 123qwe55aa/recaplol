import type { OpggBuild, Player } from '../types';
import { RankBadge } from './RankBadge';
import { ChampionPortrait } from './ChampionPortrait';
import { RuneSimulator } from './RuneSimulator';

interface PlayerCardProps {
  player: Player;
  opggBuild?: OpggBuild | null;
  opggStatusText?: string | null;
}

export function PlayerCard({ player, opggBuild = null, opggStatusText = null }: PlayerCardProps) {
  const winRateColor = player.winRate >= 50 ? 'text-green-400' : 'text-red-400';

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {player.gameName}
            <span className="text-gray-400 text-lg ml-1">#{player.tagLine}</span>
          </h2>
          <p className="text-gray-400 mt-1">等级 {player.level}</p>
        </div>
        <RankBadge tier={player.tier} rank={player.rank} lp={player.lp} />
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-3xl font-bold text-white">{player.wins}W</p>
          <p className="text-gray-400">胜</p>
        </div>
        <div className="text-center">
          <p className="text-3xl font-bold text-white">{player.losses}L</p>
          <p className="text-gray-400">负</p>
        </div>
        <div className="text-center">
          <p className={`text-3xl font-bold ${winRateColor}`}>
            {player.winRate.toFixed(1)}%
          </p>
          <p className="text-gray-400">胜率</p>
        </div>
      </div>

      <div className="mt-6 pt-6 border-t border-gray-700">
        {opggStatusText ? (
          <p className="text-xs text-gray-400 mb-2">{opggStatusText}</p>
        ) : null}
        <RuneSimulator
          recommendedRunes={opggBuild?.runes?.map((rune) => rune.name) ?? []}
          recommendedSetup={opggBuild?.rune_setup ?? null}
          recommendedSetupValid={opggBuild?.rune_setup_valid ?? false}
          defaultCollapsed
        />
      </div>

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
