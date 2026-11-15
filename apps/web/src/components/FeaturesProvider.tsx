'use client';

import { createContext, useContext } from 'react';
import { NO_FEATURES, type FeatureName, type Features } from '@/lib/features';

const FeaturesContext = createContext<Features>(NO_FEATURES);

/** Receives the flags the root server layout fetched (D-15). Without a provider every flag reads false. */
export function FeaturesProvider({ value, children }: { value: Features; children: React.ReactNode }) {
  return <FeaturesContext.Provider value={value}>{children}</FeaturesContext.Provider>;
}

export function useFeatures(): Features {
  return useContext(FeaturesContext);
}

/** `useFeature('diagram' | 'videos' | 'female_atlas')`: false when the flag is off or the features fetch failed. */
export function useFeature(name: FeatureName): boolean {
  return useContext(FeaturesContext)[name];
}
