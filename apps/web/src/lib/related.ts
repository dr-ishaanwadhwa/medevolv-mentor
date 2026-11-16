/** Related-topic chips (PRD 4.2, V-9). Pure, so the unit runner covers it. */

/** The question a related-topic chip asks: the certified concept label itself, as a new turn in the same thread. */
export function relatedQuestion(label: string): string {
  return label.trim().replace(/\s+/g, ' ');
}

/** Shared pages have no thread: the chip opens Ask with the label as the question and sends it. */
export function askHref(question: string): string {
  return `/ask?${new URLSearchParams({ q: question, go: '1' })}`;
}
