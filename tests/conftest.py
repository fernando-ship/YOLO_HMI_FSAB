import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["HMI_YOLO_PLC_MODE"] = "simulated"
os.environ["HMI_YOLO_SIMULATE_CONNECTION_ERROR"] = "false"

