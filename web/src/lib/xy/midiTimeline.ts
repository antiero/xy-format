import type {
  MidiData,
  MidiEvent,
  MidiSetTempoEvent,
  MidiTimeSignatureEvent,
} from "midi-file";

export const MIDI_OUTPUT_TICKS_PER_QUARTER = 1920;
const MIDI_OUTPUT_TICKS_PER_16TH = MIDI_OUTPUT_TICKS_PER_QUARTER / 4;

const DEFAULT_BPM = 120;
const DEFAULT_NUMERATOR = 4;
const DEFAULT_DENOMINATOR = 4;

export type MidiTempoChange = {
  tick: number;
  bpm: number;
};

export type MidiTimeSignatureChange = {
  tick: number;
  numerator: number;
  denominator: number;
};

export type MidiBar = {
  index: number;
  startTick: number;
  endTick: number;
  numerator: number;
  denominator: number;
};

export type MidiPatternWindow = {
  sourceStartTick: number;
  sourceEndTick: number;
  sourceStart16ths: number;
  sourceEnd16ths: number;
  outputStartTick: number;
  outputEndTick: number;
  steps: number;
  barCount: number;
};

type OutputTempoSegment = MidiTempoChange & {
  outputTick: number;
};

export type MidiTimeline = {
  ticksPerBeat: number;
  projectBpm: number;
  sourceEndTick: number;
  sourceTotal16ths: number;
  sourceTotalBars: number;
  tempoChanges: MidiTempoChange[];
  timeSignatureChanges: MidiTimeSignatureChange[];
  bars: MidiBar[];
  toOutputTick: (sourceTick: number) => number;
};

export type BuildMidiTimelineOptions = {
  contentStartTick: number;
  contentEndTick: number;
  bpmOverride?: number;
};

type AbsoluteEvent<T extends MidiEvent> = {
  tick: number;
  trackIndex: number;
  eventIndex: number;
  event: T;
};

function isSetTempo(event: MidiEvent): event is MidiSetTempoEvent {
  return event.type === "setTempo";
}

function isTimeSignature(event: MidiEvent): event is MidiTimeSignatureEvent {
  return event.type === "timeSignature";
}

function absoluteEvents<T extends MidiEvent>(
  midi: MidiData,
  predicate: (event: MidiEvent) => event is T,
): AbsoluteEvent<T>[] {
  const events: AbsoluteEvent<T>[] = [];
  midi.tracks.forEach((track, trackIndex) => {
    let tick = 0;
    track.forEach((event, eventIndex) => {
      tick += event.deltaTime;
      if (predicate(event)) {
        events.push({ tick, trackIndex, eventIndex, event });
      }
    });
  });
  return events.sort(
    (a, b) =>
      a.tick - b.tick ||
      a.trackIndex - b.trackIndex ||
      a.eventIndex - b.eventIndex,
  );
}

function replaceChangesAtSameTick<T extends { tick: number }>(
  changes: T[],
): T[] {
  const deduped: T[] = [];
  for (const change of changes) {
    if (deduped.at(-1)?.tick === change.tick) {
      deduped[deduped.length - 1] = change;
    } else {
      deduped.push(change);
    }
  }
  return deduped;
}

function collectTempoChanges(midi: MidiData): MidiTempoChange[] {
  const changes = absoluteEvents(midi, isSetTempo).map(({ tick, event }) => ({
    tick,
    bpm: 60_000_000 / event.microsecondsPerBeat,
  }));
  if (changes.length === 0 || changes[0].tick > 0) {
    changes.unshift({ tick: 0, bpm: DEFAULT_BPM });
  }
  return replaceChangesAtSameTick(changes);
}

function collectTimeSignatureChanges(
  midi: MidiData,
): MidiTimeSignatureChange[] {
  const changes = absoluteEvents(midi, isTimeSignature).map(
    ({ tick, event }) => ({
      tick,
      numerator: Math.max(1, event.numerator),
      denominator: Math.max(1, event.denominator),
    }),
  );
  if (changes.length === 0 || changes[0].tick > 0) {
    changes.unshift({
      tick: 0,
      numerator: DEFAULT_NUMERATOR,
      denominator: DEFAULT_DENOMINATOR,
    });
  }
  return replaceChangesAtSameTick(changes);
}

function changeAtTick<T extends { tick: number }>(
  changes: T[],
  tick: number,
): T {
  let active = changes[0];
  for (const change of changes) {
    if (change.tick > tick) break;
    active = change;
  }
  return active;
}

