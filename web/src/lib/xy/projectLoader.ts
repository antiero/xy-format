import { ImageProject } from "./image_writer";
import {
  buildProjectViewModel,
  type XYProjectViewModel,
} from "./projectViewModel";
import {
  assessXYProject,
  type XYProjectCompatibilityAssessment,
} from "./projectCompatibility";

export type XYFileLoadResult =
  | {
      kind: "editable";
      project: XYProjectViewModel;
      assessment: XYProjectCompatibilityAssessment;
    }
  | {
      kind: "diagnostic";
      fileName: string;
      originalBytes: Uint8Array;
      assessment: XYProjectCompatibilityAssessment;
    };

export async function loadXYFile(file: File): Promise<XYFileLoadResult> {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const assessment = await assessXYProject(bytes);
  if (assessment.status !== "knownCompatible") {
    return {
      kind: "diagnostic",
      fileName: file.name,
      originalBytes: bytes,
      assessment,
    };
  }

  const imageProject = ImageProject.fromBytes(bytes);
  return {
    kind: "editable",
    project: buildProjectViewModel(imageProject, file.name, undefined, false),
    assessment,
  };
}

export function loadXYBytes(
  bytes: Uint8Array,
  fileName = "project.xy",
): XYProjectViewModel {
  const imageProject = ImageProject.fromBytes(bytes);
  return buildProjectViewModel(imageProject, fileName, undefined, false);
}
