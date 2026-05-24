import { buildDdragonDataUrl, normalizeDdragonVersion } from './ddragon';

export interface ItemDetail {
  id: string;
  name: string;
  description: string;
  plaintext: string;
  totalGold: number;
  sellGold: number;
  tags: string[];
}

interface DataDragonItem {
  name?: string;
  description?: string;
  plaintext?: string;
  gold?: {
    total?: number;
    sell?: number;
  };
  tags?: string[];
}

interface ItemDataResponse {
  data?: Record<string, DataDragonItem>;
}

const itemCache = new Map<string, Promise<Record<string, ItemDetail>>>();

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

function normalizeVersion(version: string): string {
  return normalizeDdragonVersion(version);
}

export function parseVersionFromItemImageUrl(url: string): string {
  const match = url.match(/\/cdn\/([^/]+)\/img\/item\//);
  return normalizeVersion(match?.[1] ?? '16.1.1');
}

export function loadItemData(version: string, locale = 'zh_CN'): Promise<Record<string, ItemDetail>> {
  const normalizedVersion = normalizeVersion(version);
  const key = `${normalizedVersion}:${locale}`;
  const existing = itemCache.get(key);
  if (existing) return existing;

  const loader = fetch(buildDdragonDataUrl(normalizedVersion, locale, 'item.json'))
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Failed to load item data: ${res.status}`);
      }
      return res.json() as Promise<ItemDataResponse>;
    })
    .then((json) => {
      const raw = json.data ?? {};
      const mapped: Record<string, ItemDetail> = {};
      Object.entries(raw).forEach(([id, value]) => {
        mapped[id] = {
          id,
          name: value.name ?? `Item ${id}`,
          description: stripHtml(value.description ?? ''),
          plaintext: stripHtml(value.plaintext ?? ''),
          totalGold: value.gold?.total ?? 0,
          sellGold: value.gold?.sell ?? 0,
          tags: value.tags ?? [],
        };
      });
      return mapped;
    })
    .catch((error) => {
      itemCache.delete(key);
      throw error;
    });

  itemCache.set(key, loader);
  return loader;
}
