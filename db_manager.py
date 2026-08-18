import os
import sqlite3
from rich.console import Console
from rich.table import Table
import rich.box

def get_db_connection(db_path):
    """DB 연결 객체를 반환하는 공통 헬퍼 함수"""
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
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
    """rich 패키지를 이용해 한글 밀림 없는 깔끔한 표로 전체 작업자 목록 출력"""
    conn = get_db_connection(db_path)
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT pid, worker_code, name, is_active, rolltainer_code FROM pickers")
        rows = cursor.fetchall()
        conn.close()

        console = Console()
        table = Table(title="[bold cyan]📋 전체 작업자 목록[/bold cyan]", box=rich.box.ROUNDED)
        
        table.add_column("PID", justify="right", style="cyan")
        table.add_column("Worker Code", style="magenta")
        table.add_column("Name", style="green")
        table.add_column("Active", justify="center", style="yellow")
        table.add_column("Rolltainer Code", justify="right")

        for r in rows:
            active_mark = "🟢 1" if str(r["is_active"]) == "1" else "⚪ 0"
            table.add_row(
                str(r["pid"]),
                str(r["worker_code"] or ""),
                str(r["name"] or ""),
                active_mark,
                str(r["rolltainer_code"] or "")
            )

        console.print(table)
    except Exception as e:
        print(f"🚨 목록 조회 중 오류 발생: {e}")

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

def db_manage_active(db_path, pid_list=None):
    """
    pid_list가 있으면 해당 PID만 활성화(수정),
    없으면 현재 활성 상태인 작업자 목록만 조회(출력)
    """
    # 1. 수정 모드일 때
    if pid_list is not None:
        conn = get_db_connection(db_path)
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE pickers SET is_active = '0'")
            if pid_list:
                placeholders = ','.join(['?'] * len(pid_list))
                cursor.execute(f"UPDATE pickers SET is_active = '1' WHERE pid IN ({placeholders})", pid_list)
            conn.commit()
            print(f"✅ PID {pid_list} 작업자들을 활성화했습니다.")
        finally:
            conn.close()
            
    # 2. 조회 모드일 때 (pid_list가 None인 경우)
    else:
        conn = get_db_connection(db_path)
        if not conn: return
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pickers WHERE is_active = '1'")
        rows = cursor.fetchall()
        conn.close()

        console = Console()
        table = Table(title="[bold green]🟢 현재 활성(Active) 작업자 목록[/bold green]", box=rich.box.ROUNDED)
        table.add_column("PID", justify="right", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Rolltainer", justify="right")

        for r in rows:
            table.add_row(str(r["pid"]), str(r["name"]), str(r["rolltainer_code"]))
        
        console.print(table)
        console.print(f"[bold]총 활성 작업자 수: {len(rows)}명[/bold]")

def db_search_worker(db_path, keyword):
    """이름이나 코드로 작업자 검색 후 출력"""
    conn = get_db_connection(db_path)
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM pickers WHERE name LIKE ? OR worker_code LIKE ?"
        cursor.execute(query, (f"%{keyword}%", f"%{keyword}%"))
        rows = cursor.fetchall()
        conn.close()

        console = Console()
        table = Table(title=f"[bold yellow]🔍 '{keyword}' 검색 결과 ({len(rows)}건)[/bold yellow]", box=rich.box.ROUNDED)
        
        table.add_column("PID", justify="right", style="cyan")
        table.add_column("Worker Code", style="magenta")
        table.add_column("Name", style="green")
        table.add_column("Active", justify="center", style="yellow")
        table.add_column("Rolltainer Code", justify="right")

        for r in rows:
            active_mark = "🟢 1" if str(r["is_active"]) == "1" else "⚪ 0"
            table.add_row(
                str(r["pid"]),
                str(r["worker_code"] or ""),
                str(r["name"] or ""),
                active_mark,
                str(r["rolltainer_code"] or "")
            )

        console.print(table)
    except Exception as e:
        print(f"🚨 검색 중 오류 발생: {e}")