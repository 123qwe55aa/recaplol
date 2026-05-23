import { useLolVersion } from '../hooks/useLolVersion';

const PATCH_NOTES_URL = 'https://www.leagueoflegends.com/zh-tw/news/tags/patch-notes/';
const CN_NOTICES_URL = 'https://lol.qq.com/news/index.shtml';

export function LoLVersionCard() {
  const { data: version, isLoading, error } = useLolVersion();

  return (
    <section className="rounded-lg border border-gray-800 bg-gray-900 p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-yellow-300">LoL 客户端版本</p>
          <div className="mt-2 flex items-baseline gap-3">
            <p className="text-2xl font-bold text-white">
              {isLoading ? '正在检查版本...' : version || '暂时无法获取版本'}
            </p>
            {version && (
              <span className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300">
                Data Dragon
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-gray-400">
            {error
              ? '版本服务暂时不可用，可直接查看台服官方更新页。'
              : '根据 Riot Data Dragon 全局版本列表同步（非分区服）。'}
          </p>
        </div>
        <div className="flex shrink-0 flex-col gap-2">
          <a
            href={PATCH_NOTES_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-lg bg-yellow-500 px-4 py-2 font-bold text-black transition-colors hover:bg-yellow-400"
          >
            台服官网更新
          </a>
          <a
            href={CN_NOTICES_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-lg bg-gray-800 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
          >
            国服官网公告
          </a>
        </div>
      </div>
    </section>
  );
}
