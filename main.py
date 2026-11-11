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
def normalize_label(value: Any) -> Optional[str]:
    """
    내부 표준 라벨:
      - Cross
      - X

    허용 입력:
      - expected: '+', 'x', 'Cross', 'X'
      - filter key: 'cross', 'x'
    """
    if value is None:
        return None

    s = str(value).strip().lower()
    if s in ["+", "cross"]:
        return "Cross"
    if s in ["x"]:
        return "X"
    return None


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
            line = input(f"{i + 1}행 입력 (공백 구분): ").strip()
            parts = line.split()
            if len(parts) != n:
                print(f"잘못된 입력입니다. {n}개의 값을 입력해야 합니다.")
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
    ans = input(message).strip().lower()
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
        return "판정 불가"
    return "A" if score_a > score_b else "B"


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


def get_case_label_from_item(item: Dict[str, Any]) -> Optional[str]:
    """
    패턴/케이스에서 expected 라벨을 읽음
    허용 예:
      expected: "+"
      expected: "Cross"
      label: "X"
    """
    if "expected" in item:
        return normalize_label(item["expected"])
    if "label" in item:
        return normalize_label(item["label"])
    return None


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
    if wanted is None:
        return None

    # dict 형태
    if isinstance(filters_data, dict):
        # 1) size 키 직접 탐색
        for k, v in filters_data.items():
            s = extract_size_from_key(k)
            if s != size:
                continue

            if isinstance(v, dict):
                # cross / x 키 탐색
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


def find_pattern_cases(patterns_data: Any) -> List[Dict[str, Any]]:
    """
    패턴 케이스 목록 추출
    허용 형태:
      - [{"size": 5, "pattern": [[...]], "expected": "Cross"}, ...]
      - {"cases": [...]}
    """
    cases: List[Dict[str, Any]] = []

    if isinstance(patterns_data, dict):
        if "cases" in patterns_data and isinstance(patterns_data["cases"], list):
            for item in patterns_data["cases"]:
                if isinstance(item, dict):
                    cases.append(item)
            return cases

        # dict 자체가 케이스 맵일 수도 있음
        for k, v in patterns_data.items():
            if isinstance(v, dict):
                item = dict(v)
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
def benchmark_mac_2d(pattern: List[List[float]], filt: List[List[float]], repeat: int = BENCH_REPEAT) -> Tuple[float, int]:
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


def benchmark_mac_flat(pattern: Matrix, filt: Matrix, repeat: int = BENCH_REPEAT) -> Tuple[float, int]:
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
def run_json_analysis_mode(path: str = "data.json") -> int:
    print("\n[JSON 분석 모드] data.json을 불러와 판정합니다.\n")

    data = load_dataset(path)

    patterns_data = data.get("patterns")
    filters_data = data.get("filters")

    if patterns_data is None or filters_data is None:
        raise ValueError("JSON에 'patterns' 또는 'filters' 키가 없습니다.")

    cases = find_pattern_cases(patterns_data)
    if not cases:
        raise ValueError("분석할 패턴 케이스가 없습니다.")

    results: List[Dict[str, Any]] = []
    pass_count = 0
    fail_count = 0

    benchmark_rows: List[Tuple[int, float, int]] = []

    for idx, item in enumerate(cases, start=1):
        size = item.get("size")
        if size is None:
            size = extract_size_from_key(str(item.get("name", idx)))
        if size is None:
            print(f"[{idx}] size 정보를 찾을 수 없어 건너뜁니다.")
            continue

        pattern = (
            get_matrix_from_any(item)
            or get_matrix_from_any(item.get("input"))
            or get_matrix_from_any(item.get("pattern"))
        )

        if pattern is None:
            print(f"[{idx}] 패턴 행렬이 없습니다. 건너뜁니다.")
            continue

        expected = get_case_label_from_item(item)
        if expected is None:
            print(f"[{idx}] expected 라벨이 없습니다. 건너뜁니다.")
            continue

        cross_filter = find_filter_entry(filters_data, size, "Cross")
        x_filter = find_filter_entry(filters_data, size, "X")

        if cross_filter is None or x_filter is None:
            print(f"[{idx}] size={size} 필터를 찾을 수 없습니다. 건너뜁니다.")
            continue

        # MAC 점수
        cross_score = mac_score_2d(pattern, cross_filter)
        x_score = mac_score_2d(pattern, x_filter)
        predicted = compare_labels(cross_score, x_score)

        # 성능 측정
        bench_pattern = pattern
        avg_ms, ops = benchmark_mac_2d(bench_pattern, cross_filter)
        benchmark_rows.append((size, avg_ms, ops))

        # PASS/FAIL
        ok = (predicted == expected)
        if ok:
            pass_count += 1
        else:
            fail_count += 1

        result_item = {
            "case": idx,
            "size": size,
            "expected": expected,
            "predicted": predicted,
            "cross_score": cross_score,
            "x_score": x_score,
            "avg_ms": avg_ms,
            "ops": ops,
            "result": "PASS" if ok else "FAIL"
        }
        results.append(result_item)

        print("-" * 50)
        print(f"CASE {idx} | size={size}")
        print(f"expected : {expected}")
        print(f"predicted : {predicted}")
        print(f"Cross 점수: {cross_score}")
        print(f"X 점수    : {x_score}")
        print(f"평균 시간  : {avg_ms:.6f} ms")
        print(f"연산 횟수  : {ops} (N^2)")
        print(f"판정      : {'PASS' if ok else 'FAIL'}")

    # 요약 출력
    print("\n" + "=" * 50)
    print("결과 요약")
    print(f"전체 테스트 수: {len(results)}")
    print(f"통과 수       : {pass_count}")
    print(f"실패 수       : {fail_count}")

    if fail_count > 0:
        print("\n실패 케이스 목록:")
        for r in results:
            if r["result"] == "FAIL":
                print(
                    f"- CASE {r['case']} (size={r['size']}): "
                    f"expected={r['expected']}, predicted={r['predicted']}"
                )

    # result.json 저장
    output = {
        "summary": {
            "total": len(results),
            "pass": pass_count,
            "fail": fail_count
        },
        "results": results
    }
    save_json_file("result.json", output)

    print("\nresult.json 파일로 저장했습니다.")
    print("=" * 50)

    return 0


# =========================================================
# 11) 메인 메뉴
# =========================================================
def main() -> int:
    print("Mini NPU Simulator")
    print("1) 사용자 입력(3×3)")
    print("2) data.json 분석")

    choice = input("입력 방식 선택 (1/2): ").strip()

    try:
        if choice == "1":
            return run_user_input_mode()
        elif choice == "2":
            return run_json_analysis_mode("data.json")
        else:
            print("잘못된 선택입니다.")
            return 1
    except Exception as e:
        print(f"[오류] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())