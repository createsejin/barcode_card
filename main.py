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


def create_barcode_clean():
    filename = "barcode_clean2.svg"

    dwg = svgwrite.Drawing(
        filename, size=("210mm", "297mm"), viewBox="0 0 793.70076 1122.5197"
    )

    # [상수 정의] 96 DPI 기준 1mm당 픽셀 값 (Inkscape 기본 단위)
    MM_TO_PX = 3.77952756

    # 2. 외곽 커팅선 x, y 위치
    card_x = 78.271
    card_y = 40.988
    card_w = 324.475
    card_h = 203.566
    stroke_w_px = 0.099 * MM_TO_PX

    # Inkscape 가시 상자 크기에 맞추기 위해, 내부 선 중심 좌표 및 크기 계산
    adjusted_x = card_x + (stroke_w_px / 2)
    adjusted_y = card_y + (stroke_w_px / 2)
    adjusted_w = card_w - stroke_w_px
    adjusted_h = card_h - stroke_w_px
    dwg.add(
        dwg.rect(
            insert=(adjusted_x, adjusted_y),
            size=(adjusted_w, adjusted_h),
            fill="none",
            stroke="black",
            stroke_width=stroke_w_px,
        )
    )

    # rolltainer barcode
    draw_inkscape_barcode(
        dwg=dwg, code="00000040", x=104.358, y=49.240, w=259.907, h=55.963
    )

    # worker barcode
    draw_inkscape_barcode(
        dwg=dwg, code="A300011", x=106.652, y=212.255, w=119.267, h=21.725
    )

    # rolltainer code text
    draw_inkscape_text(
        dwg=dwg, text="00000040", x=231.37704, y=127.08455, font="sans-serif"
    )

    # name text
    draw_inkscape_text(dwg=dwg, text="김종건", x=276.37198, y=231.96967, font="NSimSun")

    # [코드 미화 작업] 코드를 분석하기 편하게 들여쓰기(Indent)하여 저장
    raw_svg_string = dwg.tostring()  # 순수 XML 문자열 추출

    # minidom을 이용해 보기 좋게 정렬 (줄바꿈 \n 추가 및 탭 간격 적용)
    parsed_xml = minidom.parseString(raw_svg_string)
    pretty_svg_string = parsed_xml.toprettyxml(indent="  ")  # 2칸 들여쓰기

    # 최종 파일 쓰기
    with open(filename, "w", encoding="utf-8") as f:
        f.write(pretty_svg_string)

    print(f"'{filename}' 파일이 생성되었습니다.")


if __name__ == "__main__":
    create_barcode_clean()
