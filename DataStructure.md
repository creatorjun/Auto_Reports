# DataStructure

> 생성: 2026-07-07 12:28:29  |  project: `TACEA`


======================================================================
## STEP 1 — Jira customfield 목록 (SLA 후보)
======================================================================

customfield 총 246개

### [customfield_11952] SLA 지연 여부
- schema.custom : `com.atlassian.jira.plugin.system.customfieldtypes:select`
- schema.type   : `option`

### [customfield_11038] 해결까지 시간
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_12118] QA 검토 SLA
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_11258] 해결 후 종료할 시간
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_10956] Quantify Time Spent (h)
- schema.custom : `read-only-number-issue-field`
- schema.type   : `number`

### [customfield_12455] [CHART] Time in Status
- schema.custom : `com.atlassian.jira.ext.charting:timeinstatus`
- schema.type   : `any`

### [customfield_12454] [CHART] Date of First Response
- schema.custom : `com.atlassian.jira.ext.charting:firstresponsedate`
- schema.type   : `datetime`

### [customfield_11589] 권한
- schema.custom : `com.atlassian.servicedesk.customer-context:sd-csm-entitlement`
- schema.type   : `array`

### [customfield_10802] 요청 언어
- schema.custom : `com.atlassian.servicedesk.servicedesk-lingo-integration-plugin:sd-request-language`
- schema.type   : `sd-request-lang`

### [customfield_12084] 할 일 SLA
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_12085] 연구소 대기 SLA
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_10203] 고객 요청 유형
- schema.custom : `com.atlassian.servicedesk:vp-origin`
- schema.type   : `sd-customerrequesttype`

### [customfield_10204] 기관
- schema.custom : `com.atlassian.servicedesk:sd-customer-organizations`
- schema.type   : `array`

### [customfield_10205] 만족
- schema.custom : `com.atlassian.servicedesk:sd-request-feedback`
- schema.type   : `sd-feedback`

### [customfield_10206] 만족률
- schema.custom : `com.atlassian.servicedesk:sd-request-feedback-date`
- schema.type   : `datetime`

### [customfield_11098] 감정
- schema.custom : `com.atlassian.servicedesk.sentiment:sd-sentiment`
- schema.type   : `array`

### [customfield_10200] 승인
- schema.custom : `com.atlassian.servicedesk.approvals-plugin:sd-approvals`
- schema.type   : `sd-approvals`

### [customfield_10202] 관계자 요청
- schema.custom : `com.atlassian.servicedesk:sd-request-participants`
- schema.type   : `array`

### [customfield_10317] 해결시간
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_10318] 최초 응답 시간
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_12051] SLA 지연 사유
- schema.custom : `com.atlassian.jira.plugin.system.customfieldtypes:select`
- schema.type   : `option`

### [customfield_12152] 최초 응답 SLA
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_12151] 해결 시간 SLA
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_11292] 개발 SLA
- schema.custom : `com.atlassian.servicedesk:sd-sla-field`
- schema.type   : `sd-servicelevelagreement`

### [customfield_12018] SLA 지연 책임 부서
- schema.custom : `com.atlassian.jira.plugin.system.customfieldtypes:select`
- schema.type   : `option`


======================================================================
## STEP 2 — get_sla_field_ids() 로직 결과
======================================================================

| field_id | field_name |
|---|---|
| `customfield_11038` | 해결까지 시간 |
| `customfield_12118` | QA 검토 SLA |
| `customfield_11258` | 해결 후 종료할 시간 |
| `customfield_11589` | 권한 |
| `customfield_10802` | 요청 언어 |
| `customfield_12084` | 할 일 SLA |
| `customfield_12085` | 연구소 대기 SLA |
| `customfield_10203` | 고객 요청 유형 |
| `customfield_10204` | 기관 |
| `customfield_10205` | 만족 |
| `customfield_10206` | 만족률 |
| `customfield_11098` | 감정 |
| `customfield_10200` | 승인 |
| `customfield_10202` | 관계자 요청 |
| `customfield_10317` | 해결시간 |
| `customfield_10318` | 최초 응답 시간 |
| `customfield_12152` | 최초 응답 SLA |
| `customfield_12151` | 해결 시간 SLA |
| `customfield_11292` | 개발 SLA |

======================================================================
## STEP 3 — 키워드 매칭 진단
======================================================================

- INITIAL\_KEYWORDS    : `['첫 응답', '초기 대응', 'First Response', 'Time to first response', 'Initial']`
- RESOLUTION\_KEYWORDS : `['해결', 'Resolution', 'Time to resolution', 'Time to close']`

