import { useRiotStatus } from '../hooks/useRiotStatus';
import type { RiotStatusUpdate } from '../types';

function updateTitle(update: RiotStatusUpdate | undefined): string | null {
  const title = update?.titles?.find((item) => item.locale === 'zh_TW') ?? update?.titles?.[0];
  return title?.content ?? null;
}

export function RiotStatusCard({ platform }: { platform: string }) {
  const normalizedPlatform = platform.trim().toUpperCase();
  const { data, isLoading, error } = useRiotStatus(platform);
  const maintenances = data?.maintenances ?? [];
  const incidents = data?.incidents ?? [];
  const issueCount = maintenances.length + incidents.length;
  const headline = incidents[0] ?? maintenances[0];

  return (
    <section className="mt-4 rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-yellow-300">Riot 服务状态</p>
          <p className="mt-1 text-xs text-gray-500">{normalizedPlatform || '平台未知'}</p>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-semibold ${issueCount > 0 ? 'bg-red-500/15 text-red-300' : 'bg-green-500/15 text-green-300'}`}>
          {isLoading ? '检查中' : issueCount > 0 ? '需要关注' : '服务正常'}
        </span>
      </div>

      <p className="mt-3 text-sm text-gray-300">
        {error
          ? '暂时无法读取 Riot 服务状态。'
          : issueCount > 0
            ? `维护 ${maintenances.length} 项 · 异常 ${incidents.length} 项`
            : '当前没有公开维护或异常公告。'}
      </p>

      {headline && (
        <p className="mt-2 rounded bg-gray-800 px-3 py-2 text-sm text-gray-200">
          {updateTitle(headline) ?? 'Riot 已发布服务状态更新'}
        </p>
      )}
    </section>
  );
}
