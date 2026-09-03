import type { XYProjectViewModel } from "./projectViewModel";

const INVALID_FILENAME_CHARACTERS = /[/:\\?%*"<>|]/g;

export function normalizeXYFileName(fileName: string): string {
  const cleaned =
    fileName
      .trim()
      .replace(INVALID_FILENAME_CHARACTERS, "-")
      .replace(/\s+/g, " ") || "project";

  return `${xyProjectName(cleaned)}.xy`;
}

/** The editable part of an OP-XY project filename. */
export function xyProjectName(fileName: string): string {
  return fileName.replace(/\.xy$/i, "");
}

export async function exportXYProject(
  project: XYProjectViewModel,
): Promise<Blob> {
  const bytes = project.imageProject.toBytes();
  return new Blob([bytes as BlobPart], { type: "application/octet-stream" });
}

export function exportXYProjectBytes(project: XYProjectViewModel): Uint8Array {
  return project.imageProject.toBytes();
}
