import os
import sqlite3
import rich.box
from rich.console import Console
from rich.table import Table

def get_db_connection(db_path):
    """DB 연결 객체를 반환하는 공통 헬퍼 함수"""
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 컬럼 이름으로 접근 가능하게 설정
    return conn

def fetch_active_workers_from_db(db_path):
    """is_active가 1인 활성 작업자 데이터를 조회하여 리스트로 반환"""
    active_workers = []
    conn = get_db_connection(db_path)
    if not conn:
        return active_workers

    try:
        cursor = conn.cursor()
        query = """
            SELECT worker_code, name, is_active, rolltainer_code 
            FROM pickers 
            WHERE is_active = '1' OR is_active = 1
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            raw_rt_code = str(row["rolltainer_code"] or "").strip()
            formatted_rt_code = (
                raw_rt_code.zfill(8) if raw_rt_code.isdigit() else raw_rt_code
            )

            active_workers.append({
                "name": str(row["name"] or "").strip(),
                "name_code": str(row["worker_code"] or "").strip(),
                "rt_code": formatted_rt_code,
            })
    except Exception as e:
        print(f"🚨 SQLite 데이터 조회 중 오류 발생: {e}")
    finally:
        conn.close()

    return active_workers

def db_list_workers(db_path):
    conn = get_db_connection(db_path)
    if not conn: return
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pickers")
    rows = cursor.fetchall()
    
    console = Console()
    table = Table(title="[bold blue]작업자 목록[/bold blue]", box=rich.box.ROUNDED)
    
    # 여기서 각 컬럼의 스타일과 정렬을 지정할 수 있어
    table.add_column("PID", style="cyan")
    table.add_column("Worker Code", style="magenta")
    table.add_column("Name", style="green")
    table.add_column("Active", style="yellow")
    table.add_column("Rolltainer", justify="right")

    for r in rows:
        table.add_row(
            str(r["pid"]), 
            str(r["worker_code"]), 
            str(r["name"]), 
            "🟢 1" if str(r["is_active"]) == "1" else "⚪ 0",
            str(r["rolltainer_code"])
        )
    
    console.print(table)

def db_reset_active(db_path):
    """모든 작업자의 is_active를 0으로 초기화"""
    conn = get_db_connection(db_path)
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pickers SET is_active = '0'")
        conn.commit()
        print("🔄 모든 작업자의 출근 여부(is_active)가 '0'으로 초기화되었습니다.")
    except Exception as e:
        print(f"🚨 초기화 중 오류 발생: {e}")
    finally:
        conn.close()

def db_set_active_by_pids(db_path, pid_list):
    """지정한 PID들만 is_active = '1'로 설정하고 나머지는 '0'으로 설정"""
    conn = get_db_connection(db_path)
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        # 전체 0으로 초기화 후 선택된 PID만 1로 변경
        cursor.execute("UPDATE pickers SET is_active = '0'")
        
        if pid_list:
            placeholders = ','.join(['?'] * len(pid_list))
            query = f"UPDATE pickers SET is_active = '1' WHERE pid IN ({placeholders})"
            cursor.execute(query, pid_list)
            
        conn.commit()
        print(f"✅ 지정한 PID {pid_list}번 작업자들의 상태를 활성화(1)했습니다.")
    except Exception as e:
        print(f"🚨 상태 변경 중 오류 발생: {e}")
    finally:
        conn.close()

def db_search_worker(db_path, keyword):
    """이름이나 코드로 작업자 검색"""
    conn = get_db_connection(db_path)
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM pickers WHERE name LIKE ? OR worker_code LIKE ?"
        cursor.execute(query, (f"%{keyword}%", f"%{keyword}%"))
        rows = cursor.fetchall()

        print(f"\n🔍 '{keyword}' 검색 결과 ({len(rows)}건):")
        for r in rows:
            print(f"- PID: {r['pid']}, 이름: {r['name']}, 코드: {r['worker_code']}, 활성: {r['is_active']}, 롤테이너: {r['rolltainer_code']}")
    except Exception as e:
        print(f"🚨 검색 중 오류 발생: {e}")
    finally:
        conn.close()