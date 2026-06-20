import { ImageProject } from './image_writer';
import { buildProjectViewModel, type XYProjectViewModel } from './projectViewModel';

export async function loadXYFile(file: File): Promise<XYProjectViewModel> {
  const buffer = await file.arrayBuffer();
  const imageProject = ImageProject.fromBytes(new Uint8Array(buffer));
  return buildProjectViewModel(imageProject, file.name, undefined, false);
}

export function loadXYBytes(bytes: Uint8Array, fileName = 'project.xy'): XYProjectViewModel {
  const imageProject = ImageProject.fromBytes(bytes);
  return buildProjectViewModel(imageProject, fileName, undefined, false);
}
