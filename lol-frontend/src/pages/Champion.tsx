import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useChampionBuild } from '../hooks/useChampionBuild';
import { ChampionPortrait } from '../components/ChampionPortrait';
import { RuneSimulator } from '../components/RuneSimulator';
import type { RegionCode, QueueType } from '../types';
import { loadItemData, type ItemDetail } from '../services/itemData';

type TabType = 'overview' | 'builds' | 'counters' | 'synergies';

const TABS: { id: TabType; label: string }[] = [
  { id: 'overview', label: '概览' },
  { id: 'builds', label: '出装' },
  { id: 'counters', label: '克制' },
  { id: 'synergies', label: '组合' },
];

const REGIONS: { code: RegionCode; name: string }[] = [
  { code: 'kr', name: 'Korea' },
  { code: 'na', name: 'North America' },
  { code: 'euw', name: 'EU West' },
  { code: 'eune', name: 'EU Nordic & East' },
  { code: 'jp', name: 'Japan' },
  { code: 'oce', name: 'Oceania' },
  { code: 'br', name: 'Brazil' },
  { code: 'las', name: 'Latin America South' },
  { code: 'lan', name: 'Latin America North' },
  { code: 'tr', name: 'Turkey' },
  { code: 'ru', name: 'Russia' },
  { code: 'sg', name: 'Singapore' },
  { code: 'my', name: 'Malaysia' },
  { code: 'ph', name: 'Philippines' },
  { code: 'th', name: 'Thailand' },
  { code: 'tw', name: 'Taiwan' },
  { code: 'vn', name: 'Vietnam' },
];

const QUEUES: { code: QueueType; name: string }[] = [
  { code: 'RANKED_SOLO_5x5', name: 'Ranked Solo' },
  { code: 'RANKED_FLEX_SR', name: 'Ranked Flex' },
  { code: 'ARKANE', name: 'Arena' },
];

const ROLES = [
  { code: '', name: '全部' },
  { code: 'top', name: '上单' },
  { code: 'jungle', name: '打野' },
  { code: 'mid', name: '中单' },
  { code: 'adc', name: 'ADC' },
  { code: 'support', name: '辅助' },
];

const DDRAGON_BASE = 'https://ddragon.leagueoflegends.com/cdn/16.5.1/img/item';

function formatWinRate(wr: number | null): string {
  if (wr === null || wr === undefined) return 'N/A';
  return `${wr.toFixed(1)}%`;
}

function formatLastUpdated(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function SkeletonLoader() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-gray-800 rounded-xl h-24" />
        ))}
      </div>
      <div className="bg-gray-800 rounded-xl h-48" />
      <div className="bg-gray-800 rounded-xl h-64" />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="bg-gray-800 rounded-xl p-8 text-center">
      <p className="text-red-400 text-lg mb-4">加载失败</p>
      <p className="text-gray-400 mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-6 py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors"
      >
        重试
      </button>
    </div>
  );
}

function StatsOverview({ data }: { data: NonNullable<import('../types').ChampionBuildResponse['data']> }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-gray-800 rounded-xl p-4 text-center">
        <div className="text-3xl font-bold text-green-400">
          {formatWinRate(data.win_rate)}
        </div>
        <div className="text-gray-400 text-sm mt-1">胜率</div>
      </div>
      <div className="bg-gray-800 rounded-xl p-4 text-center">
        <div className="text-3xl font-bold text-blue-400">
          {data.pick_rate !== null ? `${data.pick_rate.toFixed(1)}%` : 'N/A'}
        </div>
        <div className="text-gray-400 text-sm mt-1">选用率</div>
      </div>
      <div className="bg-gray-800 rounded-xl p-4 text-center">
        <div className="text-3xl font-bold text-purple-400">
          {data.games_played?.toLocaleString() ?? 'N/A'}
        </div>
        <div className="text-gray-400 text-sm mt-1">对局数</div>
      </div>
      <div className="bg-gray-800 rounded-xl p-4 text-center">
        <div className="text-xl font-bold text-yellow-400">
          {data.source}
        </div>
        <div className="text-gray-400 text-sm mt-1">数据源</div>
      </div>
    </div>
  );
}

