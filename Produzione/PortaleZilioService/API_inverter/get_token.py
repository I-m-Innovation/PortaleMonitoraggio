import sys

from API_iSolarCloud import login_ISC


def main() -> int:
    try:
        resp = login_ISC()
    except Exception as exc:
        print(f"Login failed: {exc}")
        return 1

    result_code = resp.get("result_code")
    result_msg = resp.get("result_msg")
    token = resp.get("result_data", {}).get("token")

    print(f"result_code: {result_code}")
    print(f"result_msg: {result_msg}")

    if not token:
        print("token: <missing>")
        return 2

    print(f"token: {token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
