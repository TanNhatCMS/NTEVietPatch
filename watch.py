import os
import sys
import time
import subprocess

def get_mtimes():
    mtimes = {}
    for root, _, files in os.walk("."):
        # Bỏ qua thư mục .venv và các file không liên quan
        if ".venv" in root or "__pycache__" in root:
            continue
        for f in files:
            if (f.endswith(".py") or f.endswith(".css")) and f != "watch.py":
                p = os.path.join(root, f)
                try:
                    mtimes[p] = os.stat(p).st_mtime
                except FileNotFoundError:
                    pass
    return mtimes

def main():
    print("👀 Đang theo dõi thay đổi code... (Nhấn Ctrl+C để thoát)")
    mtimes = get_mtimes()
    process = subprocess.Popen([sys.executable, "main.py"])
    
    try:
        while True:
            time.sleep(1)
            new_mtimes = get_mtimes()
            if new_mtimes != mtimes:
                print("\n[Dev] 🔄 Phát hiện thay đổi file, đang khởi động lại app...\n")
                process.terminate()
                process.wait()
                process = subprocess.Popen([sys.executable, "main.py"])
                mtimes = new_mtimes
            elif process.poll() is not None:
                # Người dùng tự đóng app
                break
    except KeyboardInterrupt:
        process.terminate()

if __name__ == "__main__":
    main()
