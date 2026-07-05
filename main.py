import glob
import os
import shutil
import subprocess
import sys
import csv
import svgwrite
from barcode import Code128
from barcode.writer import SVGWriter
import xml.etree.ElementTree as ET
from xml.dom import minidom


def draw_inkscape_barcode(dwg, code, x, y, w, h):
    """
    Inkscape 절대 좌표와 크기 기준으로 오차 없이 바코드를 그리는 함수
    :param dwg: svgwrite.Drawing 문서 객체
    :param code: 바코드에 담을 문자열 데이터 (예: "00000003")
    :param x: Inkscape 상의 절대 X 좌표 (px)
    :param y: Inkscape 상의 절대 Y 좌표 (px)
    :param w: 바코드 최종 가로 너비 (px)
    :param h: 바코드 최종 세로 높이 (px)
    """
    # 1. 바코드 라이브러리 원본 추출
    barcode_obj = Code128(str(code), writer=SVGWriter())
    barcode_bytes = barcode_obj.render({"write_text": False, "quiet_zone": 0.0})
    xml_root = ET.fromstring(barcode_bytes)

    # 2. 원본 가로 크기 추출 및 Y축 여백 제거를 위한 높이 고정
    orig_w = float(xml_root.get("width", "100").replace("mm", ""))
    orig_h = 15.0

    # 3. 중첩 SVG 상자틀(컨테이너) 생성
    barcode_box = dwg.svg(
        insert=(x, y),
        size=(w, h),
        viewBox=f"0 0 {orig_w} {orig_h}",
        preserveAspectRatio="none",
    )

    # 4. 자식 막대 주입 (Y좌표 여백 청소 로직 적용)
    for child in xml_root.iter():
        if child.tag.endswith("rect"):
            rw_str = child.get("width", "0")
            if rw_str == "100%":
                continue

            rx = child.get("x", "0").replace("mm", "")
            rw = rw_str.replace("mm", "")
            ry = "0"
            rh = "15.0"

            barcode_box.add(dwg.rect(insert=(rx, ry), size=(rw, rh), fill="black"))

    # 5. Inkscape 소수점 오차 방지를 위한 속성 강제 고정
    barcode_box["x"] = f"{x}"
    barcode_box["y"] = f"{y}"
    barcode_box["width"] = f"{w}"
    barcode_box["height"] = f"{h}"

    # 6. 메인 도화지에 바코드 상자 추가
    dwg.add(barcode_box)


# =========================================================================
# [새로운 설계] 사용자가 입력한 오리지널 태그 형태 그대로 출력하는 함수
# =========================================================================
def draw_inkscape_text(dwg, text, x, y, font):
    """
    보내주신 템플릿의 속성, 폰트크기, 스타일을 100% 똑같이 구현하는 함수
    :param dwg: svgwrite.Drawing 문서 객체
    :param text: 출력할 문자열 데이터
    :param x: 텍스트의 기준 X 절대좌표 (px)
    :param y: 텍스트의 기준 Y 절대좌표 (px)
    """
    # 원본에서 추출한 스타일 태그 문자열을 온전하게 그대로 이식
    text_style = (
        "font-size:23.0276px;"
        f"font-family:{font};"
        "text-align:center;"
        "text-anchor:middle;"
        "display:inline;"
        "fill:#000000;"
        "stroke-width:0.740741"
    )

    # 순수 text 엘리먼트 생성
    text_element = dwg.text(str(text), insert=(x, y), style=text_style)

    # 속성값 강제 지정
    text_element["id"] = f"text_{text}"
    text_element.attribs["xml:space"] = "preserve"

    dwg.add(text_element)