function normalizedProjectBpm(bpm: number): number {
  return Math.round(Math.max(1, bpm) * 10) / 10;
}

function buildOutputTempoSegments(args: {
  tempoChanges: MidiTempoChange[];
  projectBpm: number;
  ticksPerBeat: number;
  preserveTempoChanges: boolean;
}): OutputTempoSegment[] {
  const sourceChanges = args.preserveTempoChanges
    ? args.tempoChanges
    : [{ tick: 0, bpm: args.projectBpm }];
  const segments: OutputTempoSegment[] = [];
  let outputTick = 0;

  for (const [index, change] of sourceChanges.entries()) {
    if (index > 0) {
      const previous = sourceChanges[index - 1];
      outputTick +=
        (((change.tick - previous.tick) * MIDI_OUTPUT_TICKS_PER_QUARTER) /
          args.ticksPerBeat) *
        (args.projectBpm / previous.bpm);
    }
    segments.push({ ...change, outputTick });
  }
  return segments;
}

function buildBars(args: {
  changes: MidiTimeSignatureChange[];
  ticksPerBeat: number;
  contentEndTick: number;
}): MidiBar[] {
  const bars: MidiBar[] = [];
  const minimumEnd = Math.max(1, args.contentEndTick);
  let cursor = 0;

  while (cursor < minimumEnd) {
    const signature = changeAtTick(args.changes, cursor);
    const barTicks =
      (args.ticksPerBeat * 4 * signature.numerator) / signature.denominator;
    const nextChange = args.changes.find((change) => change.tick > cursor);
    const naturalEnd = cursor + Math.max(1, barTicks);
    const endTick =
      nextChange && nextChange.tick < naturalEnd ? nextChange.tick : naturalEnd;
    bars.push({
      index: bars.length,
      startTick: cursor,
      endTick,
      numerator: signature.numerator,
      denominator: signature.denominator,
    });
    cursor = endTick;
  }
  return bars;
}

export function midiTickTo16ths(
  timeline: Pick<MidiTimeline, "ticksPerBeat">,
  tick: number,
): number {
  return (tick * 4) / timeline.ticksPerBeat;
}

export function midi16thsToTick(
  timeline: Pick<MidiTimeline, "ticksPerBeat">,
  position16ths: number,
): number {
  return (position16ths * timeline.ticksPerBeat) / 4;
}

export function buildMidiTimeline(
  midi: MidiData,
  options: BuildMidiTimelineOptions,
): MidiTimeline {
  const parsedTicksPerBeat =
    midi.header.ticksPerBeat ?? midi.header.timeDivision;
  if (!parsedTicksPerBeat) {
    throw new Error("SMPTE-timed MIDI files are not supported yet.");
  }
  const ticksPerBeat: number = parsedTicksPerBeat;

  const tempoChanges = collectTempoChanges(midi);
  const timeSignatureChanges = collectTimeSignatureChanges(midi);
  // OP-XY stores one project tempo. Use the tempo in force when the first
  // note sounds, then convert every source tick through the complete tempo
  // map so later changes retain their wall-clock timing at that fixed BPM.
  const sourceTempo = changeAtTick(tempoChanges, options.contentStartTick).bpm;
  const projectBpm = normalizedProjectBpm(options.bpmOverride ?? sourceTempo);
  const outputSegments = buildOutputTempoSegments({
    tempoChanges,
    projectBpm,
    ticksPerBeat,
    preserveTempoChanges: options.bpmOverride === undefined,
  });
  const bars = buildBars({
    changes: timeSignatureChanges,
    ticksPerBeat,
    contentEndTick: options.contentEndTick,
  });
  const sourceEndTick = bars.at(-1)?.endTick ?? ticksPerBeat * 4;

  function toOutputTick(sourceTick: number): number {
    const tick = Math.max(0, sourceTick);
    const segment = changeAtTick(outputSegments, tick);
    return (
      segment.outputTick +
      (((tick - segment.tick) * MIDI_OUTPUT_TICKS_PER_QUARTER) / ticksPerBeat) *
        (projectBpm / segment.bpm)
    );
  }

  return {
    ticksPerBeat,
    projectBpm,
    sourceEndTick,
    sourceTotal16ths: midiTickTo16ths({ ticksPerBeat }, sourceEndTick),
    sourceTotalBars: bars.length,
    tempoChanges,
    timeSignatureChanges,
    bars,
    toOutputTick,
  };
}

