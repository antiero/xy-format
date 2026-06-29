import type { XYProjectViewModel } from "./projectViewModel";

const INVALID_FILENAME_CHARACTERS = /[/:\\?%*"<>|]/g;

export function normalizeXYFileName(fileName: string): string {
  const cleaned =
    fileName
      .trim()
      .replace(INVALID_FILENAME_CHARACTERS, "-")
      .replace(/\s+/g, " ") || "project";

  if (cleaned.toLowerCase().endsWith(".xy")) {
    return cleaned;
  }
  return `${cleaned}.xy`;
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
