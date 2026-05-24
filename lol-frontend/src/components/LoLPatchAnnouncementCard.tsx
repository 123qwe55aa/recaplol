import { usePatchAnnouncement } from '../hooks/usePatchAnnouncement';
import { useLolVersion } from '../hooks/useLolVersion';
import { useState } from 'react';
import {
  buildChampionIconUrl,
  buildDdragonAssetUrl,
  buildItemIconUrl,
  DEFAULT_DDRAGON_VERSION,
} from '../services/ddragon';

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
  const { data: lolVersion } = useLolVersion();
  const [expanded, setExpanded] = useState(false);
  const ddragonVersion = lolVersion || DEFAULT_DDRAGON_VERSION;
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
                            <EntityIcon section={section} item={group.name} version={ddragonVersion} />
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
                            <EntityIcon section={section} item={item} version={ddragonVersion} />
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

function EntityIcon({ section, item, version }: { section: string; item: string; version: string }) {
  const entityName = item.split(/[:：]/)[0]?.trim();
  const normalizedName = entityName ? normalizeEntityName(entityName) : '';
  const heroKey = resolveMappedKey(normalizedName, CHAMPION_ICON_MAP);
  const itemKey = resolveMappedKey(normalizedName, ITEM_ICON_MAP);
  const runeKey = resolveMappedKey(normalizedName, RUNE_ICON_MAP);
  const heroId = heroKey ? CHAMPION_ICON_MAP[heroKey] : undefined;
  const itemId = itemKey ? ITEM_ICON_MAP[itemKey] : undefined;
  const runeIconUrl = runeKey ? RUNE_ICON_MAP[runeKey] : undefined;

  if (section === '英雄' && heroId) {
    return (
      <img
        src={buildChampionIconUrl(version, heroId)}
        alt={`${entityName} 图标`}
        className="h-5 w-5 rounded object-cover"
        loading="lazy"
      />
    );
  }
  if (section === '道具' && itemId) {
    return (
      <img
        src={buildItemIconUrl(Number(itemId), version)}
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
  return value
    .replace(/\s+/g, '')
    .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF]/gu, '')
    .replace(/[•·,，。.!！?？()（）「」『』【】]/g, '')
    .replace(/^英雄/, '')
    .replace(/^道具/, '')
    .replace(/^符文/, '');
}

function resolveMappedKey(source: string, table: Record<string, string>) {
  if (!source) return undefined;
  const direct = table[source];
  if (direct) return source;

  const alias = ENTITY_ALIASES[source];
  if (alias && table[alias]) return alias;

  const allKeys = Object.keys(table);
  const exactInclusion = allKeys.find((key) => source.includes(key) || key.includes(source));
  if (exactInclusion) return exactInclusion;

  const simplifiedSource = toSimplified(source);
  const simplifiedMatch = allKeys.find((key) => simplifiedSource.includes(toSimplified(key)));
  return simplifiedMatch;
}

function toSimplified(value: string) {
  return value
    .replace(/蘭/g, '兰')
    .replace(/觸/g, '触')
    .replace(/護/g, '护')
    .replace(/風/g, '风')
    .replace(/劍/g, '剑')
    .replace(/盔/g, '盔');
}

const CHAMPION_ICON_MAP: Record<string, string> = {
  厄薩斯: 'Aatrox',
  阿璃: 'Ahri',
  阿卡莉: 'Akali',
  安比薩: 'Ambessa',
  阿姆姆: 'Amumu',
  安妮: 'Annie',
  艾希: 'Ashe',
  亞歷斯塔: 'Alistar',
  艾妮維亞: 'Anivia',
  布里茨: 'Blitzcrank',
  布蘭德: 'Brand',
  凱特琳: 'Caitlyn',
  卡蜜兒: 'Camille',
  卡莎碧雅: 'Cassiopeia',
  科加斯: 'Chogath',
  達瑞斯: 'Darius',
  黛安娜: 'Diana',
  伊澤瑞爾: 'Ezreal',
  菲歐拉: 'Fiora',
  飛斯: 'Fizz',
  加里歐: 'Galio',
  蓋倫: 'Garen',
  葛雷夫: 'Graves',
  古拉格斯: 'Gragas',
  漢默丁格: 'Heimerdinger',
  伊羅旖: 'Illaoi',
  伊瑞莉雅: 'Irelia',
  埃爾文: 'Ivern',
  嘉文四世: 'JarvanIV',
  杰西: 'Jayce',
  燼: 'Jhin',
  吉茵珂絲: 'Jinx',
  凱莎: 'Kaisa',
  卡瑪: 'Karma',
  卡薩丁: 'Kassadin',
  卡特蓮娜: 'Katarina',
  凱爾: 'Kayle',
  凱能: 'Kennen',
  卡力斯: 'Khazix',
  勒布朗: 'Leblanc',
  李星: 'LeeSin',
  雷歐娜: 'Leona',
  露璐: 'Lulu',
  拉克絲: 'Lux',
  墨菲特: 'Malphite',
  茂凱: 'Maokai',
  易大師: 'MasterYi',
  魔甘娜: 'Morgana',
  娜菲芮: 'Naafiri',
  娜米: 'Nami',
  納瑟斯: 'Nasus',
  納帝魯斯: 'Nautilus',
  奈德麗: 'Nidalee',
  歐拉夫: 'Olaf',
  奧莉安娜: 'Orianna',
  潘森: 'Pantheon',
  波比: 'Poppy',
  派克: 'Pyke',
  葵恩: 'Quinn',
  雷玟: 'Riven',
  雷尼克頓: 'Renekton',
  雷珂煞: 'RekSai',
  逆命: 'TwistedFate',
  雷茲: 'Ryze',
  史瓦妮: 'Sejuani',
  賽特: 'Sett',
  慎: 'Shen',
  希維爾: 'Sivir',
  索娜: 'Sona',
  索拉卡: 'Soraka',
  斯溫: 'Swain',
  賽勒斯: 'Sylas',
  塔里克: 'Taric',
  提摩: 'Teemo',
  瑟雷西: 'Thresh',
  特朗德: 'Trundle',
  泰達米爾: 'Tryndamere',
  圖奇: 'Twitch',
  烏迪爾: 'Udyr',
  烏爾加特: 'Urgot',
  汎: 'Vayne',
  維迦: 'Veigar',
  威寇茲: 'Velkoz',
  菲艾: 'Vi',
  維克特: 'Viktor',
  弗拉迪米爾: 'Vladimir',
  弗力貝爾: 'Volibear',
  沃維克: 'Warwick',
  悟空: 'MonkeyKing',
  霞: 'Xayah',
  齊勒斯: 'Xerath',
  趙信: 'XinZhao',
  犽宿: 'Yasuo',
  犽凝: 'Yone',
  約瑞科: 'Yorick',
  劫: 'Zed',
  希格斯: 'Ziggs',
  極靈: 'Zilean',
  柔依: 'Zoe',
  枷蘿: 'Zyra',
};

