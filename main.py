import json
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

EPS = 1e-9
BENCH_REPEAT = 10


# =========================================================
# 1) 데이터 구조
# =========================================================
class Matrix:
    """n×n 행렬을 1차원 배열로 저장하는 구조"""

    def __init__(self, n: int, flat: Optional[List[float]] = None):
        self.n = n
        self.data = flat if flat is not None else [0.0] * (n * n)

    @classmethod
    def from_2d(cls, rows: List[List[float]]) -> "Matrix":
        if not rows:
            raise ValueError("빈 행렬입니다.")
        n = len(rows)
        for row in rows:
            if len(row) != n:
                raise ValueError("정사각 행렬이 아닙니다.")
        flat = []
        for i in range(n):
            for j in range(n):
                flat.append(float(rows[i][j]))
        return cls(n, flat)

    def index(self, i: int, j: int) -> int:
        return i * self.n + j

    def get(self, i: int, j: int) -> float:
        return self.data[self.index(i, j)]

    def set(self, i: int, j: int, value: float) -> None:
        self.data[self.index(i, j)] = float(value)

    def to_2d(self) -> List[List[float]]:
        out = []
        for i in range(self.n):
            row = []
            for j in range(self.n):
                row.append(self.get(i, j))
            out.append(row)
        return out

    def pretty(self) -> str:
        lines = []
        for i in range(self.n):
            row = []
            for j in range(self.n):
                v = self.get(i, j)
                if abs(v - int(v)) < 1e-12:
                    row.append(str(int(v)))
                else:
                    row.append(f"{v:.6g}")
            lines.append(" ".join(row))
        return "\n".join(lines)


# =========================================================
# 2) 라벨 정규화
# =========================================================
def normalize_label(label: Any) -> str:
    if label is None:
        return ""
    s = str(label).strip().lower()
    if s in ["+", "cross", "c"]:
        return "cross"
    if s in ["x", "diag"]:
        return "x"
    return s


def normalize_filter_key(key: str) -> Optional[str]:
    return normalize_label(key)


# =========================================================
# 3) 패턴 생성기
# =========================================================
def generate_cross_2d(n: int) -> List[List[float]]:
    mat = [[0.0 for _ in range(n)] for _ in range(n)]
    mid = n // 2
    for i in range(n):
        mat[i][mid] = 1.0
        mat[mid][i] = 1.0
    return mat


def generate_x_2d(n: int) -> List[List[float]]:
    mat = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1.0
        mat[i][n - 1 - i] = 1.0
    return mat


def flatten_2d(rows: List[List[float]]) -> List[float]:
    flat = []
    for i in range(len(rows)):
        for j in range(len(rows[i])):
            flat.append(float(rows[i][j]))
    return flat


# =========================================================
# 4) 유효성 검사
# =========================================================
def validate_square_matrix(rows: Any, name: str) -> None:
    if not isinstance(rows, list) or len(rows) == 0:
        raise ValueError(f"{name}는 비어있거나 리스트가 아닙니다.")
    n = len(rows)
    for idx, row in enumerate(rows):
        if not isinstance(row, list):
            raise ValueError(f"{name}[{idx}]는 리스트가 아닙니다.")
        if len(row) != n:
            raise ValueError(f"{name}는 정사각 행렬이 아닙니다.")


def parse_matrix_input(n: int, title: str) -> List[List[float]]:
    """
    콘솔에서 n×n 행렬 입력 받기
    """
    print(title)
    rows: List[List[float]] = []

    for i in range(n):
        while True:
            try:
                line = input(f"{i + 1}행 입력 (공백 구분): ").strip()
            except EOFError:
                raise EOFError("입력이 종료되었습니다.")

            parts = line.split()
            if len(parts) != n:
                print(f"잘못된 입력입니다. {n}개의 값을 입력해야 합니다. 예: 0 1 0")
                continue

            try:
                row = [float(x) for x in parts]
                rows.append(row)
                break
            except ValueError:
                print("숫자만 입력하세요.")
    return rows


def print_matrix(title: str, mat: List[List[float]]) -> None:
    print(title)
    for row in mat:
        print(" ".join(str(int(x)) if abs(x - int(x)) < 1e-12 else str(x) for x in row))


def ask_confirm(message: str = "이대로 진행할까요? (y/n): ") -> bool:
    try:
        ans = input(message).strip().lower()
    except EOFError:
        raise EOFError("입력이 종료되었습니다.")
    return ans in ["y", "yes", "1"]


