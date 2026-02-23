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


images = get_valid_image_paths('data')

model = YOLO('yolov8n.pt')

result = model.predict(images[0])

image = cv2.imread(images[0])
weight, height, _ = image.shape
img_area = weight * height

metrics = analyze_image_metrics(
    detections=result[0].boxes,
    image_area=img_area,
    model_names=model.names,
    target_classes=["car", "truck"]
)

print(metrics)

from types import SimpleNamespace
import numpy as np

def test_analyze_image_metrics():
    # Эмулируем структуру YOLOv8 Boxes, используя xywh
    # Формат: [x_center, y_center, width, height]
    fake_detections = [
        # Первый бокс: 'car', площадь 100 * 100 = 10,000
        SimpleNamespace(cls=np.array([0]), xywh=np.array([[60, 60, 100, 100]])),
        
        # Второй бокс: 'truck', площадь 200 * 200 = 40,000
        SimpleNamespace(cls=np.array([1]), xywh=np.array([[150, 150, 200, 200]])),
        
        # Третий бокс: еще один 'car', площадь 50 * 50 = 2,500
        SimpleNamespace(cls=np.array([0]), xywh=np.array([[45, 45, 50, 50]])),
        
        # Четвёртый бокс: 'person' (id=5), должен быть проигнорирован
        SimpleNamespace(cls=np.array([5]), xywh=np.array([[2, 2, 5, 5]]))
    ]
    
    # Входные данные
    image_area = 1000 * 1000  # 1,000,000 пикселей
    model_names = {0: 'car', 1: 'truck', 5: 'person'}
    target_classes = ['car', 'truck']

    # Вызов твоей функции
    result_metrics = analyze_image_metrics(fake_detections, image_area, model_names, target_classes)
    print(result_metrics)
    # Проверки
    assert result_metrics['car'] == 2, f"ОШИБКА: Ожидалось 2 машины, но найдено {result_metrics['car']}"
    assert result_metrics['truck'] == 1, f"ОШИБКА: Ожидалось 1 грузовик, но найдено {result_metrics['truck']}"
    assert result_metrics['total_vehicles'] == 3, f"ОШИБКА: Ожидалось 3 ТС, но найдено {result_metrics['total_vehicles']}"

    # Расчет ожидаемой плотности:
    # Суммарная площадь: 10000 + 40000 + 2500 = 52500
    # Плотность: 52500 / 1000000 = 0.0525
    expected_density = 0.0525
    assert np.isclose(result_metrics['density'], expected_density), \
        f"ОШИБКА: Ожидалась плотность {expected_density}, но получено {result_metrics['density']}"
    
    # Средняя площадь: 52500 / 3 = 17500.0
    expected_avg_area = 17500.0
    assert np.isclose(result_metrics['avg_bbox_area'], expected_avg_area), \
        f"ОШИБКА: Ожидалась ср. площадь {expected_avg_area}, но получено {result_metrics['avg_bbox_area']}"

    print("Тест analyze_image_metrics пройден успешно!")

test_analyze_image_metrics()