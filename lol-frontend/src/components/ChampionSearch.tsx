import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChampionPortrait } from './ChampionPortrait';

// Popular champions for quick access
const POPULAR_CHAMPIONS = [
  'Ahri', 'Akali', 'Darius', 'Ezreal', 'Jinx', 'Lux',
  'Thresh', 'Yasuo', 'Zed', 'Vayne', 'Lee Sin', 'Orianna'
];

// Full champion list (alphabetical)
const ALL_CHAMPIONS = [
  'Aatrox', 'Ahri', 'Akali', 'Akshan', 'Alistar', 'Amumu', 'Anivia', 'Annie',
  'Aphelios', 'Ashe', 'Aurelion Sol', 'Aurora', 'Azir', 'Bard', 'Bel\'Veth',
  'Blitzcrank', 'Brand', 'Braum', 'Briar', 'Caitlyn', 'Camille', 'Cassiopeia',
  'Darius', 'Diana', 'Draven', 'Dr. Mundo', 'Ekko', 'Elise', 'Evelynn', 'Ezreal',
  'Fiddlesticks', 'Fiora', 'Fizz', 'Galio', 'Gangplank', 'Garen', 'Gnar',
  'Gragas', 'Graves', ' Gwen', 'Hecarim', 'Heimerdinger', 'Illaoi',
  'Irelia', 'Ivern', 'Janna', 'Jarvan IV', 'Jax', 'Jayce', 'Jhin', 'Jinx',
  'Kai\'Sa', 'Kalista', 'Kam', 'Kassadin', 'Katarina', 'Kayle', 'Kayn',
  'Kennen', 'Kha\'Zix', 'Kindred', 'Kled', 'Kog\'Maw', 'LeBlanc', 'Lee Sin',
  'Leona', 'Lillia', 'Lissandra', 'Lucian', 'Lulu', 'Lux', 'Malphite', 'Malzahar',
  'Maokai', 'Milio', 'Miss Fortune', 'Mordekaiser', 'Morgana', 'Naafiri',
  'Nami', 'Nasus', 'Nautilus', 'Neko', 'Nidalee', 'Nilah', 'Nocturne', 'Nunu',
  'Olaf', 'Orianna', 'Ornn', 'Pantheon', 'Poppy', 'Pyke', 'Qiyana', 'Quinn',
  'Rakan', 'Rammus', 'Rek\'Sai', 'Rell', 'Renata Glasc', 'Renekton', 'Rengar',
  'Riven', 'Rumble', 'Ryze', 'Samira', 'Sejuani', 'Senna', 'Seraphine', 'Sett',
  'Shaco', 'Shen', 'Shyvana', 'Singed', 'Sion', 'Sivir', 'Skarner', 'Sona',
  'Soraka', 'Swain', 'Sylas', 'Syndra', 'Tahm Kench', 'Taliyah', 'Talon',
  'Taric', 'Teemo', 'Thresh', 'Tristana', 'Trundle', 'Tryndamere', 'Twisted Fate',
  'Twitch', 'Udyr', 'Urgot', 'Varus', 'Vayne', 'Veigar', 'Vel\'Koz', 'Vex',
  'Vi', 'Viego', 'Viktor', 'Vladimir', 'Volibear', 'Warwick', 'Wukong',
  'Xayah', 'Xerath', 'Xin Zhao', 'Yasuo', 'Yone', 'Yorick', 'Zac', 'Zed',
  'Zeri', 'Ziggs', 'Zilean', 'Zoe', 'Zyra'
].sort();

interface ChampionSearchProps {
  onSelectChampion?: (championName: string) => void;
}

export function ChampionSearch({ onSelectChampion }: ChampionSearchProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  const filteredChampions = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const query = searchQuery.toLowerCase();
    return ALL_CHAMPIONS.filter(champ =>
      champ.toLowerCase().includes(query)
    ).slice(0, 8);
  }, [searchQuery]);

  const handleSelectChampion = (championName: string) => {
    setSearchQuery('');
    setIsExpanded(false);
    if (onSelectChampion) {
      onSelectChampion(championName);
    } else {
      navigate(`/champion-lookup?champion=${encodeURIComponent(championName)}`);
    }
  };

  return (
    <div className="w-full mt-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-400 hover:border-yellow-500 hover:text-white transition-colors flex items-center justify-between"
      >
        <span>搜索英雄数据 (OP.GG)</span>
        <span className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {isExpanded && (
        <div className="mt-4 bg-gray-800 rounded-xl p-4 border border-gray-700">
          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="输入英雄名称..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-yellow-500"
            />
            {filteredChampions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-gray-700 border border-gray-600 rounded-lg shadow-xl overflow-hidden">
                {filteredChampions.map((champion) => (
                  <button
                    key={champion}
                    onClick={() => handleSelectChampion(champion)}
                    className="w-full px-4 py-2 flex items-center gap-3 hover:bg-gray-600 transition-colors text-left"
                  >
                    <ChampionPortrait championName={champion} size="sm" />
                    <span className="text-white">{champion}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Popular Champions */}
          <div className="mt-4">
            <h4 className="text-gray-400 text-sm mb-3">热门英雄</h4>
            <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
              {POPULAR_CHAMPIONS.map((champion) => (
                <button
                  key={champion}
                  onClick={() => handleSelectChampion(champion)}
                  className="flex flex-col items-center gap-1 p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
                >
                  <ChampionPortrait championName={champion} size="sm" />
                  <span className="text-xs text-gray-300 truncate w-full text-center">
                    {champion}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Browse All Link */}
          <div className="mt-4 pt-4 border-t border-gray-700">
            <p className="text-gray-500 text-sm text-center">
              输入英雄名称搜索更多...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}