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
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <Link to="/" className="text-gray-400 hover:text-white inline-block">
          ← 返回
        </Link>

        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-yellow-400">AI 教练</h1>
            <p className="text-gray-400 mt-2">基于最近比赛生成优先训练建议，并支持本页追问。</p>
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
            <section className="bg-gray-800 rounded-xl p-6">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <span className="text-gray-400 text-sm">
                  {report.data_window.match_count} 场比赛 · {formatGeneratedAt(reportResponse?.generated_at)}
                </span>
                {reportResponse?.stale && (
                  <span className="px-3 py-1 rounded-full bg-yellow-500/15 text-yellow-300 text-sm">
                    旧报告
                  </span>
                )}
                <span className="px-3 py-1 rounded-full bg-gray-700 text-gray-300 text-sm">
                  {formatConfidence(report.confidence)}
                </span>
              </div>
              <p className="text-white text-lg leading-relaxed">{report.summary}</p>
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {report.priorities.slice(0, 3).map((priority) => (
                <article key={`${getPriorityArea(priority)}-${priority.title}`} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <h2 className="text-lg font-bold text-white">{priority.title}</h2>
                    <span className={`px-2 py-1 rounded border text-xs ${severityClass(priority.severity)}`}>
                      {priority.severity}
                    </span>
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

            <section className="bg-gray-800 rounded-xl p-6 space-y-4">
              <h2 className="text-xl font-bold text-white">后续追问</h2>
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
