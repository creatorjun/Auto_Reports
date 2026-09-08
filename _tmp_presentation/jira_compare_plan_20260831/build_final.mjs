import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "C:/Users/user/Desktop/project/Auto_Reports/_tmp_presentation/jira_compare_plan_20260831";
const starter = `${workspace}/template-starter.pptx`;
const output = "C:/Users/user/Desktop/project/Auto_Reports/Auto_Reports_JIRA_비교_시연자료_구현계획추가.pptx";
const renderDir = `${workspace}/final-render`;
const layoutDir = `${workspace}/final-layout/final`;

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

async function imageBytes(path) {
  const bytes = await fs.readFile(path);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

let starterRecords;
let roadmapStarterRecords;
let currentRecords;

function currentAidFor(sourceAid) {
  const source = starterRecords.find((record) => record.id === sourceAid);
  if (!source) throw new Error(`Missing starter record for ${sourceAid}`);
  const targetSlide = source.slide === 8 ? 9 : source.slide;
  let matches = currentRecords.filter(
    (record) => record.kind === source.kind && record.slide === targetSlide
  );
  if (source.name) {
    matches = matches.filter((record) => record.name === source.name);
  } else if (source.text !== undefined) {
    matches = matches.filter((record) => record.text === source.text);
  } else if (source.bbox) {
    matches = matches.filter((record) => JSON.stringify(record.bbox) === JSON.stringify(source.bbox));
  }
  if (matches.length !== 1) {
    throw new Error(`Could not resolve ${sourceAid}; matches=${matches.length}`);
  }
  return matches[0].id;
}

function currentRoadmapAidFor(sourceAid) {
  const source = roadmapStarterRecords.find((record) => record.id === sourceAid);
  if (!source) throw new Error(`Missing roadmap starter record for ${sourceAid}`);
  let matches = currentRecords.filter(
    (record) => record.kind === source.kind && record.slide === source.slide
  );
  if (source.name) {
    matches = matches.filter((record) => record.name === source.name);
  } else if (source.text !== undefined) {
    matches = matches.filter((record) => record.text === source.text);
  } else if (source.bbox) {
    matches = matches.filter((record) => JSON.stringify(record.bbox) === JSON.stringify(source.bbox));
  }
  if (matches.length !== 1) {
    throw new Error(`Could not resolve roadmap ${sourceAid}; matches=${matches.length}`);
  }
  return matches[0].id;
}

function rewrite(presentation, id, value) {
  const target = presentation.resolve(currentAidFor(id));
  target.text = value;
}

function rewriteRoadmap(presentation, id, value) {
  const target = presentation.resolve(currentRoadmapAidFor(id));
  target.text = value;
}

async function replaceImage(presentation, id, path, alt) {
  const image = presentation.resolve(currentAidFor(id));
  const oldFrame = image.frame;
  const oldCrop = image.crop;
  const oldFit = image.fit;
  const oldGeometry = image.geometry;
  const oldBorderRadius = image.borderRadius;
  const oldRotation = image.rotation;
  const oldFlipHorizontal = image.flipHorizontal;
  const oldFlipVertical = image.flipVertical;
  const oldLockAspectRatio = image.lockAspectRatio;
  image.replace({
    blob: await imageBytes(path),
    contentType: "image/jpeg",
    alt,
    ...(oldFit ? { fit: oldFit } : {}),
  });
  image.frame = oldFrame;
  image.crop = oldCrop;
  image.geometry = oldGeometry;
  image.borderRadius = oldBorderRadius ?? "rounded-xl";
  image.rotation = oldRotation;
  image.flipHorizontal = oldFlipHorizontal;
  image.flipVertical = oldFlipVertical;
  image.lockAspectRatio = oldLockAspectRatio;
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(starter));
starterRecords = (await fs.readFile("C:/Users/user/Desktop/project/Auto_Reports/_tmp_presentation/jira_compare_20260831/template-starter.pptx.inspect.ndjson", "utf8"))
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));
roadmapStarterRecords = (await fs.readFile(`${workspace}/template-starter.pptx.inspect.ndjson`, "utf8"))
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));
const currentSnapshot = await presentation.inspect({
  kind: "slide,textbox,image,notes",
  include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,alt",
  maxChars: 60000,
});
currentRecords = currentSnapshot.ndjson
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

