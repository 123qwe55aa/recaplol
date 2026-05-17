import { useEffect, useMemo, useState } from 'react';
import type { Match } from '../types';
import { ChampionPortrait } from './ChampionPortrait';
import { loadItemData, parseVersionFromItemImageUrl, type ItemDetail } from '../services/itemData';

interface MatchCardProps {
  match: Match;
  puuid: string;
  onClick?: () => void;
  onDeepRecap?: () => void;
  isDeepRecapLoading?: boolean;
  hasDeepRecap?: boolean;
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

function getOutcome(player: Match['participants'][number], match: Match) {
  if (player.outcome) return player.outcome;
  if (match.gameDuration > 0 && match.gameDuration <= 300) return 'REMAKE';
  return player.win ? 'WIN' : 'LOSS';
}

export function MatchCard({
  match,
  puuid,
  onClick,
  onDeepRecap,
  isDeepRecapLoading = false,
  hasDeepRecap = false,
}: MatchCardProps) {
  // If puuid lookup fails (privacy), fall back to any participant with champion data
  let player = match.participants.find((p) => p.puuid === puuid);
  if (!player && match.participants.length > 0) {
    player = match.participants[0];
  }
  if (!player) return null;
  const [itemData, setItemData] = useState<Record<string, ItemDetail>>({});

  const displayedItemIds = useMemo(() => player.items.filter((id) => id > 0).slice(0, 6), [player.items]);
  const itemDataVersion = useMemo(() => {
    if (!player.itemImages || player.itemImages.length === 0) return '';
    return parseVersionFromItemImageUrl(player.itemImages[0]);
  }, [player.itemImages]);

  useEffect(() => {
    if (!itemDataVersion) return;
    let cancelled = false;
    loadItemData(itemDataVersion)
      .then((data) => {
        if (!cancelled) setItemData(data);
      })
      .catch(() => {
        if (!cancelled) setItemData({});
      });

    return () => {
      cancelled = true;
    };
  }, [itemDataVersion]);

  const kda = `${player.kills}/${player.deaths}/${player.assists}`;
  const kdaColor = player.deaths === 0 ? 'text-purple-400' :
    player.kills / player.deaths >= 3 ? 'text-green-400' :
    player.kills / player.deaths >= 1 ? 'text-white' : 'text-red-400';
  const outcome = getOutcome(player, match);
  const outcomeText = outcome === 'WIN' ? '胜利' : outcome === 'LOSS' ? '失败' : outcome === 'REMAKE' ? '重开' : '未知';
  const outcomeColor = outcome === 'WIN' ? 'text-blue-400' : outcome === 'LOSS' ? 'text-red-400' : 'text-gray-300';
  const borderColor = outcome === 'WIN' ? 'border-blue-500' : outcome === 'LOSS' ? 'border-red-500' : 'border-gray-500';
  const getItemTooltip = (itemId: number): string => {
    const item = itemData[String(itemId)];
    if (!item) return `装备 ID: ${itemId}`;

    const lines = [item.name];
    if (item.totalGold > 0 || item.sellGold > 0) {
      lines.push(`总价: ${item.totalGold}  售价: ${item.sellGold}`);
    }
    if (item.tags.length > 0) {
      lines.push(`类型: ${item.tags.join(', ')}`);
    }
    if (item.plaintext) {
      lines.push(item.plaintext);
    }
    if (item.description) {
      lines.push(item.description);
    }
    return lines.join('\n');
  };

  return (
    <div
      onClick={onClick}
      className={`bg-gray-800 rounded-lg p-4 flex items-center gap-4 ${onClick ? 'cursor-pointer' : ''} hover:bg-gray-700 transition-colors ${
        `border-l-4 ${borderColor}`
      }`}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${outcomeColor}`}>
            {outcomeText}
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
                  title={getItemTooltip(displayedItemIds[i] ?? 0)}
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

      <div className="text-right flex flex-col items-end gap-2">
        <div>
          <p className="text-gray-400 text-sm">{formatDuration(match.gameDuration)}</p>
          <p className="text-yellow-400 text-sm">{player.goldEarned.toLocaleString()} 金币</p>
        </div>
        {onDeepRecap && (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onDeepRecap();
            }}
            disabled={isDeepRecapLoading}
            aria-label={isDeepRecapLoading ? '正在生成深度复盘' : '深度复盘'}
            title={isDeepRecapLoading ? '正在生成深度复盘' : '深度复盘'}
            className={`h-8 w-8 rounded-md border text-xs font-bold transition-colors ${
              hasDeepRecap
                ? 'border-yellow-400 bg-yellow-400 text-black'
                : 'border-gray-600 bg-gray-900 text-yellow-300 hover:bg-gray-700'
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            {isDeepRecapLoading ? '...' : 'AI'}
          </button>
        )}
      </div>
    </div>
  );
}
