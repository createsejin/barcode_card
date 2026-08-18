import argparse
import os
import subprocess
import sys

from db_manager import (
    db_list_workers,
    db_reset_active,
    db_manage_active,
    db_search_worker,
)
from barcode_engine import generate_barcode_pages_from_db

def get_base_dir():
    """실행 파일(.exe) 또는 스크립트(.py)가 위치한 디렉토리 경로를 반환"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def open_explorer_at_base():
    """실행 파일이 있는 폴더를 파일 탐색기로 오픈"""
    base_dir = get_base_dir()
    print(f"📂 파일 탐색기를 엽니다: {base_dir}")
    try:
        os.startfile(base_dir)
    except Exception:
        subprocess.run(["explorer", base_dir])

if __name__ == "__main__":
    base_dir = get_base_dir()
    db_path = r"D:\DataCenter\work_data.db"  # 필요에 따라 경로 조정

    parser = argparse.ArgumentParser(description="Picker Barcode Generator & DB Manager")
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # 서브 명령어 정의
    subparsers.add_parser("generate", help="is_active=1인 작업자들의 SVG 바코드 생성")
    subparsers.add_parser("list", help="전체 작업자 목록 및 상태 조회 (rich 표)")
    subparsers.add_parser("reset", help="모든 작업자의 is_active를 0으로 초기화")

    # main.py의 argparse 부분 수정
    active_parser = subparsers.add_parser("active", help="지정한 PID들만 활성화하거나, 입력 안 하면 현재 활성 상태 조회")
    # nargs='*' 로 변경하여 인자가 없어도 허용
    active_parser.add_argument("pids", nargs="*", type=int, help="활성화할 작업자의 PID 목록")

    search_parser = subparsers.add_parser("search", help="이름 또는 코드로 작업자 검색")
    search_parser.add_argument("keyword", type=str, help="검색할 이름 또는 코드")

    parser.add_argument("-p", "--path", action="store_true", help="출력 폴더 열기")

    args = parser.parse_args()

    # 명령어 분기 처리
    if args.path:
        open_explorer_at_base()
    elif args.command == "list":
        db_list_workers(db_path)
    elif args.command == "reset":
        db_reset_active(db_path)
    elif args.command == "active":
        # 인자가 하나라도 있으면(수정) 리스트 전달, 없으면(조회) None 전달
        if len(args.pids) > 0:
            db_manage_active(db_path, args.pids)
        else:
            db_manage_active(db_path, None)
    elif args.command == "search":
        db_search_worker(db_path, args.keyword)
    else:
        # 인자 없이 실행하거나 'generate' 입력 시 바코드 생성 동작
        if os.path.exists(db_path):
            generate_barcode_pages_from_db(db_path, base_dir)
        else:
            print(f"❌ 데이터베이스 파일이 존재하지 않습니다: {db_path}")