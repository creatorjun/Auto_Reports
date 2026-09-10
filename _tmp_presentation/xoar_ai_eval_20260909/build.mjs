// _tmp_presentation/xoar_ai_eval_20260909/build.mjs
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
import { Presentation, PresentationFile, FileBlob } from '@oai/artifact-tool';
import { samples, ticketsA, ticketsB, sources } from './evidence.mjs';

const ROOT='C:/Users/user/Desktop/project/Auto_Reports';
const TMP=path.join(ROOT,'_tmp_presentation/xoar_ai_eval_20260909');
const OUT=path.join(ROOT,'output/xoar_ai_eval_20260909');
const SKILL='C:/Users/user/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const PY='C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const { finalizePresentation, applyPresentationChartFont }=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const P=Presentation.create({slideSize:{width:1600,height:900}});
const C={bg:'#F5F7FA',navy:'#102638',ink:'#183246',muted:'#566D7D',blue:'#126A94',teal:'#087C7A',orange:'#B45326',line:'#DCE4EA',white:'#FFFFFF'};
const FONT='Malgun Gothic';
const tableOwners=[],chartOwners=[];
const counts=Object.fromEntries(['TP','FP','TN','FN'].map(k=>[k,samples.filter(s=>s.outcome===k).length]));
assert.deepEqual(counts,{TP:10,FP:6,TN:4,FN:0});
assert.equal(samples.length,20);
assert.equal(new Set([...ticketsA,...ticketsB].map(x=>x[0])).size,20);
assert(samples[12].raw.includes('7\\*7'));
assert(samples[14].raw.includes('ldap\\://'));
const metrics={accuracy:(counts.TP+counts.TN)/20,recall:counts.TP/(counts.TP+counts.FN),precision:counts.TP/(counts.TP+counts.FP),fpr:counts.FP/(counts.FP+counts.TN),specificity:counts.TN/(counts.FP+counts.TN),f1:2*counts.TP/(2*counts.TP+counts.FP+counts.FN)};

function text(s,value,x,y,w,h,size=30,color=C.ink,bold=false,align='left',font=FONT){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=value;
  sh.text.style={typeface:font,fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};
  return sh;
}
function notes(s,value){s.speakerNotes.textFrame.setText(value);}
function slide(title,sub=''){
  const s=P.slides.add();s.background.fill=C.bg;
  text(s,title,72,52,1456,78,48,C.ink,true);
  if(sub)text(s,sub,72,140,1456,72,27,C.muted);
  text(s,String(P.slides.items.length).padStart(2,'0'),1460,852,68,24,18,C.muted,false,'right');
  return s;
}
function table(s,values,x,y,widths,rowHeights,size=27){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:widths.reduce((a,b)=>a+b),height:rowHeights.reduce((a,b)=>a+b),columnWidths:widths,values});
  t.borders.assign({style:'solid',fill:C.line,width:1});
  for(let r=0;r<values.length;r++){
    t.rows[r].height=rowHeights[r];
    for(let c=0;c<values[0].length;c++){
      const cell=t.getCell(r,c);
      cell.fill=r===0?C.navy:(r%2?C.white:'#EBF0F4');
      cell.text.style={typeface:FONT,fontSize:size,color:r===0?C.white:C.ink,bold:r===0,autoFit:'none',verticalAlignment:'middle',insets:{left:14,right:14,top:8,bottom:8}};
    }
  }
  tableOwners.push(P.slides.items.indexOf(s)+1);
  return t;
}
function note(s,value,y=785){text(s,value,72,y,1456,58,24,C.muted);}
function paragraph(s,label,body,y){
  text(s,label,72,y,350,52,32,C.blue,true);
  text(s,body,450,y,1078,90,30,C.ink);
}
function resultColor(result){return result==='FP'?C.orange:result==='TP'?C.teal:C.muted;}
function sampleTable(title,subset,sub){
  const s=slide(title,sub);
  const typeBreaks={'CRLF / 헤더 삽입':'CRLF\n헤더 삽입','XML 외부 엔터티':'XML 외부\n엔터티','서버 템플릿 삽입 모사':'템플릿 삽입\n모사','시간 지연 SQL 삽입':'시간 지연\nSQL 삽입'};
  const values=[['ID','로그 유형','원값','모델','평가','수동 분류 근거'],...subset.map(r=>[r.id,typeBreaks[r.type]??r.type,r.score.toFixed(2),r.predicted,r.outcome,r.reason])];
  const t=table(s,values,72,228,[80,220,100,100,90,866],[58,94,94,94,94,94],25);
  subset.forEach((r,i)=>{t.getCell(i+1,4).text.style={typeface:FONT,fontSize:27,bold:true,color:resultColor(r.outcome)};});
  note(s,subset[0].truth==='정상'?'정상 = 제공된 요청 범위에서 공격 근거가 없는 대조 로그. 파일 내용·권한·응답까지 검증한 판정은 아님.':'공격 = 공격 의도·모사 패턴 기준. 취약점 존재, 서버 실행 또는 침해 성공을 의미하지 않음.');
  notes(s,'출처: 사용자 제공 20개 HTTP 요청과 모델 출력. S01~S20은 제공 순서로 부여한 보고서 식별자이며 티켓 ID와 매핑되지 않았다.\n'+subset.map(r=>`${r.id} 수동=${r.truth} 모델=${r.predicted} 화면값=${r.score.toFixed(2)} ${r.outcome}\n${r.raw}`).join('\n\n')+'\n분류 기준 참고:\n'+Object.values(sources).join('\n'));
  return s;
}

