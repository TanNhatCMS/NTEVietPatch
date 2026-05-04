# NTE Việt Hóa — Neverness to Everness

Công cụ cài đặt bản Việt hoá không chính thức cho game **Neverness to Everness**.

[![Discord](https://img.shields.io/badge/Discord-Tham%20gia%20server-5865F2?style=flat&logo=discord&logoColor=white)](https://discord.gg/ARfX5gf8Wn)

---

## Yêu cầu

- Game **Neverness to Everness** (CN hoặc Global) đã cài đặt
- **Hệ điều hành**: Windows 10/11 64-bit (Đã hỗ trợ bản 1.0.0)
- **Linux / Steam Deck**: Sắp ra mắt (Coming soon)
- Python 3.10+ *(nếu chạy từ source)*

---

## Cách dùng nhanh (dùng tool)

1. Chạy **NTEVietPatch.exe** (hoặc `python main.py`)
2. Nhấn **🔍 Tự động** để tìm thư mục game, hoặc duyệt thủ công
3. Nhấn **⬇ Tải & Cài Patch** → tool sẽ tải về và cài tự động
4. Mở game và chờ khoảng **10 giây** — một cửa sổ nhỏ sẽ xuất hiện (đây là cửa sổ của mod, giữ nguyên trong lúc chơi)

> ⚠ **Đừng dùng Alt+F4 hoặc nút X để tắt game!** Dùng menu thoát trong game.

---

## Cài đặt thủ công (không dùng tool)

### Bước 1 — Tải file mod

Vào [**Releases**](https://github.com/CallMeDangDev/NTE-Viet-Hoa/releases) và tải 3 file:

```
netbios.dll
game_vi.dat
viet_font.ttf
```

### Bước 2 — Tìm thư mục game

Điều hướng đến:

```
<vị trí cài game>\Neverness To Everness\Client\WindowsNoEditor\HT\Binaries\Win64\
```

> 💡 **Gợi ý:** Click chuột phải vào shortcut game → *Mở vị trí file* → vào tiếp `Binaries\Win64\`

Đây là thư mục chứa `HTGame.exe`.

### Bước 3 — Sao chép file mod

Chép cả 3 file vào thư mục `Win64\`:

```
Win64\
├── HTGame.exe
├── netbios.dll      ← sao chép vào đây
├── game_vi.dat      ← sao chép vào đây
└── viet_font.ttf    ← sao chép vào đây
```

### Bước 4 — Khởi động game

Mở game như bình thường. Sau khoảng **10 giây**, một cửa sổ nhỏ sẽ xuất hiện — đây là cửa sổ của mod.

> ⚠ **Đừng dùng Alt+F4 hoặc nút X để tắt game!** Để cửa sổ đó nguyên trong lúc chơi.

---

## Gỡ cài đặt

Dùng tab **↩ Khôi Phục** trong tool để phục hồi file gốc, hoặc xoá thủ công 3 file khỏi thư mục `Win64\`:

```
netbios.dll
game_vi.dat
viet_font.ttf
```

---

## Cài đặt Linux / Proton

Trên Linux, dùng `version.dll` thay vì `netbios.dll`.  
Chọn **Linux / Proton — version.dll** trong tab **⚙ Cài đặt** của tool trước khi cài patch.

---

## Cấu trúc dự án

```
NTEVietPatch/
├── main.py           # Điểm khởi động, App controller
├── gui.py            # Giao diện Tkinter (dark mode)
├── github_loader.py  # Tải file từ GitHub Releases
├── file_patcher.py   # Detect game, backup, apply patch
├── config.json       # Cấu hình (tự tạo khi chạy lần đầu)
├── mods/             # Thư mục chứa mod đã tải về
└── backup/           # Thư mục chứa các bản sao lưu
```

Nếu bạn muốn đóng góp code hoặc tự build lại ứng dụng, hãy sử dụng các file `.ps1` đã được chuẩn bị sẵn:

1. **Cài đặt môi trường:**
   Chạy file `.\setup.ps1` để tạo môi trường ảo `.venv` và cài đặt dependencies.
2. **Chạy test giao diện:**
   Chạy file `.\run.ps1` để mở app bằng Python mà không cần build thành EXE.
3. **Đóng gói EXE:**
   Chạy file `.\build.ps1` để dọn dẹp cache cũ và tự động build ra file EXE mới trong thư mục `dist\`.

> ⚠ **Yêu cầu**: Python phải có **Tkinter** (bản từ [python.org](https://www.python.org/downloads/) hoặc `uv`-managed CPython).  
> Một số bản Python stripped (FlyEnv, conda minimal, v.v.) không có Tkinter và sẽ báo lỗi.

## Bản quyền

MIT License
