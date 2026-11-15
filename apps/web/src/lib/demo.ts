export interface DemoPrompt {
  tag: string;
  text: string;
}

export const DEMO_PROMPTS: DemoPrompt[] = [
  {
    tag: 'Compare · split into parts',
    text: 'Compare the mechanism of action of penicillins and aminoglycosides.',
  },
  {
    tag: 'Clinical vignette',
    text: 'A patient with pheochromocytoma is posted for surgery. What drug should be started first and why?',
  },
  {
    tag: 'Clinical case',
    text: 'A 22-year-old from Odisha has fever with rigors, severe headache and confusion. A peripheral smear shows ring forms and banana-shaped gametocytes. What is the diagnosis and how is it treated?',
  },
  {
    tag: 'Anatomy · opens in 3D',
    text: 'What structures pass through the superior orbital fissure?',
  },
  {
    tag: 'Watch it decline',
    text: 'Who won the 2011 cricket world cup?',
  },
  {
    tag: 'Watch it refuse',
    text: 'My mother has TB, what dose of rifampicin should she take?',
  },
];