{
 const s=P.slides.add();s.background.fill=C.navy;
 text(s,'eyeCloudXOAR',72,70,1456,75,50,'#77CEE8',true);
 text(s,'검색 기반 AI 정오탐 모델\n샘플로그 검증 결과',72,250,1456,190,76,C.white,true);
 text(s,'LogGenerator 연동 및 AI TEST 플레이북 실행 기록',76,490,1430,65,34,'#C9DFEA');
 text(s,'테스트 기록  2026.09.08\n대상 서버  10.1.42.80',76,687,1420,96,29,'#C9DFEA');
 notes(s,'사용자가 제공한 기존 테스트 과정과 결과를 정리한 자료. 작성일 2026-09-09. 현재 세션에서 서버 재전송·등록·플레이북 실행은 수행하지 않았다. 표기한 서버와 이름은 사용자 제공 정보다.');
}
{
 const s=slide('공격 10건을 탐지했고 정상 6건을 공격으로 판정','공격 의도·모사 10건, 정상 대조군 10건에 대한 사후 수동 검토 결과');
 [['70.0%','전체 정확도','20건 중 14건 정분류',C.blue],['100.0%','공격 탐지율','공격 모사 10건 모두 탐지',C.teal],['62.5%','공격 판정 정밀도','공격 판정 16건 중 10건 적중',C.orange]].forEach((v,i)=>{
   const x=72+i*495;text(s,v[0],x,276,455,116,86,v[3],true);text(s,v[1],x,415,455,56,32,C.ink,true);text(s,v[2],x,484,455,85,29,C.muted);
 });
 text(s,'정상 대조군 오탐률 60.0%  (6 / 10)',72,653,1456,68,41,C.orange,true);
 note(s,'이 수치는 제공된 20건의 결과이며, 학습·평가 데이터 분리 여부와 운영 환경의 일반화 성능은 확인되지 않았다.');
 notes(s,'산출 근거: TP=10, FP=6, TN=4, FN=0. Accuracy=(TP+TN)/20=70%; TPR=TP/(TP+FN)=100%; Precision=TP/(TP+FP)=62.5%; FPR=FP/(FP+TN)=60%. 공격 라벨은 공격 의도·모사 기준이다.');
}
{
 const s=slide('평가 대상과 수동 분류 기준','화면의 공격·정상 판정과 독립적인 기준으로 20개 요청을 다시 분류');
 paragraph(s,'평가 단위','제공 순서대로 S01~S20을 부여한 HTTP 요청 20건.\n각 요청의 화면 값과 공격·정상 판정을 그대로 비교한다.',246);
 paragraph(s,'정상 대조군','S01~S10은 제공된 요청 범위에서 공격 구문이 없는 대조군 10건.\n업로드 파일 본문, 로그인 응답, 반복 행위는 확인되지 않았다.',390);
 paragraph(s,'공격 모사군','S11~S20은 삽입, 경로 순회, 외부 접근 등을 시도·모사하는 10건.\n실제 취약점 악용 성공 여부는 이 자료의 평가 대상에 포함하지 않는다.',534);
 note(s,'원문의 퍼센트 인코딩, 역슬래시, 개행 이스케이프와 Referer의 Markdown 링크 표기를 보존한다.',766);
 notes(s,'정상 판정은 보안 정책 적합성 또는 무해성을 인증하는 의미가 아니다. 공격 판정은 공격 의도·모사 패턴 기준이다. 192.0.2.0/24는 RFC 5737의 문서용 TEST-NET-1 주소.\n'+sources.rfc);
}
{
 const s=slide('기존 테스트의 연동 과정','사용자 설명에 따른 구성 명칭과 처리 순서');
 table(s,[['단계','구성 요소','테스트 과정'],['01','LogGenerator','학습 후 판정을 확인할 샘플 로그를 선택하고 전송'],['02','10.1.42.80','테스트 서버의 로그 수신 경로로 전달'],['03','LogGenerator 파서','수신 로그를 파싱하고 AI 입력에 필요한 payload를 추출'],['04','일반 이벤트  AITEST','로그를 일반 이벤트로 연동'],['05','플레이북 티켓  AI TEST','AI 정오탐 분석을 실행하고 피드백 저장 단계로 진행']],72,238,[100,450,906],[58,90,90,90,90,90],29);
 note(s,'대상 서버와 구성 명칭은 제공 내용 기준. 실제 전송 프로토콜·포트·EPS·수신 건수는 제공 자료에 없다.');
 notes(s,'사용자 설명을 재구성한 기존 테스트 흐름. 현재 세션에서 서버 연결, 로그 전송, 파서/이벤트 등록은 수행하지 않았다. LogGenerator README.md 264–275행은 프로토콜 선택, Host/Port 설정, 카탈로그·샘플 선택, IP/날짜, EPS, 전송 및 총 로그 수 확인 순서를 설명한다.');
}
{
 const s=slide('파서와 이벤트·티켓 연계','연동 이름과 분석 입력을 구분해 테스트 조건을 재현');
 paragraph(s,'수신 로그 파싱','등록 이름  LogGenerator\nHTTP 요청이 포함된 payload와 이벤트 연동 필드를 추출한다.',239);
 paragraph(s,'이벤트 및 티켓','일반 이벤트  AITEST\n플레이북 티켓  AI TEST',380);
 paragraph(s,'AI 분석 입력','티켓의 payload를 정오탐 분석 요청에 전달한다.\n정답 라벨과 보고서용 S번호는 모델 입력에서 분리한다.',520);
 note(s,'파서 정규식, 장비 매핑, 이벤트 조건식, 활성 모델 버전 및 실제 입력 전문은 별도 설정 증거가 필요하다.',755);
 notes(s,'제공 정보: LogGenerator 파서, AITEST 일반 이벤트, AI TEST 티켓. 현재 설정값을 직접 조회하지 않았다. eyeCloudXOAR-playbook-guide_v4_ko.pdf p74, p77–80: 정오탐 분석과 payload, 결과 및 수동 피드백. 활성 알고리즘/모델 입력 매핑은 제공 자료에서 확인되지 않았다.');
}
{
 const s=slide('AI TEST 플레이북 실행 화면','제공 화면의 노드 이름과 자동·수동 실행 모드');
 const bytes=new Uint8Array(await fs.readFile('C:/Users/user/AppData/Local/Temp/codex-clipboard-b275dc3b-4de1-4eb9-9aa0-9cb439990e1d.png'));
 s.images.add({blob:bytes,contentType:'image/png',alt:'사용자 제공 AI TEST 플레이북 화면. 정오탐 분석 요청 Auto, 정오탐 피드백 데이터 저장 Manual, End',fit:'contain',position:{left:72,top:244,width:1456,height:194}});
 text(s,'정오탐 분석 요청',72,493,675,52,36,C.blue,true);
 text(s,'Auto\n분석 요청을 자동 실행하는 노드',72,560,675,103,31,C.ink);
 text(s,'정오탐 피드백 데이터 저장',840,493,688,52,36,C.teal,true);
 text(s,'Manual\n사용자 피드백을 처리하는 수동 단계',840,560,688,103,31,C.ink);
 note(s,'티켓에는 이 단계의 상태가 표시된다. 제공 화면과 목록만으로 피드백 저장 완료 또는 End 도달을 확정할 수 없다.',762);
 notes(s,'출처: 사용자 첨부 원본 PNG codex-clipboard-b275dc3b-4de1-4eb9-9aa0-9cb439990e1d.png. 화면 #3 이름은 말줄임 처리되어 있으므로 전체 명칭은 사용자 제공 티켓 상태 “정오탐 피드백 데이터 저장”을 따른다. 매뉴얼의 다른 명칭으로 교체하지 않았다. 현재 화면은 저장 완료 또는 재학습 완료의 증거가 아니다.');
}
{
 const s=slide('AI TEST 티켓 20건의 실행 기록','2026.09.08  /  공통 담당자: 미지정  /  상태: 분석/대응 ( 정오탐 피드백 데이터 저장 )');
 text(s,'제공 목록 A   14:18:13 ~ 14:19:07',72,225,710,48,30,C.blue,true);
 text(s,'제공 목록 B   16:54:54 ~ 16:55:39',832,225,696,48,30,C.blue,true);
 table(s,[['티켓 ID','시각'],...ticketsA],72,280,[520,180],[48,...Array(10).fill(44)],23);
 table(s,[['티켓 ID','시각'],...ticketsB],832,280,[516,180],[48,...Array(10).fill(44)],23);
 note(s,'티켓과 개별 로그의 1:1 대응은 미제공. 목록 B의 00000453 미표시만으로 수집 누락이나 실행 실패를 판단하지 않는다.',785);
 notes(s,'출처: 사용자 제공 티켓 목록 전문. 각 티켓의 제목 AI TEST, 담당자 미지정, 상태 분석/대응 ( 정오탐 피드백 데이터 저장 ). 날짜는 모두 2026-09-08. 두 목록을 정상군/공격군에 임의 매핑하지 않았다.\n'+[...ticketsA,...ticketsB].map(t=>t.join(' ')).join('\n'));
}
{
 const s=slide('혼동행렬과 성능 지표','양성 클래스 = 공격 의도·모사 로그  /  정답 = 본 보고서의 수동 분류');
 table(s,[['수동 분류','모델 공격','모델 정상','합계'],['공격','TP 10','FN 0','10'],['정상','FP 6','TN 4','10'],['합계','16','4','20']],72,270,[200,180,180,140],[65,110,110,75],30);
 table(s,[['지표','계산','결과'],['전체 정확도','14 / 20','70.0%'],['공격 탐지율','10 / 10','100.0%'],['공격 판정 정밀도','10 / 16','62.5%'],['정상 오탐률','6 / 10','60.0%'],['정상 판별률','4 / 10','40.0%'],['F1 점수','20 / 26','76.9%']],842,247,[310,180,196],[58,69,69,69,69,69,69],28);
 note(s,'FP: 정상 로그를 공격으로 판정한 6건. FN: 공격 로그를 정상으로 판정한 건수는 이번 표본에서 0건.');
 notes(s,'독립 계산: '+JSON.stringify({counts,metrics})+'\nAccuracy=(TP+TN)/(TP+TN+FP+FN). Recall=TP/(TP+FN). Precision=TP/(TP+FP). FPR=FP/(FP+TN). Specificity=TN/(TN+FP). F1=2TP/(2TP+FP+FN). 혼동행렬 정의는 eyeCloudXOAR-playbook-guide_v4_ko.pdf p74·77–80과 부합한다.');
}
sampleTable('정상 로그 판정 근거  S01~S05',samples.slice(0,5),'수동 정상 5건 중 모델 오탐 3건');
sampleTable('정상 로그 판정 근거  S06~S10',samples.slice(5,10),'수동 정상 5건 중 모델 오탐 3건');
sampleTable('공격 로그 판정 근거  S11~S15',samples.slice(10,15),'공격 의도·모사 기준 5건 모두 공격으로 판정');
sampleTable('공격 로그 판정 근거  S16~S20',samples.slice(15,20),'공격 삽입·경로 순회 패턴 5건 모두 공격으로 판정');
{
 const s=slide('화면의 개별 ‘정확도’ 값 해석','값의 산식은 미제공. 확률·유사도 여부는 미확인이며, 데이터셋 정확도 70.0%는 별도로 계산');
 const chart=s.charts.add('bar',{position:{left:72,top:237,width:1456,height:428},categories:samples.map(s=>s.id),series:[{name:'화면 값',values:samples.map(s=>s.score),valuesFormatCode:'0.00',points:samples.map((s,idx)=>({idx,fill:resultColor(s.outcome)}))}],hasLegend:false,barOptions:{direction:'column',grouping:'clustered',gapWidth:58},xAxis:{textStyle:{typeface:FONT,fontSize:22,fill:C.ink},line:{fill:C.line,width:1},majorGridlines:null},yAxis:{min:0,max:1.1,majorUnit:0.2,numberFormatCode:'0.0',textStyle:{typeface:FONT,fontSize:22,fill:C.muted},majorGridlines:{fill:C.line,width:1}},dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:FONT,fontSize:22,fill:C.ink}},chartFill:C.bg,plotAreaFill:C.bg});
 applyPresentationChartFont(chart,{fontFamily:FONT});chartOwners.push(P.slides.items.length);
 text(s,'주황: FP    청록: TP    회색: TN',72,689,1456,40,26,C.muted);
 text(s,'0.31도 공격, 0.39는 정상. 0.5 기준으로 판정을 재계산할 근거가 없다.',72,750,1456,68,32,C.ink,true);
 notes(s,'개별 화면 값은 사용자 명칭 “정확도”를 보존한다. 산식이 제공되지 않았으므로 확률, 신뢰도, 유사도로 단정하지 않는다. 각 값의 단순 평균은 모델 정확도가 아니다. 점수와 판정은 사용자 제공 원값이며 차트 데이터는 편집 가능한 리터럴 값이다.\n'+samples.map(s=>`${s.id} ${s.score.toFixed(2)} ${s.predicted} ${s.outcome}`).join('\n'));
}
{
 const s=slide('해석의 한계와 후속 검증','이번 표본에서는 정상 요청의 오탐 감소가 주요 개선 과제');
 paragraph(s,'오탐 6건의 재검토','S01·S03·S05·S06·S08·S10을 정상 피드백 후보로 검토한다.\n어휘만으로 공격을 추정했는지는 모델 내부 근거가 있어야 확인할 수 있다.',230);
 paragraph(s,'입력과 결과 추적','전송 원문, 파서 payload, 이벤트 ID, 티켓 ID, AI 입력을 연결한다.\n모델 버전·전처리·실행 시각을 함께 남겨 같은 조건으로 재평가한다.',375);
 paragraph(s,'평가 데이터 분리','학습에 사용하지 않은 정상·공격 로그로 다시 평가한다.\n이번 20건만으로 학습 효과나 운영 환경의 성능 개선을 입증할 수 없다.',520);
 note(s,'피드백 저장 완료와 재학습 실행·활성화는 별도 증거가 필요하다. 정상과 공격을 함께 재검증해 오탐·미탐 변화를 확인한다.',770);
 notes(s,'권고는 관측 결과(FP 6건)에 대한 후속 검증 제안이며 이미 수행했다는 의미가 아니다. eyeCloudXOARforAll-in-one_v4_ko.pdf p263–266은 Label 변경, 임시저장, Feedback, 강화학습의 별도 절차를 설명한다. 학습/평가 분리 여부와 활성 모델 메타데이터는 사용자 제공 자료에서 확인되지 않았다.');
}

