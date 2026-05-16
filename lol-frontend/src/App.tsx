import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home } from './pages/Home';
import { PlayerPage } from './pages/Player';
import { MatchHistory } from './pages/MatchHistory';
import { Analysis } from './pages/Analysis';
import { ChampionPage } from './pages/Champion';
import { ChampionLookupPage } from './pages/ChampionLookup';
import { CoachPage } from './pages/Coach';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/player/:gameName/:tagLine" element={<PlayerPage />} />
          <Route path="/matches/:puuid" element={<MatchHistory />} />
          <Route path="/analysis/:puuid" element={<Analysis />} />
          <Route path="/coach/:puuid" element={<CoachPage />} />
          <Route path="/champion/:championName" element={<ChampionPage />} />
          <Route path="/champion-lookup" element={<ChampionLookupPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
