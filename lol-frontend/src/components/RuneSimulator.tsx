import { useEffect, useMemo, useRef, useState } from 'react';

type RunePathId = 'precision' | 'domination' | 'sorcery' | 'resolve' | 'inspiration';

interface RunePath {
  id: RunePathId;
  name: string;
  color: string;
  icon: string;
  slots: string[][];
}

const RUNE_PATHS: RunePath[] = [
  {
    id: 'precision',
    name: '精密',
    color: 'text-yellow-400',
    icon: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7201_Precision.png',
    slots: [
      ['致命节奏', '强攻', '迅捷步伐', '征服者'],
      ['气定神闲', '凯旋', '过量治疗'],
      ['传说：欢欣', '传说：韧性', '传说：血统'],
      ['致命一击', '坚毅不倒', '砍倒'],
    ],
  },
  {
    id: 'domination',
    name: '主宰',
    color: 'text-red-400',
    icon: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7200_Domination.png',
    slots: [
      ['电刑', '掠食者', '黑暗收割', '丛刃'],
      ['恶意中伤', '猛然冲击', '血之滋味', '僵尸守卫'],
      ['幽灵魄罗', '眼球收集器'],
      ['贪欲猎手', '终极猎人', '无情猎手'],
    ],
  },
  {
    id: 'sorcery',
    name: '巫术',
    color: 'text-blue-400',
    icon: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7202_Sorcery.png',
    slots: [
      ['艾黎', '奥术彗星', '相位猛冲'],
      ['法力流系带', '虚空行走', '灵光披风'],
      ['超然', '迅捷', '绝对专注'],
      ['焦灼', '风暴聚集', '水上行走'],
    ],
  },
  {
    id: 'resolve',
    name: '坚决',
    color: 'text-green-400',
    icon: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7204_Resolve.png',
    slots: [
      ['不灭之握', '余震', '守护者'],
      ['生命源泉', '护盾猛击', '爆破'],
      ['调节', '复苏之风', '骸骨镀层'],
      ['坚定', '复苏', '过度生长'],
    ],
  },
  {
    id: 'inspiration',
    name: '启迪',
    color: 'text-cyan-400',
    icon: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/7203_Whimsy.png',
    slots: [
      ['冰川增幅', '先攻', '原型：全能石'],
      ['海克斯闪现', '神奇之鞋', '完美时机'],
      ['未来市场', '小兵去质器', '饼干配送'],
      ['星界洞悉', '行进速率', '时间扭曲补药'],
    ],
  },
];

const SHARDS = [
  ['自适应之力', '攻击速度', '冷却缩减'],
  ['自适应之力', '移动速度', '生命值'],
  ['护甲', '魔抗', '生命值'],
];

const DDRAGON_BASE = 'https://ddragon.leagueoflegends.com/cdn';
const DDRAGON_VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json';

const SHARD_ICON_MAP: Record<string, string> = {
  自适应之力: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAdaptiveForceIcon.png',
  攻击速度: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAttackSpeedIcon.png',
  冷却缩减: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsCDRScalingIcon.png',
  移动速度: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsMovementSpeedIcon.png',
  生命值: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsHealthScalingIcon.png',
  护甲: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsArmorIcon.png',
  魔抗: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsMagicResIcon.png',
};