function wrapRaw(raw,max=92){
 const tokens=raw.split(/(\\r\\n)/);const out=[];let line='';
 for(let i=0;i<tokens.length;i++){
  let token=tokens[i];
  if(token==='\\r\\n'){line+=token;out.push(line);line='';continue;}
  while(token.length){const room=max-line.length;if(room<=0){out.push(line);line='';continue;}line+=token.slice(0,room);token=token.slice(room);if(token.length){out.push(line);line='';}}
 }
 if(line)out.push(line);return out.join('\n');
}
for(let n=0;n<20;n+=2){
 const pair=samples.slice(n,n+2),s=slide(`원문 부록  ${pair[0].id} · ${pair[1].id}`,'제공 문자열 전체. 읽기용 줄바꿈을 추가했으며 원문의 개행·인코딩·이스케이프 표기를 유지');
 for(let i=0;i<2;i++){
   const r=pair[i],y=231+i*302;
   text(s,`${r.id}   ${r.type}`,72,y,880,44,30,C.blue,true);
   text(s,`수동 ${r.truth}   화면 ${r.score.toFixed(2)}   모델 ${r.predicted}   ${r.outcome}`,950,y,578,44,27,resultColor(r.outcome),true,'right');
   const rawText=wrapRaw(r.raw,96);
   const lines=rawText.split('\n').length;
   text(s,rawText,72,y+61,1456,224,lines>6?23:25,C.ink,false,'left','Consolas');
 }
 notes(s,'사용자 제공 원문을 보존했다. 슬라이드의 실제 줄바꿈은 가독성을 위한 것이며 원래의 전송 경계를 뜻하지 않는다. Literal \\r\\n을 제거하거나 실제 CRLF로 디코딩하지 않았다.\n\n'+pair.map(r=>`${r.id}\n${r.raw}\n화면 값=${r.score.toFixed(2)} 모델=${r.predicted} 수동=${r.truth} 결과=${r.outcome}`).join('\n\n'));
}
{
 const s=slide('근거 자료와 확인 범위','판정 근거, 계산 결과, 제품 동작 설명의 출처');
 paragraph(s,'직접 제공한 증거','HTTP 요청·화면 값·모델 판정 20건\nAI TEST 티켓 목록 20건과 플레이북 화면 1장',224);
 paragraph(s,'제품 동작 참고','LogGenerator 현재 README의 로그 전송 절차\neyeCloudXOAR v4 사용자 매뉴얼과 플레이북 가이드',363);
 paragraph(s,'공격 유형 기준','OWASP의 SQL·명령·XML·템플릿 삽입 및 경로 순회 자료\nApache Log4j 보안 공지, RFC 5737, Kubernetes Probe 문서',502);
 text(s,'확인 범위',72,665,350,48,32,C.blue,true);
 text(s,'제공된 기록의 사후 분석. 서버 수신, 설정 저장, 티켓별 로그 매핑,\n피드백 DB 반영과 재학습 완료는 직접 검증하지 않았다.',450,665,1078,102,30,C.ink);
 notes(s,'사용자 제공 자료: 이 대화의 20개 샘플 및 20개 티켓, 첨부 원본 PNG.\n로컬 자료: C:/Users/user/Desktop/project/LogGenerator/README.md 264–275행. C:/Users/user/Desktop/AI 서버/eyeCloudXOARforAll-in-one_v4_ko.pdf p263–269. C:/Users/user/Desktop/AI 서버/eyeCloudXOAR-playbook-guide_v4_ko.pdf p74·77–80.\n웹 1차 출처(2026-09-09 확인):\n'+Object.entries(sources).map(([key,url])=>`${key}: ${url}`).join('\n')+'\n이전 로컬 ai_model_detection_samples.json은 메서드·헤더·정상군이 현재 제공 데이터와 달라 평가에 대체 사용하지 않았다.');
}

