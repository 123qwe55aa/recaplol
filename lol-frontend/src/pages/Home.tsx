import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePlayerStore } from '../stores/playerStore';
import { ChampionSearch } from '../components/ChampionSearch';

export function Home() {
  const navigate = useNavigate();
  const [gameName, setGameName] = useState('DEADLY VEN0M');
  const [tagLine, setTagLine] = useState('TW2');
  const { recentSearches } = usePlayerStore();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (gameName && tagLine) {
      navigate(`/player/${gameName}/${tagLine}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-md">
        <h1 className="text-4xl font-bold text-yellow-400 text-center mb-8">
          LoL Stats
        </h1>
        <p className="text-gray-400 text-center mb-8">
          查询英雄联盟玩家数据
        </p>

        <button
          type="button"
          onClick={() => navigate('/champion-lookup')}
          className="w-full mb-4 py-3 bg-gray-800 text-yellow-400 font-bold rounded-lg hover:bg-gray-700 transition-colors border border-gray-700"
        >
          OP.GG 英雄聚合查询
        </button>

        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <input
              type="text"
              placeholder="游戏名称"
              value={gameName}
              onChange={(e) => setGameName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400"
            />
          </div>
          <div>
            <input
              type="text"
              placeholder="标签 (如 NA1, KR)"
              value={tagLine}
              onChange={(e) => setTagLine(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-yellow-400"
            />
          </div>
          <button
            type="submit"
            className="w-full py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors"
          >
            查询
          </button>
        </form>

        <ChampionSearch />

        {recentSearches.length > 0 && (
          <div className="mt-8">
            <h3 className="text-gray-400 text-sm mb-2">最近查询</h3>
            <div className="space-y-2">
              {recentSearches.map((player) => (
                <button
                  key={player.puuid}
                  onClick={() => navigate(`/player/${player.gameName}/${player.tagLine}`)}
                  className="w-full text-left px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <span className="text-white font-semibold">{player.gameName}</span>
                  <span className="text-gray-400 text-sm ml-2">#{player.tagLine}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
