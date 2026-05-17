import { FormEvent, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useCoachChat, useCoachReport, useGenerateCoachReport } from '../hooks/useCoach';
import type { CoachChatResponse, CoachPriority } from '../types';

interface ChatMessage {
  role: 'user' | 'coach';
  text: string;
}

function formatGeneratedAt(value?: string | null) {
  if (!value) return '刚刚生成';
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function severityClass(severity: CoachPriority['severity']) {
  if (severity === 'high') return 'border-red-500/60 text-red-300 bg-red-500/10';
  if (severity === 'medium') return 'border-yellow-500/60 text-yellow-300 bg-yellow-500/10';
  return 'border-green-500/60 text-green-300 bg-green-500/10';
}

function getPriorityArea(priority: CoachPriority) {
  return priority.area ?? priority.category ?? priority.title;
}

function getPriorityRecommendation(priority: CoachPriority) {
  return priority.recommendation ?? priority.rationale ?? '';
}

function getPriorityActions(priority: CoachPriority) {
  return priority.action_items ?? (priority.recommendation ? [priority.recommendation] : []);
}

function formatConfidence(confidence: number | string) {
  if (typeof confidence === 'number') {
    return `可信度 ${(confidence * 100).toFixed(0)}%`;
  }
  const labels: Record<string, string> = {
    high: '可信度高',
    medium: '可信度中',
    low: '可信度低',
  };
  return labels[confidence] ?? `可信度 ${confidence}`;
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return '-';
  return `${Math.round(value * 100)}%`;
}

function formatNumber(value?: number | null, digits = 1) {
  if (value === null || value === undefined) return '-';
  return Number(value).toFixed(digits).replace(/\.0$/, '');
}

function formatDelta(value?: number | null, digits = 1) {
  if (value === null || value === undefined) return '-';
  const formatted = formatNumber(value, digits);
  return value > 0 ? `+${formatted}` : formatted;
}

function roleLabel(role?: string | null) {
  const labels: Record<string, string> = {
    TOP: '上路',
    JUNGLE: '打野',
    MIDDLE: '中路',
    MID: '中路',
    BOTTOM: '下路',
    ADC: '下路',
    UTILITY: '辅助',
    SUPPORT: '辅助',
  };
  return role ? labels[role] ?? role : '-';
}

function resultLabel(win?: boolean | null) {
  if (win === true) return '胜';
  if (win === false) return '负';
  return '重开/未知';
}

function resultClass(win?: boolean | null) {
  if (win === true) return 'text-blue-300 bg-blue-500/10 border-blue-500/40';
  if (win === false) return 'text-red-300 bg-red-500/10 border-red-500/40';
  return 'text-gray-300 bg-gray-700 border-gray-600';
}

function metricTone(label: string) {
  if (label.includes('死亡')) return 'text-red-300 border-red-500/30 bg-red-500/10';
  if (label.includes('视野')) return 'text-cyan-300 border-cyan-500/30 bg-cyan-500/10';
  if (label.includes('胜率')) return 'text-blue-300 border-blue-500/30 bg-blue-500/10';
  return 'text-yellow-200 border-yellow-500/30 bg-yellow-500/10';
}

export function CoachPage() {
  const { puuid = '' } = useParams<{ puuid: string }>();
  const reportQuery = useCoachReport(puuid);
  const generateReport = useGenerateCoachReport(puuid);
  const chat = useCoachChat(puuid);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const reportResponse = reportQuery.data;
  const report = reportResponse?.report ?? null;
  const busy = reportQuery.isLoading || reportQuery.isFetching || generateReport.isPending;
  const dashboard = report?.dashboard ?? {};
  const averages = dashboard.averages ?? {};
  const laneComparison = dashboard.lane_opponent_comparison;
  const recentMatches = report?.recent_matches ?? [];
  const kdaText = `${formatNumber(averages.kills)}/${formatNumber(averages.deaths)}/${formatNumber(averages.assists)}`;
  const metrics = [
    { label: '近况胜率', value: formatPercent(dashboard.win_rate), sub: `${dashboard.match_count ?? report?.data_window.match_count ?? 0} 场样本` },
    { label: '主位置', value: roleLabel(dashboard.primary_role ?? report?.data_window.primary_role), sub: 'Riot teamPosition' },
    { label: '场均 KDA', value: kdaText, sub: '击杀 / 死亡 / 助攻' },
    { label: '场均死亡', value: formatNumber(averages.deaths), sub: '越低越稳定' },
    { label: 'CS/min', value: formatNumber(averages.cs_per_minute), sub: '按主位置解读' },
    { label: '视野分', value: formatNumber(averages.vision_score), sub: '资源前信息量' },
  ];

  const handleGenerate = (force = false) => {
    generateReport.mutate(force);
  };

  const handleQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || chat.isPending) return;

    setQuestion('');
    setMessages((current) => [...current, { role: 'user', text: trimmed }]);
    const answer: CoachChatResponse = await chat.mutateAsync(trimmed);
    setMessages((current) => [...current, { role: 'coach', text: answer.answer }]);
  };

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <Link to="/" className="text-gray-400 hover:text-white inline-block">
          ← 返回
        </Link>

        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b border-gray-800 pb-5">
          <div>
            <h1 className="text-3xl font-bold text-yellow-400">AI 教练</h1>
            <p className="text-gray-400 mt-2">把最近比赛拆成训练优先级、数据样本和可追问的改进计划。</p>
          </div>
          {report && (
            <button
              type="button"
              onClick={() => handleGenerate(true)}
              disabled={busy}
              className="px-5 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              重新生成
            </button>
          )}
        </div>

        {busy && !report && (
          <div className="bg-gray-800 rounded-xl p-8 text-center text-gray-300">
            正在准备训练报告...
          </div>
        )}

        {reportQuery.error && !busy && (
          <div className="bg-gray-800 rounded-xl p-8 text-center">
            <p className="text-red-400 text-lg font-semibold">训练报告加载失败</p>
            <p className="text-gray-400 mt-2">
              {reportQuery.error instanceof Error ? reportQuery.error.message : '请稍后再试'}
            </p>
            <button
              type="button"
              onClick={() => reportQuery.refetch()}
              className="mt-5 px-5 py-2 bg-yellow-500 text-black rounded-lg font-semibold hover:bg-yellow-400"
            >
              重试
            </button>
          </div>
        )}

        {!busy && !reportQuery.error && reportResponse && (reportResponse.has_report === false || !report) && (
          <div className="bg-gray-800 rounded-xl p-8 text-center">
            <h2 className="text-xl font-bold text-white">还没有训练报告</h2>
            <p className="text-gray-400 mt-2">生成一份报告后，AI 教练会给出 3 个优先提升方向。</p>
            <button
              type="button"
              onClick={() => handleGenerate(false)}
              disabled={generateReport.isPending}
              className="mt-5 px-6 py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 disabled:opacity-50"
            >
              生成训练报告
            </button>
          </div>
        )}

        {report && (
          <div className="space-y-6">
            <section className="border border-gray-800 bg-gray-900 rounded-lg p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-gray-500 text-xs uppercase">训练仪表盘</p>
                  <h2 className="text-2xl font-bold text-white mt-1">本轮训练重点</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-sm">
                    {report.data_window.match_count} 场比赛
                  </span>
                  <span className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-sm">
                    {formatGeneratedAt(reportResponse?.generated_at)}
                  </span>
                  {reportResponse?.stale && (
                    <span className="px-3 py-1 rounded-full bg-yellow-500/15 text-yellow-300 text-sm">
                      旧报告
                    </span>
                  )}
                  <span className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-sm">
                    {formatConfidence(report.confidence)}
                  </span>
                </div>
              </div>
              <p className="text-white text-lg leading-relaxed mt-5">{report.summary}</p>
            </section>

            <section className="grid grid-cols-2 lg:grid-cols-6 gap-3">
              {metrics.map((metric) => (
                <article key={metric.label} className={`border rounded-lg p-4 ${metricTone(metric.label)}`}>
                  <p className="text-xs text-gray-400">{metric.label}</p>
                  <p className="text-2xl font-bold text-white mt-2">{metric.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{metric.sub}</p>
                </article>
              ))}
            </section>

            <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
              {report.priorities.slice(0, 3).map((priority, index) => (
                <article key={`${getPriorityArea(priority)}-${priority.title}`} className="bg-gray-900 rounded-lg p-5 border border-gray-800">
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex items-center gap-3">
                      <span className="h-9 w-9 rounded-md bg-yellow-400 text-black font-bold flex items-center justify-center">
                        {index + 1}
                      </span>
                      <div>
                        <p className="text-gray-500 text-xs">{getPriorityArea(priority)}</p>
                        <h2 className="text-lg font-bold text-white">{priority.title}</h2>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded border text-xs ${severityClass(priority.severity)}`}>{priority.severity}</span>
                  </div>
                  <p className="text-gray-300 text-sm leading-6">{getPriorityRecommendation(priority)}</p>
                  <div className="mt-4 space-y-3">
                    <div>
                      <p className="text-gray-500 text-xs uppercase">证据</p>
                      <ul className="mt-2 space-y-1 text-sm text-gray-300">
                        {priority.evidence.map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs uppercase">行动</p>
                      <ul className="mt-2 space-y-1 text-sm text-gray-300">
                        {getPriorityActions(priority).map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </article>
              ))}
            </section>

            {laneComparison && (laneComparison.sample_size ?? 0) > 0 && (
              <section className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
                <div className="p-5 flex items-center justify-between gap-3 border-b border-gray-800">
                  <div>
                    <p className="text-gray-500 text-xs uppercase">Same-role benchmark</p>
                    <h2 className="text-xl font-bold text-white">对位横向对比</h2>
                  </div>
                  <span className="text-gray-400 text-sm">{laneComparison.sample_size} 局同位置样本</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-950 text-gray-400">
                      <tr>
                        <th className="text-left font-medium px-4 py-3">指标</th>
                        <th className="text-left font-medium px-4 py-3">你</th>
                        <th className="text-left font-medium px-4 py-3">敌方同位置</th>
                        <th className="text-left font-medium px-4 py-3">差值</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {[
                        { key: 'kills', label: '击杀', digits: 1 },
                        { key: 'deaths', label: '死亡', digits: 1 },
                        { key: 'assists', label: '助攻', digits: 1 },
                        { key: 'cs_per_minute', label: 'CS/min', digits: 1 },
                        { key: 'vision_score', label: '视野', digits: 1 },
                        { key: 'gold_earned', label: '金币', digits: 0 },
                      ].map((metric) => {
                        const key = metric.key as keyof NonNullable<typeof laneComparison.player>;
                        return (
                          <tr key={metric.key} className="text-gray-300">
                            <td className="px-4 py-3 text-white font-medium">{metric.label}</td>
                            <td className="px-4 py-3">
                              {formatNumber(laneComparison.player?.[key], metric.digits)}
                            </td>
                            <td className="px-4 py-3">
                              {formatNumber(laneComparison.opponent?.[key], metric.digits)}
                            </td>
                            <td className="px-4 py-3 font-semibold text-yellow-200">
                              {formatDelta(laneComparison.delta?.[key], metric.digits)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
            {laneComparison && (laneComparison.sample_size ?? 0) === 0 && (
              <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
                <p className="text-gray-500 text-xs uppercase">Same-role benchmark</p>
                <h2 className="text-xl font-bold text-white mt-1">对位横向对比</h2>
                <p className="text-gray-300 text-sm mt-3">
                  当前样本里缺少可匹配的敌方同位置数据，暂时无法生成横向对比。
                </p>
              </section>
            )}

            {recentMatches.length > 0 && (
              <section className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
                <div className="p-5 flex items-center justify-between gap-3 border-b border-gray-800">
                  <div>
                    <p className="text-gray-500 text-xs uppercase">Recent sample</p>
                    <h2 className="text-xl font-bold text-white">最近比赛样本</h2>
                  </div>
                  <span className="text-gray-400 text-sm">{recentMatches.length} 局</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-950 text-gray-400">
                      <tr>
                        <th className="text-left font-medium px-4 py-3">英雄</th>
                        <th className="text-left font-medium px-4 py-3">敌方同位</th>
                        <th className="text-left font-medium px-4 py-3">位置</th>
                        <th className="text-left font-medium px-4 py-3">结果</th>
                        <th className="text-left font-medium px-4 py-3">KDA</th>
                        <th className="text-left font-medium px-4 py-3">CS/min</th>
                        <th className="text-left font-medium px-4 py-3">视野</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {recentMatches.map((match) => {
                        const minutes = (match.game_duration ?? 0) / 60;
                        const csPerMinute = minutes > 0 ? (Number(match.cs ?? 0) / minutes) : null;
                        return (
                          <tr key={match.match_id} className="text-gray-300">
                            <td className="px-4 py-3 text-white font-medium">{match.champion_name || '-'}</td>
                            <td className="px-4 py-3">{match.lane_opponent?.champion_name || '-'}</td>
                            <td className="px-4 py-3">{roleLabel(match.role)}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 rounded border text-xs ${resultClass(match.win)}`}>{resultLabel(match.win)}</span>
                            </td>
                            <td className="px-4 py-3">{formatNumber(match.kills, 0)}/{formatNumber(match.deaths, 0)}/{formatNumber(match.assists, 0)}</td>
                            <td className="px-4 py-3">{formatNumber(csPerMinute)}</td>
                            <td className="px-4 py-3">{formatNumber(match.vision_score, 0)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            <section className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white">后续追问</h2>
                {chat.isPending && <span className="text-yellow-300 text-sm">AI 正在思考...</span>}
              </div>
              <div className="space-y-3">
                {messages.length === 0 && (
                  <p className="text-gray-400">可以继续问某个优先项该怎么练，回答只保留在当前页面会话。</p>
                )}
                {messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={message.role === 'user' ? 'text-right' : 'text-left'}
                  >
                    <p
                      className={`inline-block max-w-3xl rounded-lg px-4 py-3 text-sm leading-6 ${
                        message.role === 'user'
                          ? 'bg-yellow-500 text-black'
                          : 'bg-gray-700 text-gray-100'
                      }`}
                    >
                      {message.text}
                    </p>
                  </div>
                ))}
                {chat.isPending && (
                  <div className="text-left">
                    <p className="inline-block rounded-lg px-4 py-3 text-sm leading-6 bg-gray-800 text-gray-300">
                      正在整理证据和建议...
                    </p>
                  </div>
                )}
              </div>
              <form data-testid="coach-chat-form" onSubmit={handleQuestion} className="flex flex-col md:flex-row gap-3">
                <input
                  type="text"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="问一个后续问题..."
                  className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-yellow-500"
                />
                <button
                  type="submit"
                  disabled={!question.trim() || chat.isPending}
                  className="px-5 py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 disabled:opacity-50"
                >
                  发送
                </button>
              </form>
              {chat.error && (
                <p className="text-red-400 text-sm">
                  {chat.error instanceof Error ? chat.error.message : '追问失败，请稍后再试'}
                </p>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
