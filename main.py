import json
import re               # data 필터 크기 비교
import time             # 시간

EPS = 1e-9              # 부동소수점 오차 방지 
REPEAT = 10             # 최소기준 10회 반복측정 후 평균시간
USER_SIZE = 3           # 사용자 입력값 변경시 반영


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
    if isinstance(obj, list):       # 리스트형이면 그대로 반환
        return obj
    if isinstance(obj, dict):       # 딕셔너리형이면 키값이 matrix, data, input, pattern 중 하나인 경우 반환
        for k in ["matrix", "data", "input", "pattern"]:
            if k in obj and isinstance(obj[k], list):       # 입력된 데이터는 리스트형이여야함
                return obj[k]
    return None


def mat_shape(mat):     # mat[][] == rows[][]
    """행렬 크기 반환"""
    if not isinstance(mat, list) or not mat:        # 리스트가 아니거나 비어있는지
        return None
    if not all(isinstance(row, list) for row in mat):  # 각 행이 리스트인지
        return None

    rows = len(mat)         # 행 수    **[0]**[0]
    cols = len(mat[0])      # 첫번째 행의 열 수    [0]**[0]**

    if any(len(row) != cols for row in mat):    # 모든 행의 길이가 같은지
        return None
    if rows != cols :
        return None
    
    return rows, cols           # 데이터를 정사각형 데이터라 가정함 N^2


def mac_score(p, f):
    """패턴과 필터의 합성곱 계산"""
    if p is None or f is None:
        raise ValueError("패턴 또는 필터가 None입니다.")

    sp = mat_shape(p)           # 패턴
    sf = mat_shape(f)           # 필터 

    if sp is None or sf is None:        # 정사각형 판정을 받았는지
        raise ValueError("행렬 형식이 올바르지 않습니다.")

    if sp != sf:                        # 필터와 패턴의 크기가 다른 경우
        raise ValueError(f"행렬 크기가 다릅니다: pattern={sp}, filter={sf}")

    rows, cols = sp                     # 행과 열의 크기를 각각 담음
    return sum(float(p[i][j]) * float(f[i][j]) for i in range(rows) for j in range(cols))   # 곱차계산
            # 각 위치에 곱을 먼저 한 뒤 sum으로 합한다  자료형은 실수형, 행렬 크기만큼 곱차계산을 수행
    


def benchmark(p, f):
    """MAC 연산 성능 측정"""
    start = time.perf_counter()     # 시간 측정 시작(s)
    for _ in range(REPEAT):         # REPEAT 번 반복
        mac_score(p, f)             # 점수계산
    elapsed_ms = ((time.perf_counter() - start) / REPEAT) * 1000  # 평균 실행시간(ms) 
    ops = len(p) ** 2               # 연산횟수 N^2
    return elapsed_ms, ops


def find_filter(filters, size, kind):
    """filters에서 size와 kind(cross/x)에 맞는 행렬 찾기"""
    target = normalize(kind)                            # 값 정규화

    if isinstance(filters, dict):                       # 필터 값이 딕셔너리면
        for k, v in filters.items():                    # 딕셔너리의 키는 k, 값은 v에 받아옴 k={"v": {"sk"}: sv...}
            num = re.search(r"(\d+)", str(k))           # re모듈(정수찾기) \d 숫자1글자, +1번이상연속반복 -> ()로 묶어 연속된 숫자는 전부 반환
            if num and int(num.group(1)) == size:       # 키의 처음 마주친 숫자그룹이 size(패턴크기)와 같으면
                if isinstance(v, dict):                 # 그 딕셔너리 값을 v{"sv" : [...]}
                    for sk, sv in v.items():            # 안쪽 딕셔너리 키값쌍을 가져옴
                        if normalize(sk) == target:     # 그 키가 kind와 일치하면
                            return get_mat(sv)          # 값을 반환함

    elif isinstance(filters, list):                     # 필터 값이 리스트면
        for item in filters:            
            if not isinstance(item, dict):              # 각 항목이 딕셔너리가 아니면 건너뜀
                continue                                
            if item.get("size") == size and normalize(item.get("label")) == target:     # 크기와 kind가 같으면
                return get_mat(item)                                                    # 그 행렬을 반환

    return None


def analyze_logic(p, f1, f2, l1="Cross", l2="X"):
    """
    사용자 입력 모드에서 패턴과 두 필터를 비교하여 점수와 시간을 측정하고 판정을 내림
    p: 패턴 / f1: 필터1 / f2: 필터2
    """
    s1 = mac_score(p, f1)   # A 필터 점수
    s2 = mac_score(p, f2)   # B 필터 점수

    t1, ops = benchmark(p, f1)  # A 필터 연산시간, ops: 연산횟수
    t2, _ = benchmark(p, f2)    # B 필터 연산시간, 연산횟수는 같아서 값을 쓰지 않음(_) 처리

    if abs(s1 - s2) < EPS:      # 판정
        res = "UNDECIDED"
    elif s1 > s2:
        res = l1
    else:
        res = l2

    return res, s1, s2, (t1 + t2) / 2, ops

