import glob
import os
import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
import svgwrite
from barcode import Code128
from barcode.writer import SVGWriter

from db_manager import fetch_active_workers_from_db

def draw_inkscape_barcode(dwg, code, x, y, w, h):
    """Inkscape 절대 좌표와 크기 기준으로 오차 없이 바코드를 그리는 함수"""
    barcode_obj = Code128(str(code), writer=SVGWriter())
    barcode_bytes = barcode_obj.render({"write_text": False, "quiet_zone": 0.0})
    xml_root = ET.fromstring(barcode_bytes)

    orig_w = float(xml_root.get("width", "100").replace("mm", ""))
    orig_h = 15.0

    barcode_box = dwg.svg(
        insert=(x, y),
        size=(w, h),
        viewBox=f"0 0 {orig_w} {orig_h}",
        preserveAspectRatio="none",
    )

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

    barcode_box["x"] = f"{x}"
    barcode_box["y"] = f"{y}"
    barcode_box["width"] = f"{w}"
    barcode_box["height"] = f"{h}"

    dwg.add(barcode_box)

def draw_inkscape_text(dwg, text, x, y, font):
    """템플릿 속성, 폰트크기, 스타일을 동일하게 구현하는 텍스트 함수"""
    text_style = (
        "font-size:23.0276px;"
        f"font-family:{font};"
        "text-align:center;"
        "text-anchor:middle;"
        "display:inline;"
        "fill:#000000;"
        "stroke-width:0.740741"
    )

    text_element = dwg.text(str(text), insert=(x, y), style=text_style)
    text_element["id"] = f"text_{text}"
    text_element.attribs["xml:space"] = "preserve"

    dwg.add(text_element)

def draw_single_card_component(dwg, name, name_code, rt_code, offset_x, offset_y):
    """오프셋을 받아 개별 카드를 생성하는 컴포넌트 함수"""
    MM_TO_PX = 3.77952756
    stroke_w_px = 0.099 * MM_TO_PX

    base_card_x = 78.271
    base_card_y = 40.988
    base_card_w = 324.475
    base_card_h = 203.566

    card_x = base_card_x + offset_x
    card_y = base_card_y + offset_y

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

    # 2. 대차 코드 바코드
    draw_inkscape_barcode(dwg=dwg, code=rt_code, x=card_x + (104.358 - base_card_x), y=card_y + (49.240 - base_card_y), w=259.907, h=55.963)
    # 3. 작업자 코드 바코드
    draw_inkscape_barcode(dwg=dwg, code=name_code, x=card_x + (106.652 - base_card_x), y=card_y + (212.255 - base_card_y), w=119.267, h=21.725)
    # 4. 대차 코드 텍스트
    draw_inkscape_text(dwg=dwg, text=rt_code, x=card_x + (231.37704 - base_card_x), y=card_y + (127.08455 - base_card_y), font="sans-serif")
    # 5. 이름 텍스트
    draw_inkscape_text(dwg=dwg, text=name, x=card_x + (276.37198 - base_card_x), y=card_y + (231.96967 - base_card_y), font="NSimSun")

def generate_barcode_pages_from_db(db_path, base_dir):
    """SQLite DB에서 데이터를 읽어 실행 파일 기준 output 폴더에 2x5 배열 SVG 생성"""
    MM_TO_PX = 3.77952756
    stroke_w_px = 0.099 * MM_TO_PX

    card_step_w = 324.475 - stroke_w_px
    card_step_h = 203.566 - stroke_w_px

    # 무조건 실행 파일(base_dir) 기준 output 폴더 지정
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    existing_files = glob.glob(os.path.join(output_dir, "*.svg"))
    if existing_files:
        print(f"⚠️ 'output' 폴더에 이미 {len(existing_files)}개의 기존 결과물 파일이 존재합니다.")
        user_input = input("🔄 기존 파일을 모두 삭제하고 새로 생성하시겠습니까? (y/n): ").strip().lower()

        if user_input in ["y", "yes"]:
            print("🧹 구버전 파일을 안전하게 삭제하는 중...")
            for file_path in existing_files:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"❌ 파일 삭제 중 오류: {e}")
            print("✅ 기존 파일 초기화 완료.")
        else:
            print("🛑 작업을 취소합니다. 기존 파일을 유지합니다.")
            return

    active_workers = fetch_active_workers_from_db(db_path)
    if not active_workers:
        print("⚠️ 출력할 활성 작업자(is_active = 1)가 없습니다.")
        return

    chunked_pages = [active_workers[i : i + 5] for i in range(0, len(active_workers), 5)]

    for page_idx, page_data in enumerate(chunked_pages):
        filename = f"barcode_page_{page_idx + 1}.svg"
        full_output_path = os.path.join(output_dir, filename)

        dwg = svgwrite.Drawing(
            full_output_path, size=("210mm", "297mm"), viewBox="0 0 793.70076 1122.5197"
        )

        for row_idx, person in enumerate(page_data):
            for col_idx in range(2):
                grid_offset_x = col_idx * card_step_w
                grid_offset_y = row_idx * card_step_h

                draw_single_card_component(
                    dwg=dwg,
                    name=person["name"],
                    name_code=person["name_code"],
                    rt_code=person["rt_code"],
                    offset_x=grid_offset_x,
                    offset_y=grid_offset_y,
                )

        raw_svg_string = dwg.tostring()
        parsed_xml = minidom.parseString(raw_svg_string)
        pretty_svg_string = parsed_xml.toprettyxml(indent="    ")

        with open(full_output_path, "w", encoding="utf-8") as f:
            f.write(pretty_svg_string)

        print(f"📄 페이지 {page_idx + 1} 생성 완료: '{filename}' (배치: {len(page_data)}명)")

    print(f"\n🎉 모든 바코드 생성이 완료되었습니다! 총 {len(chunked_pages)}개 페이지 생성.")

    try:
        os.startfile(output_dir)
    except Exception:
        subprocess.run(["explorer", output_dir])