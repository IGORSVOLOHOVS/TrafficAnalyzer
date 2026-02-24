

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
    density = total_bbox_trasport_area / image_area if total_bbox_trasport_area > 0 else 0
    # Вычисляем среднюю площадь bounding box'а
    avg_bbox_area = total_bbox_trasport_area / transports_count if total_bbox_trasport_area > 0 else 0
    # Формируем отчёт с метриками
    report = {
        'total_vehicles': total_vehicles,
        'density': round(density, 4),
        'avg_bbox_area': round(avg_bbox_area, 2),
        **object_counts
    }

    return report


def find_highlight_examples(all_reports, top_n=3):
    """
    Аргументы:
        all_reports (list): Полный список словарей с метриками по всем изображениям.
        top_n (int): Количество "топовых" примеров для отбора по каждому критерию.

    Возвращает:
        dict: Словарь, где ключи - имена файлов, а значения - отчёты для
              самых показательных изображений.
    """
    if len(all_reports) < top_n:
        return {r['filename']: r for r in all_reports}
    
    # sort by Самые загруженные и Самые плотные
    sort_report = sorted(
        all_reports,
        key=lambda val: (val['total_vehicles'], val['density']),
        reverse=True
    )

    return {r['filename']: r for r in sort_report[:top_n]}

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


def test_find_highlight_examples():
    # Создаём искусственный набор данных (mock data)
    mock_reports = [
        # Лидер по количеству
        {'filename': 'crowded.jpg', 'total_vehicles': 20, 'density': 0.3},
        # Просто средний файл
        {'filename': 'normal_1.jpg', 'total_vehicles': 8, 'density': 0.15},
        # Лидер по плотности
        {'filename': 'dense.jpg', 'total_vehicles': 5, 'density': 0.6},
        # Второй по количеству
        {'filename': 'crowded_2.jpg', 'total_vehicles': 18, 'density': 0.25},
        # Второй по плотности и третий по количеству => топ по обоим критериям
        {'filename': 'dense_and_crowded.jpg', 'total_vehicles': 15, 'density': 0.5},
        # Ещё один средний файл
        {'filename': 'normal_2.jpg', 'total_vehicles': 2, 'density': 0.1},
        # Третий по плотности
        {'filename': 'dense_3.jpg', 'total_vehicles': 4, 'density': 0.4}
    ]

    top_examples = find_highlight_examples(mock_reports, top_n=4)

    expected_filenames = {'crowded.jpg', 'crowded_2.jpg', 'normal_1.jpg', 'dense_and_crowded.jpg'}

    assert len(top_examples) == 4, \
        f"ОШИБКА: Ожидалось 4 уникальных примера, но получено {len(top_examples)}"

    result_filenames = set(top_examples.keys())
    assert result_filenames == expected_filenames, \
        f"ОШИБКА: Набор файлов не совпадает. Найдено: {result_filenames}, Ожидалось: {expected_filenames}"
 
    small_reports = [{'filename': 'a.jpg', 'total_vehicles': 1, 'density': 0.1}]
    top_small = find_highlight_examples(small_reports, top_n=3)
    assert len(top_small) == 1, \
        "ОШИБКА: Неверная обработка, когда отчётов меньше, чем top_n"
    assert 'a.jpg' in top_small, \
        "ОШИБКА: Потерян единственный отчёт при обработке малого набора"

test_find_highlight_examples()