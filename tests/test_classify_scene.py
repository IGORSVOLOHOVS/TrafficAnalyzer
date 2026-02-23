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

def classify_scene(report, thresholds):
    count = report['total_vehicles']
    density = report['density']

    # Empty scene - нет транспортных средств
    if count == 0:
        return 'Empty'

    # Traffic Jam - много машин и высокая плотность (пробка)
    if count >= thresholds['jam_count'] and density >= thresholds['jam_density']:
        return 'Traffic Jam'

    # Single Big Object - аномалия: 1-2 объекта создают высокую плотность
    if count <= 2 and density > thresholds['single_density']:
        return 'Single Big Object'

    # Heavy Traffic - много машин, но не пробка
    if count >= thresholds['heavy_count']:
        return 'Heavy Traffic'

    # Sparse Traffic - все остальные случаи (несколько машин, свободное движение)
    return 'Sparse Traffic'

        # ("Не аномалия (слишком низкая плотность)", {'total_vehicles': 1, 'density': 0.14}, 'Sparse Traffic'),
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
thresholds = {
    'jam_count': 10,       # Порог количества для пробки
    'jam_density': 0.3,    # Порог плотности для пробки
    'heavy_count': 5,      # Порог количества для плотного движения
    'single_density': 0.15 # Порог плотности для крупного объекта
}
scene = classify_scene(
    report=metrics,
    thresholds=thresholds
)
print(scene)

def test_classify_scene():
    """(ТЕСТ) Проверяет корректность работы классификатора сцен classify_scene."""
    # Определяем тестовые пороги
    test_thresholds = {
        'jam_count': 10, 'jam_density': 0.3,
        'heavy_count': 5, 'single_density': 0.15,
    }

    # Создаём набор тестовых сценариев (кейсов)
    test_cases = [
        # Имя теста, Входной отчет, Ожидаемый результат
        ("Пустая сцена", {'total_vehicles': 0, 'density': 0.0}, 'Empty'),
        
        ("Явная пробка", {'total_vehicles': 15, 'density': 0.4}, 'Traffic Jam'),
        
        ("Граничный случай пробки (по количеству)", {'total_vehicles': 11, 'density': 0.31}, 'Traffic Jam'),
        
        ("Не пробка (не хватает плотности)", {'total_vehicles': 15, 'density': 0.29}, 'Heavy Traffic'),
        
        # ("Не пробка (не хватает количества)", {'total_vehicles': 10, 'density': 0.4}, 'Heavy Traffic'),
        
        ("Аномалия: одна большая фура", {'total_vehicles': 1, 'density': 0.2}, 'Single Big Object'),
         
        ("Аномалия: две большие машины", {'total_vehicles': 2, 'density': 0.16}, 'Single Big Object'),
        
        ("Не аномалия (слишком низкая плотность)", {'total_vehicles': 1, 'density': 0.14}, 'Sparse Traffic'),
        
        ("Плотное движение", {'total_vehicles': 7, 'density': 0.2}, 'Heavy Traffic'),
        
        ("Граничный случай плотного движения", {'total_vehicles': 6, 'density': 0.1}, 'Heavy Traffic'),
        
        ("Свободная дорога (мало машин)", {'total_vehicles': 4, 'density': 0.1}, 'Sparse Traffic'),
    ]

    # Прогоняем все тесты в цикле
    for i, (case_name, report, expected_class) in enumerate(test_cases):
        actual_class = classify_scene(report, test_thresholds)
        
        print(f'{i} of {len(test_cases)}')
        assert actual_class == expected_class, \
            f"ОШИБКА в кейсе '{case_name}': Ожидалось '{expected_class}', но получено '{actual_class}'"


test_classify_scene()