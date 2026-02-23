import os, cv2, csv, argparse, datetime
from ultralytics import YOLO
from tqdm import tqdm
import numpy as np
from fpdf import FPDF
from fpdf.enums import XPos, YPos

def get_valid_image_paths(source_dir: str) -> list[str]:
    image_paths = []
    allowed_extensions = {'.jpg', '.jpeg', '.png'}

    files = os.listdir(source_dir)
    if files is None or len(files) == 0:
        raise Exception("files is None or len(files) > 0")
    
    for file in sorted(files):
        fname, fext = os.path.splitext(file)
        if fext.lower() in allowed_extensions:
            full_path = os.path.join(source_dir, file)
            if cv2.imread(full_path) is None:
                continue
            image_paths.append(full_path)

    
    return image_paths 

def analyze_image_metrics(detections, image_area, model_names, target_classes):
    # Инициализируем счётчики для каждого целевого класса
    object_counts = {transport_cls: 0 for transport_cls in target_classes}
    # Список для хранения площадей всех bounding box'ов
    total_bbox_area = 0
    total_bbox_trasport_area = 0

    transports_count = 0

    # ну получается  так что мне надо пройти по всем найденным объектам
    for det in detections:
        # det - это херь которая хранит наш бокс и всю залупу, точнее xywh
        box = det.xywh[0].tolist()
        x, y, w, h = box
        area = w * h

        # так мне нужен ID точбы определить название есть ли он в target_classes
        det_id = int(det.cls[0])
        det_name = model_names[det_id]

        # увеличиваем площади
        if det_name in target_classes:
            total_bbox_trasport_area += area
            transports_count += 1
            object_counts[det_name] += 1
        total_bbox_area += area
    
    # Считаем общее количество транспортных средств
    total_vehicles = transports_count
    # Вычисляем плотность - долю изображения, занятую объектами
    density = total_bbox_trasport_area / image_area
    # Вычисляем среднюю площадь bounding box'а
    avg_bbox_area = total_bbox_trasport_area / transports_count
    # Формируем отчёт с метриками
    report = {
        'total_vehicles': total_vehicles,
        'density': round(density, 4),
        'avg_bbox_area': round(avg_bbox_area, 2),
        **object_counts
    }

    return report


def find_highlight_examples(all_reports, top_n=3):
    """Находит наиболее показательные примеры в наборе данных."""
    pass


def generate_visualizations(model, examples_to_visualize, source_dir, output_dir, conf):
    """Создаёт визуальные артефакты (изображения с аннотациями) для отчёта."""
    pass


def classify_scene(report, thresholds):
    """Классифицирует сцену на основе метрик и порогов."""
    pass


if __name__ == "__main__":
    images = get_valid_image_paths('data')

    model = YOLO('yolov8n.pt')
    target_classes = [ 'car', 'bus']
    for image in images:
        results = model.predict(image, conf=0.25)
        result = results[0]
        image_area = None#

        metrics = analyze_image_metrics(
            detections=result.boxes,
            image_area=image_area,
            model_names=model.names,
            target_classes=target_classes
        )

        best_examples = find_highlight_examples(metrics)
        generate_visualizations(
            model=model,
            examples_to_visualize=best_examples,
            source_dir='ttf',
            output_dir='report_output',
            conf=0.25
        )






    print("Этап инициализации завершён. Среда настроена, каркас скрипта создан.")