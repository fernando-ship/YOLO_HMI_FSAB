import logging
import sys
from pathlib import Path

from hmi_yolo_311d_fsab.app.bootstrap import create_controller
from hmi_yolo_311d_fsab.infrastructure.config import ConfigurationError


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    try:
        controller = create_controller(project_root)
        return controller.run()
    except ConfigurationError as exc:
        logging.getLogger(__name__).error("No se pudo iniciar: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