# =========================================================
# 5) MAC 연산
# =========================================================
def mac_score_2d(pattern: List[List[float]], filt: List[List[float]]) -> float:
    """2D 배열 기반 MAC"""
    if len(pattern) != len(filt):
        raise ValueError("크기 불일치")
    n = len(pattern)
    score = 0.0
    for i in range(n):
        if len(pattern[i]) != n or len(filt[i]) != n:
            raise ValueError("정사각 행렬이 아닙니다.")
        for j in range(n):
            score += float(pattern[i][j]) * float(filt[i][j])
    return score


def mac_score_flat(pattern: Matrix, filt: Matrix) -> float:
    """1D 배열 기반 MAC"""
    if pattern.n != filt.n:
        raise ValueError("크기 불일치")
    score = 0.0
    for i in range(pattern.n * pattern.n):
        score += pattern.data[i] * filt.data[i]
    return score


# =========================================================
# 6) 비교 정책
# =========================================================
def compare_labels(score_cross: float, score_x: float, eps: float = EPS) -> str:
    """Cross/X 판정용"""
    if abs(score_cross - score_x) < eps:
        return "UNDECIDED"
    return "Cross" if score_cross > score_x else "X"


def compare_ab(score_a: float, score_b: float, eps: float = EPS) -> str:
    """사용자 입력 모드용 A/B 판정"""
    if abs(score_a - score_b) < eps:
        return "UNDECIDED"
    return "A" if score_a > score_b else "B"


