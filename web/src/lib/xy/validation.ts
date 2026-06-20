import { SCENE_COUNT, SONG_MAX_CHAIN } from './image_writer';
import type { ValidationIssue, XYProjectViewModel } from './projectViewModel';

export function validateProject(project: XYProjectViewModel): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  for (const track of project.tracks) {
    for (const pattern of track.patterns) {
      if (pattern.notes.length > 120) {
        issues.push({
          severity: 'error',
          code: 'pattern-note-limit',
          message: `Pattern has ${pattern.notes.length} notes; the OP-XY limit is 120.`,
          target: { track: track.index, pattern: pattern.index },
        });
      }
      if (pattern.bars < 1 || pattern.bars > 4 || pattern.rawSteps < 1 || pattern.rawSteps > 64) {
        issues.push({
          severity: 'error',
          code: 'pattern-length-range',
          message: `Pattern length byte ${pattern.rawSteps} is outside the supported 1..64 step range.`,
          target: { track: track.index, pattern: pattern.index },
        });
      }
      if (pattern.finalBarSteps < 1 || pattern.finalBarSteps > 16) {
        issues.push({
          severity: 'error',
          code: 'final-bar-range',
          message: `Final bar length ${pattern.finalBarSteps} is outside the supported 1..16 step range.`,
          target: { track: track.index, pattern: pattern.index },
        });
      }
      if (!pattern.trackScaleKnown) {
        issues.push({
          severity: 'warning',
          code: 'track-scale-unknown',
          message: `Track scale byte 0x${pattern.trackScaleRaw.toString(16).padStart(2, '0')} is not decoded; timing uses scale 1 fallback.`,
          target: { track: track.index, pattern: pattern.index },
        });
      }
    }
  }

  for (const scene of project.scenes) {
    scene.patternByTrack.forEach((patternIndex, trackIndex) => {
      const patternCount = project.tracks[trackIndex]?.patterns.length ?? 0;
      if (patternIndex < 0 || patternIndex >= patternCount) {
        issues.push({
          severity: 'error',
          code: 'scene-missing-pattern',
          message: `Scene ${scene.index + 1} references P${patternIndex + 1} on T${trackIndex + 1}, but the track has ${patternCount} pattern(s).`,
          target: { scene: scene.index, track: trackIndex, pattern: patternIndex },
        });
      }
    });
  }

  for (const song of project.songs) {
    if (!song.supported) {
      issues.push({
        severity: 'warning',
        code: 'song-footer-partial',
        message: `Song ${song.index + 1} footer could not be parsed confidently and is read-only.`,
        target: { song: song.index },
      });
      continue;
    }
    if (song.sceneChain.length > SONG_MAX_CHAIN) {
      issues.push({
        severity: 'error',
        code: 'song-chain-limit',
        message: `Song ${song.index + 1} has ${song.sceneChain.length} scenes; the guide limit is ${SONG_MAX_CHAIN}.`,
        target: { song: song.index },
      });
    }
    song.sceneChain.forEach((sceneIndex) => {
      if (sceneIndex < 0 || sceneIndex >= SCENE_COUNT) {
        issues.push({
          severity: 'error',
          code: 'song-scene-range',
          message: `Song ${song.index + 1} references scene ${sceneIndex + 1}, outside the 1..99 scene range.`,
          target: { song: song.index, scene: sceneIndex },
        });
      } else if (!project.scenes[sceneIndex]?.present) {
        issues.push({
          severity: 'warning',
          code: 'song-empty-scene',
          message: `Song ${song.index + 1} includes scene ${sceneIndex + 1}, which is not marked present.`,
          target: { song: song.index, scene: sceneIndex },
        });
      }
    });
  }

  return issues;
}

export function validationCounts(issues: ValidationIssue[]): { errors: number; warnings: number; info: number } {
  return {
    errors: issues.filter((issue) => issue.severity === 'error').length,
    warnings: issues.filter((issue) => issue.severity === 'warning').length,
    info: issues.filter((issue) => issue.severity === 'info').length,
  };
}
