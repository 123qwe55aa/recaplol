const DDRAGON_VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json';
const DDRAGON_CHAMPION_DATA_BASE = 'https://ddragon.leagueoflegends.com/cdn';
const DEFAULT_VERSION = '16.1.1';
const FALLBACK_CHAMPION_KEY = 'Aatrox';

const CHAMPION_NAME_ALIASES: Record<string, string> = {
  "wukong": 'MonkeyKing',
  "monkey king": 'MonkeyKing',
  "nunu": 'Nunu',
  "nunu & willump": 'Nunu',
  "nunu and willump": 'Nunu',
  "renata": 'Renata',
  "renata glasc": 'Renata',
  "belveth": 'Belveth',
  "bel'veth": 'Belveth',
  "kai'sa": 'Kaisa',
  "kaisa": 'Kaisa',
  "kha'zix": 'Khazix',
  "khazix": 'Khazix',
  "kog'maw": 'KogMaw',
  "kogmaw": 'KogMaw',
  "rek'sai": 'RekSai',
  "reksai": 'RekSai',
  "vel'koz": 'Velkoz',
  "velkoz": 'Velkoz',
  "cho'gath": 'Chogath',
  "chogath": 'Chogath',
  "dr. mundo": 'DrMundo',
  "dr mundo": 'DrMundo',
  "miss fortune": 'MissFortune',
  "master yi": 'MasterYi',
  "lee sin": 'LeeSin',
  "twisted fate": 'TwistedFate',
  "xin zhao": 'XinZhao',
  "jarvan iv": 'JarvanIV',
  "aurelion sol": 'AurelionSol',
};

let latestVersionPromise: Promise<string> | null = null;
let championKeyMapPromise: Promise<Record<string, string>> | null = null;

function normalizeVersion(version: string): string {
  const parts = version.split('.');
  if (parts.length >= 2) {
    return `${parts[0]}.${parts[1]}.1`;
  }
  return DEFAULT_VERSION;
}

function normalizeChampionName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[’']/g, "'")
    .replace(/[.]/g, '')
    .replace(/&/g, 'and')
    .replace(/\s+/g, ' ');
}

function sanitizeChampionKey(name: string): string {
  return name.replace(/[^A-Za-z0-9]/g, '');
}

export function buildChampionIconUrl(version: string, championKey: string): string {
  return `${DDRAGON_CHAMPION_DATA_BASE}/${version}/img/champion/${championKey}.png`;
}

export async function getLatestDdragonVersion(): Promise<string> {
  if (!latestVersionPromise) {
    latestVersionPromise = fetch(DDRAGON_VERSIONS_URL)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to fetch Data Dragon versions: ${res.status}`);
        }
        return res.json() as Promise<string[]>;
      })
      .then((versions) => normalizeVersion(versions?.[0] ?? DEFAULT_VERSION))
      .catch(() => DEFAULT_VERSION);
  }
  return latestVersionPromise;
}

async function loadChampionKeyMap(version: string): Promise<Record<string, string>> {
  const url = `${DDRAGON_CHAMPION_DATA_BASE}/${version}/data/en_US/champion.json`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch champion data: ${res.status}`);
  }
  const payload = (await res.json()) as {
    data?: Record<string, { id?: string; name?: string }>;
  };

  const map: Record<string, string> = {};
  for (const champ of Object.values(payload.data ?? {})) {
    const id = champ.id ?? '';
    const name = champ.name ?? '';
    const normalizedName = normalizeChampionName(name);
    if (normalizedName && id) {
      map[normalizedName] = id;
    }
    const sanitizedName = sanitizeChampionKey(normalizedName);
    if (sanitizedName && id) {
      map[sanitizedName] = id;
    }
    const normalizedId = normalizeChampionName(id);
    if (normalizedId && id) {
      map[normalizedId] = id;
    }
  }
  return map;
}

export async function resolveChampionKey(championName: string): Promise<string> {
  const normalized = normalizeChampionName(championName);
  if (!normalized) return FALLBACK_CHAMPION_KEY;

  const alias = CHAMPION_NAME_ALIASES[normalized];
  if (alias) return alias;

  const sanitized = sanitizeChampionKey(normalized);

  try {
    if (!championKeyMapPromise) {
      championKeyMapPromise = getLatestDdragonVersion().then((version) => loadChampionKeyMap(version));
    }
    const championMap = await championKeyMapPromise;
    return championMap[normalized] || championMap[sanitized] || sanitizeChampionKey(championName) || FALLBACK_CHAMPION_KEY;
  } catch {
    return sanitizeChampionKey(championName) || FALLBACK_CHAMPION_KEY;
  }
}

export async function resolveChampionIconUrl(championName: string): Promise<string> {
  const version = await getLatestDdragonVersion();
  const championKey = await resolveChampionKey(championName);
  return buildChampionIconUrl(version, championKey);
}

export async function resolveChampionIconUrlByKey(championKey: string): Promise<string> {
  const version = await getLatestDdragonVersion();
  const safeKey = sanitizeChampionKey(championKey) || FALLBACK_CHAMPION_KEY;
  return buildChampionIconUrl(version, safeKey);
}

export function getFallbackChampionIconUrl(version: string): string {
  return buildChampionIconUrl(version, FALLBACK_CHAMPION_KEY);
}