const RUNE_ICON_MAP: Record<string, string> = {
  致命节奏: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png',
  强攻: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/PressTheAttack/PressTheAttack.png',
  迅捷步伐: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/FleetFootwork/FleetFootwork.png',
  征服者: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/Conqueror/Conqueror.png',
  气定神闲: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/PresenceOfMind/PresenceOfMind.png',
  凯旋: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/Triumph.png',
  过量治疗: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/Overheal.png',
  '传说：欢欣': 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LegendAlacrity/LegendAlacrity.png',
  '传说：韧性': 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LegendTenacity/LegendTenacity.png',
  '传说：血统': 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LegendBloodline/LegendBloodline.png',
  致命一击: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/CoupDeGrace/CoupDeGrace.png',
  坚毅不倒: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/LastStand/LastStand.png',
  砍倒: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Precision/CutDown/CutDown.png',

  电刑: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/Electrocute/Electrocute.png',
  掠食者: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/Predator/Predator.png',
  黑暗收割: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/DarkHarvest/DarkHarvest.png',
  丛刃: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/HailOfBlades/HailOfBlades.png',
  恶意中伤: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/CheapShot/CheapShot.png',
  猛然冲击: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/SuddenImpact/SuddenImpact.png',
  血之滋味: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/TasteOfBlood/GreenTerror_TasteOfBlood.png',
  僵尸守卫: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/ZombieWard/ZombieWard.png',
  幽灵魄罗: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/GhostPoro/GhostPoro.png',
  眼球收集器: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/EyeballCollection/EyeballCollection.png',
  贪欲猎手: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/TreasureHunter/TreasureHunter.png',
  终极猎人: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/UltimateHunter/UltimateHunter.png',
  无情猎手: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/RelentlessHunter/RelentlessHunter.png',

  艾黎: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/SummonAery/SummonAery.png',
  奥术彗星: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/ArcaneComet/ArcaneComet.png',
  相位猛冲: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/PhaseRush/PhaseRush.png',
  法力流系带: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/ManaflowBand/ManaflowBand.png',
  虚空行走: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/NullifyingOrb/Pokeshield.png',
  灵光披风: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/NimbusCloak/6361.png',
  超然: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Transcendence/Transcendence.png',
  迅捷: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Celerity/CelerityTemp.png',
  绝对专注: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/AbsoluteFocus/AbsoluteFocus.png',
  焦灼: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Scorch/Scorch.png',
  风暴聚集: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/GatheringStorm/GatheringStorm.png',
  水上行走: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/Waterwalking/Waterwalking.png',

  不灭之握: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/GraspOfTheUndying/GraspOfTheUndying.png',
  余震: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/VeteranAftershock/VeteranAftershock.png',
  守护者: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Guardian/Guardian.png',
  生命源泉: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/FontOfLife/FontOfLife.png',
  护盾猛击: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/ShieldBash/ShieldBash.png',
  爆破: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Demolish/Demolish.png',
  调节: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Conditioning/Conditioning.png',
  复苏之风: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/SecondWind/SecondWind.png',
  骸骨镀层: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/BonePlating/BonePlating.png',
  坚定: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Unflinching/Unflinching.png',
  复苏: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Revitalize/Revitalize.png',
  过度生长: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Overgrowth/Overgrowth.png',

  冰川增幅: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/GlacialAugment/GlacialAugment.png',
  先攻: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png',
  '原型：全能石': 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/UnsealedSpellbook/UnsealedSpellbook.png',
  海克斯闪现: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/HextechFlashtraption/HextechFlashtraption.png',
  神奇之鞋: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/MagicalFootwear/MagicalFootwear.png',
  完美时机: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/PerfectTiming/PerfectTiming.png',
  未来市场: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/FuturesMarket/FuturesMarket.png',
  小兵去质器: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/MinionDematerializer/MinionDematerializer.png',
  饼干配送: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/BiscuitDelivery/BiscuitDelivery.png',
  星界洞悉: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/CosmicInsight/CosmicInsight.png',
  行进速率: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/ApproachVelocity/ApproachVelocity.png',
  时间扭曲补药: 'https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/TimeWarpTonic/TimeWarpTonic.png',
};

const buildInitialSelections = (slotCount: number): (string | null)[] =>
  Array.from({ length: slotCount }, () => null);

const RUNE_PRESET_STORAGE_KEY = 'lol_rune_simulator_presets_v2';

interface RunePreset {
  primaryPathId: RunePathId;
  secondaryPathId: RunePathId;
  primarySelections: (string | null)[];
  secondarySelections: (string | null)[];
  shardSelections: (string | null)[];
}

interface RunePresetRecord extends RunePreset {
  id: string;
  name: string;
  updatedAt: number;
}

interface RecommendedRuneSetup {
  primary_runes: string[];
  secondary_runes: string[];
}

interface RuneInfo {
  icon: string;
  shortDesc: string;
  longDesc: string;
}

type RuneInfoMap = Record<string, RuneInfo>;

