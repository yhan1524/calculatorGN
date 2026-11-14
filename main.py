import json
import re               # data 필터 크기 비교
import time

EPS = 1e-9              # 부동소수점 오차 방지 
REPEAT = 10
USER_SIZE = 3


def normalize(label):
    """라벨 정규화: +/cross/plus -> cross, x/diag -> x"""
    if label is None:
        return ""
    s = str(label).strip().lower()
    if s in ["+", "cross", "c", "plus"]:
        return "cross"
    if s in ["x", "diag"]:
        return "x"
    return "undecided" if s == "undecided" else s


def get_mat(obj):
    """dict/list에서 행렬 추출"""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ["matrix", "data", "input", "pattern"]:
            if k in obj and isinstance(obj[k], list):
                return obj[k]
    return None


def mat_shape(mat):
    """행렬 크기 확인 (정사각형인지 포함)"""
    if not isinstance(mat, list) or not mat:
        return None
    if not all(isinstance(row, list) for row in mat):
        return None

    rows = len(mat)
    cols = len(mat[0])

    if any(len(row) != cols for row in mat):
        return None

    return rows, cols


def mac_score(p, f):
    """패턴과 필터의 MAC score 계산"""
    if p is None or f is None:
        raise ValueError("패턴 또는 필터가 None입니다.")

    sp = mat_shape(p)
    sf = mat_shape(f)

    if sp is None or sf is None:
        raise ValueError("행렬 형식이 올바르지 않습니다.")

    if sp != sf:
        raise ValueError(f"행렬 크기가 다릅니다: pattern={sp}, filter={sf}")

    rows, cols = sp
    return sum(float(p[i][j]) * float(f[i][j]) for i in range(rows) for j in range(cols))


def benchmark(p, f):
    """MAC 연산 성능 측정"""
    start = time.perf_counter()
    for _ in range(REPEAT):
        mac_score(p, f)
    elapsed_ms = ((time.perf_counter() - start) / REPEAT) * 1000
    ops = len(p) ** 2
    return elapsed_ms, ops


def find_filter(filters, size, kind):
    """filters에서 size와 kind(cross/x)에 맞는 행렬 찾기"""
    target = normalize(kind)

    if isinstance(filters, dict):
        for k, v in filters.items():
            num = re.search(r"(\d+)", str(k))
            if num and int(num.group(1)) == size:
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        if normalize(sk) == target:
                            return get_mat(sv)

    elif isinstance(filters, list):
        for item in filters:
            if not isinstance(item, dict):
                continue
            if item.get("size") == size and normalize(item.get("label")) == target:
                return get_mat(item)

    return None


def analyze_logic(p, f1, f2, l1="Cross", l2="X"):
    """
    점수 계산 및 판정 로직
    p: 패턴 / f1: 필터1 / f2: 필터2
    """
    s1 = mac_score(p, f1)
    s2 = mac_score(p, f2)

    t1, ops = benchmark(p, f1)
    t2, _ = benchmark(p, f2)

    if abs(s1 - s2) < EPS:
        pred = "UNDECIDED"
    elif s1 > s2:
        pred = l1
    else:
        pred = l2

    return pred, s1, s2, (t1 + t2) / 2, ops


def input_matrix(size, title):
    """사용자 입력용 행렬 받기"""
    while True:
        print(f"\n--- {title} 입력 ---")
        try:
            rows = []
            for i in range(size):
                vals = input(f"{i + 1}행 ({size}개, 공백 구분): ").split()
                if len(vals) != size:
                    raise ValueError(f"{size}개의 숫자를 입력해야 합니다.")
                row = [float(x) for x in vals]
                rows.append(row)

            print(f"\n[{title}]")
            for r in rows:
                print("  ".join(f"{v:g}" for v in r))

            confirm = input("\n입력이 맞는지 확인 (y/n): ").strip().lower()
            if confirm in ["y", "yes"]:
                return rows

            print("다시 입력을 시작합니다.")

        except ValueError as e:
            print(f"입력 오류: {e}. 처음부터 다시 입력해주세요.")
        except EOFError:
            return None


def run_user_mode():
    """3x3 사용자 입력 모드"""
    print(f"\n[사용자 모드] {USER_SIZE}x{USER_SIZE} 행렬 입력")

    a = input_matrix(USER_SIZE, "필터 A")
    if a is None:
        return

    b = input_matrix(USER_SIZE, "필터 B")
    if b is None:
        return

    p = input_matrix(USER_SIZE, "입력 패턴")
    if p is None:
        return

    try:
        res, s_a, s_b, t, ops = analyze_logic(p, a, b, l1="A", l2="B")
    except ValueError as e:
        print(f"분석 오류: {e}")
        return

    print("\n" + "=" * 50)
    print(f" - 필터 A 점수: {s_a:.4f}")
    print(f" - 필터 B 점수: {s_b:.4f}")

    if res == "UNDECIDED":
        print(" - 판정: 판정 불가(|A-B| < 1e-9)")
    else:
        print(f" - 평균 연산 시간: {t:.6f} ms")
        print(f" - 총 연산 횟수: {ops} (N^2)")
        print(f" - 판정: {res}")

    print("=" * 50)