| field_id | field_name | W15 초기대응 | W16 해결시간 |
|---|---|---|---|
| `customfield_11038` | 해결까지 시간 | ❌ | ✅ ['해결'] |
| `customfield_12118` | QA 검토 SLA | ❌ | ❌ |
| `customfield_11258` | 해결 후 종료할 시간 | ❌ | ✅ ['해결'] |
| `customfield_11589` | 권한 | ❌ | ❌ |
| `customfield_10802` | 요청 언어 | ❌ | ❌ |
| `customfield_12084` | 할 일 SLA | ❌ | ❌ |
| `customfield_12085` | 연구소 대기 SLA | ❌ | ❌ |
| `customfield_10203` | 고객 요청 유형 | ❌ | ❌ |
| `customfield_10204` | 기관 | ❌ | ❌ |
| `customfield_10205` | 만족 | ❌ | ❌ |
| `customfield_10206` | 만족률 | ❌ | ❌ |
| `customfield_11098` | 감정 | ❌ | ❌ |
| `customfield_10200` | 승인 | ❌ | ❌ |
| `customfield_10202` | 관계자 요청 | ❌ | ❌ |
| `customfield_10317` | 해결시간 | ❌ | ✅ ['해결'] |
| `customfield_10318` | 최초 응답 시간 | ❌ | ❌ |
| `customfield_12152` | 최초 응답 SLA | ❌ | ❌ |
| `customfield_12151` | 해결 시간 SLA | ❌ | ✅ ['해결'] |
| `customfield_11292` | 개발 SLA | ❌ | ❌ |

======================================================================
## STEP 4 — 최근 5개 이슈 raw SLA 필드 값
======================================================================

조회된 이슈: **5개**
```
project = TACEA AND issuetype IN ("인시던트", "개선", "CVE", "서비스 요청") AND created >= "-30d" ORDER BY created DESC
```

### TACEA-4540 | 개선 | 생성: 2026-07-06

**[customfield_11038] 해결까지 시간**
`null`