function lastTickWithinStepLimit(args: {
  timeline: MidiTimeline;
  rangeOutputStart: number;
  renderedSteps: number;
  startTick: number;
  endTick: number;
  maxSteps: number;
}): number {
  let low = Math.ceil(args.startTick) + 1;
  let high = Math.floor(args.endTick);
  let best = low;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    const roundedEnd = Math.round(
      (args.timeline.toOutputTick(middle) - args.rangeOutputStart) /
        MIDI_OUTPUT_TICKS_PER_16TH,
    );
    if (roundedEnd - args.renderedSteps <= args.maxSteps) {
      best = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return Math.min(args.endTick, Math.max(args.startTick + 1, best));
}

export function buildMidiPatternWindows(
  timeline: MidiTimeline,
  start16ths: number,
  end16ths: number,
  maxWindows: number,
): MidiPatternWindow[] {
  const startTick = Math.max(
    0,
    Math.min(timeline.sourceEndTick, midi16thsToTick(timeline, start16ths)),
  );
  const endTick = Math.max(
    startTick + 1,
    Math.min(timeline.sourceEndTick, midi16thsToTick(timeline, end16ths)),
  );
  // A Song scene represents up to four source bars, not four assumed 4/4
  // bars. Slow tempo-map sections may need fewer bars to stay within the
  // device's 64-step pattern limit.
  const barParts = timeline.bars
    .filter((bar) => bar.endTick > startTick && bar.startTick < endTick)
    .map((bar) => ({
      startTick: Math.max(startTick, bar.startTick),
      endTick: Math.min(endTick, bar.endTick),
      barIndex: bar.index,
    }));
  const windows: MidiPatternWindow[] = [];
  const rangeOutputStart = timeline.toOutputTick(startTick);
  let renderedSteps = 0;
  let currentStart = 0;
  let currentEnd = 0;
  let currentBars = new Set<number>();

  function flush() {
    if (currentEnd <= currentStart || windows.length >= maxWindows) return;
    const roundedEnd = Math.round(
      (timeline.toOutputTick(currentEnd) - rangeOutputStart) /
        MIDI_OUTPUT_TICKS_PER_16TH,
    );
    const steps = Math.max(1, roundedEnd - renderedSteps);
    windows.push({
      sourceStartTick: currentStart,
      sourceEndTick: currentEnd,
      sourceStart16ths: midiTickTo16ths(timeline, currentStart),
      sourceEnd16ths: midiTickTo16ths(timeline, currentEnd),
      outputStartTick: timeline.toOutputTick(currentStart),
      outputEndTick: timeline.toOutputTick(currentEnd),
      steps,
      barCount: currentBars.size,
    });
    renderedSteps += steps;
    currentStart = 0;
    currentEnd = 0;
    currentBars = new Set<number>();
  }

  for (const part of barParts) {
    let partStart = part.startTick;
    while (partStart < part.endTick && windows.length < maxWindows) {
      if (currentEnd <= currentStart) {
        currentStart = partStart;
        currentEnd = partStart;
      }
      const addsBar = !currentBars.has(part.barIndex);
      const roundedEnd = Math.round(
        (timeline.toOutputTick(part.endTick) - rangeOutputStart) /
          MIDI_OUTPUT_TICKS_PER_16TH,
      );
      const proposedSteps = roundedEnd - renderedSteps;
      if (
        currentEnd > currentStart &&
        ((addsBar && currentBars.size >= 4) || proposedSteps > 64)
      ) {
        flush();
        continue;
      }
      if (proposedSteps > 64) {
        const splitTick = lastTickWithinStepLimit({
          timeline,
          rangeOutputStart,
          renderedSteps,
          startTick: partStart,
          endTick: part.endTick,
          maxSteps: 64,
        });
        currentEnd = splitTick;
        currentBars.add(part.barIndex);
        flush();
        partStart = splitTick;
        continue;
      }
      currentEnd = part.endTick;
      currentBars.add(part.barIndex);
      partStart = part.endTick;
    }
  }
  flush();
  return windows;
}

export function midiBarIndexAtTick(
  timeline: MidiTimeline,
  tick: number,
): number {
  const bar = timeline.bars.find(
    (candidate) => candidate.startTick <= tick && tick < candidate.endTick,
  );
  return bar?.index ?? Math.max(0, timeline.bars.length - 1);
}