def run_json_mode():
    """data.json 기반 성능 분석 모드"""
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"파일 오류: {e}")
        return

    filters = data.get("filters") or data.get("mac_filters")
    cases = data.get("cases") or data.get("patterns", {})

    if filters is None:
        print("오류: filters 데이터가 없습니다.")
        return

    if not cases:
        print("오류: patterns(cases) 데이터가 없습니다.")
        return

    print("\n# [1] 필터 로드")
    available_sizes = set()

    if isinstance(filters, dict):
        for k in filters.keys():
            num = re.search(r"(\d+)", str(k))
            if num:
                available_sizes.add(int(num.group(1)))
    elif isinstance(filters, list):
        for item in filters:
            if isinstance(item, dict) and "size" in item:
                try:
                    available_sizes.add(int(item["size"]))
                except:
                    pass

    for s in sorted(available_sizes):
        print(f"✓ size_{s} 필터 로드 완료 (Cross, X)")

    print("\n# [2] 패턴 분석 (라벨 정규화 적용)")

    perf_map = {}
    pass_cnt, fail_cnt = 0, 0
    failed_details = []

    # dict / list 둘 다 대응
    case_items = cases.items() if isinstance(cases, dict) else enumerate(cases, 1)

    for c_id, c_data in case_items:
        try:
            p = get_mat(c_data)
            if p is None:
                raise ValueError("패턴 행렬을 찾을 수 없습니다.")

            if not isinstance(c_data, dict):
                raise ValueError("케이스 형식이 dict가 아닙니다.")

            size = c_data.get("size", len(p))
            exp = normalize(c_data.get("expected") or c_data.get("label"))
            name = c_data.get("name", f"size_{size}_{c_id}")

            f_c = find_filter(filters, size, "cross")
            f_x = find_filter(filters, size, "x")

            if f_c is None or f_x is None:
                raise ValueError(f"size_{size} 필터를 찾을 수 없습니다.")

            sc = mac_score(p, f_c)
            sx = mac_score(p, f_x)
            t, ops = benchmark(p, f_c)

            if abs(sc - sx) < EPS:
                pred = "UNDECIDED"
            else:
                pred = "Cross" if sc > sx else "X"

            res_tag = "PASS" if normalize(pred) == exp else "FAIL"

            print(f"\n- {name} ---")
            print(f"Cross 점수: {sc}")
            print(f"X 점수: {sx}")
            print(f"판정: {pred} | expected: {exp.upper() if exp != 'undecided' else 'UNDECIDED'} | {res_tag}")

            if res_tag == "PASS":
                pass_cnt += 1
            else:
                fail_cnt += 1
                reason = "동점(UNDECIDED) 처리 규칙에 따라 FAIL" if pred == "UNDECIDED" else "판정 불일치"
                failed_details.append(f"- {name}: {reason}")

            if size not in perf_map:
                perf_map[size] = {"times": [], "ops": ops}
            perf_map[size]["times"].append(t)

        except Exception as e:
            print(f"⚠ {c_id} 처리 중 오류: {e}")

    print("\n# [3] 성능 분석 (평균/10회)")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수':<10}")
    print("-" * 40)

    for s in sorted(perf_map.keys()):
        avg_t = sum(perf_map[s]["times"]) / len(perf_map[s]["times"])
        print(f"{s}×{s:<8} {avg_t:<15.6f} {perf_map[s]['ops']:<10}")

    print("\n#---------------------------------------")
    print("# [4] 결과 요약")
    print(f"총 테스트: {pass_cnt + fail_cnt}개")
    print(f"통과: {pass_cnt}개")
    print(f"실패: {fail_cnt}개")

    if failed_details:
        print("\n실패 케이스:")
        for fd in failed_details:
            print(fd)


def main():
    while True:
        print("\n1. 사용자 입력 3x3")
        print("2. 성능 분석")
        print("0. 종료")

        choice = input("메뉴를 선택하세요: ").strip()

        try:
            if choice == "1":
                run_user_mode()
            elif choice == "2":
                run_json_mode()
            elif choice == "0":
                print("프로그램을 종료합니다.")
                break
            else:
                print("잘못된 선택입니다.")
        except Exception as e:
            print("오류:", e)


if __name__ == "__main__":
    main()