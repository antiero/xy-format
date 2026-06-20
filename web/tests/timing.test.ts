import { describe, expect, it } from 'vitest';
import {
  decodePatternSteps,
  decodeTrackScale,
  noteToDisplayPosition,
  normalizeTickToPattern,
  patternEffectiveLength16ths,
  sceneLength16ths,
} from '../src/lib/xy/timing';
import { collectPlaybackEvents, crossesPlaybackPosition } from '../src/lib/xy/playback';
import type { XYPatternViewModel, XYSceneViewModel, XYTrackViewModel } from '../src/lib/xy/projectViewModel';

describe('timing model', () => {
  it('derives bars and final-bar length from total steps', () => {
    expect(decodePatternSteps(16)).toMatchObject({ bars: 1, finalBarSteps: 16, totalSteps: 16, valid: true });
    expect(decodePatternSteps(24)).toMatchObject({ bars: 2, finalBarSteps: 8, totalSteps: 24, valid: true });
    expect(decodePatternSteps(64)).toMatchObject({ bars: 4, finalBarSteps: 16, totalSteps: 64, valid: true });
  });

  it('decodes confirmed track-scale bytes and leaves unknown values read-only', () => {
    expect(decodeTrackScale(0x01)).toMatchObject({ scale: '1/2', factor16ths: 0.5, supportedForWrite: true });
    expect(decodeTrackScale(0x03)).toMatchObject({ scale: '1', factor16ths: 1, supportedForWrite: true });
    expect(decodeTrackScale(0x05)).toMatchObject({ scale: '2', factor16ths: 2, supportedForWrite: true });
    expect(decodeTrackScale(0x07)).toMatchObject({ scale: '3', factor16ths: 3, supportedForWrite: false });
    expect(decodeTrackScale(0x0e)).toMatchObject({ scale: '16', factor16ths: 16, supportedForWrite: true });
    expect(decodeTrackScale(0x09)).toMatchObject({ scale: 'unknown', factor16ths: null, supportedForWrite: false });
  });

  it('converts note ticks into scale-aware display units', () => {
    expect(noteToDisplayPosition({ tick: 960, gateTicks: 480 }, { trackScale: '1' })).toEqual({
      start16ths: 2,
      duration16ths: 1,
    });
    expect(noteToDisplayPosition({ tick: 960, gateTicks: 480 }, { trackScale: '2' })).toEqual({
      start16ths: 4,
      duration16ths: 2,
    });
    expect(normalizeTickToPattern(0xfffffff6, 16)).toBe(7670);
    expect(noteToDisplayPosition({ tick: 0xfffffff6, gateTicks: 480 }, { trackScale: '1', totalSteps: 16 })).toEqual({
      start16ths: 15.979166666666666,
      duration16ths: 1,
    });
  });

  it('computes scene length as the longest selected scaled pattern', () => {
    const p1 = { totalSteps: 64, trackScale: '1', effectiveLength16ths: 64 } as XYPatternViewModel;
    const p2 = { totalSteps: 24, trackScale: '4', effectiveLength16ths: patternEffectiveLength16ths({ totalSteps: 24, trackScale: '4' } as XYPatternViewModel) } as XYPatternViewModel;
    const tracks = [
      { patterns: [p1] },
      { patterns: [p2] },
    ] as XYTrackViewModel[];
    const scene = { patternByTrack: [0, 0] } as XYSceneViewModel;
    expect(sceneLength16ths(scene, tracks)).toBe(96);
  });

  it('collects scale-aware playback events and detects loop crossings', () => {
    const project = {
      activeSceneIndex: 0,
      tracks: [
        {
          patterns: [
            {
              index: 0,
              totalSteps: 16,
              trackScale: '3',
              effectiveLength16ths: 48,
              notes: [{ id: 'n1', tick: 960, gateTicks: 480, note: 60, velocity: 100 }],
            },
          ],
        },
      ],
      scenes: [{ length16ths: 48, patternByTrack: [0], mutedTracks: [false] }],
    } as never;

    expect(collectPlaybackEvents(project, 'track', 0, 0)[0]).toMatchObject({
      start16ths: 6,
      duration16ths: 3,
      note: 60,
    });
    expect(crossesPlaybackPosition(1, 47, 2, true)).toBe(true);
    expect(crossesPlaybackPosition(20, 10, 12, false)).toBe(false);
  });
});
