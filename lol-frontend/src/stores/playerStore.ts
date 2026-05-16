import { create } from 'zustand';
import type { Player } from '../types';

interface PlayerState {
  currentPlayer: Player | null;
  recentSearches: Player[];
  setCurrentPlayer: (player: Player) => void;
  addRecentSearch: (player: Player) => void;
}

export const usePlayerStore = create<PlayerState>((set) => ({
  currentPlayer: null,
  recentSearches: [],
  setCurrentPlayer: (player) => set({ currentPlayer: player }),
  addRecentSearch: (player) =>
    set((state) => ({
      recentSearches: [
        player,
        ...state.recentSearches.filter(
          (p) => p.puuid !== player.puuid
        ),
      ].slice(0, 5),
    })),
}));
