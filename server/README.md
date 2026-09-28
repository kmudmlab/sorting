# Sort Lab 제출 서버

Google Apps Script V8 웹 앱입니다. `Code.gs`는 제출 처리, `grader.js`는 제한된 Python AST 실행기입니다.
Skulpt 1.2.0은 구문 분석에만 사용하며 학생 소스를 JavaScript로 컴파일하거나 eval하지 않습니다.
서버의 고정 정렬 절차와 테스트 입력을 사용해 정확성과 연산 예산을 검사합니다.
입력 소스 12,000자, AST 2,500개, 재귀 100회, 실행기 연산 예산, 전체 채점 20초 제한을 둡니다.
저장은 FormApp만 사용합니다. Google Cloud 유료 서비스나 결제 수단은 연결하지 않습니다.
Apps Script 할당량을 초과하면 실행이 실패하며 자동 유료 전환은 없습니다.

## 빌드 / 검증

이 폴더를 sorting 저장소의 `server/`에 두고 실행합니다.

```sh
python3 server/build_server.py
python3 server/make_test_cases.py
node server/test_grader.cjs
node server/test_submission.cjs
```

`build_server.py`는 부모 폴더의 assignment_engine.py에서 교사용 고정 코드와 결정적 테스트 입력을 추출합니다.
`Server.gs`가 라이선스·파서·입력·실행기·제출 처리를 묶은 배포 파일입니다.
Apps Script 편집기의 Code.gs 전체를 Server.gs로 교체해 저장한 뒤 기존 웹 앱 배포를 새 버전으로 갱신합니다.
웹 앱은 소유자 계정으로 실행하고 모든 사용자의 접속을 허용합니다. 함수 소스 외에 클라이언트 점수는 신뢰하지 않습니다.
Google Form의 응답자 일반 액세스는 제한됨으로 설정하고 소유자 외 응답자를 추가하지 않습니다. 응답받기는 켜 두어 서버의 저장을 허용하며 응답 수정·공개 요약은 허용하지 않습니다.
제출 서버의 Form ID를 바꾸거나 응답 문항명을 바꾸면 Code.gs의 매핑도 변경해야 합니다.
폼과 연결 시트의 공유는 비공개를 유지합니다.

클라이언트 설정은 부모 폴더의 submission-api.json입니다. URL 갱신 후 build_assignments.py를 실행합니다.
ORIGINS는 공개 사이트와 개발용 127.0.0.1:8765만 포함합니다. 이 값은 iframe 메시지 검증용이며 사용자 인증을 대신하지 않습니다.
학번·이름은 자가 입력입니다. 학생 계정 인증은 구현하지 않았습니다.
서버는 임의 파일/URL/OS 접근 기능을 학생 코드에 제공하지 않습니다.

검증용 TEST2026 응답은 실제 학생 성적과 구분해 관리하세요.
