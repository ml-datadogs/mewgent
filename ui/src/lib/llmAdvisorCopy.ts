/** Hover / screen-reader context for the AI chip (popover + home FAB). */
export function getLlmAdvisorTooltip(available: boolean): string {
  return available
    ? 'Change model or API key. Powers AI team fill, breeding pair hints, and smart room layout.'
    : 'Add an OpenAI API key to unlock AI team suggestions, breeding picks, and distribution advice.';
}

export function llmAdvisorTitleAttr(available: boolean): string {
  return available
    ? 'OpenAI — model & key for AI team, breeding, and rooms'
    : 'Add API key — enables AI team, breeding, and room help';
}
