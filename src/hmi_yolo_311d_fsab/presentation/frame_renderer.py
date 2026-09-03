from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

from hmi_yolo_311d_fsab.domain.camera import CameraFrame
from hmi_yolo_311d_fsab.domain.inference import InferenceResult


def frame_to_image(frame: CameraFrame) -> QImage:
    return QImage(
        frame.rgb_data,
        frame.width,
        frame.height,
        frame.width * 3,
        QImage.Format.Format_RGB888,
    ).copy()


def render_frame(frame: CameraFrame, result: InferenceResult) -> QImage:
    image = frame_to_image(frame)
    painter = QPainter(image)
    painter.setPen(QPen(QColor(30, 255, 100), 3))
    painter.setFont(QFont("Sans Serif", 11))
    for detection in result.detections:
        box = detection.box
        painter.drawRect(QRect(box.x, box.y, box.width, box.height))
        label = f"{detection.label} {detection.confidence:.0%}"
        label_y = max(16, box.y - 4)
        painter.drawText(box.x, label_y, label)
    painter.end()
    return image