# =========================================================================
# 3. [핵심] 오프셋을 받아 개별 카드를 생성하는 컴포넌트 함수
# =========================================================================
def draw_single_card_component(dwg, name, name_code, rt_code, offset_x, offset_y):
    """
    기본 1번 카드 레이아웃 수식에 외부 격자 이동 거리(offset)를 더해 카드를 그립니다.
    """
    MM_TO_PX = 3.77952756
    stroke_w_px = 0.099 * MM_TO_PX  # 약 0.37417 px

    # [기본 카드 치수 정의]
    base_card_x = 78.271
    base_card_y = 40.988
    base_card_w = 324.475
    base_card_h = 203.566

    # 오프셋이 적용된 실제 사각형 시작 좌표 계산
    card_x = base_card_x + offset_x
    card_y = base_card_y + offset_y

    # Inkscape Cutting 박스 보정 공식 유지
    adjusted_x = card_x + (stroke_w_px / 2)
    adjusted_y = card_y + (stroke_w_px / 2)
    adjusted_w = base_card_w - stroke_w_px
    adjusted_h = base_card_h - stroke_w_px

    # 1. 외곽선 추가
    dwg.add(
        dwg.rect(
            insert=(adjusted_x, adjusted_y),
            size=(adjusted_w, adjusted_h),
            fill="none",
            stroke="black",
            stroke_width=stroke_w_px,
        )
    )

    # 2. 대차 코드 바코드 (상대 간격 반영)
    draw_inkscape_barcode(
        dwg=dwg,
        code=rt_code,
        x=card_x + (104.358 - base_card_x),
        y=card_y + (49.240 - base_card_y),
        w=259.907,
        h=55.963,
    )

    # 3. 작업자 코드 바코드 (상대 간격 반영)
    draw_inkscape_barcode(
        dwg=dwg,
        code=name_code,
        x=card_x + (106.652 - base_card_x),
        y=card_y + (212.255 - base_card_y),
        w=119.267,
        h=21.725,
    )

    # 4. 대차 코드 텍스트 (상대 간격 반영)
    draw_inkscape_text(
        dwg=dwg,
        text=rt_code,
        x=card_x + (231.37704 - base_card_x),
        y=card_y + (127.08455 - base_card_y),
        font="sans-serif",
    )

    # 5. 이름 텍스트 (상대 간격 반영)
    draw_inkscape_text(
        dwg=dwg,
        text=name,
        x=card_x + (276.37198 - base_card_x),
        y=card_y + (231.96967 - base_card_y),
        font="NSimSun",
    )


