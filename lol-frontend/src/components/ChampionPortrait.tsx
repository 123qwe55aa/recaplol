interface ChampionPortraitProps {
  championId?: number;
  championName: string;
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
}

const sizeClasses = {
  sm: 'w-10 h-10 rounded',
  md: 'w-16 h-16 rounded-lg',
  lg: 'w-24 h-24 rounded-xl',
};

const CDN_BASE = 'https://ddragon.leagueoflegends.com/cdn/16.5.1/img/champion';

export function ChampionPortrait({
  championName,
  size = 'md',
  showName = false,
}: ChampionPortraitProps) {
  const imageUrl = `${CDN_BASE}/${encodeURIComponent(championName)}.png`;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`${sizeClasses[size]} bg-gray-700 overflow-hidden`}>
        <img
          src={imageUrl}
          alt={championName}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).src = `https://ddragon.leagueoflegends.com/cdn/16.5.1/img/champion/Aatrox.png`;
          }}
        />
      </div>
      {showName && (
        <span className="text-xs text-gray-300 truncate max-w-[80px] text-center">
          {championName}
        </span>
      )}
    </div>
  );
}
