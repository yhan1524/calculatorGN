from time import perf_counter                       # 실행 시간을 아주 정밀하게 측정하고 싶을 때 사용(순수하게 흐른 시간만)

# =========================================================
# 1. 입력 검증
# =========================================================
def validate_positive_int(value, name="값"):
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name}은(는) 1 이상의 정수여야 합니다.")

def validate_kind(kind):
    if kind not in ("cross", "x"):
        raise ValueError("kind는 'cross' 또는 'x'여야 합니다.")


# =========================================================
# 2. 패턴 생성기
# =========================================================
def generate_cross(n):
    """
    N x N Cross 패턴 생성
    - 가운데 행
    - 가운데 열
    """
    validate_positive_int(n, "n")
    center = n // 2

    pattern = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(1 if (i == center or j == center) else 0)
        pattern.append(row)
    return pattern


def generate_x(n):
    """
    N x N X 패턴 생성
    - 주대각선
    - 부대각선
    """
    validate_positive_int(n, "n")

    pattern = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(1 if (i == j or i + j == n - 1) else 0)
        pattern.append(row)
    return pattern


def generate_pattern(n, kind):
    """
    kind == 'cross' 또는 'x'
    """
    validate_kind(kind)
    if kind == "cross":
        return generate_cross(n)
    return generate_x(n)


# =========================================================
# 3. 2차원 <-> 1차원 변환
# =========================================================
def flatten_matrix(matrix):
    """
    2차원 NxN -> 1차원 길이 N^2
    """
    n = len(matrix)
    if n == 0:
        raise ValueError("행렬이 비어 있습니다.")

    flat = []
    for i in range(n):
        if len(matrix[i]) != n:
            raise ValueError("정사각 행렬(NxN)만 허용됩니다.")
        for j in range(n):
            flat.append(matrix[i][j])
    return flat


def matrix_from_flat(flat, n):
    """
    1차원 길이 N^2 -> 2차원 NxN
    """
    validate_positive_int(n, "n")
    if len(flat) != n * n:
        raise ValueError("flat의 길이는 반드시 N^2 이어야 합니다.")

    matrix = []
    idx = 0
    for i in range(n):
        row = []
        for j in range(n):
            row.append(flat[idx])
            idx += 1
        matrix.append(row)
    return matrix


def get_pattern(n, kind, flat=False):
    """
    모드 1 / 성능 분석 공용 패턴 생성
    flat=True면 1차원으로 반환
    """
    pattern = generate_pattern(n, kind)
    return flatten_matrix(pattern) if flat else pattern


# =========================================================
# 4. 출력 유틸
# =========================================================
def print_matrix(matrix):
    for row in matrix:
        print(" ".join(str(v) for v in row))


# =========================================================
# 5. 성능 비교용 예시 연산
#    ※ 여기 부분을 기존 MAC 판정 로직으로 연결하세요.
# =========================================================
def mac_check_2d(a, b):
    """
    2차원 배열용 비교 예시
    - 현재는 단순히 다른 칸 개수를 셈
    - 기존 MAC 판정 로직이 있다면 이 함수 내용만 교체
    """
    n = len(a)
    if n != len(b):
        raise ValueError("두 행렬의 크기가 같아야 합니다.")

    mismatch = 0
    for i in range(n):
        if len(a[i]) != n or len(b[i]) != n:
            raise ValueError("정사각 행렬(NxN)만 허용됩니다.")
        for j in range(n):
            if a[i][j] != b[i][j]:
                mismatch += 1
    return mismatch


def mac_check_1d(a, b, n):
    """
    1차원 배열용 비교 예시
    - 현재는 단순히 다른 칸 개수를 셈
    - 기존 MAC 판정 로직이 있다면 이 함수 내용만 교체
    """
    validate_positive_int(n, "n")
    if len(a) != n * n or len(b) != n * n:
        raise ValueError("배열 길이는 반드시 N^2 이어야 합니다.")

    mismatch = 0
    for idx in range(n * n):
        if a[idx] != b[idx]:
            mismatch += 1
    return mismatch


# =========================================================
# 6. 벤치마크
# =========================================================
def benchmark(func, *args, repeat=1000):
    validate_positive_int(repeat, "repeat")

    start = perf_counter()
    result = None
    for _ in range(repeat):
        result = func(*args)
    end = perf_counter()

    return end - start, result


# =========================================================
# 7. 모드 1: 패턴 생성
# =========================================================
def mode_generate_pattern():
    n = int(input("크기 N을 입력하세요: ").strip())
    kind = input("패턴 종류를 입력하세요 (cross/x): ").strip().lower()

    pattern = get_pattern(n, kind, flat=False)

    print(f"\n생성된 {kind.upper()} 패턴 ({n}x{n})")
    print_matrix(pattern)


# =========================================================
# 8. 성능 분석 모드
# =========================================================
def mode_benchmark():
    n = int(input("크기 N을 입력하세요: ").strip())
    kind = input("패턴 종류를 입력하세요 (cross/x): ").strip().lower()
    repeat = int(input("반복 횟수를 입력하세요: ").strip())

    # 동일 입력 생성
    pattern_2d = get_pattern(n, kind, flat=False)
    pattern_1d = get_pattern(n, kind, flat=True)

    # 비교 대상도 동일 데이터로 구성
    target_2d = get_pattern(n, kind, flat=False)
    target_1d = get_pattern(n, kind, flat=True)

    # 2D 성능 측정
    time_2d, result_2d = benchmark(mac_check_2d, pattern_2d, target_2d, repeat=repeat)

    # 1D 성능 측정
    time_1d, result_1d = benchmark(mac_check_1d, pattern_1d, target_1d, n, repeat=repeat)

    print("\n[성능 비교 결과]")
    print(f"2D 실행 시간 : {time_2d:.6f} sec")
    print(f"1D 실행 시간 : {time_1d:.6f} sec")
    print(f"2D 결과      : {result_2d}")
    print(f"1D 결과      : {result_1d}")
    print(f"결과 동일 여부: {result_2d == result_1d}")

    if time_1d < time_2d:
        print(f"1D가 더 빠릅니다. (차이: {time_2d - time_1d:.6f} sec)")
    elif time_2d < time_1d:
        print(f"2D가 더 빠릅니다. (차이: {time_1d - time_2d:.6f} sec)")
    else:
        print("실행 시간이 거의 동일합니다.")


# =========================================================
# 9. 메인 메뉴
# =========================================================
def main():
    while True:
        print("\n==============================")
        print("1. 패턴 생성")
        print("2. 성능 분석")
        print("0. 종료")
        print("==============================")

        choice = input("메뉴를 선택하세요: ").strip()

        try:
            if choice == "1":
                mode_generate_pattern()
            elif choice == "2":
                mode_benchmark()
            elif choice == "0":
                print("프로그램을 종료합니다.")
                break
            else:
                print("잘못된 선택입니다.")
        except Exception as e:
            print("오류:", e)


if __name__ == "__main__":
    main()