await fs.mkdir(TMP,{recursive:true});await fs.mkdir(OUT,{recursive:true});
await fs.writeFile(path.join(TMP,'metrics.json'),JSON.stringify({counts,metrics},null,2));
await fs.writeFile(path.join(TMP,'evidence.json'),JSON.stringify(samples,null,2));
const candidate=path.join(TMP,'candidate.pptx');
await (await PresentationFile.exportPptx(P)).save(candidate);
await fs.writeFile(path.join(TMP,'presentation.proto.json'),JSON.stringify(P.toProto()));
const requirements={requiredNativeTableOwnerSlides:[...new Set(tableOwners)],requiredNativeChartOwnerSlides:chartOwners,materializeLiteralChartWorkbooks:true};
const finalPath=path.join(OUT,'eyeCloudXOAR_검색기반_AI_검증결과_20260908.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit',...requirements.requiredNativeTableOwnerSlides.flatMap(n=>['--require-native-table-slide',String(n)])],fontPolicy:{basis:'design',families:[FONT,'Consolas']},verifyArtifactToolImport:true,receiptPath:path.join(TMP,'validation-final.json'),...requirements});
console.log(JSON.stringify({slides:P.slides.items.length,finalPath:result.finalPath,findings:result.presentationLayout.findings,warnings:result.presentationLayout.warnings}));
if(!process.argv.includes('--skip-render')){
 const finalDeck=await PresentationFile.importPptx(await FileBlob.load(finalPath));
 await fs.mkdir(path.join(TMP,'render'),{recursive:true});
 for(let i=0;i<P.slides.items.length;i++){
   const b=await finalDeck.export({slide:finalDeck.slides.items[i],format:'png',scale:1});
   await fs.writeFile(path.join(TMP,'render',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await b.arrayBuffer()));
   console.log('Rendered '+(i+1));
 }
}