const edits = {
  "sh/cje5c72p": "AUTO REPORTS × JIRA",
  "sh/l8769cj6": "JIRA 원천은 그대로,\n운영 판단까지는 더 짧게",
  "sh/qhwnaxkj": "현재 TACEA 화면과 워크스페이스를 같은 업무 질문으로 직접 비교합니다",
  "sh/bi543214": "전사 확대 비교 시연 자료  |  2026.08.31",

  "sh/xwfah8bm": "CURRENT JIRA",
  "sh/2l4jqdc3": "현재 JIRA는 한 건을 깊게 보지만 전체 현황은 다시 만들어야 합니다",
  "sh/cb61wnu5": "02",
  "sh/dcf2psvq": "한 건은 깊게\n전체는 다시 묻습니다",
  "sh/qp4judcz": "TACEA 1,000+건 중 50건을 펼쳐 보고, 선택한 한 건의 설명·담당·SLA를 자세히 확인하는 현재 화면입니다.",
  "sh/0f6l0nuh": "현황 질문마다 유형·상태·기간 재필터",
  "sh/9svad8vq": "합계·추세·병목은 별도 쿼리·재조합",
  "sh/mp4b2tcz": "현재 운영 JIRA · TACEA 업무 검색 화면 캡처  |  2026-08-31",

  "sh/x0z6t4z2": "WORKSPACE VIEW",
  "sh/kz2d87qd": "같은 TACEA를 한 화면에서 운영 질문으로 바꿉니다",
  "sh/61kvah8j": "03",
  "sh/72tcjm94": "유형 선택 → 요약 → 추세",
  "sh/832dcrq9": "요청 유형 7종과 조회 기간을 맞추면 생성·해결·미완료·대기 상태와 월별 추세가 함께 갱신됩니다.",
  "sh/250bydsz": "생성 966 · 해결 865 · 미완료 130",
  "sh/jmh8veh8": "리뷰 20 · 자료 요청 14 · 결과 대기 44",
  "sh/5ozqxoze": "열림: 지원 31 · 개선 63 · 인시던트 30 · CVE 1",
  "sh/axo7i9gr": "현재 배포 워크스페이스 대시보드 캡처  |  2026-08-31",

  "sh/2xcba14f": "TASK PATH",
  "sh/fahcv6t4": "같은 질문에 답하는 경로가 다릅니다: JIRA 5단계, 워크스페이스 2단계",
  "sh/t8zutwby": "04",
  "sh/s7qtkrud": "주간 운영 현황을 묻는다면",
  "sh/r6hcrmts": "질문: 이번 달 유입·해결 차이와 지금 막힌 상태는 무엇인가?",
  "sh/658bi1c7": "워크스페이스는\n유형·반기 선택 → 카드·차트 클릭",
  "sh/29ozad8v": "JIRA 필터",
  "sh/3axgjipg": "프로젝트·유형·상태·기간 지정",
  "sh/f6dgfy9k": "결과 탐색",
  "sh/g7mh83q5": "50건 목록에서 관련 티켓 확인",
  "sh/vm9w3up0": "상세 확인",
  "sh/al0vapof": "티켓별 SLA·담당·업데이트 확인",
  "sh/i9kve9or": "재집계",
  "sh/5cbe94n2": "상태·유형별 쿼리를 반복",
  "sh/4jetcbm5": "보고 작성",
  "sh/pkna5gnq": "수치를 복사해 표·문장으로 정리",

  "sh/uhw7ehwr": "SLA FOLLOW-UP",
  "sh/8byd0zit": "지연 이슈 후속 조치는 티켓 이동보다 최근 근거가 먼저입니다",
  "sh/y5wvu50b": "05",
  "sh/l8nu5kj2": "같은 업무, 더 짧은 확인 흐름",
  "sh/bilcza10": "JIRA: 검색 → 티켓 선택 → 활동·SLA 이동",
  "sh/6tc7axwv": "워크스페이스: 지연 티켓 + 최근 댓글 최대 5개",
  "sh/8fupc7e1": "원문이 필요할 때 JIRA 티켓으로 즉시 연결",
  "sh/vi58nmdc": "현재 배포 SLA 대시보드 캡처  |  2026-08-31",

  "sh/d8z25c76": "VISIBILITY MATRIX",
  "sh/m90bi543": "가시성 차이는 화면 수보다 답변 단위에서 납니다",
  "sh/k7ytgvmd": "06",
  "sh/l8rup03y": "운영 질문",
  "sh/ylgbel47": "현재 TACEA 화면에서 반복되는 세 가지 질문을 기준으로 비교했습니다.",
  "sh/zmpcnqls": "이번 달 유입·해결 차이",
  "sh/432dsfmh": "재조회",
  "sh/xw7i1ozm": "지금 막힌 상태·유형",
  "sh/wvyhsjy1": "재필터",
  "sh/atgzq9gb": "SLA 위험과 최근 근거",
  "sh/9s7yx4zq": "티켓별",
  "sh/m5wzm9gz": "워크스페이스",
  "sh/tori98zu": "한 필터 기준",
  "sh/s3ih03y9": "요약 → 근거 → 원문",
  "sh/s7q1w76l": "같은 원천을 유지하면서 재조회와 수기 합산을 줄입니다.",

  "sh/mlc3e9k3": "OPERATING MODEL",
  "sh/sb298bqd": "JIRA는 기록 시스템, 워크스페이스는 운영 판단 레이어입니다",
  "sh/i50r2h8v": "07",
  "sh/n2ds7q90": "JIRA",
  "sh/32h0rah4": "TACEA 원천\n이슈·상태·SLA",
  "sh/poz2tkza": "수집·정규화",
  "sh/onq1kfip": "프로젝트 전체\n유형·기간 기준",
  "sh/qp8jm50v": "운영 화면",
  "sh/dsz2xkz6": "요약·추세\nSLA·파트너",
  "sh/zu1kzuhc": "후속 조치",
  "sh/yt8jqp0r": "JIRA 원문\n보고서·파일",
  "sh/apc3itkz": "원천을 복제하지 않고, 전사 공통 질문에 맞는 읽기 모델을 제공합니다.",
  "sh/vql4ry1k": "프로젝트 전체 기준",
  "sh/wru5k325": "JIRA 직접 연결",
  "sh/xs3mtojq": "권한·자격정보 보호",

  "sh/c7a5srm9": "DECISION",
  "sh/ju90be1w": "전사 확대 여부는\n이 세 지표로 판단하면 됩니다",
  "sh/t0rihojy": "답변까지 걸린 시간",
  "sh/szih8jid": "운영 질문 제시 → 근거 화면 확인",
  "sh/hobiloja": "화면·필터 전환 수",
  "sh/gn21c3ip": "JIRA 재조회·티켓 이동·수기 합산",
  "sh/4ja54rmx": "결과 재사용성",
  "sh/pkjmxwni": "보고서 생성·공유·원문 추적",
  "sh/rm14zm5o": "제안: 2개 부서의 동일 업무를 JIRA 기준선과 비교해 2주간 측정 후 확대 결정"
};

