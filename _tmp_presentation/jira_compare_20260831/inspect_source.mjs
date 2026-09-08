import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "C:/Users/user/Desktop/project/Auto_Reports/_tmp_presentation/jira_compare_20260831/source-deck.pptx";
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,image,table,chart,notes,layout",
  include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,isPlaceholder,placeholders",
  maxChars: 50000,
});
process.stdout.write(snapshot.ndjson);