def input_matrix(size, title):
    """사용자 입력용 행렬 받기"""
    while True:
        print(f"\n--- {title} 입력 ---")
        try:
            rows = []
            for i in range(size):           # 3번 반복 (0부터 size-1)
                vals = input(f"{i + 1}행 ({size}개, 공백 구분): ").split()
                if len(vals) != size:   # 3개가 아닌경우
                    raise ValueError(f"{size}개의 숫자를 입력해야 합니다.")
                row = [float(x) for x in vals] # vals 리스트의 값 x를 실수형으로
                rows.append(row)    # 리스트를 행에 추가 rows[0][0]

            print(f"\n[{title}]")
            for r in rows:
                print("  ".join(f"{v:g}" for v in r))   # 각 값 사이에 다시 공백을 주고, :g 자릿수정리, 행단위 출력

            confirm = input("\n입력이 맞는지 확인 (y/n): ").strip().lower()
            if confirm in ["y", "yes", "1"]:
                return rows

            print("다시 입력을 시작합니다.")

        except ValueError as e:         # 숫자가 아닌 값을 입력한 경우
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
    print_user_result(s_a,s_b,t,ops,res)

def print_user_result(s_a,s_b,t,ops,res):
    print("\n" + "=" * 50)
    print(f" - 필터 A 점수: {s_a:.4f}")
    print(f" - 필터 B 점수: {s_b:.4f}")
    print(f" - 평균 연산 시간: {t:.6f} ms")
    print(f" - 총 연산 횟수: {ops} (N^2)")

    if res == "UNDECIDED":                      # 동점에 대한 판정불가
        print(" - 판정: 판정 불가(|A-B| < 1e-9)")
    else:
        print(f" - 판정: {res}")

    print("=" * 50)



