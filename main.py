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
    m = re.match(r"^size_(\d+)", key)
    if not m:
        return None
    return int(m.group(1))


def get_filter_pair(filters: Dict[str, Any], size: int) -> Tuple[List[List[float]], List[List[float]]]:
    key = f"size_{size}"
    if key not in filters:
        raise KeyError(f"필터가 없습니다: {key}")

    block = filters[key]
    if not isinstance(block, dict):
        raise ValueError(f"{key}의 형식이 잘못되었습니다.")

    cross_key = None
    x_key = None
    for k in block.keys():
        nk = normalize_filter_key(k)
        if nk == "Cross":
            cross_key = k
        elif nk == "X":
            x_key = k

    if cross_key is None or x_key is None:
        raise ValueError(f"{key}에는 cross와 x가 모두 있어야 합니다.")

    cross_filter = block[cross_key]
    x_filter = block[x_key]

    validate_square_matrix(cross_filter, f"{key}.cross")
    validate_square_matrix(x_filter, f"{key}.x")

    return cross_filter, x_filter


# =========================================================
# 8) 평가 로직
# =========================================================
def evaluate_case(
    case_id: str,
    pattern: List[List[float]],
    cross_filter: List[List[float]],
    x_filter: List[List[float]],
    expected: Any
) -> Dict[str, Any]:
    expected_norm = normalize_label(expected)
    if expected_norm is None:
        return {
            "case_id": case_id,
            "result": "FAIL",
            "reason": f"expected 라벨 오류: {expected}"
        }

    if len(pattern) != len(cross_filter) or len(pattern) != len(x_filter):
        return {
            "case_id": case_id,
            "result": "FAIL",
            "reason": "패턴과 필터 크기가 일치하지 않음"
        }

    score_cross = mac_score_2d(pattern, cross_filter)
    score_x = mac_score_2d(pattern, x_filter)
    pred = compare_labels(score_cross, score_x)

    if pred == "UNDECIDED":
        verdict = "PASS" if expected_norm == "UNDECIDED" else "FAIL"
    else:
        verdict = "PASS" if pred == expected_norm else "FAIL"

    return {
        "case_id": case_id,
        "score_cross": score_cross,
        "score_x": score_x,
        "prediction": pred,
        "expected": expected_norm,
        "result": verdict
    }


# =========================================================
# 9) 성능 측정
# =========================================================
def benchmark(pattern: List[List[float]], filt: List[List[float]], repeat: int = BENCH_REPEAT) -> float:
    total = 0.0
    for _ in range(repeat):
        start = time.perf_counter()
        _ = mac_score_2d(pattern, filt)
        end = time.perf_counter()
        total += (end - start) * 1000.0
    return total / repeat


# =========================================================
# 10) 메인 실행
# =========================================================
def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data.json"

    try:
        data = load_json_file(path)
        filters = data.get("filters", {})
        patterns = data.get("patterns", {})

        if not isinstance(filters, dict) or not isinstance(patterns, dict):
            raise ValueError("JSON 최상위 구조가 올바르지 않습니다.")

        if not patterns:
            print("patterns가 비어 있습니다.")
            return 0

        results = []

        for case_id, case_info in patterns.items():
            if not isinstance(case_info, dict):
                results.append({
                    "case_id": case_id,
                    "result": "FAIL",
                    "reason": "case 형식이 잘못됨"
                })
                continue

            size = extract_size_from_key(case_id)
            if size is None:
                results.append({
                    "case_id": case_id,
                    "result": "FAIL",
                    "reason": "case_id에서 크기를 추출할 수 없음"
                })
                continue

            pattern = case_info.get("input")
            expected = case_info.get("expected")

            try:
                validate_square_matrix(pattern, f"{case_id}.input")
                cross_filter, x_filter = get_filter_pair(filters, size)
                result = evaluate_case(case_id, pattern, cross_filter, x_filter, expected)

                cross_time = benchmark(pattern, cross_filter)
                x_time = benchmark(pattern, x_filter)
                result["benchmark_ms"] = {
                    "cross": round(cross_time, 6),
                    "x": round(x_time, 6)
                }

                results.append(result)

            except Exception as e:
                results.append({
                    "case_id": case_id,
                    "result": "FAIL",
                    "reason": str(e)
                })

        pass_count = 0
        fail_count = 0

        for r in results:
            if r.get("result") == "PASS":
                pass_count += 1
            else:
                fail_count += 1

            print("=" * 50)
            print(f"CASE: {r.get('case_id')}")
            print(f"RESULT: {r.get('result')}")

            if "reason" in r:
                print(f"REASON: {r.get('reason')}")
                continue

            print(f"score_cross: {r.get('score_cross')}")
            print(f"score_x: {r.get('score_x')}")
            print(f"prediction: {r.get('prediction')}")
            print(f"expected: {r.get('expected')}")
            bm = r.get("benchmark_ms", {})
            print(f"benchmark_ms.cross: {bm.get('cross')}")
            print(f"benchmark_ms.x: {bm.get('x')}")

        output = {
            "summary": {
                "total": len(results),
                "pass": pass_count,
                "fail": fail_count
            },
            "results": results
        }

        save_json_file("result.json", output)

        print("=" * 50)
        print(f"TOTAL: {len(results)}, PASS: {pass_count}, FAIL: {fail_count}")
        print("결과가 result.json 파일로 저장되었습니다.")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())