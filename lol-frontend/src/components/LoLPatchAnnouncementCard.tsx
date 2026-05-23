import { usePatchAnnouncement } from '../hooks/usePatchAnnouncement';
import { useState } from 'react';

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
                      <li key={`${section}-${item}`}>• {item}</li>
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