def load_json_data(path="data.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:     # data 파일로드
            return json.load(f)
    except Exception as e:
        print(f"파일 오류: {e}")
        return None

    
def get_filters_and_cases(data):

    filters = data.get("filters")# 필터 가져오기
    if filters is None:
        filters = data.get("mac_filters")   # filters 키가 없으면 mac_filters 키를 가져옴

    cases = data.get("cases")
    if cases is None:
        cases = data.get("patterns", {})    # patterns 키가 없으면 빈 딕셔너리 반환  
    return filters, cases

def collect_available_sizes(filters):
    available_sizes = set()                                     # 필터 사이즈를 받아오기 위한 변수, 빈집합 생성, 집합은 중복을 자동으로 제거
    if isinstance(filters, dict):                               # 필터가 딕셔너리이면 키 반환
        for k in filters.keys():
            num = re.search(r"(\d+)", str(k))                   # re모듈(정수찾기) \d 숫자1글자, +1번이상연속반복 -> ()로 묶어 연속된 숫자는 전부 반환
            if num:
                available_sizes.add(int(num.group(1)))          # 첫번째로 찾은 정수그룹을 반환 13_5_1이면 13을 반환한다
    elif isinstance(filters, list):                             # 필터가 리스트라면
        for item in filters:
            if isinstance(item, dict) and "size" in item:       # 각 항목이 딕셔너리이고, size 키가 있다면 
                try:
                    available_sizes.add(int(item["size"]))      # size의 정수형, 필터 사이즈를 반환
                except:
                    pass
    return available_sizes

def print_loaded_filters(available_sizes):
    print("\n# [1] 필터 로드")
    for s in sorted(available_sizes):                           # 확인된 사이즈 출력용, 라벨에서 먼저 마주치는 정수반환
        print(f"✓ size_{s} 필터 로드 완료 (Cross, X)")

def get_case_items(cases):
    if isinstance(cases, dict):
        return cases.items()
    return enumerate(cases, 1)

def analyze_case(c_id, c_data, filters):
    p = get_mat(c_data)             # 리스트, 행렬 데이터를 반환, 합성곱을 할 대상
    if p is None:
        raise ValueError("패턴 행렬을 찾을 수 없습니다.")

    if not isinstance(c_data, dict):                    # {} 여야 함
        raise ValueError("케이스 형식이 dict가 아닙니다.")
    try:
        size = int(c_data.get("size", len(p)))                   # size가 있다면 size 키캆 사용, 없으면 행렬크기
    except (TypeError, ValueError) :
        raise ValueError("size 값이 올바르지 않습니다")
    
    exp = normalize(c_data.get("expected") or c_data.get("label"))  # expected나 label의 +,x,cross.. 등을 정규화
    name = c_data.get("name", f"size_{size}_{c_id}")                # 케이스 이름, 없으면 동일 형태로 만듦
    
    f_c = find_filter(filters, size, "Cross")           # 사이즈 별 cross 필터
    f_x = find_filter(filters, size, "X")               # 사이즈 별 x 필터
    
    if f_c is None or f_x is None:                      # 필터가 존재하지 않는 경우
        raise ValueError(f"size_{size} 필터를 찾을 수 없습니다.")
    
    sc = mac_score(p, f_c)                              # cross 필터와 패턴의 MAC계산 수행
    sx = mac_score(p, f_x)                              # x 필터와 패턴의 MAC 계산 수행
    t, ops = benchmark(p, f_c)                          # 시간과 N^2 값을 반환
    
    if abs(sc - sx) < EPS:                              # 두 점수 차이가 작으면 동점으로 판정
        pred = "UNDECIDED"
    else:
        pred = "Cross" if sc > sx else "X"              # cross 필터가 크면 Cross로 판정, 아니면 X로 판정
    
    res_tag = "PASS" if pred == exp else "FAIL"      # 판정결과 패턴 라벨과 일치시 pass, 아니면 fail

    return {                                        # 결과를 딕셔너리로 반환
        "c_id": c_id,                               # 패턴 인덱스
        "name": name,                               # 케이스 이름
        "size": size,                               # 패턴 크기
        "expected": exp,                            # 패턴의 판정 기준
        "pred": pred,                               # 판정결과
        "res_tag": res_tag,                         # PASS/FAIL
        "sc": sc,                                   # cross 필터 점수
        "sx": sx,                                   # x 필터 점수
        "time_ms": t,                               # 평균 실행시간(ms)
        "ops": ops,                                 # 연산횟수 N^2
    }

def print_case_result(result):
    print(f"\n- {result['name']} ---")                            # 패턴 이름 출력
    print(f"Cross 점수: {result['sc']}")                          # Cross 필터와 일치정도
    print(f"X 점수: {result['sx']}")                              # X 필터와 일치정도
    print(f"판정: {result['pred']} | expected: {result['expected']} | {result['res_tag']}")

def update_perf_map(perf_map, size, time_ms, ops):
    """성능기록저장"""
    if size not in perf_map:                            # size 라는 키가 없으면 만들기
        perf_map[size] = {"times": [], "ops": ops}      # 실행시간 저장용 빈 리스트, 연산횟수 N^2
    perf_map[size]["times"].append(time_ms)                   # [size]의 times리스트에 실행시간 추가

def handle_case_error(c_id, error):         
    print(f"⚠ {c_id} 처리 중 오류: {error}")           # 오류가 난 케이스만 건너 뛰고 실행하도록 처리

def run_json_mode():
    """data.json 기반 성능 분석 모드"""
    data = load_json_data("data.json")
    if data is None:
        return
    filters, cases = get_filters_and_cases(data)                # json 데이터에서 필터와 케이스를 가져옴

    if filters is None:                                         # 필터가 없으면 오류 메시지 출력 후 종료
        print("오류: filters 데이터가 없습니다.")
        return

    if not cases:                                               # 패턴이 없으면 오류 메시지 출력 후 종료
        print("오류: patterns(cases) 데이터가 없습니다.")
        return
    available_sizes = collect_available_sizes(filters)          # 필터 size를 수집하여 집합으로 반환
    print_loaded_filters(available_sizes)                       # [1] 필터로드
    
    print("\n# [2] 패턴 분석 (라벨 정규화 적용)")

    perf_map = {}                                               # 크기별 성능 기록 저장
    pass_cnt, fail_cnt = 0, 0                                   # P/F 카운트
    failed_details = []                                         # 실패 이유 저장


    for c_id, c_data in get_case_items(cases):         # 키(인덱스), 데이터 in 케이스(패턴)
        try:
            result = analyze_case(c_id, c_data, filters)    # 결과를 딕셔너리로 반환
            print_case_result(result)                       # 딕셔너리를 인자로 받아 케이스 결과 출력

            if result["res_tag"] == "PASS":
                pass_cnt += 1
            else:                                               # 판정 불일치와, 동점도 F
                fail_cnt += 1
                reason = (
                    "동점(UNDECIDED) 처리 규칙에 따라 FAIL" 
                    if result["pred"] == "UNDECIDED" 
                    else "판정 불일치"
                )
                failed_details.append(f"- {result['name']}: {reason}")    # 실패 케이스 정리용
            update_perf_map(perf_map, result["size"],result["time_ms"],result["ops"])
        except Exception as e:
            handle_case_error(c_id, e)                      # 오류가 난 케이스만 건너 뛰고 실행하도록 처리

    print_perf_table(perf_map)
    print_result_summary(pass_cnt, fail_cnt, failed_details)

def print_perf_table(perf_map):
    print("\n# [3] 성능 분석 (평균/10회)")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수':<10}")      
    print("-" * 40)

    for s in sorted(perf_map.keys()):                           # 키값을 오름차순 정렬 
        avg_t = sum(perf_map[s]["times"]) / len(perf_map[s]["times"])   # 순서대로 평균계산
        print(f"{s}×{s:<8} {avg_t:<15.6f} {perf_map[s]['ops']:<10}")    # 평균, 연산시간 출력

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