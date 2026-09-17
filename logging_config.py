import logging
from pathlib import Path


# =========================
# Create Logs Folder
# =========================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


# =========================
# Log File
# =========================

LOG_FILE = LOG_DIR / "app.log"

# =========================
# Logging Configuration
# =========================

logging.basicConfig(
    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),

    handlers=[
        logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        ),

        logging.StreamHandler()
    ]
)


logger = logging.getLogger("ecommerce")