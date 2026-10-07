/** Preserve the entire identifier; wrap long labels rather than overlapping ticks. */
export function batchLabelLines(label: string, width = 17): string[] {
  if (!label) return [''];
  const lines: string[] = [];
  let rest = label;
  while (rest.length > width) {
    const separator = rest.lastIndexOf('-', width - 1);
    const end = separator > width / 2 ? separator + 1 : width;
    lines.push(rest.slice(0, end));
    rest = rest.slice(end);
  }
  if (rest) lines.push(rest);
  return lines;
}
