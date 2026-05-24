export interface DdragonChampionMetadata {
  id: string;
  key: number;
  name: string;
}

export const DDRAGON_VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json';
export const DDRAGON_CDN_BASE = 'https://ddragon.leagueoflegends.com/cdn';
export const DEFAULT_DDRAGON_VERSION = '16.1.1';

interface DdragonChampionResponse {
  data?: Record<string, { id?: string; key?: string; name?: string }>;
}

const championByIdCache = new Map<string, Promise<Record<number, DdragonChampionMetadata>>>();

export function normalizeDdragonVersion(version: string): string {
  const parts = version.split('.');
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return `${parts[0]}.${parts[1]}.1`;
  }
  return DEFAULT_DDRAGON_VERSION;
}

export function buildItemIconUrl(itemId: number | string, version: string): string {
  return `${DDRAGON_CDN_BASE}/${normalizeDdragonVersion(version)}/img/item/${itemId}.png`;
}

export function buildDdragonAssetUrl(assetPath: string): string {
  const normalizedPath = assetPath.replace(/^\/+/, '').replace(/^img\//, '');
  return `${DDRAGON_CDN_BASE}/img/${normalizedPath}`;
}

export function buildDdragonDataUrl(version: string, locale: string, fileName: string): string {
  return `${DDRAGON_CDN_BASE}/${normalizeDdragonVersion(version)}/data/${locale}/${fileName}`;
}

export function buildChampionIconUrl(version: string, championKey: string): string {
  return `${DDRAGON_CDN_BASE}/${normalizeDdragonVersion(version)}/img/champion/${championKey}.png`;
}

export async function loadChampionByIdMap(
  version: string,
  locale = 'en_US'
): Promise<Record<number, DdragonChampionMetadata>> {
  const normalizedVersion = normalizeDdragonVersion(version);
  const cacheKey = `${normalizedVersion}:${locale}`;
  const existing = championByIdCache.get(cacheKey);
  if (existing) return existing;

  const loader = fetch(buildDdragonDataUrl(normalizedVersion, locale, 'champion.json'))
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Failed to load champion data: ${res.status}`);
      }
      return res.json() as Promise<DdragonChampionResponse>;
    })
    .then((json) => {
      const mapped: Record<number, DdragonChampionMetadata> = {};
      Object.values(json.data ?? {}).forEach((champion) => {
        const key = Number(champion.key);
        if (!Number.isFinite(key) || !champion.id) return;

        mapped[key] = {
          id: champion.id,
          key,
          name: champion.name ?? champion.id,
        };
      });
      return mapped;
    })
    .catch((error) => {
      championByIdCache.delete(cacheKey);
      throw error;
    });

  championByIdCache.set(cacheKey, loader);
  return loader;
}