for (const [id, value] of Object.entries(edits)) rewrite(presentation, id, value);

const roadmapEdits = {
  "sh/snmx8fu1": "IMPLEMENTATION PLAN",
  "sh/6xsj650v": "AI 연동·계정별 사용자 정의·팀별 요구사항을 순차 구현합니다",
  "sh/gnulcfix": "08",
  "sh/vm1kjahc": "PHASE 1",
  "sh/wrq10vit": "AI 연동 고도화",
  "sh/xsz29gje": "업무 효율성 개선\n업무 요약·후속 조치 추천\n일부 기능 완료",
  "sh/cza5onil": "PHASE 2",
  "sh/be14fi10": "계정별 대시보드",
  "sh/qdsnmd0f": "컴포넌트 분리\n사용자 정의 배치·표시\n계정 설정 저장",
  "sh/k3u5s7ih": "PHASE 3",
  "sh/z214j21w": "팀별 요구사항",
  "sh/y1snqx0b": "팀별 지표·업무 흐름 적용\n공통 컴포넌트 재사용\n단계별 요구사항 반영",
  "sh/9836pcjy": "현재 기능을 기반으로 확장",
  "sh/87u5w7it": "일부 완료 → 계정별 개인화 → 팀별 확장"
};

for (const [id, value] of Object.entries(roadmapEdits)) rewriteRoadmap(presentation, id, value);

