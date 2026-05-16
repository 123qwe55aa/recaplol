import { useParams, Link } from 'react-router-dom';
import { useStats } from '../hooks/useStats';

export function Analysis() {
  const { puuid } = useParams<{ puuid: string }>();
  const { data: stats, isLoading } = useStats(puuid || '');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-yellow-400 text-xl">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="text-gray-400 hover:text-white mb-4 inline-block">
          ← 返回
        </Link>

        <h1 className="text-2xl font-bold text-white mb-6">数据分析</h1>

        {stats && (
          <div className="space-y-8">
            <div className="bg-gray-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-white">AI 教练</h3>
                <p className="text-gray-400 mt-2">
                  基于最近比赛生成 3 个优先提升建议，并支持围绕报告追问。
                </p>
              </div>
              <Link
                to={`/coach/${puuid}`}
                className="inline-block px-5 py-3 bg-yellow-500 text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors text-center"
              >
                打开 AI 教练
              </Link>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">总体统计</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-3xl font-bold text-yellow-400">{stats.gamesPlayed}</p>
                  <p className="text-gray-400">总场次</p>
                </div>
                <div className="text-center">
                  <p className={`text-3xl font-bold ${stats.winRate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                    {stats.winRate.toFixed(1)}%
                  </p>
                  <p className="text-gray-400">胜率</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-purple-400">{stats.kda.toFixed(2)}</p>
                  <p className="text-gray-400">KDA</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">场均数据</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-red-400">{stats.avgKills.toFixed(1)}</p>
                  <p className="text-gray-400">场均击杀</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-400">{stats.avgDeaths.toFixed(1)}</p>
                  <p className="text-gray-400">场均死亡</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-400">{stats.avgAssists.toFixed(1)}</p>
                  <p className="text-gray-400">场均助攻</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