function normalizeRuneName(name: string): string {
  return name
    .replace(/：/g, ':')
    .replace(/\s+/g, '')
    .replace(/[()（）'".,，。]/g, '')
    .toLowerCase();
}

function stripHtml(input: string): string {
  return input
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/?[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim();
}

function extractRuneInfo(payload: unknown): RuneInfoMap {
  const result: RuneInfoMap = {};
  if (!Array.isArray(payload)) return result;

  for (const style of payload) {
    const slots = (style as { slots?: unknown[] }).slots;
    if (!Array.isArray(slots)) continue;
    for (const slot of slots) {
      const runes = (slot as { runes?: unknown[] }).runes;
      if (!Array.isArray(runes)) continue;
      for (const rune of runes) {
        const node = rune as { name?: string; icon?: string; shortDesc?: string; longDesc?: string };
        const name = (node.name ?? '').trim();
        if (!name) continue;
        result[normalizeRuneName(name)] = {
          icon: node.icon ? `${DDRAGON_BASE}/img/${node.icon}` : '',
          shortDesc: stripHtml(node.shortDesc ?? ''),
          longDesc: stripHtml(node.longDesc ?? ''),
        };
      }
    }
  }

  return result;
}

function getStorage(): Pick<Storage, 'getItem' | 'setItem'> | null {
  const candidate = globalThis.localStorage as Partial<Storage> | undefined;
  if (!candidate) return null;
  if (typeof candidate.getItem !== 'function' || typeof candidate.setItem !== 'function') return null;
  return {
    getItem: candidate.getItem.bind(candidate),
    setItem: candidate.setItem.bind(candidate),
  };
}

function loadPresets(): RunePresetRecord[] {
  try {
    const storage = getStorage();
    if (!storage) return [];
    const raw = storage.getItem(RUNE_PRESET_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RunePresetRecord[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item) => item?.id && item?.name && item?.primaryPathId && item?.secondaryPathId);
  } catch {
    return [];
  }
}

function RuneNode({
  name,
  active,
  onClick,
  activeClass,
  iconMap = RUNE_ICON_MAP,
  runeInfoMap,
}: {
  name: string;
  active: boolean;
  onClick: () => void;
  activeClass: string;
  iconMap?: Record<string, string>;
  runeInfoMap?: RuneInfoMap;
}) {
  const info = runeInfoMap?.[normalizeRuneName(name)];
  const icon = info?.icon || iconMap[name];
  return (
    <button
      type="button"
      title={info?.shortDesc ? `${name}\n${info.shortDesc}` : name}
      aria-label={name}
      onClick={onClick}
      className={`group flex items-center gap-2 rounded-lg px-2 py-1 transition-colors ${
        active ? 'bg-gray-900/80' : 'bg-transparent hover:bg-gray-900/40'
      }`}
    >
      <span
        className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold ${
          active ? `${activeClass} border-transparent` : 'border-gray-500 text-gray-300'
        }`}
      >
        {icon ? (
          <img src={icon} alt="" className="w-full h-full rounded-full object-cover" />
        ) : (
          <span aria-hidden="true">{name.slice(0, 1)}</span>
        )}
      </span>
      <span className={`text-sm ${active ? 'text-white' : 'text-gray-400 group-hover:text-gray-200'}`}>
        {name}
      </span>
    </button>
  );
}

export function RuneSimulator({
  recommendedRunes,
  recommendedSetup,
  recommendedSetupValid = true,
  defaultCollapsed = false,
}: {
  recommendedRunes: string[];
  recommendedSetup?: RecommendedRuneSetup | null;
  recommendedSetupValid?: boolean;
  defaultCollapsed?: boolean;
}) {
  const initialPresets = loadPresets();
  const initialPreset = initialPresets[0];
  const [presets, setPresets] = useState<RunePresetRecord[]>(initialPresets);
  const [selectedPresetId, setSelectedPresetId] = useState<string>(initialPreset?.id ?? '');
  const [presetName, setPresetName] = useState<string>(initialPreset?.name ?? '');
  const [primaryPathId, setPrimaryPathId] = useState<RunePathId>(initialPreset?.primaryPathId ?? 'precision');
  const [secondaryPathId, setSecondaryPathId] = useState<RunePathId>(initialPreset?.secondaryPathId ?? 'domination');
  const [primarySelections, setPrimarySelections] = useState<(string | null)[]>(
    initialPreset?.primarySelections?.length === 4 ? initialPreset.primarySelections : buildInitialSelections(4)
  );
  const [secondarySelections, setSecondarySelections] = useState<(string | null)[]>(
    initialPreset?.secondarySelections?.length === 3
      ? initialPreset.secondarySelections
      : initialPreset?.secondarySelections?.length === 2
        ? [initialPreset.secondarySelections[0], initialPreset.secondarySelections[1], null]
        : [null, null, null]
  );
  const [shardSelections, setShardSelections] = useState<(string | null)[]>(
    initialPreset?.shardSelections?.length === 3 ? initialPreset.shardSelections : [null, null, null]
  );
  const [notice, setNotice] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isFetchingRuneInfo, setIsFetchingRuneInfo] = useState(false);
  const [runeInfoMap, setRuneInfoMap] = useState<RuneInfoMap>({});
  const [focusedRuneName, setFocusedRuneName] = useState<string | null>(null);
  const [runeInfoVersion, setRuneInfoVersion] = useState<string | null>(null);
  const didAutoExpandRef = useRef(false);

  const hasRecommendedData =
    (recommendedSetup?.primary_runes?.length ?? 0) > 0 || recommendedRunes.length > 0;

  useEffect(() => {
    if (!hasRecommendedData || didAutoExpandRef.current || !isCollapsed) return;
    setIsCollapsed(false);
    didAutoExpandRef.current = true;
  }, [hasRecommendedData, isCollapsed]);

  const primaryPath = useMemo(
    () => RUNE_PATHS.find((path) => path.id === primaryPathId) ?? RUNE_PATHS[0],
    [primaryPathId]
  );
  const secondaryPath = useMemo(
    () => RUNE_PATHS.find((path) => path.id === secondaryPathId) ?? RUNE_PATHS[1],
    [secondaryPathId]
  );

  const availableSecondaryRows = secondaryPath.slots.slice(1);

  const onPrimaryPathChange = (pathId: RunePathId) => {
    setPrimaryPathId(pathId);
    setPrimarySelections(buildInitialSelections(4));
    if (pathId === secondaryPathId) {
      const fallback = RUNE_PATHS.find((path) => path.id !== pathId);
      setSecondaryPathId((fallback?.id ?? 'domination') as RunePathId);
      setSecondarySelections([null, null, null]);
    }
  };

  const onSecondaryPathChange = (pathId: RunePathId) => {
    if (pathId === primaryPathId) return;
    setSecondaryPathId(pathId);
    setSecondarySelections([null, null, null]);
  };

  const currentSummary = [
    `主系 ${primaryPath.name}: ${(primarySelections.filter(Boolean) as string[]).join(' / ') || '未选择'}`,
    `副系 ${secondaryPath.name}: ${(secondarySelections.filter(Boolean) as string[]).join(' / ') || '未选择'}`,
    `碎片: ${(shardSelections.filter(Boolean) as string[]).join(' / ') || '未选择'}`,
  ].join('\n');

  const persistPresets = (next: RunePresetRecord[]) => {
    const storage = getStorage();
    if (!storage) return false;
    storage.setItem(RUNE_PRESET_STORAGE_KEY, JSON.stringify(next));
    return true;
  };

  const applyPreset = (preset: RunePresetRecord) => {
    setPrimaryPathId(preset.primaryPathId);
    setSecondaryPathId(
      preset.secondaryPathId === preset.primaryPathId
        ? (RUNE_PATHS.find((path) => path.id !== preset.primaryPathId)?.id ?? 'domination')
        : preset.secondaryPathId
    );
    setPrimarySelections(preset.primarySelections?.length === 4 ? preset.primarySelections : [null, null, null, null]);
    setSecondarySelections(
      preset.secondarySelections?.length === 3
        ? preset.secondarySelections
        : preset.secondarySelections?.length === 2
          ? [preset.secondarySelections[0], preset.secondarySelections[1], null]
          : [null, null, null]
    );
    setShardSelections(preset.shardSelections?.length === 3 ? preset.shardSelections : [null, null, null]);
  };

  const applyRecommendedSetup = () => {
    if (!recommendedSetup?.primary_runes?.length) {
      setNotice('暂无可应用的 OP.GG 符文');
      return;
    }

    const matchPrimaryPath = RUNE_PATHS.find((path) =>
      recommendedSetup.primary_runes.every((rune) => path.slots.some((slot) => slot.includes(rune)))
    );
    if (!matchPrimaryPath) {
      setNotice('无法匹配 OP.GG 主系符文');
      return;
    }

    const primaryNext: (string | null)[] = [null, null, null, null];
    for (const rune of recommendedSetup.primary_runes) {
      const slotIdx = matchPrimaryPath.slots.findIndex((slot) => slot.includes(rune));
      if (slotIdx >= 0) primaryNext[slotIdx] = rune;
    }

    const secondaryCandidatePaths = RUNE_PATHS.filter((path) => path.id !== matchPrimaryPath.id);
    const matchSecondaryPath =
      secondaryCandidatePaths.find((path) =>
        recommendedSetup.secondary_runes.every((rune) => path.slots.slice(1).some((slot) => slot.includes(rune)))
      ) ?? secondaryCandidatePaths[0];

    const secondaryNext: (string | null)[] = [null, null, null];
    for (const rune of recommendedSetup.secondary_runes.slice(0, 2)) {
      const rowIdx = matchSecondaryPath.slots.slice(1).findIndex((slot) => slot.includes(rune));
      if (rowIdx >= 0) secondaryNext[rowIdx] = rune;
    }

    setPrimaryPathId(matchPrimaryPath.id);
    setSecondaryPathId(matchSecondaryPath.id);
    setPrimarySelections(primaryNext);
    setSecondarySelections(secondaryNext);
    setNotice('已套用 OP.GG 符文推荐');
  };

  const savePreset = () => {
    const storage = getStorage();
    if (!storage) {
      setNotice('保存失败');
      return;
    }
    const trimmedName = presetName.trim() || '未命名预设';
    const payload: RunePreset = {
      primaryPathId,
      secondaryPathId,
      primarySelections,
      secondarySelections,
      shardSelections,
    };
    const now = Date.now();
    const existing = presets.find((item) => item.name === trimmedName);
    const nextPreset: RunePresetRecord = {
      id: existing?.id ?? `${now}`,
      name: trimmedName,
      updatedAt: now,
      ...payload,
    };
    const next = [nextPreset, ...presets.filter((item) => item.id !== nextPreset.id)].sort(
      (a, b) => b.updatedAt - a.updatedAt
    );
    if (!persistPresets(next)) {
      setNotice('保存失败');
      return;
    }
    setPresets(next);
    setSelectedPresetId(nextPreset.id);
    setPresetName(nextPreset.name);
    setNotice('已保存预设');
  };

  const loadSelectedPreset = () => {
    const preset = presets.find((item) => item.id === selectedPresetId);
    if (!preset) {
      setNotice('未找到预设');
      return;
    }
    applyPreset(preset);
    setPresetName(preset.name);
    setNotice('已读取预设');
  };

  const deleteSelectedPreset = () => {
    const target = presets.find((item) => item.id === selectedPresetId);
    if (!target) {
      setNotice('未找到预设');
      return;
    }
    const next = presets.filter((item) => item.id !== target.id);
    if (!persistPresets(next)) {
      setNotice('删除失败');
      return;
    }
    setPresets(next);
    setSelectedPresetId(next[0]?.id ?? '');
    setNotice('已删除预设');
  };

  const copySummary = async () => {
    if (!navigator.clipboard) {
      setNotice('复制失败');
      return;
    }
    try {
      await navigator.clipboard.writeText(currentSummary);
      setNotice('已复制当前符文页');
    } catch {
      setNotice('复制失败');
    }
  };

  const fetchRuneInfoUpdate = async () => {
    setIsFetchingRuneInfo(true);
    try {
      const versionsRes = await fetch(DDRAGON_VERSIONS_URL);
      if (!versionsRes.ok) throw new Error('version fetch failed');
      const versions = (await versionsRes.json()) as string[];
      const latestVersion = versions?.[0];
      if (!latestVersion) throw new Error('version missing');

      const locales = ['zh_CN', 'en_US'];
      const merged: RuneInfoMap = {};
      for (const locale of locales) {
        const url = `${DDRAGON_BASE}/${latestVersion}/data/${locale}/runesReforged.json`;
        const res = await fetch(url);
        if (!res.ok) continue;
        const payload = await res.json();
        const parsed = extractRuneInfo(payload);
        Object.assign(merged, parsed);
      }

      if (!Object.keys(merged).length) throw new Error('no rune info');
      setRuneInfoMap(merged);
      setRuneInfoVersion(latestVersion);
      setNotice(`已更新符文信息（${latestVersion}）`);
    } catch {
      setNotice('符文信息更新失败');
    } finally {
      setIsFetchingRuneInfo(false);
    }
  };

  const focusedRuneInfo = focusedRuneName ? runeInfoMap[normalizeRuneName(focusedRuneName)] : null;

  return (
    <div className="bg-gray-800 rounded-xl p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h3 className="text-xl font-bold text-white">符文模拟器</h3>
        <div className="flex items-center gap-3">
          <div className="text-sm text-gray-400">模拟游戏内符文页配置（展示用途）</div>
          <button
            type="button"
            aria-label="toggle-rune-simulator"
            aria-expanded={!isCollapsed}
            onClick={() => setIsCollapsed((prev) => !prev)}
            className="px-3 py-1 rounded-lg bg-gray-700 text-white hover:bg-gray-600 text-sm"
          >
            {isCollapsed ? '展开' : '收起'}
          </button>
        </div>
      </div>

      {isCollapsed ? null : (
        <>
      {recommendedRunes.length > 0 && (
        <div className="bg-gray-700 rounded-lg p-3">
          <p className="text-gray-300 text-sm mb-2">OP.GG 推荐</p>
          <div className="flex flex-wrap gap-2">
            {recommendedRunes.map((rune, idx) => (
              <span key={`${rune}-${idx}`} className="bg-purple-600 text-white px-3 py-1 rounded-lg text-sm">
                {rune}
              </span>
            ))}
          </div>
          {recommendedSetup && !recommendedSetupValid && (
            <p className="text-xs text-yellow-400 mt-2">
              OP.GG 推荐符文配置不完整，已保留名称列表作为降级展示。
            </p>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="text"
          value={presetName}
          onChange={(e) => setPresetName(e.target.value)}
          placeholder="预设名称"
          className="px-3 py-2 rounded-lg bg-gray-700 text-white text-sm"
        />
        <select
          aria-label="preset-select"
          value={selectedPresetId}
          onChange={(e) => setSelectedPresetId(e.target.value)}
          className="px-3 py-2 rounded-lg bg-gray-700 text-white text-sm"
        >
          <option value="">选择预设</option>
          {presets.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={fetchRuneInfoUpdate}
          disabled={isFetchingRuneInfo}
          className="px-3 py-2 rounded-lg bg-blue-700 text-white hover:bg-blue-600 disabled:opacity-60 text-sm"
        >
          {isFetchingRuneInfo ? '更新中...' : 'Fetch 符文更新'}
        </button>
        {recommendedSetup?.primary_runes?.length ? (
          <button
            type="button"
            onClick={applyRecommendedSetup}
            disabled={!recommendedSetupValid}
            className="px-3 py-2 rounded-lg bg-purple-700 text-white hover:bg-purple-600 disabled:opacity-60 text-sm"
          >
            应用 OP.GG 符文
          </button>
        ) : null}
        <button
          type="button"
          onClick={copySummary}
          className="px-3 py-2 rounded-lg bg-gray-700 text-white hover:bg-gray-600 text-sm"
        >
          复制当前符文页
        </button>
        <button
          type="button"
          onClick={savePreset}
          className="px-3 py-2 rounded-lg bg-gray-700 text-white hover:bg-gray-600 text-sm"
        >
          保存本地预设
        </button>
        <button
          type="button"
          onClick={loadSelectedPreset}
          className="px-3 py-2 rounded-lg bg-gray-700 text-white hover:bg-gray-600 text-sm"
        >
          读取预设
        </button>
        <button
          type="button"
          onClick={deleteSelectedPreset}
          className="px-3 py-2 rounded-lg bg-gray-700 text-white hover:bg-gray-600 text-sm"
        >
          删除预设
        </button>
        {notice && <span className="text-sm text-green-400">{notice}</span>}
      </div>

      {focusedRuneName && (
        <div className="bg-gray-900 rounded-lg p-4">
          <p className="text-sm text-gray-400 mb-1">符文信息</p>
          <p className="text-white font-semibold">{focusedRuneName}</p>
          {focusedRuneInfo ? (
            <div className="text-sm text-gray-300 mt-2 whitespace-pre-line">
              {focusedRuneInfo.shortDesc || focusedRuneInfo.longDesc || '暂无描述'}
              {runeInfoVersion && (
                <div className="text-xs text-gray-500 mt-2">来源版本: {runeInfoVersion}</div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500 mt-2">暂无符文信息，点击“Fetch 符文更新”获取最新数据。</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-700 rounded-lg p-4 space-y-4">
          <label className="text-sm text-gray-300">主系</label>
          <select
            aria-label="primary-path"
            value={primaryPathId}
            onChange={(e) => onPrimaryPathChange(e.target.value as RunePathId)}
            className="w-full bg-gray-900 text-white rounded px-3 py-2"
          >
            {RUNE_PATHS.map((path) => (
              <option key={path.id} value={path.id}>
                {path.name}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-3 bg-gray-900/60 rounded-lg p-2">
            <img src={primaryPath.icon} alt={primaryPath.name} className="w-8 h-8 rounded" />
            <p className={`text-sm font-semibold ${primaryPath.color}`}>{primaryPath.name}</p>
          </div>

          {primaryPath.slots.map((slot, slotIndex) => (
            <div key={`primary-slot-${slotIndex}`}>
              <p className="text-xs text-gray-400 mb-2">{slotIndex === 0 ? '基石符文' : `主系槽位 ${slotIndex}`}</p>
              <div className="grid grid-cols-1 gap-1">
                {slot.map((rune) => (
                  <RuneNode
                    key={rune}
                    name={rune}
                    runeInfoMap={runeInfoMap}
                    active={primarySelections[slotIndex] === rune}
                    activeClass="bg-yellow-500 text-black"
                    onClick={() => {
                      setPrimarySelections((prev) => {
                        const next = [...prev];
                        next[slotIndex] = rune;
                        return next;
                      });
                      setFocusedRuneName(rune);
                    }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="bg-gray-700 rounded-lg p-4 space-y-4">
          <label className="text-sm text-gray-300">副系</label>
          <p className="text-xs text-gray-400">从 3 行中最多选择 2 个</p>
          <select
            aria-label="secondary-path"
            value={secondaryPathId}
            onChange={(e) => onSecondaryPathChange(e.target.value as RunePathId)}
            className="w-full bg-gray-900 text-white rounded px-3 py-2"
          >
            {RUNE_PATHS.filter((path) => path.id !== primaryPathId).map((path) => (
              <option key={path.id} value={path.id}>
                {path.name}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-3 bg-gray-900/60 rounded-lg p-2">
            <img src={secondaryPath.icon} alt={secondaryPath.name} className="w-8 h-8 rounded" />
            <p className={`text-sm font-semibold ${secondaryPath.color}`}>{secondaryPath.name}</p>
          </div>

          {availableSecondaryRows.map((slot, slotIndex) => (
            <div key={`secondary-slot-${slotIndex}`}>
              <p className="text-xs text-gray-400 mb-2">副系槽位 {slotIndex + 1}</p>
              <div className="grid grid-cols-1 gap-1">
                {slot.map((rune) => (
                  <RuneNode
                    key={rune}
                    name={rune}
                    runeInfoMap={runeInfoMap}
                    active={secondarySelections[slotIndex] === rune}
                    activeClass="bg-cyan-400 text-black"
                    onClick={() => {
                      setSecondarySelections((prev) => {
                        const selectedCount = prev.filter(Boolean).length;
                        const next = [...prev];
                        if (next[slotIndex] === rune) {
                          next[slotIndex] = null;
                          return next;
                        }
                        if (!next[slotIndex] && selectedCount >= 2) {
                          setNotice('副系最多选择 2 个符文');
                          return prev;
                        }
                        next[slotIndex] = rune;
                        return next;
                      });
                      setFocusedRuneName(rune);
                    }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-700 rounded-lg p-4">
        <p className="text-sm text-gray-300 mb-3">属性碎片</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {SHARDS.map((options, rowIndex) => (
            <div key={`shard-row-${rowIndex}`} className="space-y-2">
              {options.map((shard) => (
                <RuneNode
                  key={shard}
                  name={shard}
                  active={shardSelections[rowIndex] === shard}
                  activeClass="bg-green-500 text-black"
                  iconMap={SHARD_ICON_MAP}
                  onClick={() =>
                    setShardSelections((prev) => {
                      const next = [...prev];
                      next[rowIndex] = shard;
                      return next;
                    })
                  }
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-900 rounded-lg p-4">
        <p className="text-sm text-gray-400 mb-2">当前符文页</p>
        <div className="text-sm text-gray-200 space-y-1">
          <p>
            主系：
            <span className={primaryPath.color}> {primaryPath.name}</span>
            {' · '}
            {(primarySelections.filter(Boolean) as string[]).join(' / ') || '未选择'}
          </p>
          <p>
            副系：
            <span className={secondaryPath.color}> {secondaryPath.name}</span>
            {' · '}
            {(secondarySelections.filter(Boolean) as string[]).join(' / ') || '未选择'}
          </p>
          <p>碎片：{(shardSelections.filter(Boolean) as string[]).join(' / ') || '未选择'}</p>
        </div>
      </div>
        </>
      )}
    </div>
  );
}
