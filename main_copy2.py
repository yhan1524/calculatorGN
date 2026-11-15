import time             # 시간

EPS = 1e-9              # 부동소수점 오차 방지 
REPEAT = 10
USER_SIZE = 3           # 사용자 입력값 변경시 반영

def make_cross(n):
    mat = [[0] * n for _ in range(n)]
    mids = [n // 2] if n % 2 == 1 else [n // 2 - 1, n // 2]

    for m in mids:
        for i in range(n):
            mat[m][i] = 1
            mat[i][m] = 1
    return mat


def make_x(n):
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1
        mat[i][n - 1 - i] = 1
    return mat


def generate_filters(n):
    return {
        "Cross": make_cross(n),
        "X": make_x(n),
    }


def generate_cases(n):
    return [
        {
            "name": f"auto_cross_{n}",
            "size": n,
            "expected": "Cross",
            "pattern": make_cross(n),
        },
        {
            "name": f"auto_x_{n}",
            "size": n,
            "expected": "X",
            "pattern": make_x(n),
        },
    ]


def normalize(label):
    """라벨 정규화: +/cross/plus -> cross, x/diag -> x"""
    if label is None:
        return ""
    s = str(label).strip().lower()
    if s in ["+", "cross", "c", "plus"]:
        return "Cross"
    if s in ["x", "diag"]:
        return "X"
    return "UNDECIDED" if s == "undecided" else s


def get_mat(obj):
    """dict/list에서 행렬 추출"""
    if isinstance(obj, list):       # 리스트형이면 그대로 출력, 각 데이터가 딕셔너리{}형으로 저장되기 때문임
        return obj
    if isinstance(obj, dict):       # 딕셔너리의 행렬 데이터를 찾아 꺼냄
        for k in ["matrix", "data", "input", "pattern"]:
            if k in obj and isinstance(obj[k], list):
                return obj[k]
    return None

def flatten(mat):
    """2차원 배열을 1차원 배열로 변환"""
    return [x for row in mat for x in row]

def mac_score_1d(p1, f1):
    """1차원 배열 MAC score 계산"""
    if p1 is None or f1 is None:
        raise ValueError("패턴 또는 필터가 None입니다.")
    if len(p1) != len(f1):
        raise ValueError(f"배열 길이가 다릅니다: pattern={len(p1)}, filter={len(f1)}")

    return sum(float(a) * float(b) for a, b in zip(p1, f1))


def benchmark_1d(p1, f1):
    """1D MAC 연산 성능 측정"""
    start = time.perf_counter()
    for _ in range(REPEAT):
        mac_score_1d(p1, f1)
    elapsed_ms = ((time.perf_counter() - start) / REPEAT) * 1000
    ops = len(p1)
    return elapsed_ms, ops   

def input_vector(size, title):
    """사용자 입력용 1차원 배열 받기"""
    while True:
        print(f"\n--- {title} 입력 ---")
        try:
            vals = input(f"{size}개 숫자를 공백 구분으로 입력: ").split()
            if len(vals) != size:
                raise ValueError(f"{size}개의 숫자를 입력해야 합니다.")
            vec = [float(x) for x in vals]

            print(f"\n[{title}]")
            print("  ".join(f"{v:g}" for v in vec))

            confirm = input("\n입력이 맞는지 확인 (y/n): ").strip().lower()
            if confirm in ["y", "yes", "1"]:
                return vec

            print("다시 입력을 시작합니다.")

        except ValueError as e:
            print(f"입력 오류: {e}. 처음부터 다시 입력해주세요.")
        except EOFError:
            return None


def run_user_mode():
    """사용자 입력 모드"""
    print(f"\n[사용자 모드] {USER_SIZE}개 원소 벡터 입력")

    a = input_vector(USER_SIZE, "필터 A")
    if a is None:
        return

    b = input_vector(USER_SIZE, "필터 B")
    if b is None:
        return

    p = input_vector(USER_SIZE, "입력 패턴")
    if p is None:
        return

    try:
        s_a = mac_score_1d(p, a)
        s_b = mac_score_1d(p, b)
        res = "UNDECIDED" if abs(s_a - s_b) < EPS else ("A" if s_a > s_b else "B")
    except ValueError as e:
        print(f"분석 오류: {e}")
        return

    print_user_result(s_a, s_b, res)

def print_user_result(s_a, s_b, res):
    print("\n" + "=" * 50)
    print(f" - 필터 A 점수: {s_a:.4f}")
    print(f" - 필터 B 점수: {s_b:.4f}")

    if res == "UNDECIDED":
        print(" - 판정: 판정 불가(|A-B| < 1e-9)")
    else:
        print(f" - 판정: {res}")

    print("=" * 50)

def get_case_items(cases):
    if isinstance(cases, dict):
        return cases.items()
    return enumerate(cases, 1)

def analyze_case(c_id, c_data, filters):
    p = get_mat(c_data)
    if p is None:
        raise ValueError("패턴 행렬을 찾을 수 없습니다.")

    if not isinstance(c_data, dict):
        raise ValueError("케이스 형식이 dict가 아닙니다.")

    try:
        size = int(c_data.get("size", len(p)))
    except (TypeError, ValueError):
        raise ValueError("size 값이 올바르지 않습니다")

    exp = normalize(c_data.get("expected") or c_data.get("label"))
    name = c_data.get("name", f"size_{size}_{c_id}")

    f_c = filters.get("Cross")
    f_x = filters.get("X")

    if f_c is None or f_x is None:
        raise ValueError(f"size_{size} 필터를 찾을 수 없습니다.")

    p1 = flatten(p)
    f_c1 = flatten(f_c)
    f_x1 = flatten(f_x)

    sc1d = mac_score_1d(p1, f_c1)
    sx1d = mac_score_1d(p1, f_x1)
    t1d_c, ops1d = benchmark_1d(p1, f_c1)
    t1d_x, _ = benchmark_1d(p1, f_x1)

    pred1d = "UNDECIDED" if abs(sc1d - sx1d) < EPS else ("Cross" if sc1d > sx1d else "X")

    return {
        "c_id": c_id,
        "name": name,
        "size": size,
        "expected": exp,
        "pred_1d": pred1d,
        "res_tag_1d": "PASS" if pred1d == exp else "FAIL",
        "sc_1d": sc1d,
        "sx_1d": sx1d,
        "time_1d_ms": (t1d_c + t1d_x) / 2,
        "ops_1d": ops1d,
    }

def print_case_result_compare(result):
    print(f"\n- {result['name']} ---")
    print(f"[1D] Cross 점수: {result['sc_1d']}")
    print(f"[1D] X 점수: {result['sx_1d']}")
    print(f"[1D] 판정: {result['pred_1d']} | expected: {result['expected']} | {result['res_tag_1d']}")
    print(f"[1D] 평균 시간: {result['time_1d_ms']:.6f} ms")

def update_perf_map(perf_map, size, time_ms, ops):
    """성능기록저장"""
    if size not in perf_map:                            # size 라는 키가 없으면 만들기
        perf_map[size] = {"times": [], "ops": ops}      # 실행시간 저장용 빈 리스트, 
    perf_map[size]["times"].append(time_ms)                   # [size]의 times리스트에 실행시간 추가

def handle_case_error(c_id, error):         
    print(f"⚠ {c_id} 처리 중 오류: {error}")           # 오류가 난 케이스만 건너 뛰고 실행하도록 처리

def run_json_mode():
    """N 입력 기반 자동 생성 모드"""
    try:
        n = int(input("크기 N 입력: "))
        if n <= 0:
            raise ValueError("N은 양수여야 합니다.")
    except ValueError as e:
        print(f"오류: {e}")
        return

    filters = generate_filters(n)
    cases = generate_cases(n)

    print(f"\n# [1] 자동 생성 필터: N={n}")
    print(" - Cross 생성 완료")
    print(" - X 생성 완료")

    print("\n# [2] 패턴 분석 (1D)")

    perf_map_1d = {}
    pass_cnt_1d, fail_cnt_1d = 0, 0
    failed_details_1d = []

    for c_id, c_data in get_case_items(cases):
        try:
            result = analyze_case(c_id, c_data, filters)
            print_case_result_compare(result)

            if result["res_tag_1d"] == "PASS":
                pass_cnt_1d += 1
            else:
                fail_cnt_1d += 1
                failed_details_1d.append(f"- {result['name']}: 판정 불일치")

            update_perf_map(perf_map_1d, result["size"], result["time_1d_ms"], result["ops_1d"])

        except Exception as e:
            handle_case_error(c_id, e)

    print_perf_table(perf_map_1d, "1D")
    print_result_summary(pass_cnt_1d, fail_cnt_1d, failed_details_1d)

def print_perf_table(perf_map, title):
    print(f"\n# [3] 성능 분석 - {title} (평균/10회)")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수':<10}")
    print("-" * 40)

    for s in sorted(perf_map.keys()):
        avg_t = sum(perf_map[s]["times"]) / len(perf_map[s]["times"])
        print(f"{s}×{s:<8} {avg_t:<15.6f} {perf_map[s]['ops']:<10}")

def print_result_summary(pass_cnt, fail_cnt, failed_details):
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
        print("\n1. 사용자 입력")
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