def get_matrix_from_any(obj: Any) -> Optional[List[List[float]]]:
    """
    다양한 JSON 형태에서 행렬을 추출
    허용 형태:
      - [[...], [...]]
      - {"matrix": [[...]]}
      - {"data": [[...]]}
      - {"input": [[...]]}
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("matrix", "data", "input"):
            if key in obj and isinstance(obj[key], list):
                return obj[key]
    return None


def extract_size_from_key(key: str) -> Optional[int]:
    """
    예:
      size_13_2 -> 13
      size_5 -> 5
    """
    m = re.search(r"(\d+)", str(key))
    if not m:
        return None
    return int(m.group(1))


def find_filter_entry(filters_data: Any, size: int, kind: str) -> Optional[List[List[float]]]:
    """
    filters_data에서 size와 kind(Cross/X)에 맞는 필터 찾기

    허용 형태 예시:
    1) {
         "5": {"cross": [[...]], "x": [[...]]},
         "13": {...}
       }

    2) [
         {"size": 5, "label": "Cross", "matrix": [[...]]},
         {"size": 5, "label": "X", "matrix": [[...]]}
       ]
    """
    wanted = normalize_label(kind)

    # dict 형태
    if isinstance(filters_data, dict):
        for k, v in filters_data.items():
            s = extract_size_from_key(k)
            if s != size:
                continue

            if isinstance(v, dict):
                for subk, subv in v.items():
                    lab = normalize_filter_key(subk)
                    if lab == wanted:
                        mat = get_matrix_from_any(subv)
                        if mat is not None:
                            return mat

    # list 형태
    if isinstance(filters_data, list):
        for item in filters_data:
            if not isinstance(item, dict):
                continue
            item_size = item.get("size")
            item_label = normalize_label(item.get("label"))
            if item_size == size and item_label == wanted:
                mat = get_matrix_from_any(item)
                if mat is not None:
                    return mat

    return None


def analyze_one_case(
    case: Dict[str, Any],
    filters_data: Any,
    eps: float = EPS
) -> Tuple[str, float, float, int]:
    """
    한 케이스에 대해 Cross/X MAC 점수를 계산하고 판정한다.
    반환:
      predicted_label, cross_score, x_score, ops
    """
    if not isinstance(case, dict):
        raise TypeError("case는 dict여야 합니다.")

    case_id = case.get("case", "?")

    # 1) 패턴 행렬 찾기
    pattern = None
    for key in ("pattern", "input", "data", "matrix"):
        if key in case and case[key] is not None:
            pattern = get_matrix_from_any(case[key])
            if pattern is not None:
                break

    # 2) 위에서 못 찾으면 case 전체에서 탐색
    if pattern is None:
        pattern = get_matrix_from_any(case)

    if pattern is None:
        raise ValueError(f"case {case_id}에서 패턴 행렬을 찾을 수 없습니다.")

    # 3) 정사각 행렬인지 검사
    validate_square_matrix(pattern, "pattern")

    # 4) size 확인
    size = case.get("size")
    if size is None:
        size = len(pattern)
    elif not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError(f"case {case_id}의 size가 올바르지 않습니다.")

    # 5) size와 패턴 크기 일치 검사
    if len(pattern) != size:
        raise ValueError(
            f"case {case_id}: size({size})와 패턴 크기({len(pattern)})가 일치하지 않습니다."
        )

    # 6) 필터 찾기
    cross_filter = find_filter_entry(filters_data, size, "Cross")
    x_filter = find_filter_entry(filters_data, size, "X")

    if cross_filter is None:
        raise ValueError(f"size={size}에 대한 Cross 필터를 찾을 수 없습니다.")
    if x_filter is None:
        raise ValueError(f"size={size}에 대한 X 필터를 찾을 수 없습니다.")

    # 7) 필터가 행렬인지 검사
    validate_square_matrix(cross_filter, "cross_filter")
    validate_square_matrix(x_filter, "x_filter")

    # 8) 점수 계산
    cross_score = mac_score_2d(pattern, cross_filter)
    x_score = mac_score_2d(pattern, x_filter)

    # 9) 판정
    predicted_label = compare_labels(cross_score, x_score, eps=eps)

    # 10) 연산량(간단 추정)
    ops = size * size

    return predicted_label, cross_score, x_score, ops


def _extract_cases_and_filters(payload: Any) -> Tuple[List[Dict[str, Any]], Any]:
    """
    입력 JSON 구조가 조금 달라도 최대한 안전하게 cases와 filters를 추출한다.
    """
    if isinstance(payload, dict):
        if "cases" in payload and "filters" in payload:
            return payload["cases"], payload["filters"]

        if "cases" in payload:
            return payload["cases"], payload.get("filters")

        if "data" in payload and isinstance(payload["data"], dict):
            data = payload["data"]
            if "cases" in data and "filters" in data:
                return data["cases"], data["filters"]

    elif isinstance(payload, list):
        return payload, None

    raise ValueError("입력 JSON에서 cases와 filters를 추출할 수 없습니다.")


# =========================================================
# 7) JSON 처리
# =========================================================
def load_json_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}")


def save_json_file(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_pattern_cases(patterns_data: Any) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    if isinstance(patterns_data, dict):
        if "cases" in patterns_data and isinstance(patterns_data["cases"], list):
            for item in patterns_data["cases"]:
                if isinstance(item, dict):
                    cases.append(item)
            return cases

        for k, v in patterns_data.items():
            if isinstance(v, dict):
                item = dict(v)
                item.setdefault("case", k)  # 원래 키 보존
                if "size" not in item:
                    s = extract_size_from_key(k)
                    if s is not None:
                        item["size"] = s
                cases.append(item)
        return cases

    if isinstance(patterns_data, list):
        for item in patterns_data:
            if isinstance(item, dict):
                cases.append(item)

    return cases


def load_dataset(path: str) -> Dict[str, Any]:
    data = load_json_file(path)
    if not isinstance(data, dict):
        raise ValueError("JSON 최상위는 객체(dict)여야 합니다.")
    return data


# =========================================================
# 8) 성능 측정
# =========================================================
def benchmark_mac_2d(
    pattern: List[List[float]],
    filt: List[List[float]],
    repeat: int = BENCH_REPEAT
) -> Tuple[float, int]:
    """
    MAC 연산 평균 시간(ms), 연산 횟수(N^2) 반환
    """
    n = len(pattern)
    ops = n * n

    start = time.perf_counter()
    for _ in range(repeat):
        _ = mac_score_2d(pattern, filt)
    end = time.perf_counter()

    avg_ms = ((end - start) / repeat) * 1000.0
    return avg_ms, ops


def benchmark_mac_flat(
    pattern: Matrix,
    filt: Matrix,
    repeat: int = BENCH_REPEAT
) -> Tuple[float, int]:
    """
    MAC 연산 평균 시간(ms), 연산 횟수(N^2) 반환
    """
    ops = pattern.n * pattern.n

    start = time.perf_counter()
    for _ in range(repeat):
        _ = mac_score_flat(pattern, filt)
    end = time.perf_counter()

    avg_ms = ((end - start) / repeat) * 1000.0
    return avg_ms, ops


# =========================================================
# 9) 사용자 입력 모드
# =========================================================
def run_user_input_mode() -> int:
    print("\n[사용자 입력 모드] 3×3 필터 A/B와 패턴을 입력합니다.\n")

    n = 3
    a_rows = parse_matrix_input(n, "필터 A 입력")
    print_matrix("입력된 필터 A:", a_rows)
    if not ask_confirm("필터 A가 맞습니까? (y/n): "):
        print("다시 실행해 주세요.")
        return 0

    b_rows = parse_matrix_input(n, "필터 B 입력")
    print_matrix("입력된 필터 B:", b_rows)
    if not ask_confirm("필터 B가 맞습니까? (y/n): "):
        print("다시 실행해 주세요.")
        return 0

    p_rows = parse_matrix_input(n, "패턴 입력")
    print_matrix("입력된 패턴:", p_rows)
    if not ask_confirm("패턴이 맞습니까? (y/n): "):
        print("다시 실행해 주세요.")
        return 0

    a_score = mac_score_2d(p_rows, a_rows)
    b_score = mac_score_2d(p_rows, b_rows)
    winner = compare_ab(a_score, b_score)

    a_time, ops = benchmark_mac_2d(p_rows, a_rows)
    b_time, _ = benchmark_mac_2d(p_rows, b_rows)

    print("\n" + "=" * 50)
    print("[결과]")
    print(f"A 점수: {a_score}")
    print(f"B 점수: {b_score}")
    print(f"A 연산 시간(평균): {a_time:.6f} ms")
    print(f"B 연산 시간(평균): {b_time:.6f} ms")
    print(f"판정 결과: {winner}")
    print(f"연산 횟수: {ops} (N^2)")
    print("=" * 50)

    return 0


# =========================================================
# 10) JSON 분석 모드
# =========================================================
def run_json_analysis_mode(json_path: str = "data.json", result_path: str = "result.json") -> None:
    REPEAT = BENCH_REPEAT

    results: List[Dict[str, Any]] = []
    benchmark_rows: List[Tuple[int, int, float, int]] = []

    pass_count = 0
    fail_count = 0
    undecided_count = 0

    # =========================
    # JSON 로드
    # =========================
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"[오류] 입력 파일을 찾을 수 없습니다: {json_path}")
        return
    except json.JSONDecodeError:
        print(f"[오류] JSON 형식이 올바르지 않습니다: {json_path}")
        return

    if not isinstance(raw_data, dict):
        print("[오류] JSON 최상위 구조는 dict 여야 합니다.")
        return

    # 필터 데이터와 케이스 데이터 분리
    filters_data = None
    for key in ("filters", "filter", "mac_filters"):
        if key in raw_data:
            filters_data = raw_data[key]
            break

    if filters_data is None:
        print("[오류] 필터 데이터(filters/filter/mac_filters)를 찾을 수 없습니다.")
        return

    if "cases" in raw_data and isinstance(raw_data["cases"], list):
        cases = raw_data["cases"]
    elif "patterns" in raw_data:
        cases = find_pattern_cases(raw_data["patterns"])
    else:
        print("[오류] 케이스 데이터(cases/patterns)를 찾을 수 없습니다.")
        return

    if not cases:
        print("[오류] 분석할 케이스가 없습니다.")
        return

    # =========================
    # 케이스별 분석
    # =========================
    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            print(f"[경고] case {idx}는 dict가 아니므로 건너뜁니다.")
            continue

        try:
            size = case.get("size")
            if not isinstance(size, int) or isinstance(size, bool):
                pattern_guess = None
                for key in ("pattern", "input", "data", "matrix"):
                    if key in case:
                        pattern_guess = get_matrix_from_any(case[key])
                        if pattern_guess is not None:
                            break
                if pattern_guess is None:
                    raise ValueError("size를 추정할 수 없습니다.")
                size = len(pattern_guess)

            expected_raw = case.get("expected", case.get("label"))
            expected = normalize_label(expected_raw)
            if expected not in ("cross", "x"):
                raise ValueError(f"expected 라벨이 올바르지 않습니다: {expected_raw}")

            # -------------------------
            # 패턴 / 필터 추출
            # -------------------------
            pattern = None
            for key in ("pattern", "input", "data", "matrix"):
                if key in case and case[key] is not None:
                    pattern = get_matrix_from_any(case[key])
                    if pattern is not None:
                        break
            if pattern is None:
                raise ValueError(f"case {idx}에서 패턴 행렬을 찾을 수 없습니다.")

            validate_square_matrix(pattern, "pattern")

            cross_filter = find_filter_entry(filters_data, size, "Cross")
            x_filter = find_filter_entry(filters_data, size, "X")

            if cross_filter is None:
                raise ValueError(f"size={size}에 대한 Cross 필터를 찾을 수 없습니다.")
            if x_filter is None:
                raise ValueError(f"size={size}에 대한 X 필터를 찾을 수 없습니다.")

            validate_square_matrix(cross_filter, "cross_filter")
            validate_square_matrix(x_filter, "x_filter")

            # -------------------------
            # MAC 연산 시간 측정
            # -------------------------
            start_time = time.perf_counter()
            cross_score = 0.0
            x_score = 0.0

            for _ in range(REPEAT):
                cross_score = mac_score_2d(pattern, cross_filter)
                x_score = mac_score_2d(pattern, x_filter)

            end_time = time.perf_counter()
            avg_ms = ((end_time - start_time) / REPEAT) * 1000.0

            # -------------------------
            # 판정
            # -------------------------
            predicted_label = compare_labels(cross_score, x_score, eps=EPS)
            pred_norm = normalize_label(predicted_label)

            if pred_norm == "undecided":
                undecided_count += 1
                result_tag = "UNDECIDED"
            elif pred_norm == expected:
                pass_count += 1
                result_tag = "PASS"
            else:
                fail_count += 1
                result_tag = "FAIL"

            ops = size * size

            results.append(
                {
                    "case": idx,
                    "size": size,
                    "expected": expected,
                    "predicted": predicted_label,
                    "result": result_tag,
                    "cross_score": round(cross_score, 6),
                    "x_score": round(x_score, 6),
                    "avg_ms": round(avg_ms, 6),
                    "ops": ops,
                }
            )

            benchmark_rows.append((size, avg_ms, ops))

            print("\n[케이스 결과]")
            print(f"case        : {idx}")
            print(f"size        : {size}")
            print(f"expected    : {expected}")
            print(f"predicted   : {predicted_label}")
            print(f"result      : {result_tag}")
            print(f"cross_score : {cross_score:.6f}")
            print(f"x_score     : {x_score:.6f}")
            print(f"avg_ms      : {avg_ms:.6f} ms")
            print(f"ops         : {ops}")

        except Exception as e:
            fail_count += 1
            results.append(
                {
                    "case": idx,
                    "size": case.get("size", None),
                    "expected": normalize_label(case.get("expected", case.get("label"))),
                    "predicted": None,
                    "result": "FAIL",
                    "error": str(e),
                }
            )
            print(f"[오류] case {idx}: {e}")

    # =========================
    # 요약 출력
    # =========================
    total_count = len(results)
    fail_rate = (fail_count / total_count * 100) if total_count > 0 else 0.0
    avg_time = (
        sum(row[2] for row in benchmark_rows) / len(benchmark_rows)
        if benchmark_rows
        else 0.0
    )

    print("\n" + "=" * 50)
    print("결과 요약")
    print(f"전체 테스트 수: {total_count}")
    print(f"통과 수       : {pass_count}")
    print(f"실패 수       : {fail_count}")
    print(f"동점 수       : {undecided_count}")
    print(f"실패 비율     : {fail_rate:.2f}%")
    print(f"평균 시간     : {avg_time:.6f} ms")

    failed_cases = [r for r in results if r.get("result") == "FAIL"]
    if failed_cases:
        print("\n실패 케이스:")
        for r in failed_cases:
            if "error" in r:
                print(f"- case {r['case']} | error={r['error']}")
            else:
                print(
                    f"- case {r['case']} | size={r['size']} | "
                    f"expected={r['expected']} | predicted={r['predicted']} | "
                    f"cross_score={r['cross_score']:.6f} | x_score={r['x_score']:.6f} | "
                    f"avg_ms={r['avg_ms']:.6f}"
                )

    if benchmark_rows:
        print("\n" + "=" * 50)
        print("크기별 성능 표")
        print("-" * 50)
        print(f"{'크기(N×N)':>12} | {'평균 시간(ms)':>14} | {'연산 횟수(N²)':>14}")
        print("-" * 50)

        for size, avg_ms, ops in sorted(benchmark_rows, key=lambda x: x[0]):
            print(f"{size}×{size:<1} | {avg_ms:>14.6f} | {ops:>14}")

    # =========================
    # result.json 저장
    # =========================
    summary = {
        "total": total_count,
        "pass": pass_count,
        "fail": fail_count,
        "undecided": undecided_count,
        "fail_rate": round(fail_rate, 2),
        "avg_time_ms": round(avg_time, 6),
    }

    output_data = {
        "summary": summary,
        "results": results,
    }

    try:
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n{result_path} 저장 완료")
    except OSError as e:
        print(f"[오류] 결과 파일 저장 실패: {e}")


# =========================================================
# 11) 메인 메뉴
# =========================================================
def main() -> int:
    print("Mini NPU Simulator")
    print("1) 사용자 입력(3×3)")
    print("2) data.json 분석")

    try:
        choice = input("입력 방식 선택 (1/2): ").strip()

        if choice == "1":
            return run_user_input_mode()
        elif choice == "2":
            run_json_analysis_mode("data.json")
            return 0
        else:
            print("잘못된 선택입니다.")
            return 1

    except EOFError:
        print("\n[오류] 입력이 종료되었습니다.")
        return 1
    except Exception as e:
        print(f"[오류] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())