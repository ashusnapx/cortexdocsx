import { create } from "zustand";

interface GlobalState {
  isAdvancedMode: boolean;
  setAdvancedMode: (val: boolean) => void;
  // This store is kept intentionally minimal.
  // Feature-specific state belongs in feature slices.
}

export const useGlobalStore = create<GlobalState>((set) => ({
  isAdvancedMode: false,
  setAdvancedMode: (isAdvancedMode) => set({ isAdvancedMode }),
}));
