import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ChampionPortrait } from '../components/ChampionPortrait';
import { useChampionBuild } from '../hooks/useChampionBuild';
import type { RegionCode, QueueType } from '../types';

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

function formatRate(value: number | null | undefined) {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(1)}%`;
}

export function ChampionLookupPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialChampion = searchParams.get('champion') ?? '';

  const [query, setQuery] = useState(initialChampion);
  const [submittedChampion, setSubmittedChampion] = useState(initialChampion.trim());
  const [region, setRegion] = useState<RegionCode>((searchParams.get('region') as RegionCode) || 'kr');
  const [queue, setQueue] = useState<QueueType>((searchParams.get('queue') as QueueType) || 'RANKED_SOLO_5x5');
  const [role, setRole] = useState(searchParams.get('role') ?? '');

  useEffect(() => {
    setQuery(initialChampion);
    setSubmittedChampion(initialChampion.trim());
  }, [initialChampion]);

  const enabled = submittedChampion.length > 0;
  const { data, isLoading, isFetching, error, refetch } = useChampionBuild(submittedChampion, enabled, {
    region,
    queue,
    role,
  });

  const busy = isLoading || isFetching;

  const searchSummary = useMemo(() => {
    if (!data?.data) return null;
    return data.data;
  }, [data]);

  const submitSearch = (champion: string) => {
    const trimmed = champion.trim();
    setSubmittedChampion(trimmed);
    if (!trimmed) {
      setSearchParams({ region, queue, role });
      return;
    }
    setSearchParams({ champion: trimmed, region, queue, role });
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submitSearch(query);
  };

  useEffect(() => {
    if (!submittedChampion) return;
    setSearchParams({ champion: submittedChampion, region, queue, role });
  }, [region, queue, role]);

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-yellow-400">OP.GG 聚合查询</h1>
            <p className="text-gray-400 mt-2">输入英雄名字，立即抓取推荐出装和克制信息</p>
          </div>
          {submittedChampion && (
            <button
              onClick={() => navigate(`/champion/${encodeURIComponent(submittedChampion)}`)}
              className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              进入详情页
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-800 rounded-2xl p-5 space-y-4">
          <div className="flex flex-col md:flex-row gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入英雄名字，例如 Ahri / Yasuo / Lee Sin"
              className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-yellow-500"
            />
            <button
              type="submit"
              className="px-6 py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors disabled:opacity-50"
              disabled={!query.trim()}
            >
              立即抓取
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select value={region} onChange={(e) => setRegion(e.target.value as RegionCode)} className="bg-gray-700 text-white rounded-lg px-3 py-3">
              {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
            </select>
            <select value={queue} onChange={(e) => setQueue(e.target.value as QueueType)} className="bg-gray-700 text-white rounded-lg px-3 py-3">
              {QUEUES.map((q) => <option key={q.code} value={q.code}>{q.name}</option>)}
            </select>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="bg-gray-700 text-white rounded-lg px-3 py-3">
              {ROLES.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
            </select>
          </div>
        </form>

        {!submittedChampion && (
          <div className="bg-gray-800 rounded-2xl p-8 text-center text-gray-400">
            输入英雄名后就会开始抓取。
          </div>
        )}

        {busy && submittedChampion && (
          <div className="bg-gray-800 rounded-2xl p-8 text-center text-gray-300">
            正在抓取 <span className="text-yellow-400 font-semibold">{submittedChampion}</span> 的 OP.GG 聚合信息...
          </div>
        )}

        {error && submittedChampion && !busy && (
          <div className="bg-gray-800 rounded-2xl p-8 text-center">
            <p className="text-red-400 text-lg">抓取失败</p>
            <p className="text-gray-400 mt-2">{error instanceof Error ? error.message : '未知错误'}</p>
            <button onClick={() => refetch()} className="mt-4 px-5 py-2 bg-yellow-500 text-black rounded-lg font-semibold hover:bg-yellow-400">
              重试
            </button>
          </div>
        )}

        {searchSummary && !busy && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-2xl p-6 flex items-center gap-4">
              <ChampionPortrait championName={submittedChampion} size="lg" showName />
              <div className="space-y-1">
                <h2 className="text-2xl font-bold text-white">{submittedChampion}</h2>
                <p className="text-gray-400">数据源: {searchSummary.source}</p>
                <div className="flex flex-wrap gap-3 text-sm">
                  <span className="text-green-400">胜率 {formatRate(searchSummary.win_rate)}</span>
                  <span className="text-blue-400">选用率 {formatRate(searchSummary.pick_rate)}</span>
                  <span className="text-purple-400">对局数 {searchSummary.games_played?.toLocaleString() ?? 'N/A'}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-gray-800 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-white mb-4">推荐出装</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-gray-400 mb-2">核心出装</p>
                    <div className="flex flex-wrap gap-2">
                      {searchSummary.items.core.length > 0 ? searchSummary.items.core.map((item, idx) => (
                        <span key={`${item.id}-${idx}`} className="bg-gray-700 text-white px-3 py-2 rounded-lg">{item.name}</span>
                      )) : <span className="text-gray-500">暂无数据</span>}
                    </div>
                  </div>
                  <div>
                    <p className="text-gray-400 mb-2">起始装备</p>
                    <div className="flex flex-wrap gap-2">
                      {searchSummary.items.start.length > 0 ? searchSummary.items.start.map((item, idx) => (
                        <span key={`${item.id}-${idx}`} className="bg-gray-700 text-gray-200 px-3 py-2 rounded-lg">{item.name}</span>
                      )) : <span className="text-gray-500">暂无数据</span>}
                    </div>
                  </div>
                  <div>
                    <p className="text-gray-400 mb-2">后期装备</p>
                    <div className="flex flex-wrap gap-2">
                      {searchSummary.items.final.length > 0 ? searchSummary.items.final.map((item, idx) => (
                        <span key={`${item.id}-${idx}`} className="bg-gray-700 text-gray-200 px-3 py-2 rounded-lg">{item.name}</span>
                      )) : <span className="text-gray-500">暂无数据</span>}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-white mb-4">英雄克制</h3>
                <div className="space-y-5">
                  <div>
                    <p className="text-red-400 mb-2">克制该英雄</p>
                    <div className="space-y-2">
                      {searchSummary.matchups.counters.length > 0 ? searchSummary.matchups.counters.slice(0, 5).map((item, idx) => (
                        <div key={`${item.champion_name}-${idx}`} className="flex items-center justify-between bg-gray-700 rounded-lg px-3 py-2">
                          <span className="text-white">{item.champion_name}</span>
                          <span className="text-red-400">{formatRate(item.win_rate)}</span>
                        </div>
                      )) : <span className="text-gray-500">暂无数据</span>}
                    </div>
                  </div>

                  <div>
                    <p className="text-green-400 mb-2">该英雄克制</p>
                    <div className="space-y-2">
                      {searchSummary.matchups.countered_by.length > 0 ? searchSummary.matchups.countered_by.slice(0, 5).map((item, idx) => (
                        <div key={`${item.champion_name}-${idx}`} className="flex items-center justify-between bg-gray-700 rounded-lg px-3 py-2">
                          <span className="text-white">{item.champion_name}</span>
                          <span className="text-green-400">{formatRate(item.win_rate)}</span>
                        </div>
                      )) : <span className="text-gray-500">暂无数据</span>}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-2xl p-6 lg:col-span-2">
                <h3 className="text-xl font-bold text-white mb-4">最佳组合英雄</h3>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  {(searchSummary.synergies ?? []).length > 0 ? searchSummary.synergies.slice(0, 5).map((item, idx) => (
                    <div key={`${item.champion_name}-${idx}`} className="bg-gray-700 rounded-lg px-3 py-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-gray-400 text-sm">#{idx + 1}</span>
                        <span className="text-green-400 font-semibold">{formatRate(item.win_rate)}</span>
                      </div>
                      <p className="text-white font-medium mt-2 truncate">{item.champion_name}</p>
                      <p className="text-gray-400 text-sm mt-1">选用率 {formatRate(item.pick_rate)}</p>
                    </div>
                  )) : <span className="text-gray-500">暂无数据</span>}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