**[customfield_12118] QA 검토 SLA**
```json
{
  "id": "57",
  "name": "QA 검토 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224/sla/57"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11258] 해결 후 종료할 시간**
`null`

**[customfield_11589] 권한**
`null`

**[customfield_10802] 요청 언어**
```json
{
  "languageCode": "ko",
  "displayName": "한국어"
}
```

**[customfield_12084] 할 일 SLA**
```json
{
  "id": "55",
  "name": "할 일 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224/sla/55"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-06T18:02:13+0900",
        "jira": "2026-07-06T18:02:13.432+0900",
        "friendly": "어제 18:02",
        "epochMillis": 1783328533432
      },
      "stopTime": {
        "iso8601": "2026-07-07T10:01:40+0900",
        "jira": "2026-07-07T10:01:40.376+0900",
        "friendly": "오늘 10:01",
        "epochMillis": 1783386100376
      },
      "breachTime": {
        "iso8601": "2026-07-07T18:00:00+0900",
        "jira": "2026-07-07T18:00:00.000+0900",
        "friendly": "오늘 18:00",
        "epochMillis": 1783414800000
      },
      "breached": false,
      "goalDuration": {
        "millis": 28800000,
        "friendly": "8시간"
      },
      "elapsedTime": {
        "millis": 3700376,
        "friendly": "1시간 1분"
      },
      "remainingTime": {
        "millis": 25099624,
        "friendly": "6시간 58분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12085] 연구소 대기 SLA**
```json
{
  "id": "56",
  "name": "연구소 대기 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224/sla/56"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_10203] 고객 요청 유형**
```json
{
  "_links": {
    "jiraRest": "https://seculayer.atlassian.net/rest/api/2/issue/49224",
    "web": "https://seculayer.atlassian.net/servicedesk/customer/portal/1/TACEA-4540",
    "agent": "https://seculayer.atlassian.net/browse/TACEA-4540",
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224"
  },
  "requestType": {
    "_expands": [
      "field"
    ],
    "id": "88",
    "_links": {
      "self": "https://seculayer.atlassian.net/rest/servicedeskapi/servicedesk/1/requesttype/88"
    },
    "name": "개선 요청",
    "description": "개선 이슈 오픈(영업 본부의 검토가 필요한 이슈 및 솔루션의 개선이 필요한 이슈) - 화면설계서 필수 첨부 요망",
    "helpText": "양식에 맞지 않게 등록할 경우 안내 없이 반려 처리 될 수 있습니다.\n1개월 이상 답변 없으실 경우 임의로 종결 처리 할 수 있으니 참고 부탁드립니다.",
    "defaultName": "개선 요청",
    "issueTypeId": "10110",
    "serviceDeskId": "1",
    "portalId": "1",
    "groupIds": [
      "9"
    ],
    "icon": {
      "id": "11340",
      "_links": {
        "iconUrls": {
          "48x48": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/11340?size=large",
          "24x24": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/11340?size=small",
          "16x16": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/11340?size=xsmall",
          "32x32": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/11340?size=medium"
        }
      }
    }
  },
  "currentStatus": {
    "status": "이슈 리뷰 중",
    "statusCategory": "INDETERMINATE",
    "statusDate": {
      "iso8601": "2026-07-07T10:01:40+0900",
      "jira": "2026-07-07T10:01:40.376+0900",
      "friendly": "오늘 10:01",
      "epochMillis": 1783386100376
    }
  }
}
```

**[customfield_10204] 기관**
```json
[]
```

**[customfield_10205] 만족**
`null`

**[customfield_10206] 만족률**
`null`

**[customfield_11098] 감정**
```json
{
  "id": "2000",
  "name": "중립적"
}
```

**[customfield_10200] 승인**
`null`

**[customfield_10202] 관계자 요청**
```json
[]
```

**[customfield_10317] 해결시간**
`null`

**[customfield_10318] 최초 응답 시간**
`null`

**[customfield_12152] 최초 응답 SLA**
```json
{
  "id": "59",
  "name": "최초 응답 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224/sla/59"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-06T18:02:13+0900",
        "jira": "2026-07-06T18:02:13.432+0900",
        "friendly": "어제 18:02",
        "epochMillis": 1783328533432
      },
      "stopTime": {
        "iso8601": "2026-07-07T10:01:40+0900",
        "jira": "2026-07-07T10:01:40.376+0900",
        "friendly": "오늘 10:01",
        "epochMillis": 1783386100376
      },
      "breachTime": {
        "iso8601": "2026-07-07T14:00:00+0900",
        "jira": "2026-07-07T14:00:00.000+0900",
        "friendly": "오늘 14:00",
        "epochMillis": 1783400400000
      },
      "breached": false,
      "goalDuration": {
        "millis": 14400000,
        "friendly": "4시간"
      },
      "elapsedTime": {
        "millis": 3700376,
        "friendly": "1시간 1분"
      },
      "remainingTime": {
        "millis": 10699624,
        "friendly": "2시간 58분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12151] 해결 시간 SLA**
```json
{
  "id": "58",
  "name": "해결 시간 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224/sla/58"
  },
  "completedCycles": [],
  "ongoingCycle": {
    "startTime": {
      "iso8601": "2026-07-06T18:02:13+0900",
      "jira": "2026-07-06T18:02:13.432+0900",
      "friendly": "어제 18:02",
      "epochMillis": 1783328533432
    },
    "breachTime": {
      "iso8601": "2026-07-27T18:00:00+0900",
      "jira": "2026-07-27T18:00:00.000+0900",
      "friendly": "2026/07/27 18:00",
      "epochMillis": 1785142800000
    },
    "breached": false,
    "paused": false,
    "withinCalendarHours": false,
    "goalDuration": {
      "millis": 432000000,
      "friendly": "120시간"
    },
    "elapsedTime": {
      "millis": 10800000,
      "friendly": "3시간"
    },
    "remainingTime": {
      "millis": 421200000,
      "friendly": "117시간"
    }
  },
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11292] 개발 SLA**
```json
{
  "id": "54",
  "name": "개발 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49224/sla/54"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

### TACEA-4539 | 서비스 요청 | 생성: 2026-07-06

**[customfield_11038] 해결까지 시간**
`null`

**[customfield_12118] QA 검토 SLA**
```json
{
  "id": "57",
  "name": "QA 검토 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223/sla/57"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11258] 해결 후 종료할 시간**
`null`

**[customfield_11589] 권한**
`null`

**[customfield_10802] 요청 언어**
```json
{
  "languageCode": "ko",
  "displayName": "한국어"
}
```

**[customfield_12084] 할 일 SLA**
```json
{
  "id": "55",
  "name": "할 일 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223/sla/55"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-06T17:54:40+0900",
        "jira": "2026-07-06T17:54:40.306+0900",
        "friendly": "어제 17:54",
        "epochMillis": 1783328080306
      },
      "stopTime": {
        "iso8601": "2026-07-06T18:48:44+0900",
        "jira": "2026-07-06T18:48:44.759+0900",
        "friendly": "어제 18:48",
        "epochMillis": 1783331324759
      },
      "breachTime": {
        "iso8601": "2026-07-07T17:54:40+0900",
        "jira": "2026-07-07T17:54:40.306+0900",
        "friendly": "오늘 17:54",
        "epochMillis": 1783414480306
      },
      "breached": false,
      "goalDuration": {
        "millis": 28800000,
        "friendly": "8시간"
      },
      "elapsedTime": {
        "millis": 319694,
        "friendly": "5분"
      },
      "remainingTime": {
        "millis": 28480306,
        "friendly": "7시간 54분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12085] 연구소 대기 SLA**
```json
{
  "id": "56",
  "name": "연구소 대기 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223/sla/56"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_10203] 고객 요청 유형**
```json
{
  "_links": {
    "jiraRest": "https://seculayer.atlassian.net/rest/api/2/issue/49223",
    "web": "https://seculayer.atlassian.net/servicedesk/customer/portal/1/TACEA-4539",
    "agent": "https://seculayer.atlassian.net/browse/TACEA-4539",
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223"
  },
  "requestType": {
    "_expands": [
      "field"
    ],
    "id": "1",
    "_links": {
      "self": "https://seculayer.atlassian.net/rest/servicedeskapi/servicedesk/1/requesttype/1"
    },
    "name": "지원 요청",
    "description": "Tech-Ops, Dev-Ops에게 도움 요청(단순 문의 시 등록)",
    "helpText": "양식에 맞지 않게 등록할 경우 안내 없이 반려 처리 될 수 있습니다.\n1개월 이상 답변 없으실 경우 임의로 종결 처리 할 수 있으니 참고 부탁드립니다.",
    "defaultName": "지원 요청",
    "issueTypeId": "10105",
    "serviceDeskId": "1",
    "portalId": "1",
    "groupIds": [
      "9"
    ],
    "icon": {
      "id": "10627",
      "_links": {
        "iconUrls": {
          "48x48": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=large",
          "24x24": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=small",
          "16x16": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=xsmall",
          "32x32": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=medium"
        }
      }
    }
  },
  "currentStatus": {
    "status": "닫힘",
    "statusCategory": "DONE",
    "statusDate": {
      "iso8601": "2026-07-07T10:51:22+0900",
      "jira": "2026-07-07T10:51:22.753+0900",
      "friendly": "오늘 10:51",
      "epochMillis": 1783389082753
    }
  }
}
```

**[customfield_10204] 기관**
```json
[]
```

**[customfield_10205] 만족**
`null`

**[customfield_10206] 만족률**
`null`

**[customfield_11098] 감정**
```json
{
  "id": "3000",
  "name": "긍정적"
}
```

**[customfield_10200] 승인**
`null`

**[customfield_10202] 관계자 요청**
```json
[]
```

**[customfield_10317] 해결시간**
`null`

**[customfield_10318] 최초 응답 시간**
`null`

**[customfield_12152] 최초 응답 SLA**
```json
{
  "id": "59",
  "name": "최초 응답 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223/sla/59"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-06T17:54:40+0900",
        "jira": "2026-07-06T17:54:40.306+0900",
        "friendly": "어제 17:54",
        "epochMillis": 1783328080306
      },
      "stopTime": {
        "iso8601": "2026-07-06T18:48:44+0900",
        "jira": "2026-07-06T18:48:44.759+0900",
        "friendly": "어제 18:48",
        "epochMillis": 1783331324759
      },
      "breachTime": {
        "iso8601": "2026-07-07T13:54:40+0900",
        "jira": "2026-07-07T13:54:40.306+0900",
        "friendly": "오늘 13:54",
        "epochMillis": 1783400080306
      },
      "breached": false,
      "goalDuration": {
        "millis": 14400000,
        "friendly": "4시간"
      },
      "elapsedTime": {
        "millis": 319694,
        "friendly": "5분"
      },
      "remainingTime": {
        "millis": 14080306,
        "friendly": "3시간 54분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12151] 해결 시간 SLA**
```json
{
  "id": "58",
  "name": "해결 시간 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223/sla/58"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-06T17:54:40+0900",
        "jira": "2026-07-06T17:54:40.306+0900",
        "friendly": "어제 17:54",
        "epochMillis": 1783328080306
      },
      "stopTime": {
        "iso8601": "2026-07-07T10:51:22+0900",
        "jira": "2026-07-07T10:51:22.753+0900",
        "friendly": "오늘 10:51",
        "epochMillis": 1783389082753
      },
      "breachTime": {
        "iso8601": "2026-07-14T10:46:03+0900",
        "jira": "2026-07-14T10:46:03.059+0900",
        "friendly": "2026/07/14 10:46",
        "epochMillis": 1783993563059
      },
      "breached": false,
      "goalDuration": {
        "millis": 144000000,
        "friendly": "40시간"
      },
      "elapsedTime": {
        "millis": 319694,
        "friendly": "5분"
      },
      "remainingTime": {
        "millis": 143680306,
        "friendly": "39시간 54분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11292] 개발 SLA**
```json
{
  "id": "54",
  "name": "개발 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49223/sla/54"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

### TACEA-4537 | 인시던트 | 생성: 2026-07-03

**[customfield_11038] 해결까지 시간**
`null`

**[customfield_12118] QA 검토 SLA**
```json
{
  "id": "57",
  "name": "QA 검토 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192/sla/57"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11258] 해결 후 종료할 시간**
`null`

**[customfield_11589] 권한**
`null`

**[customfield_10802] 요청 언어**
```json
{
  "languageCode": "ko",
  "displayName": "한국어"
}
```

**[customfield_12084] 할 일 SLA**
```json
{
  "id": "55",
  "name": "할 일 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192/sla/55"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T17:41:39+0900",
        "jira": "2026-07-03T17:41:39.756+0900",
        "friendly": "금요일 17:41",
        "epochMillis": 1783068099756
      },
      "stopTime": {
        "iso8601": "2026-07-03T17:42:55+0900",
        "jira": "2026-07-03T17:42:55.310+0900",
        "friendly": "금요일 17:42",
        "epochMillis": 1783068175310
      },
      "breachTime": {
        "iso8601": "2026-07-06T17:41:39+0900",
        "jira": "2026-07-06T17:41:39.756+0900",
        "friendly": "어제 17:41",
        "epochMillis": 1783327299756
      },
      "breached": false,
      "goalDuration": {
        "millis": 28800000,
        "friendly": "8시간"
      },
      "elapsedTime": {
        "millis": 75554,
        "friendly": "1분"
      },
      "remainingTime": {
        "millis": 28724446,
        "friendly": "7시간 58분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12085] 연구소 대기 SLA**
```json
{
  "id": "56",
  "name": "연구소 대기 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192/sla/56"
  },
  "completedCycles": [],
  "ongoingCycle": {
    "startTime": {
      "iso8601": "2026-07-06T14:47:59+0900",
      "jira": "2026-07-06T14:47:59.409+0900",
      "friendly": "어제 14:47",
      "epochMillis": 1783316879409
    },
    "breachTime": {
      "iso8601": "2026-07-07T14:47:59+0900",
      "jira": "2026-07-07T14:47:59.409+0900",
      "friendly": "오늘 14:47",
      "epochMillis": 1783403279409
    },
    "breached": false,
    "paused": false,
    "withinCalendarHours": false,
    "goalDuration": {
      "millis": 28800000,
      "friendly": "8시간"
    },
    "elapsedTime": {
      "millis": 22320591,
      "friendly": "6시간 12분"
    },
    "remainingTime": {
      "millis": 6479409,
      "friendly": "1시간 47분"
    }
  },
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_10203] 고객 요청 유형**
```json
{
  "_links": {
    "jiraRest": "https://seculayer.atlassian.net/rest/api/2/issue/49192",
    "web": "https://seculayer.atlassian.net/servicedesk/customer/portal/1/TACEA-4537",
    "agent": "https://seculayer.atlassian.net/browse/TACEA-4537",
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192"
  },
  "requestType": {
    "_expands": [
      "field"
    ],
    "id": "14",
    "_links": {
      "self": "https://seculayer.atlassian.net/rest/servicedeskapi/servicedesk/1/requesttype/14"
    },
    "name": "인시던트 보고",
    "description": "기술지원 과정에서 인지한 오류, 장애로 추측되는 사안 보고",
    "helpText": "양식에 맞지 않게 등록할 경우 안내 없이 반려 처리 될 수 있습니다.\n1개월 이상 답변 없으실 경우 임의로 종결 처리 할 수 있으니 참고 부탁드립니다.",
    "defaultName": "인시던트 보고",
    "issueTypeId": "10104",
    "serviceDeskId": "1",
    "portalId": "1",
    "groupIds": [
      "9"
    ],
    "icon": {
      "id": "10638",
      "_links": {
        "iconUrls": {
          "48x48": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=large",
          "24x24": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=small",
          "16x16": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=xsmall",
          "32x32": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=medium"
        }
      }
    }
  },
  "currentStatus": {
    "status": "연구소 대기 중",
    "statusCategory": "INDETERMINATE",
    "statusDate": {
      "iso8601": "2026-07-06T14:47:59+0900",
      "jira": "2026-07-06T14:47:59.409+0900",
      "friendly": "어제 14:47",
      "epochMillis": 1783316879409
    }
  }
}
```

**[customfield_10204] 기관**
```json
[]
```

**[customfield_10205] 만족**
`null`

**[customfield_10206] 만족률**
`null`

**[customfield_11098] 감정**
```json
{
  "id": "2000",
  "name": "중립적"
}
```

**[customfield_10200] 승인**
`null`

**[customfield_10202] 관계자 요청**
```json
[]
```

**[customfield_10317] 해결시간**
`null`

**[customfield_10318] 최초 응답 시간**
`null`

**[customfield_12152] 최초 응답 SLA**
```json
{
  "id": "59",
  "name": "최초 응답 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192/sla/59"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T17:41:39+0900",
        "jira": "2026-07-03T17:41:39.756+0900",
        "friendly": "금요일 17:41",
        "epochMillis": 1783068099756
      },
      "stopTime": {
        "iso8601": "2026-07-03T17:42:55+0900",
        "jira": "2026-07-03T17:42:55.310+0900",
        "friendly": "금요일 17:42",
        "epochMillis": 1783068175310
      },
      "breachTime": {
        "iso8601": "2026-07-06T13:41:39+0900",
        "jira": "2026-07-06T13:41:39.756+0900",
        "friendly": "어제 13:41",
        "epochMillis": 1783312899756
      },
      "breached": false,
      "goalDuration": {
        "millis": 14400000,
        "friendly": "4시간"
      },
      "elapsedTime": {
        "millis": 75554,
        "friendly": "1분"
      },
      "remainingTime": {
        "millis": 14324446,
        "friendly": "3시간 58분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12151] 해결 시간 SLA**
```json
{
  "id": "58",
  "name": "해결 시간 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192/sla/58"
  },
  "completedCycles": [],
  "ongoingCycle": {
    "startTime": {
      "iso8601": "2026-07-03T17:41:39+0900",
      "jira": "2026-07-03T17:41:39.756+0900",
      "friendly": "금요일 17:41",
      "epochMillis": 1783068099756
    },
    "breachTime": {
      "iso8601": "2026-07-31T17:41:39+0900",
      "jira": "2026-07-31T17:41:39.756+0900",
      "friendly": "2026/07/31 17:41",
      "epochMillis": 1785487299756
    },
    "breached": false,
    "paused": false,
    "withinCalendarHours": false,
    "goalDuration": {
      "millis": 576000000,
      "friendly": "160시간"
    },
    "elapsedTime": {
      "millis": 40700244,
      "friendly": "11시간 18분"
    },
    "remainingTime": {
      "millis": 535299756,
      "friendly": "148시간 41분"
    }
  },
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11292] 개발 SLA**
```json
{
  "id": "54",
  "name": "개발 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49192/sla/54"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

### TACEA-4536 | 서비스 요청 | 생성: 2026-07-03

**[customfield_11038] 해결까지 시간**
`null`

**[customfield_12118] QA 검토 SLA**
```json
{
  "id": "57",
  "name": "QA 검토 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189/sla/57"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11258] 해결 후 종료할 시간**
`null`

**[customfield_11589] 권한**
`null`

**[customfield_10802] 요청 언어**
```json
{
  "languageCode": "ko",
  "displayName": "한국어"
}
```

**[customfield_12084] 할 일 SLA**
```json
{
  "id": "55",
  "name": "할 일 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189/sla/55"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T17:28:10+0900",
        "jira": "2026-07-03T17:28:10.756+0900",
        "friendly": "금요일 17:28",
        "epochMillis": 1783067290756
      },
      "stopTime": {
        "iso8601": "2026-07-03T17:42:39+0900",
        "jira": "2026-07-03T17:42:39.139+0900",
        "friendly": "금요일 17:42",
        "epochMillis": 1783068159139
      },
      "breachTime": {
        "iso8601": "2026-07-06T17:28:10+0900",
        "jira": "2026-07-06T17:28:10.756+0900",
        "friendly": "어제 17:28",
        "epochMillis": 1783326490756
      },
      "breached": false,
      "goalDuration": {
        "millis": 28800000,
        "friendly": "8시간"
      },
      "elapsedTime": {
        "millis": 868383,
        "friendly": "14분"
      },
      "remainingTime": {
        "millis": 27931617,
        "friendly": "7시간 45분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12085] 연구소 대기 SLA**
```json
{
  "id": "56",
  "name": "연구소 대기 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189/sla/56"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_10203] 고객 요청 유형**
```json
{
  "_links": {
    "jiraRest": "https://seculayer.atlassian.net/rest/api/2/issue/49189",
    "web": "https://seculayer.atlassian.net/servicedesk/customer/portal/1/TACEA-4536",
    "agent": "https://seculayer.atlassian.net/browse/TACEA-4536",
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189"
  },
  "requestType": {
    "_expands": [
      "field"
    ],
    "id": "1",
    "_links": {
      "self": "https://seculayer.atlassian.net/rest/servicedeskapi/servicedesk/1/requesttype/1"
    },
    "name": "지원 요청",
    "description": "Tech-Ops, Dev-Ops에게 도움 요청(단순 문의 시 등록)",
    "helpText": "양식에 맞지 않게 등록할 경우 안내 없이 반려 처리 될 수 있습니다.\n1개월 이상 답변 없으실 경우 임의로 종결 처리 할 수 있으니 참고 부탁드립니다.",
    "defaultName": "지원 요청",
    "issueTypeId": "10105",
    "serviceDeskId": "1",
    "portalId": "1",
    "groupIds": [
      "9"
    ],
    "icon": {
      "id": "10627",
      "_links": {
        "iconUrls": {
          "48x48": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=large",
          "24x24": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=small",
          "16x16": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=xsmall",
          "32x32": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10627?size=medium"
        }
      }
    }
  },
  "currentStatus": {
    "status": "닫힘",
    "statusCategory": "DONE",
    "statusDate": {
      "iso8601": "2026-07-06T15:36:21+0900",
      "jira": "2026-07-06T15:36:21.421+0900",
      "friendly": "어제 15:36",
      "epochMillis": 1783319781421
    }
  }
}
```

**[customfield_10204] 기관**
```json
[]
```

**[customfield_10205] 만족**
`null`

**[customfield_10206] 만족률**
`null`

**[customfield_11098] 감정**
```json
{
  "id": "2000",
  "name": "중립적"
}
```

**[customfield_10200] 승인**
`null`

**[customfield_10202] 관계자 요청**
```json
[]
```

**[customfield_10317] 해결시간**
`null`

**[customfield_10318] 최초 응답 시간**
`null`

**[customfield_12152] 최초 응답 SLA**
```json
{
  "id": "59",
  "name": "최초 응답 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189/sla/59"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T17:28:10+0900",
        "jira": "2026-07-03T17:28:10.756+0900",
        "friendly": "금요일 17:28",
        "epochMillis": 1783067290756
      },
      "stopTime": {
        "iso8601": "2026-07-03T17:42:39+0900",
        "jira": "2026-07-03T17:42:39.139+0900",
        "friendly": "금요일 17:42",
        "epochMillis": 1783068159139
      },
      "breachTime": {
        "iso8601": "2026-07-06T13:28:10+0900",
        "jira": "2026-07-06T13:28:10.756+0900",
        "friendly": "어제 13:28",
        "epochMillis": 1783312090756
      },
      "breached": false,
      "goalDuration": {
        "millis": 14400000,
        "friendly": "4시간"
      },
      "elapsedTime": {
        "millis": 868383,
        "friendly": "14분"
      },
      "remainingTime": {
        "millis": 13531617,
        "friendly": "3시간 45분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12151] 해결 시간 SLA**
```json
{
  "id": "58",
  "name": "해결 시간 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189/sla/58"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T17:28:10+0900",
        "jira": "2026-07-03T17:28:10.756+0900",
        "friendly": "금요일 17:28",
        "epochMillis": 1783067290756
      },
      "stopTime": {
        "iso8601": "2026-07-06T15:36:21+0900",
        "jira": "2026-07-06T15:36:21.421+0900",
        "friendly": "어제 15:36",
        "epochMillis": 1783319781421
      },
      "breachTime": {
        "iso8601": "2026-07-13T15:21:47+0900",
        "jira": "2026-07-13T15:21:47.214+0900",
        "friendly": "2026/07/13 15:21",
        "epochMillis": 1783923707214
      },
      "breached": false,
      "goalDuration": {
        "millis": 144000000,
        "friendly": "40시간"
      },
      "elapsedTime": {
        "millis": 874207,
        "friendly": "14분"
      },
      "remainingTime": {
        "millis": 143125793,
        "friendly": "39시간 45분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11292] 개발 SLA**
```json
{
  "id": "54",
  "name": "개발 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49189/sla/54"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

### TACEA-4532 | 인시던트 | 생성: 2026-07-03

**[customfield_11038] 해결까지 시간**
`null`

**[customfield_12118] QA 검토 SLA**
```json
{
  "id": "57",
  "name": "QA 검토 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175/sla/57"
  },
  "completedCycles": [],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11258] 해결 후 종료할 시간**
`null`

**[customfield_11589] 권한**
`null`

**[customfield_10802] 요청 언어**
```json
{
  "languageCode": "ko",
  "displayName": "한국어"
}
```

**[customfield_12084] 할 일 SLA**
```json
{
  "id": "55",
  "name": "할 일 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175/sla/55"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T11:14:10+0900",
        "jira": "2026-07-03T11:14:10.309+0900",
        "friendly": "금요일 11:14",
        "epochMillis": 1783044850309
      },
      "stopTime": {
        "iso8601": "2026-07-03T11:29:13+0900",
        "jira": "2026-07-03T11:29:13.435+0900",
        "friendly": "금요일 11:29",
        "epochMillis": 1783045753435
      },
      "breachTime": {
        "iso8601": "2026-07-06T11:14:10+0900",
        "jira": "2026-07-06T11:14:10.309+0900",
        "friendly": "어제 11:14",
        "epochMillis": 1783304050309
      },
      "breached": false,
      "goalDuration": {
        "millis": 28800000,
        "friendly": "8시간"
      },
      "elapsedTime": {
        "millis": 903126,
        "friendly": "15분"
      },
      "remainingTime": {
        "millis": 27896874,
        "friendly": "7시간 44분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12085] 연구소 대기 SLA**
```json
{
  "id": "56",
  "name": "연구소 대기 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175/sla/56"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T11:31:48+0900",
        "jira": "2026-07-03T11:31:48.256+0900",
        "friendly": "금요일 11:31",
        "epochMillis": 1783045908256
      },
      "stopTime": {
        "iso8601": "2026-07-06T08:24:46+0900",
        "jira": "2026-07-06T08:24:46.680+0900",
        "friendly": "어제 08:24",
        "epochMillis": 1783293886680
      },
      "breachTime": {
        "iso8601": "2026-07-06T11:31:48+0900",
        "jira": "2026-07-06T11:31:48.256+0900",
        "friendly": "어제 11:31",
        "epochMillis": 1783305108256
      },
      "breached": false,
      "goalDuration": {
        "millis": 28800000,
        "friendly": "8시간"
      },
      "elapsedTime": {
        "millis": 19691744,
        "friendly": "5시간 28분"
      },
      "remainingTime": {
        "millis": 9108256,
        "friendly": "2시간 31분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_10203] 고객 요청 유형**
```json
{
  "_links": {
    "jiraRest": "https://seculayer.atlassian.net/rest/api/2/issue/49175",
    "web": "https://seculayer.atlassian.net/servicedesk/customer/portal/1/TACEA-4532",
    "agent": "https://seculayer.atlassian.net/browse/TACEA-4532",
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175"
  },
  "requestType": {
    "_expands": [
      "field"
    ],
    "id": "14",
    "_links": {
      "self": "https://seculayer.atlassian.net/rest/servicedeskapi/servicedesk/1/requesttype/14"
    },
    "name": "인시던트 보고",
    "description": "기술지원 과정에서 인지한 오류, 장애로 추측되는 사안 보고",
    "helpText": "양식에 맞지 않게 등록할 경우 안내 없이 반려 처리 될 수 있습니다.\n1개월 이상 답변 없으실 경우 임의로 종결 처리 할 수 있으니 참고 부탁드립니다.",
    "defaultName": "인시던트 보고",
    "issueTypeId": "10104",
    "serviceDeskId": "1",
    "portalId": "1",
    "groupIds": [
      "9"
    ],
    "icon": {
      "id": "10638",
      "_links": {
        "iconUrls": {
          "48x48": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=large",
          "24x24": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=small",
          "16x16": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=xsmall",
          "32x32": "https://seculayer.atlassian.net/rest/api/3/universal_avatar/view/type/SD_REQTYPE/avatar/10638?size=medium"
        }
      }
    }
  },
  "currentStatus": {
    "status": "연구소 검토 중",
    "statusCategory": "INDETERMINATE",
    "statusDate": {
      "iso8601": "2026-07-06T08:24:46+0900",
      "jira": "2026-07-06T08:24:46.680+0900",
      "friendly": "어제 08:24",
      "epochMillis": 1783293886680
    }
  }
}
```

**[customfield_10204] 기관**
```json
[]
```

**[customfield_10205] 만족**
`null`

**[customfield_10206] 만족률**
`null`

**[customfield_11098] 감정**
```json
{
  "id": "2000",
  "name": "중립적"
}
```

**[customfield_10200] 승인**
`null`

**[customfield_10202] 관계자 요청**
```json
[]
```

**[customfield_10317] 해결시간**
`null`

**[customfield_10318] 최초 응답 시간**
`null`

**[customfield_12152] 최초 응답 SLA**
```json
{
  "id": "59",
  "name": "최초 응답 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175/sla/59"
  },
  "completedCycles": [
    {
      "startTime": {
        "iso8601": "2026-07-03T11:14:10+0900",
        "jira": "2026-07-03T11:14:10.309+0900",
        "friendly": "금요일 11:14",
        "epochMillis": 1783044850309
      },
      "stopTime": {
        "iso8601": "2026-07-03T11:29:13+0900",
        "jira": "2026-07-03T11:29:13.435+0900",
        "friendly": "금요일 11:29",
        "epochMillis": 1783045753435
      },
      "breachTime": {
        "iso8601": "2026-07-03T16:14:10+0900",
        "jira": "2026-07-03T16:14:10.309+0900",
        "friendly": "금요일 16:14",
        "epochMillis": 1783062850309
      },
      "breached": false,
      "goalDuration": {
        "millis": 14400000,
        "friendly": "4시간"
      },
      "elapsedTime": {
        "millis": 903126,
        "friendly": "15분"
      },
      "remainingTime": {
        "millis": 13496874,
        "friendly": "3시간 44분"
      }
    }
  ],
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_12151] 해결 시간 SLA**
```json
{
  "id": "58",
  "name": "해결 시간 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175/sla/58"
  },
  "completedCycles": [],
  "ongoingCycle": {
    "startTime": {
      "iso8601": "2026-07-03T11:14:10+0900",
      "jira": "2026-07-03T11:14:10.309+0900",
      "friendly": "금요일 11:14",
      "epochMillis": 1783044850309
    },
    "breachTime": {
      "iso8601": "2026-07-31T11:14:10+0900",
      "jira": "2026-07-31T11:14:10.309+0900",
      "friendly": "2026/07/31 11:14",
      "epochMillis": 1785464050309
    },
    "breached": false,
    "paused": false,
    "withinCalendarHours": false,
    "goalDuration": {
      "millis": 576000000,
      "friendly": "160시간"
    },
    "elapsedTime": {
      "millis": 60349691,
      "friendly": "16시간 45분"
    },
    "remainingTime": {
      "millis": 515650309,
      "friendly": "143시간 14분"
    }
  },
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

**[customfield_11292] 개발 SLA**
```json
{
  "id": "54",
  "name": "개발 SLA",
  "_links": {
    "self": "https://seculayer.atlassian.net/rest/servicedeskapi/request/49175/sla/54"
  },
  "completedCycles": [],
  "ongoingCycle": {
    "startTime": {
      "iso8601": "2026-07-06T08:24:46+0900",
      "jira": "2026-07-06T08:24:46.680+0900",
      "friendly": "어제 08:24",
      "epochMillis": 1783293886680
    },
    "breachTime": {
      "iso8601": "2026-07-13T18:00:00+0900",
      "jira": "2026-07-13T18:00:00.000+0900",
      "friendly": "2026/07/13 18:00",
      "epochMillis": 1783933200000
    },
    "breached": false,
    "paused": false,
    "withinCalendarHours": false,
    "goalDuration": {
      "millis": 172800000,
      "friendly": "48시간"
    },
    "elapsedTime": {
      "millis": 39600000,
      "friendly": "11시간"
    },
    "remainingTime": {
      "millis": 133200000,
      "friendly": "37시간"
    }
  },
  "slaDisplayFormat": "NEW_SLA_FORMAT"
}
```