await replaceImage(
  presentation,
  "im/vypo3yts",
  `${workspace}/jira-current-issues.jpg`,
  "현재 운영 JIRA TACEA 업무 검색과 선택 이슈 상세 화면"
);
await replaceImage(
  presentation,
  "im/jmx07654",
  `${workspace}/workspace-current-dashboard.jpg`,
  "현재 배포 워크스페이스 대시보드의 유형 필터, 요약 카드, 월별 추세"
);
await replaceImage(
  presentation,
  "im/mpofuhk3",
  `${workspace}/workspace-current-sla.jpg`,
  "현재 배포 워크스페이스 SLA 대시보드의 티켓과 최근 댓글 펼침 화면"
);

const notes = [
  [
    "오프닝: JIRA 대체가 아니라, 현재 JIRA 데이터를 운영 판단에 맞게 재구성한 화면이라는 점을 먼저 설명한다.",
    "근거 없는 시간 절감률은 사용하지 않고, 이후 슬라이드에서 실제 화면과 단계 수로 비교한다.",
    "",
    "[Sources]",
    "- https://seculayer.atlassian.net/issues/?jql=project%20%3D%20TACEA%20ORDER%20BY%20updated%20DESC",
    "- http://10.1.43.100/",
    "- C:/Users/user/Desktop/project/Auto_Reports/README.md"
  ],
  [
    "현재 로그인된 JIRA TACEA 업무 검색 화면을 2026-08-31에 직접 확인했다.",
    "화면에는 TACEA 1,000+건, 50건 결과, 선택 티켓 상세, 담당 및 SLA 패널이 동시에 보인다.",
    "개별 티켓 확인 강점과 운영 집계 시 반복 필터가 필요한 지점을 구분해 설명한다.",
    "",
    "[Sources]",
    "- https://seculayer.atlassian.net/issues/?jql=project%20%3D%20TACEA%20ORDER%20BY%20updated%20DESC",
    "- Current JIRA screenshot captured from the authenticated internal browser on 2026-08-31"
  ],
  [
    "현재 배포 화면에서 요청 유형 7/7, 생성 966, 해결 865, 미완료 130, 상태별 대기 수치와 월별 차트를 확인했다.",
    "수치는 2026-08-31 화면 스냅샷이며 운영 성과 개선률을 뜻하지 않는다.",
    "",
    "[Sources]",
    "- http://10.1.43.100/",
    "- C:/Users/user/Desktop/project/Auto_Reports/frontend/src/presentation/pages/DashboardPage.tsx",
    "- C:/Users/user/Desktop/project/Auto_Reports/frontend/src/presentation/hooks/useDashboardData.ts",
    "- Current deployed workspace screenshot captured on 2026-08-31"
  ],
  [
    "단계 비교는 현재 보이는 UI를 기준으로 동일한 운영 질문에 답하는 조작 단위를 정리한 것이다.",
    "JIRA는 필터, 결과 탐색, 티켓 상세, 재집계, 보고 작성이 필요하고 워크스페이스는 유형·기간 선택 후 카드·차트에서 근거로 내려간다.",
    "실측 시간 절감 수치는 아직 주장하지 않는다.",
    "",
    "[Sources]",
    "- https://seculayer.atlassian.net/issues/?jql=project%20%3D%20TACEA%20ORDER%20BY%20updated%20DESC",
    "- http://10.1.43.100/",
    "- C:/Users/user/Desktop/project/Auto_Reports/frontend/src/presentation/pages/DashboardPage.tsx"
  ],
  [
    "현재 SLA 대시보드는 티켓별 최근 댓글 최대 5개를 행 아래에서 펼치고 JIRA 원문 링크를 유지한다.",
    "발표에서는 댓글 내용 자체보다 티켓 이동 없이 최신 근거를 훑는 흐름을 보여준다.",
    "",
    "[Sources]",
    "- http://10.1.43.100/sla-dashboard",
    "- https://seculayer.atlassian.net/issues/?jql=project%20%3D%20TACEA%20ORDER%20BY%20updated%20DESC",
    "- C:/Users/user/Desktop/project/Auto_Reports/frontend/src/presentation/pages/SlaDashboardPage.tsx",
    "- C:/Users/user/Desktop/project/Auto_Reports/frontend/src/presentation/components/sla/SlaIssueActivityTable.tsx",
    "- Current deployed SLA screenshot captured on 2026-08-31"
  ],
  [
    "비교 기준은 화면 개수 자체가 아니라 반복 운영 질문에 답하기 위한 재조회, 재필터, 티켓별 이동 여부다.",
    "워크스페이스는 동일한 유형·기간 범위를 카드, 차트, 상세 목록에 적용하고 JIRA 원문으로 연결한다.",
    "",
    "[Sources]",
    "- https://seculayer.atlassian.net/issues/?jql=project%20%3D%20TACEA%20ORDER%20BY%20updated%20DESC",
    "- http://10.1.43.100/",
    "- http://10.1.43.100/sla-dashboard"
  ],
  [
    "JIRA를 시스템 오브 레코드로 유지하고, 애플리케이션이 프로젝트 전체 기준으로 읽어 운영 화면을 구성하는 모델을 설명한다.",
    "이 슬라이드는 대체가 아니라 읽기·판단 레이어의 역할 분리를 보여준다.",
    "",
    "[Sources]",
    "- C:/Users/user/Desktop/project/Auto_Reports/README.md",
    "- C:/Users/user/Desktop/project/Auto_Reports/backend/docs/01_architecture.md",
    "- C:/Users/user/Desktop/project/Auto_Reports/frontend/src/app/router.tsx"
  ],
  [
    "향후 구현 계획은 현재 기능을 기반으로 AI 고도화, 계정별 개인화, 팀별 확장의 순서로 제시한다.",
    "'일부 기능 완료'는 사용자가 제공한 현재 상태 표현이며, 독립적으로 측정한 완료율이나 일정 약속이 아니다.",
    "컴포넌트 분리를 통해 계정별 배치·표시 설정을 저장하고, 공통 컴포넌트를 재사용해 팀별 지표와 업무 흐름을 단계적으로 반영한다.",
    "",
    "[Sources]",
    "- User-provided implementation priorities on 2026-08-31"
  ],
  [
    "전사 확대 판단은 시간, 화면·필터 전환, 결과 재사용성을 동일 업무에서 전후 측정하는 방식으로 제안한다.",
    "2개 부서와 2주 기간은 의사결정을 위한 파일럿 제안이며 현재 성과 수치가 아니다.",
    "",
    "[Sources]",
    "- Internal pilot measurement proposal based on the current JIRA and workspace workflows",
    "- https://seculayer.atlassian.net/issues/?jql=project%20%3D%20TACEA%20ORDER%20BY%20updated%20DESC",
    "- http://10.1.43.100/"
  ]
];

for (let index = 0; index < notes.length; index += 1) {
  const speakerNotes = presentation.slides.getItem(index).speakerNotes;
  speakerNotes.textFrame.setText(notes[index].join("\n"));
  speakerNotes.setVisible(true);
}

await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(layoutDir, { recursive: true });

for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${renderDir}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${layoutDir}/${stem}.layout.json`, await layout.text(), "utf8");
}

await writeBlob(
  `${workspace}/final-montage.webp`,
  await presentation.export({ format: "webp", montage: true, scale: 1 })
);

const finalInspect = await presentation.inspect({
  kind: "deck,slide,textbox,shape,image,table,chart,notes,layout",
  include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,alt,isPlaceholder,placeholders",
  maxChars: 60000,
});
await fs.writeFile(`${workspace}/final-inspect.ndjson`, finalInspect.ndjson, "utf8");

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);
process.stdout.write(JSON.stringify({ output, slideCount: presentation.slides.items.length }, null, 2));