function BuildSection({ data }: { data: NonNullable<import('../types').ChampionBuildResponse['data']> }) {
  const [itemData, setItemData] = useState<Record<string, ItemDetail>>({});
  const itemVersion = useMemo(() => {
    const match = DDRAGON_BASE.match(/\/cdn\/([^/]+)\/img\/item$/);
    return match?.[1] ?? '16.5.1';
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadItemData(itemVersion)
      .then((loaded) => {
        if (!cancelled) setItemData(loaded);
      })
      .catch(() => {
        if (!cancelled) setItemData({});
      });

    return () => {
      cancelled = true;
    };
  }, [itemVersion]);

  const getItemTooltip = (itemId: string, fallbackName: string): string => {
    const item = itemData[itemId];
    if (!item) return fallbackName || `装备 ID: ${itemId}`;

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
    <div className="space-y-6">
      {/* Core Item Build */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-4">核心出装</h3>
        {data.items.core.length > 0 ? (
          <div className="flex flex-wrap gap-3">
            {data.items.core.map((item, idx) => (
              <div key={item.id || idx} className="flex items-center gap-2 bg-gray-700 rounded-lg px-3 py-2">
                <span className="text-yellow-400 font-bold text-sm">#{idx + 1}</span>
                {item.id ? (
                  <img
                    src={`${DDRAGON_BASE}/${item.id}.png`}
                    alt={item.name}
                    className="w-10 h-10 rounded"
                    title={getItemTooltip(item.id, item.name)}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                ) : null}
                <span className="text-white">{item.name}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">暂无数据</p>
        )}

        {data.items.start.length > 0 && (
          <div className="mt-4">
            <h4 className="text-lg font-semibold text-gray-300 mb-2">起始装备</h4>
            <div className="flex flex-wrap gap-3">
              {data.items.start.map((item, idx) => (
                <div key={item.id || idx} className="flex items-center gap-2 bg-gray-700 rounded-lg px-3 py-2">
                  {item.id ? (
                    <img
                      src={`${DDRAGON_BASE}/${item.id}.png`}
                      alt={item.name}
                      className="w-8 h-8 rounded"
                      title={getItemTooltip(item.id, item.name)}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  ) : null}
                  <span className="text-gray-300">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.items.final.length > 0 && (
          <div className="mt-4">
            <h4 className="text-lg font-semibold text-gray-300 mb-2">后期装备</h4>
            <div className="flex flex-wrap gap-3">
              {data.items.final.map((item, idx) => (
                <div key={item.id || idx} className="flex items-center gap-2 bg-gray-700 rounded-lg px-3 py-2">
                  {item.id ? (
                    <img
                      src={`${DDRAGON_BASE}/${item.id}.png`}
                      alt={item.name}
                      className="w-8 h-8 rounded"
                      title={getItemTooltip(item.id, item.name)}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  ) : null}
                  <span className="text-gray-300">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Skill Order */}
      {data.skills.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-6">
          <h3 className="text-xl font-bold text-white mb-4">技能顺序</h3>
          <div className="flex flex-wrap gap-2">
            {data.skills.map((skill, idx) => (
              <span
                key={idx}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      <RuneSimulator recommendedRunes={data.runes.map((rune) => rune.name)} />
    </div>
  );
}

function CountersSection({
  data,
  countersCount,
}: {
  data: NonNullable<import('../types').ChampionBuildResponse['data']>;
  countersCount: number;
}) {
  return (
    <div className="space-y-6">
      {/* Counter Matchups - 克制 (Champions that beat this champ) */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-4">
          克制该英雄 Top {countersCount}
        </h3>
        {data.matchups.counters.length > 0 ? (
          <div className="space-y-2">
            {data.matchups.counters.map((counter, idx) => (
              <Link
                key={counter.champion_name || idx}
                to={`/champion/${encodeURIComponent(counter.champion_name)}`}
                className="flex items-center justify-between bg-gray-700 rounded-lg px-4 py-3 hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 font-bold w-6">#{idx + 1}</span>
                  <ChampionPortrait championName={counter.champion_name} size="sm" />
                  <span className="text-white font-medium">
                    {counter.champion_name}
                  </span>
                  <span className="text-gray-400 text-sm">
                    {counter.games.toLocaleString()} 场
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-red-400 font-bold">
                    {formatWinRate(counter.win_rate)}
                  </span>
                  <span className="text-gray-400 text-sm ml-2">胜率</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">暂无数据</p>
        )}
      </div>

      {/* Countered By - 被克制 (Champions this champ loses to) */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-4">
          该英雄克制 Top {countersCount}
        </h3>
        {data.matchups.countered_by.length > 0 ? (
          <div className="space-y-2">
            {data.matchups.countered_by.map((counter, idx) => (
              <Link
                key={counter.champion_name || idx}
                to={`/champion/${encodeURIComponent(counter.champion_name)}`}
                className="flex items-center justify-between bg-gray-700 rounded-lg px-4 py-3 hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 font-bold w-6">#{idx + 1}</span>
                  <ChampionPortrait championName={counter.champion_name} size="sm" />
                  <span className="text-white font-medium">
                    {counter.champion_name}
                  </span>
                  <span className="text-gray-400 text-sm">
                    {counter.games.toLocaleString()} 场
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-green-400 font-bold">
                    {formatWinRate(counter.win_rate)}
                  </span>
                  <span className="text-gray-400 text-sm ml-2">胜率</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">暂无数据</p>
        )}
      </div>
    </div>
  );
}

function SynergiesSection({ data }: { data: NonNullable<import('../types').ChampionBuildResponse['data']> }) {
  const synergies = data.synergies ?? [];

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      <h3 className="text-xl font-bold text-white mb-4">最佳组合英雄 Top 5</h3>
      {synergies.length > 0 ? (
        <div className="space-y-2">
          {synergies.slice(0, 5).map((synergy, idx) => (
            <Link
              key={synergy.champion_name || idx}
              to={`/champion/${encodeURIComponent(synergy.champion_name)}`}
              className="flex items-center justify-between bg-gray-700 rounded-lg px-4 py-3 hover:bg-gray-600 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-gray-500 font-bold w-6">#{idx + 1}</span>
                <ChampionPortrait championName={synergy.champion_name} size="sm" />
                <span className="text-white font-medium">{synergy.champion_name}</span>
              </div>
              <div className="text-right">
                <span className="text-green-400 font-bold">
                  {formatWinRate(synergy.win_rate)}
                </span>
                <span className="text-gray-400 text-sm ml-2">
                  选用率 {formatWinRate(synergy.pick_rate)}
                </span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-gray-400">暂无数据</p>
      )}
    </div>
  );
}

export function ChampionPage() {
  const { championName } = useParams<{ championName: string }>();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [region, setRegion] = useState<RegionCode>('kr');
  const [queue, setQueue] = useState<QueueType>('RANKED_SOLO_5x5');
  const [countersCount, setCountersCount] = useState(5);
  const [role, setRole] = useState('');

  const {
    data: buildData,
    isLoading,
    error,
    isFetching,
    refetch,
  } = useChampionBuild(championName ?? '', !!championName, {
    region,
    queue,
    countersCount,
    role,
  });

  if (!championName) {
    return (
      <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-8">
        <p className="text-red-400 text-xl mb-4">未找到英雄</p>
        <Link to="/" className="text-yellow-400 hover:underline">
          返回首页
        </Link>
      </div>
    );
  }

  const renderContent = () => {
    if (isLoading || isFetching) {
      return <SkeletonLoader />;
    }

    if (error) {
      return (
        <ErrorState
          message={error instanceof Error ? error.message : '未知错误'}
          onRetry={() => refetch()}
        />
      );
    }

    if (buildData?.success && buildData.data) {
      const data = buildData.data;

      switch (activeTab) {
        case 'overview':
          return (
            <div className="space-y-6">
              <StatsOverview data={data} />
              <BuildSection data={data} />
            </div>
          );
        case 'builds':
          return <BuildSection data={data} />;
        case 'counters':
          return <CountersSection data={data} countersCount={countersCount} />;
        case 'synergies':
          return <SynergiesSection data={data} />;
        default:
          return null;
      }
    }

    return (
      <ErrorState
        message={buildData?.error ?? '无法加载OP.GG数据'}
        onRetry={() => refetch()}
      />
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-6xl mx-auto">
        <Link to="/" className="text-gray-400 hover:text-white mb-4 inline-block">
          ← 返回
        </Link>

        {/* Champion Header */}
        <div className="flex items-center gap-6 mb-8">
          <ChampionPortrait championName={championName} size="lg" showName />
          <div>
            <h1 className="text-3xl font-bold text-white">{championName}</h1>
            <p className="text-gray-400">OP.GG 数据</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-gray-800 rounded-xl p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <label className="text-gray-400 text-sm">服务器:</label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value as RegionCode)}
                className="bg-gray-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
              >
                {REGIONS.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-gray-400 text-sm">队列:</label>
              <select
                value={queue}
                onChange={(e) => setQueue(e.target.value as QueueType)}
                className="bg-gray-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
              >
                {QUEUES.map((q) => (
                  <option key={q.code} value={q.code}>
                    {q.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Role Filter - F6 */}
            <div className="flex items-center gap-2">
              <label className="text-gray-400 text-sm">位置:</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="bg-gray-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
              >
                {ROLES.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>

            {activeTab === 'counters' && (
              <div className="flex items-center gap-2">
                <label className="text-gray-400 text-sm">对手数量:</label>
                <select
                  value={countersCount}
                  onChange={(e) => setCountersCount(Number(e.target.value))}
                  className="bg-gray-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
                >
                  {[3, 5, 7, 10].map((n) => (
                    <option key={n} value={n}>
                      Top {n}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="ml-auto text-sm text-gray-500">
              {buildData?.cached && buildData?.data && (
                <span className="text-yellow-500">
                  缓存于 {formatLastUpdated(buildData.data.last_updated)}
                  {buildData.data.stale && ' (过期)'}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Tab Navigation - F1 */}
        <div className="flex gap-2 mb-6 border-b border-gray-700">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 font-medium transition-colors relative ${
                activeTab === tab.id
                  ? 'text-yellow-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-yellow-400" />
              )}
            </button>
          ))}
          <div className="ml-auto flex items-center text-sm text-gray-500">
            Data source: {buildData?.data?.source ?? 'OP.GG'}
          </div>
        </div>

        {/* Tab Content */}
        {renderContent()}
      </div>
    </div>
  );
}
