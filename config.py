# config.py

# --- App Version ---
APP_VERSION = "1.0.0"

# --- Repositories ---
# Repo chứa các file mod (Việt Hóa)
GITHUB_MOD_REPO = "CallMeDangDev/NTE-Viet-Hoa"
GITHUB_MOD_API = "https://api.github.com/repos/CallMeDangDev/NTE-Viet-Hoa/releases"

# Repo chứa bản cập nhật của chính phần mềm (Tool EXE)
GITHUB_APP_REPO = "TanNhatCMS/NTEVietPatch"
GITHUB_APP_API = "https://api.github.com/repos/TanNhatCMS/NTEVietPatch/releases/latest"

# --- Game Details ---
GAME_NAME = "Neverness to Everness"
GAME_EXE = "HTGame.exe"
GAME_EXE_ALT = "HTGame-Win64-Shipping.exe"
GAME_SUBDIR = r"Client\WindowsNoEditor\HT\Binaries\Win64"

# --- Mod Files ---
# Danh sách các file mod sẽ được chép vào thư mục game
MOD_FILES = [
    "netbios.dll", 
    "version.dll",
    "game_vi.dat", 
    "viet_font.ttf"
]
