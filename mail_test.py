# mail_test.py
# LDAP 그룹 조회 테스트
# pip install ldap3 python-dotenv
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[.env] {env_path} 로드 완료")
    else:
        print(f"[.env] 파일 없음: {env_path}")
except ImportError:
    print("[.env] python-dotenv 미설치 — 환경변수에서 직접 읽기")

try:
    from ldap3 import Server, Connection, ALL, SUBTREE
except ImportError:
    print("[ERROR] ldap3 미설치: pip install ldap3")
    raise

LDAP_HOST     = os.getenv("LDAP_HOST", "")
LDAP_PORT     = int(os.getenv("LDAP_PORT", "389"))
LDAP_USE_SSL  = os.getenv("LDAP_USE_SSL", "false").lower() == "true"
LDAP_BIND_DN  = os.getenv("LDAP_BIND_DN", "")   # ex) CN=svc,CN=Users,DC=seculayer,DC=com
LDAP_PASSWORD = os.getenv("LDAP_PASSWORD", "")
LDAP_BASE_DN  = os.getenv("LDAP_BASE_DN", "")   # ex) DC=seculayer,DC=com
LDAP_FILTER   = os.getenv("LDAP_FILTER", "(objectClass=group)")
LDAP_ATTRS    = os.getenv("LDAP_ATTRS", "cn,mail,description,member").split(",")
LDAP_LIMIT    = int(os.getenv("LDAP_LIMIT", "50"))


def main() -> None:
    print("\n=== LDAP 설정 ===")
    print(f"  LDAP_HOST    : {LDAP_HOST!r}")
    print(f"  LDAP_PORT    : {LDAP_PORT}")
    print(f"  LDAP_USE_SSL : {LDAP_USE_SSL}")
    print(f"  LDAP_BIND_DN : {LDAP_BIND_DN!r}")
    print(f"  LDAP_BASE_DN : {LDAP_BASE_DN!r}")
    print(f"  LDAP_FILTER  : {LDAP_FILTER!r}")
    print(f"  LDAP_ATTRS   : {LDAP_ATTRS}")
    print(f"  LDAP_LIMIT   : {LDAP_LIMIT}")

    if not LDAP_HOST or not LDAP_BASE_DN:
        print("\n[ERROR] LDAP_HOST 또는 LDAP_BASE_DN 이 비어 있습니다. .env 파일을 확인하세요.")
        print("\n필수 .env 항목:")
        print("  LDAP_HOST=10.1.1.x          # AD/LDAP 서버 IP")
        print("  LDAP_BASE_DN=DC=seculayer,DC=com")
        print("  LDAP_BIND_DN=CN=svc,CN=Users,DC=seculayer,DC=com  # 에러 시 비우면 익명 시도")
        print("  LDAP_PASSWORD=your-password")
        return

    print(f"\n[INFO] {LDAP_HOST}:{LDAP_PORT} 연결 시도...")

    server = Server(LDAP_HOST, port=LDAP_PORT, use_ssl=LDAP_USE_SSL, get_info=ALL)

    try:
        if LDAP_BIND_DN and LDAP_PASSWORD:
            conn = Connection(server, user=LDAP_BIND_DN, password=LDAP_PASSWORD, auto_bind=True)
            print(f"[INFO] 인증 연결: {LDAP_BIND_DN}")
        else:
            conn = Connection(server, auto_bind=True)
            print("[INFO] 익명(엵명) 연결")
    except Exception as e:
        print(f"[FAIL] LDAP 연결 실패: {type(e).__name__}: {e}")
        return

    print(f"[SUCCESS] 연결 성공 ✅")
    print(f"  서버 정보: {server.info.vendor_name if server.info else 'N/A'}")

    print(f"\n[INFO] 그룹 검색: base={LDAP_BASE_DN!r} filter={LDAP_FILTER!r} limit={LDAP_LIMIT}")

    try:
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=LDAP_FILTER,
            search_scope=SUBTREE,
            attributes=LDAP_ATTRS,
            size_limit=LDAP_LIMIT,
        )
    except Exception as e:
        print(f"[FAIL] LDAP 검색 실패: {type(e).__name__}: {e}")
        conn.unbind()
        return

    entries = conn.entries
    print(f"\n=== 그룹 목록 ({len(entries)}건) ===")
    for i, entry in enumerate(entries, 1):
        cn   = entry.cn.value   if "cn"   in entry   else ""
        mail = entry.mail.value if "mail" in entry   else "(없음)"
        desc = entry.description.value if "description" in entry else ""
        try:
            member_count = len(entry.member.values) if "member" in entry else 0
        except Exception:
            member_count = 0
        print(f"  [{i:3}] {cn:<40}  mail={mail:<35}  멤버={member_count}명  {desc}")

    conn.unbind()
    print(f"\n[DONE] 총 {len(entries)}건")


if __name__ == "__main__":
    main()
