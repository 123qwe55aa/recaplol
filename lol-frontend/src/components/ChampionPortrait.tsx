import { useEffect, useMemo, useState } from 'react';
import {
  getFallbackChampionIconUrl,
  resolveChampionIconUrl,
  resolveChampionIconUrlByKey,
  getLatestDdragonVersion,
} from '../services/championIcon';

interface ChampionPortraitProps {
  championId?: number;
  championName: string;
  championKey?: string | null;
  championIconUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
}

const sizeClasses = {
  sm: 'w-10 h-10 rounded',
  md: 'w-16 h-16 rounded-lg',
  lg: 'w-24 h-24 rounded-xl',
};

const STATIC_FALLBACK_VERSION = '16.1.1';

export function ChampionPortrait({
  championName,
  championKey,
  championIconUrl,
  size = 'md',
  showName = false,
}: ChampionPortraitProps) {
  const [imageUrl, setImageUrl] = useState(() => getFallbackChampionIconUrl(STATIC_FALLBACK_VERSION));
  const [fallbackUrl, setFallbackUrl] = useState(() => getFallbackChampionIconUrl(STATIC_FALLBACK_VERSION));

  const safeName = useMemo(() => championName?.trim() || 'Aatrox', [championName]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        if (championIconUrl) {
          const version = await getLatestDdragonVersion();
          if (cancelled) return;
          setImageUrl(championIconUrl);
          setFallbackUrl(getFallbackChampionIconUrl(version));
          return;
        }

        const [resolvedUrl, version] = await Promise.all([
          championKey ? resolveChampionIconUrlByKey(championKey) : resolveChampionIconUrl(safeName),
          getLatestDdragonVersion(),
        ]);

        if (cancelled) return;
        setImageUrl(resolvedUrl);
        setFallbackUrl(getFallbackChampionIconUrl(version));
      } catch {
        if (cancelled) return;
        setImageUrl(getFallbackChampionIconUrl(STATIC_FALLBACK_VERSION));
        setFallbackUrl(getFallbackChampionIconUrl(STATIC_FALLBACK_VERSION));
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [championIconUrl, championKey, safeName]);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`${sizeClasses[size]} bg-gray-700 overflow-hidden`}>
        <img
          src={imageUrl}
          alt={safeName}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).src = fallbackUrl;
          }}
        />
      </div>
      {showName && (
        <span className="text-xs text-gray-300 truncate max-w-[80px] text-center">
          {safeName}
        </span>
      )}
    </div>
  );
}
