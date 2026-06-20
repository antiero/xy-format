import type { XYProjectViewModel } from './projectViewModel';

export function editedFileName(fileName: string): string {
  const trimmed = fileName.trim() || 'project.xy';
  if (trimmed.toLowerCase().endsWith('.xy')) {
    return `${trimmed.slice(0, -3)}-edited.xy`;
  }
  return `${trimmed}-edited.xy`;
}

export async function exportXYProject(project: XYProjectViewModel): Promise<Blob> {
  const bytes = project.imageProject.toBytes();
  return new Blob([bytes as BlobPart], { type: 'application/octet-stream' });
}

export function exportXYProjectBytes(project: XYProjectViewModel): Uint8Array {
  return project.imageProject.toBytes();
}
