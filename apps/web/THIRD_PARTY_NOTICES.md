# Third-party notices

Code in this app that is adapted from other projects. The 3D anatomy models and their licences are credited on the
`/credits` page and are not covered here.

## human-atlas-enhanced (MIT)

Source: https://github.com/PrejudiceNeutrino/human-atlas-enhanced, a fork of https://github.com/ashemag/human-atlas.

We re-implemented four viewer ideas for our own architecture: zooming towards the cursor or pinch centre, hiding and
restoring individual structures, grouped search results, and a staged explode view (families first, then pieces).
The explode layout and playback timing follow `app/explosion-layout.ts` and `app/explode-playback.ts`, and the
hide/restore rules follow `app/hide-restore.ts`. They live in `src/lib/atlas-zoom.ts`, `atlas-hidden.ts`,
`atlas-search.ts` and `atlas-explode.ts`. No model data, Learn text or images were taken.

The fork's own `LICENSE` carries only the upstream holder line below; PrejudiceNeutrino, the fork's author, adds no
separate copyright line, so the fork's work is credited here by name.

```
MIT License

Copyright (c) 2026 ashemag

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
