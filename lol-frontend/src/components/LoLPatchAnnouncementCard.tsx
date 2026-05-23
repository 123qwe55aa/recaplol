import { usePatchAnnouncement } from '../hooks/usePatchAnnouncement';
import { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

function formatDate(value?: string | null) {
  if (!value) return '最新公告';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

export function LoLPatchAnnouncementCard() {
  const { data: announcement, isLoading, error } = usePatchAnnouncement();
  const [expanded, setExpanded] = useState(false);
  const details = announcement?.analysis?.details ?? {};
  const categoryMetrics = buildCategoryMetrics(details);

  if (isLoading) {
    return (
      <section className="rounded-lg border border-gray-800 bg-gray-900 p-5">
        <p className="text-sm font-semibold text-yellow-300">LoL 版本公告</p>
        <p className="mt-3 text-white">正在读取台服最新版本公告...</p>
      </section>
    );
  }

  if (error || !announcement) {
    return (
      <section className="rounded-lg border border-gray-800 bg-gray-900 p-5">
        <p className="text-sm font-semibold text-yellow-300">LoL 版本公告</p>
        <p className="mt-3 text-gray-300">暂时无法读取最新公告，请稍后重试。</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-yellow-500/30 bg-gray-900 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-yellow-300">LoL 版本公告</p>
            <span className="rounded bg-yellow-500/15 px-2 py-1 text-xs font-semibold text-yellow-200">
              {announcement.version}
            </span>
            <span className="text-xs text-gray-500">{formatDate(announcement.published_at)}</span>
          </div>
          <h3 className="mt-3 text-2xl font-bold text-white">{announcement.title}</h3>
          <p className="mt-2 text-gray-300">{announcement.summary}</p>
          <p className="mt-3 text-sm leading-6 text-gray-400">{announcement.overview}</p>
        </div>
        <a
          href={announcement.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex shrink-0 items-center justify-center rounded-lg bg-yellow-500 px-4 py-2 font-bold text-black transition-colors hover:bg-yellow-400"
        >
          查看官方原文
        </a>
      </div>

      <div className="mt-5 border-t border-gray-800 pt-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold text-white">{announcement.analysis.headline}</p>
          {announcement.analysis.sections.slice(0, 4).map((section) => (
            <span key={section} className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300">
              {section}
            </span>
          ))}
        </div>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-gray-300">
          {announcement.analysis.takeaways.slice(0, 4).map((takeaway) => (
            <li key={takeaway}>• {takeaway}</li>
          ))}
        </ul>

        <div className="mt-4 rounded-lg border border-gray-800 bg-gray-950 p-3">
          <p className="text-sm font-semibold text-white">平衡性变更概览</p>
          <div className="mt-3 h-56 w-full">
            <ResponsiveContainer>
              <BarChart data={categoryMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="category" stroke="#9CA3AF" fontSize={12} />
                <YAxis allowDecimals={false} stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Legend />
                <Bar dataKey="buff" name="增强" fill="#22C55E" radius={[4, 4, 0, 0]} />
                <Bar dataKey="nerf" name="削弱" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {categoryMetrics.map((metric) => (
              <div key={metric.category} className="rounded-lg bg-gray-900 px-3 py-2 text-xs text-gray-300">
                <p className="text-gray-400">{metric.category}</p>
                <p className="mt-1">
                  增强 <span className="font-semibold text-green-300">{metric.buff}</span>
                  {' · '}
                  削弱 <span className="font-semibold text-red-300">{metric.nerf}</span>
                </p>
              </div>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className="mt-4 inline-flex items-center justify-center rounded-lg bg-gray-800 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
        >
          {expanded ? '收起完整版本清单' : '展开完整版本清单'}
        </button>

        {expanded && (
          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {Object.entries(announcement.analysis.details)
              .length === 0 && (
                <section className="rounded-lg border border-gray-800 bg-gray-950 p-3">
                  <p className="text-sm text-gray-400">暂无详细条目，稍后刷新重试。</p>
                </section>
              )}
            {Object.entries(details)
              .filter(([, items]) => items.length > 0)
              .slice(0, 8)
              .map(([section, items]) => (
                <section key={section} className="rounded-lg border border-gray-800 bg-gray-950 p-3">
                  <p className="text-sm font-semibold text-yellow-200">{section}</p>
                  <ul className="mt-2 space-y-1 text-sm text-gray-300">
                    {items.slice(0, 6).map((item) => (
                      <li key={`${section}-${item}`}>
                        <span className={toneClass(item)}>{toneLabel(item)}</span>
                        <span className="ml-2">• {item}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
          </div>
        )}
      </div>
    </section>
  );
}

function toneClass(value: string) {
  if (isBuff(value)) return 'rounded bg-green-500/20 px-2 py-0.5 text-xs text-green-300';
  if (isNerf(value)) return 'rounded bg-red-500/20 px-2 py-0.5 text-xs text-red-300';
  return 'rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300';
}

function toneLabel(value: string) {
  if (isBuff(value)) return '增强';
  if (isNerf(value)) return '削弱';
  return '调整';
}

function isBuff(value: string) {
  return /(提升|增加|上调|Buff|⇒)/i.test(value) && !/(降低|削弱|下调|Nerf)/i.test(value);
}

function isNerf(value: string) {
  return /(降低|削弱|下调|Nerf|⇒)/i.test(value) && !/(提升|增加|上调|Buff)/i.test(value);
}

function buildCategoryMetrics(details: Record<string, string[]>) {
  const labels = ['英雄', '道具', '符文'];
  return labels.map((label) => {
    const values = details[label] ?? [];
    const buff = values.filter(isBuff).length;
    const nerf = values.filter(isNerf).length;
    return { category: label, buff, nerf };
  });
}
