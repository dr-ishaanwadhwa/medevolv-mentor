// Tooltip copy for the atlas toolbar (WS-A). Merged into the shared TipId type by tips/index.ts (WS-K).
// Rules: never repeat the visible label; state purpose and effect; plain words, about 20 words at most.
interface AtlasTip {
  purpose: string;
  effect: string;
  disabled?: string;
}

export const ATLAS_TIPS = {
  'atlas.isolate': {
    purpose: 'Shows only the selected structure.',
    effect: 'Hides everything else. Tap again to bring the body back.',
    disabled: 'Select a structure first.',
  },
  'atlas.reset': {
    purpose: 'Goes back to the whole-body starting view.',
    effect: 'Clears your selection and Isolate. Layers stay as you set them. You can undo.',
    disabled: 'Atlas still loading',
  },
  'atlas.layers': {
    purpose: 'Chooses which body systems are visible.',
    effect: 'Opens the layer list.',
  },
} as const satisfies Record<string, AtlasTip>;
