// Tooltip copy for the atlas (WS-A). Merged into the shared TipId type by tips/index.ts (WS-K); until that one-line
// spread lands the atlas components pass these objects directly (the `tip` prop accepts a plain {purpose, effect}).
// Rules: never repeat the visible label; state purpose and effect; plain words, 26 words at most per tip.
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
    purpose: "Goes back to this model's starting view.",
    effect: 'Clears your selection and Isolate. Layers stay as you set them. You can undo.',
    disabled: 'Atlas still loading',
  },
  'atlas.layers': {
    purpose: 'Chooses which body systems are visible.',
    effect: 'Opens the layer list.',
  },
  'atlas.layers.default': {
    purpose: 'Puts the layers back to how the atlas first opens.',
    effect: 'Skin and the pregnancy reference stay off.',
  },
  'atlas.panel.toggle': {
    purpose: 'Folds or unfolds the details sheet.',
    effect: 'Gives the 3D view more room, or shows the details again.',
  },
  'atlas.search.clear': {
    purpose: 'Empties the structure search.',
    effect: 'Clears the typed text. The 3D view does not change.',
  },
  'atlas.sex.male': {
    purpose: 'BodyParts3D adult male reference (2,234 parts).',
    effect: 'Shows the male model.',
  },
  'atlas.sex.female': {
    purpose: 'Visible Human Female reference organs. Skeleton and muscles are partial.',
    effect: 'Shows the female model.',
  },
  'atlas.panel.expand': {
    purpose: 'Shows the full details of the selected structure.',
    effect: 'Opens the sheet to full height.',
  },
  'atlas.panel.collapse': {
    purpose: 'Makes more room for the 3D view.',
    effect: 'Folds the details down to one line.',
  },
  'atlas.panel.clear': {
    purpose: 'Closes the selected structure.',
    effect: 'Clears the highlight and returns to the whole body.',
  },
  'atlas.panel.concept': {
    purpose: 'Opens the textbook page for this structure.',
    effect: 'Leaves the atlas for the concept page.',
  },
  'atlas.female.download': {
    purpose: 'Starts loading the female model.',
    effect: 'Downloads the files once, then keeps them on this device.',
  },
  'atlas.female.notNow': {
    purpose: 'Skips the female download.',
    effect: 'Stays on the male model. Nothing is downloaded.',
  },
  'atlas.female.cancel': {
    purpose: 'Stops the female download.',
    effect: 'Returns to the male model. Files already fetched stay saved.',
  },
} as const satisfies Record<string, AtlasTip>;

/** Layer toggle for one body system. */
export function layerTip(name: string, on: boolean): AtlasTip {
  return on
    ? { purpose: `${name} is showing.`, effect: 'Hides this layer.' }
    : { purpose: `${name} is hidden.`, effect: 'Shows this layer.' };
}

/** A structure in the search results or the suggestion chips. */
export function structureTip(name: string): AtlasTip {
  return { purpose: `Finds ${name} in the model.`, effect: 'Selects it and moves the camera to it.' };
}

/** A related-concept chip in the selection panel. */
export function relatedTip(label: string): AtlasTip {
  return { purpose: `Opens the textbook page for ${label}.`, effect: 'Leaves the atlas.' };
}
