interface RankBadgeProps {
  tier: string;
  rank: string;
  lp: number;
}

const tierColors: Record<string, string> = {
  Iron: 'bg-gray-400',
  Bronze: 'bg-amber-700',
  Silver: 'bg-gray-300',
  Gold: 'bg-yellow-500',
  Platinum: 'bg-emerald-400',
  Diamond: 'bg-blue-400',
  Master: 'bg-purple-500',
  Grandmaster: 'bg-red-500',
  Challenger: 'bg-cyan-400',
};

export function RankBadge({ tier, rank, lp }: RankBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`${tierColors[tier] || 'bg-gray-500'} text-black font-bold px-3 py-1 rounded`}
      >
        {tier} {rank}
      </div>
      <span className="text-yellow-400 font-semibold">{lp} LP</span>
    </div>
  );
}
