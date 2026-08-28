import { tickToDisplayStep } from "./timing";

type StepNote = {
  id: string;
  tick: number;
};

type TickOverrides = Readonly<Record<string, { tick: number } | undefined>>;

export function groupNotesByDisplayStep<T extends StepNote>(
  notes: readonly T[],
  totalSteps: number,
  tickOverrides: TickOverrides = {},
): Map<number, T[]> {
  const grouped = new Map<number, T[]>();

  for (const note of notes) {
    const tick = tickOverrides[note.id]?.tick ?? note.tick;
    const step = tickToDisplayStep(tick, totalSteps);
    const stepNotes = grouped.get(step);
    if (stepNotes) stepNotes.push(note);
    else grouped.set(step, [note]);
  }

  return grouped;
}
