import type { Match } from '../types';
import { ChampionPortrait } from './ChampionPortrait';

interface MatchCardProps {
  match: Match;
  puuid: string;
  onClick?: () => void;
}

const QUEUE_LABELS: Record<string, string> = {
  CLASSIC: '峡谷匹配',
  ARAM: '极地大乱斗',
  420: '单双排',
  440: '灵活排位',
  450: '极地大乱斗',
  1700: '竞技场',
};

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return '今天';
  if (diffDays === 1) return '昨天';
  if (diffDays < 7) return `${diffDays}天前`;
  return date.toLocaleDateString('zh-CN');
}

export function MatchCard({ match, puuid, onClick }: MatchCardProps) {
  // If puuid lookup fails (privacy), fall back to any participant with champion data
  let player = match.participants.find((p) => p.puuid === puuid);
  if (!player && match.participants.length > 0) {
    player = match.participants[0];
  }
  if (!player) return null;

  const kda = `${player.kills}/${player.deaths}/${player.assists}`;
  const kdaColor = player.deaths === 0 ? 'text-purple-400' :
    player.kills / player.deaths >= 3 ? 'text-green-400' :
    player.kills / player.deaths >= 1 ? 'text-white' : 'text-red-400';

  return (
    <div
      onClick={onClick}
      className={`bg-gray-800 rounded-lg p-4 flex items-center gap-4 cursor-pointer hover:bg-gray-700 transition-colors ${
        player.win ? 'border-l-4 border-blue-500' : 'border-l-4 border-red-500'
      }`}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${player.win ? 'text-blue-400' : 'text-red-400'}`}>
            {player.win ? '胜利' : '失败'}
          </span>
          <span className="text-gray-400 text-sm">
            {QUEUE_LABELS[match.queueType] || match.queueType}
          </span>
          <span className="text-gray-500 text-sm">{formatDate(match.gameCreation)}</span>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <ChampionPortrait championName={player.championName} size="md" />
          <div>
            <p className="text-white font-semibold">{player.championName}</p>
            <p className={`text-lg font-bold ${kdaColor}`}>{kda}</p>
          </div>
          {player.itemImages && player.itemImages.length > 0 && (
            <div className="flex items-center gap-0.5 ml-2">
              {player.itemImages.slice(0, 6).map((url, i) => (
                <img
                  key={i}
                  src={url}
                  alt="item"
                  className="w-5 h-5 rounded-sm object-cover bg-gray-700"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              ))}
              {player.itemImages.length > 6 && (
                <span className="text-gray-500 text-xs">+</span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="text-right">
        <p className="text-gray-400 text-sm">{formatDuration(match.gameDuration)}</p>
        <p className="text-yellow-400 text-sm">{player.goldEarned.toLocaleString()} 金币</p>
      </div>
    </div>
  );
}
