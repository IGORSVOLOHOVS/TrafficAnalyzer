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


def generate_visualizations(model, examples_to_visualize, source_dir, output_dir, conf):
    """Создаёт визуальные артефакты (изображения с аннотациями) для отчёта."""
    vis_report = []
    for example in examples_to_visualize:
        full_img_path = os.path.join(source_dir, example)

        results = model.predict(full_img_path, conf=conf)
        # results = model(full_img_path, conf=conf, verbose=False)

        img = results[0].plot()

        report = examples_to_visualize[example]
        cv2.putText(
            img,
            report['scene'],
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1, (0, 255, 0), 2
        )

        full_img_out_path = os.path.join(output_dir, f"highlight_{example}")
        cv2.imwrite(full_img_out_path, img)

        stats_text = (
            f"Имя файла: {report['filename']}\n"
            f"Тип сцены: {report['scene']}\n"
            f"Всего ТС: {report['total_vehicles']}\n"
            f"  - Легковые автомобили: {report.get('car', 0)}\n"
            f"  - Грузовики: {report.get('truck', 0)}\n"
            f"Плотность объектов: {report['density']:.2%}\n"
            f"Средний размер объекта: {report['avg_bbox_area']:.0f} пикс."
        )
        vis_report.append({
            'path': full_img_out_path,
            'report': example,
            'stats': stats_text
        })
    return vis_report


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Инструмент для анализа дорожного трафика на основе YOLOv8.",
        formatter_class=argparse.RawTextHelpFormatter 
    )
    parser.add_argument(
        "mode", 
        choices=['experiment', 'report'],
        help="Режим работы скрипта:\n"
             " 'experiment' - запуск одного прогона для сбора CSV-статистики.\n"
             " 'report' - полный цикл анализа с генерацией PDF-отчёта."
    )
    parser.add_argument(
        "--conf", 
        type=float, 
        default=0.45, 
        help="Порог уверенности (confidence) для детекции. (По умолчанию: 0.45)"
    )

    args = parser.parse_args()

    # Выбор режима работы на основе аргументов
    thresholds = {
        'jam_count': 10,       # Порог количества для пробки
        'jam_density': 0.3,    # Порог плотности для пробки
        'heavy_count': 5,      # Порог количества для плотного движения
        'single_density': 0.15 # Порог плотности для крупного объекта
    }
    if args.mode == 'experiment':
        # Определяем константы для этого режима
        TARGET_CLASSES = ['car', 'truck']
        
        # Получаем список валидных изображений
        image_paths = get_valid_image_paths('data')

        model = YOLO('yolov8n.pt')
        
        # Готовимся собирать отчёты со всех изображений
        all_reports = []
        
        # Основной цикл обработки, обёрнутый в tqdm для наглядности
        for path in tqdm(image_paths, desc=f"Анализ [conf={args.conf}]"):
            try:
                # Читаем изображение и получаем его размеры
                image = cv2.imread(path)
                h, w, _ = image.shape
                
                # Запускаем инференс с заданным `conf`
                results = model(image, conf=args.conf, verbose=False)
                
                # Извлекаем метрики из результатов детекции
                metrics = analyze_image_metrics(
                    detections=results[0].boxes, 
                    image_area=h*w, 
                    model_names=model.names, 
                    target_classes=TARGET_CLASSES
                )

                metrics['scene'] = classify_scene(metrics, thresholds)
                
                # Дополняем отчёт информацией об изображении
                metrics['filename'] = os.path.basename(path)
                all_reports.append(metrics)
            except Exception as e:
                print(f"Критическая ошибка при обработке файла {path}: {e}")
        
        # Сохранение результатов в CSV-файл
        if all_reports:
            # Создаём папку для экспериментов, если она ещё не существует
            os.makedirs('experiments', exist_ok=True)
            # Имя файла будет отражать параметр, с которым проводился эксперимент
            csv_path = os.path.join('experiments', f'analysis_conf_{args.conf}.csv')

            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                # Заголовки берём из ключей первого словаря в списке
                writer = csv.DictWriter(f, fieldnames=all_reports[0].keys())
                writer.writeheader()
                writer.writerows(all_reports)
        
        highlight_examples = find_highlight_examples(
            all_reports=all_reports,
            top_n=3
        )

        vis_report = generate_visualizations(
            model=model,
            examples_to_visualize=highlight_examples,
            source_dir='data',
            output_dir='report_output',
            conf=0.25
        )
        print(vis_report)

    elif args.mode == 'report':
        # Этот блок реализуем на следующих шагах
        pass