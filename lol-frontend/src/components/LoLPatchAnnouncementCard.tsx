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
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {categoryMetrics.map((metric) => (
              <div key={metric.category} className="rounded-lg border border-gray-800 bg-gray-900 px-3 py-2 text-xs text-gray-300">
                <p className="flex items-center gap-2 text-gray-200">
                  <span aria-hidden="true" className="text-sm">
                    {getCategoryIcon(metric.category)}
                  </span>
                  <span>{metric.category}</span>
                </p>
                <p className="mt-1 text-gray-300">
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
                  {section === '英雄' || section === '道具' || section === '符文' ? (
                    <div className="mt-2 space-y-3">
                      {buildEntityGroups(items).map((group) => (
                        <div key={`${section}-${group.name}`} className="rounded border border-gray-800 bg-gray-900/60 p-2">
                          <p className="flex items-center gap-2 text-sm font-semibold text-gray-100">
                            <EntityIcon section={section} item={group.name} />
                            <span>{group.name}</span>
                          </p>
                          <ul className="mt-2 space-y-1 text-sm text-gray-300">
                            {group.items.map((item) => (
                              <li key={`${section}-${group.name}-${item}`}>
                                <span className={toneClass(item)}>{toneLabel(item)}</span>
                                <span className="ml-2">• {item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <ul className="mt-2 space-y-1 text-sm text-gray-300">
                      {items.slice(0, 6).map((item) => (
                        <li key={`${section}-${item}`}>
                          <span className={toneClass(item)}>{toneLabel(item)}</span>
                          <span className="ml-2 inline-flex items-center gap-2">
                            <EntityIcon section={section} item={item} />
                            <span>• {item}</span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
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

function getCategoryIcon(category: string) {
  if (category === '英雄') return '⚔';
  if (category === '道具') return '🛡';
  return '✦';
}

function buildEntityGroups(items: string[]) {
  const groups = new Map<string, string[]>();
  items.forEach((item) => {
    const name = item.split(/[:：]/)[0]?.trim() || '其他';
    const bucket = groups.get(name);
    if (bucket) bucket.push(item);
    else groups.set(name, [item]);
  });
  return Array.from(groups.entries()).map(([name, groupedItems]) => ({
    name,
    items: groupedItems.slice(0, 6),
  }));
}

function EntityIcon({ section, item }: { section: string; item: string }) {
  const entityName = item.split(/[:：]/)[0]?.trim();
  const normalizedName = entityName ? normalizeEntityName(entityName) : undefined;
  const heroId = normalizedName ? CHAMPION_ICON_MAP[normalizedName] : undefined;
  const itemId = normalizedName ? ITEM_ICON_MAP[normalizedName] : undefined;
  const runeIconUrl = normalizedName ? RUNE_ICON_MAP[normalizedName] : undefined;

  if (section === '英雄' && heroId) {
    return (
      <img
        src={`https://ddragon.leagueoflegends.com/cdn/${DDRAGON_CDN_VERSION}/img/champion/${heroId}.png`}
        alt={`${entityName} 图标`}
        className="h-5 w-5 rounded object-cover"
        loading="lazy"
      />
    );
  }
  if (section === '道具' && itemId) {
    return (
      <img
        src={`https://ddragon.leagueoflegends.com/cdn/${DDRAGON_CDN_VERSION}/img/item/${itemId}.png`}
        alt={`${entityName} 图标`}
        className="h-5 w-5 rounded object-cover"
        loading="lazy"
      />
    );
  }
  if (section === '符文' && runeIconUrl) {
    return (
      <img
        src={runeIconUrl}
        alt={`${entityName} 图标`}
        className="h-5 w-5 rounded object-cover"
        loading="lazy"
      />
    );
  }
  return (
    <span aria-label={`${section} 图标`} className="text-sm">
      {getCategoryIcon(section)}
    </span>
  );
}

function normalizeEntityName(value: string) {
  return value.replace(/\s+/g, '');
}

const DDRAGON_CDN_VERSION = '16.10.1';

const CHAMPION_ICON_MAP: Record<string, string> = {
  安妮: 'Annie',
  安比薩: 'Ambessa',
  艾妮維亞: 'Anivia',
  李星: 'LeeSin',
  葵恩: 'Quinn',
};

const ITEM_ICON_MAP: Record<string, string> = {
  多蘭之劍: '1055',
  多蘭之戒: '1056',
  多蘭之盾: '1054',
  多蘭之弓: '1086',
  多蘭之盔: '1120',
  電流旋風劍: '6699',
  風暴浪湧: '4646',
  雷霆風暴: '4646',
  貪婪護脛: '3008',
};

const RUNE_ICON_MAP: Record<string, string> = {
  冥火之觸: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Scorch/Scorch.png',
  不死之握: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/GraspOfTheUndying/GraspOfTheUndying.png',
  先攻: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png',
  致命節奏: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png',
};