def generate_barcode_pages_from_csv(csv_file_path):
    """
    롤테이너 코드가 포함된 CSV 파일을 읽어 출근 여부가 1인 작업자만
    필터링하여 2x5 배열 페이지를 생성하는 함수
    """
    MM_TO_PX = 3.77952756
    stroke_w_px = 0.099 * MM_TO_PX  # 약 0.37417 px

    # 커팅선이 정확하게 포개어지도록 격자 이동 간격 설정
    card_step_w = 324.475 - stroke_w_px
    card_step_h = 203.566 - stroke_w_px

    # 1. CSV 파일 읽기 및 데이터 필터링
    active_workers = []

    with open(csv_file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # '출력 여부'가 '1'인 사람만 리스트에 담음
            is_active = row.get("출력 여부", "").strip()
            if is_active == "1":
                # [수정 포인트] 롤테이너 코드를 숫자로만 처리하거나 8자리 고정 형태로 맞추기 위해
                # zfill(8)을 사용해 입력값이 '1'이면 '00000001'로 포맷을 자동 변환합니다.
                raw_rt_code = row.get("롤테이너 코드", "").strip()
                formatted_rt_code = (
                    raw_rt_code.zfill(8) if raw_rt_code.isdigit() else raw_rt_code
                )

                active_workers.append(
                    {
                        "name": row.get("성명", "").strip(),
                        "name_code": row.get("작업자 코드", "").strip(),
                        "rt_code": formatted_rt_code,  # ◀ 파싱 및 변환된 롤테이너 코드 적용
                    }
                )

    # 2. 데이터를 5명씩 분할 (한 페이지당 세로 5줄 배치)
    chunked_pages = [
        active_workers[i : i + 5] for i in range(0, len(active_workers), 5)
    ]

    # 3. 페이지별 SVG 도화지 생성 및 배치 루프
    for page_idx, page_data in enumerate(chunked_pages):
        filename = f"barcode_page_{page_idx + 1}.svg"
        dwg = svgwrite.Drawing(
            filename, size=("210mm", "297mm"), viewBox="0 0 793.70076 1122.5197"
        )

        for row_idx, person in enumerate(page_data):
            # 데이터 1개당 좌측(0)과 우측(1)에 한 쌍으로 복제 배치
            for col_idx in range(2):
                grid_offset_x = col_idx * card_step_w
                grid_offset_y = row_idx * card_step_h

                # 개별 카드 컴포넌트 호출 (전달받은 실제 데이터를 칼같이 매핑)
                draw_single_card_component(
                    dwg=dwg,
                    name=person["name"],
                    name_code=person["name_code"],
                    rt_code=person["rt_code"],
                    offset_x=grid_offset_x,
                    offset_y=grid_offset_y,
                )

        # 4. 소스코드 미화 및 파일 저장 (Tab Size 4)
        raw_svg_string = dwg.tostring()
        parsed_xml = minidom.parseString(raw_svg_string)
        pretty_svg_string = parsed_xml.toprettyxml(indent="    ")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(pretty_svg_string)

        print(
            f"📄 페이지 {page_idx + 1} 생성 완료: '{filename}' (실제 배치 인원: {len(page_data)}명)"
        )


def get_base_dir():
    """실행 파일(.exe) 또는 스크립트(.py)가 위치한 디렉토리 경로를 반환합니다."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def open_explorer_at_base():
    """현재 실행 파일이 있는 폴더를 파일 탐색기로 엽니다."""
    base_dir = get_base_dir()
    print(f"📂 파일 탐색기를 엽니다: {base_dir}")
    try:
        # os.startfile을 사용하면 윈도우 기본 파일 탐색기로 해당 폴더가 열립니다.
        os.startfile(base_dir)
    except Exception as e:
        # 예외 상황 발생 시 subprocess로 explorer 실행 안전장치
        subprocess.run(["explorer", base_dir])


def get_target_download_dir(base_dir):
    """config.txt에서 download_folder= 값을 찾아 반환하거나 시스템 기본 경로를 반환합니다."""
    config_path = os.path.join(base_dir, "config.txt")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    # 공백 제거 및 주석(#) 처리된 라인 제외
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # download_folder= 구문이 포함되어 있는지 확인
                    if line.startswith("download_folder="):
                        # '=' 기준 우측의 경로 값 추출 및 양끝 공백 제거
                        custom_dir = line.split("=", 1)[1].strip()

                        # 경로가 존재하고 유효한 폴더인지 검증
                        if custom_dir and os.path.isdir(custom_dir):
                            print(
                                f"📂 config.txt (download_folder) 경로 감지: {custom_dir}"
                            )
                            return custom_dir
                        elif custom_dir:
                            print(
                                f"⚠️ config.txt에 적힌 경로가 올바르지 않습니다: {custom_dir}"
                            )
        except Exception as e:
            print(f"⚠️ config.txt 읽기 실패 (기본 경로로 대체합니다): {e}")

    # 파일이 없거나, 설정값이 비어있거나, 경로가 유효하지 않다면 시스템 기본 다운로드 폴더 사용
    user_profile = os.environ.get("USERPROFILE", "")
    default_download = os.path.join(user_profile, "Downloads") if user_profile else ""
    print(f"📂 시스템 기본 다운로드 경로 사용: {default_download}")
    return default_download


def get_latest_csv_file(target_dir):
    """지정된 디렉토리 내에서 가장 최근에 수정된 .csv 파일의 경로를 반환합니다."""
    if not target_dir or not os.path.exists(target_dir):
        return None

    # 폴더 내의 모든 .csv 파일 검색
    csv_files = glob.glob(os.path.join(target_dir, "*.csv"))
    if not csv_files:
        return None

    # 수정 시간(mtime) 기준 내림차순 정렬하여 가장 최근 파일 획득
    latest_file = max(csv_files, key=os.path.getmtime)
    return latest_file


def run_copy_tasks():
    """설정된 경로에서 최신 CSV 파일을 찾아 실행 파일 옆으로 input_data.csv로 복사합니다."""
    print("🔄 최신 CSV 데이터 복사 작업을 시작합니다...")

    base_dir = get_base_dir()

    # 1. 탐색할 다운로드 디렉토리 결정
    download_dir = get_target_download_dir(base_dir)
    if not download_dir:
        print("❌ 유효한 다운로드 폴더 경로를 지정할 수 없습니다.")
        return

    # 2. 가장 최근에 수정된 CSV 파일 탐색
    src_file = get_latest_csv_file(download_dir)
    if not src_file:
        print(f"❌ '{download_dir}' 폴더 내에 CSV 파일이 존재하지 않습니다.")
        return

    # 3. 목적지 파일명 지정 (실행 파일 옆 input_data.csv)
    dest_file = os.path.join(base_dir, "input_data.csv")

    try:
        # 4. 복사 실행
        (
            shutil.copy2(src_file)
            if src_file == dest_file
            else shutil.copy2(src_file, dest_file)
        )
        print(f"✅ 가져온 원본 파일: {os.path.basename(src_file)}")
        print(f"👉 저장된 위치: {dest_file}")
        print("🎉 복사 작업이 성공적으로 끝났습니다.")

    except Exception as e:
        print(f"🚨 복사 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    args = set(sys.argv)
    base_dir = get_base_dir()

    # 1. -p 또는 --path 명령어가 인자로 들어왔을 때 -> 탐색기 오픈
    if {"-p", "--path"} & args:
        open_explorer_at_base()

    # 2. -c 또는 --copy 명령어가 인자로 들어왔을 때 -> 최신 CSV 복사
    elif {"-c", "--copy"} & args:
        run_copy_tasks()

    else:
        # 기본 실행 시에는 실행 파일 바로 옆의 input_data.csv를 사용
        csv_path = os.path.join(base_dir, "input_data.csv")
        if os.path.exists(csv_path):
            generate_barcode_pages_from_csv(csv_path)
        else:
            print(f"❌ 실행을 위한 '{csv_path}' 파일이 없습니다.")
            print("💡 먼저 'barcode -c' 명령어로 데이터를 가져오세요.")