const ITEM_ICON_MAP: Record<string, string> = {
  多蘭之劍: '1055',
  多蘭之戒: '1056',
  多蘭之盾: '1054',
  多蘭之弓: '1086',
  多蘭之盔: '1120',
  狂戰士護脛: '3006',
  貪婪護脛: '3008',
  法師之靴: '3020',
  鍍板鋼蓋: '3047',
  水星之靴: '3111',
  愛歐尼亞之靴: '3158',
  海妖殺手: '6672',
  不朽盾弓: '6673',
  狂怒匕首: '6677',
  電流旋風劍: '6699',
  風暴浪湧: '4646',
  雷霆風暴: '4646',
  死亡之帽: '3089',
  黎安卓的折磨: '6653',
  盧登回音: '6655',
  巫妖之禍: '3100',
  時光之杖: '6657',
  虛空之杖: '3135',
};

const RUNE_ICON_MAP: Record<string, string> = {
  冥火之觸: buildDdragonAssetUrl('perk-images/Styles/Sorcery/Scorch/Scorch.png'),
  不死之握: buildDdragonAssetUrl('perk-images/Styles/Resolve/GraspOfTheUndying/GraspOfTheUndying.png'),
  先攻: buildDdragonAssetUrl('perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png'),
  致命節奏: buildDdragonAssetUrl('perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png'),
  征服者: buildDdragonAssetUrl('perk-images/Styles/Precision/Conqueror/Conqueror.png'),
  電刑: buildDdragonAssetUrl('perk-images/Styles/Domination/Electrocute/Electrocute.png'),
  相位衝擊: buildDdragonAssetUrl('perk-images/Styles/Sorcery/PhaseRush/PhaseRush.png'),
  奧術彗星: buildDdragonAssetUrl('perk-images/Styles/Sorcery/ArcaneComet/ArcaneComet.png'),
};

const ENTITY_ALIASES: Record<string, string> = {
  多兰之剑: '多蘭之劍',
  多兰之戒: '多蘭之戒',
  多兰之盾: '多蘭之盾',
  多兰之弓: '多蘭之弓',
  多兰之盔: '多蘭之盔',
  狂战士护胫: '狂戰士護脛',
  电流旋风剑: '電流旋風劍',
  狂怒匕首: '狂怒匕首',
  海妖杀手: '海妖殺手',
  不朽盾弓: '不朽盾弓',
  法师之靴: '法師之靴',
  水银之靴: '水星之靴',
  锁子甲靴: '鍍板鋼蓋',
  明朗之靴: '愛歐尼亞之靴',
  风暴浪涌: '風暴浪湧',
  雷霆风暴: '雷霆風暴',
  贪婪护胫: '貪婪護脛',
  灭世者的死亡之帽: '死亡之帽',
  兰德里的折磨: '黎安卓的折磨',
  卢登的回声: '盧登回音',
  巫妖之祸: '巫妖之禍',
  时光之杖: '時光之杖',
  虚空之杖: '虛空之杖',
  冥火之触: '冥火之觸',
  致命节奏: '致命節奏',
  征服者: '征服者',
  电刑: '電刑',
  相位猛冲: '相位衝擊',
  奥术彗星: '奧術彗星',
  安比萨: '安比薩',
  娜菲芮: '娜菲芮',
  艾妮维亚: '艾妮維亞',
  加里奥: '加里歐',
  加里欧: '加里歐',
  艾希: '艾希',
};
