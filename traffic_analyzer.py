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
            report['scene_type'],
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1, (0, 255, 0), 2
        )

        full_img_out_path = os.path.join(output_dir, f"highlight_{example}")
        cv2.imwrite(full_img_out_path, img)

        stats_text = (
            f"Имя файла: {report['filename']}\n"
            f"Тип сцены: {report['scene_type']}\n"
            f"Всего ТС: {report['total_vehicles']}\n"
            f"  - Легковые автомобили: {report.get('car', 0)}\n"
            f"  - Грузовики: {report.get('truck', 0)}\n"
            f"Плотность объектов: {report['density']:.2%}\n"
            f"Средний размер объекта: {report['avg_bbox_area']:.0f} пикс."
        )
        vis_report.append({
            'path': full_img_out_path,
            'report': report,
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

class PDFReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Пробуем использовать красивые шрифты, если они доступны (их мы скачивали в нашу папку ttf/)
        regular_font_path = os.path.join('ttf', 'DejaVuSans.ttf')
        bold_font_path = os.path.join('ttf', 'DejaVuSans-Bold.ttf')

        if os.path.exists(regular_font_path) and os.path.exists(bold_font_path):
            self.add_font('DejaVu', '', regular_font_path)
            self.add_font('DejaVu', 'B', bold_font_path)

            self.font_family = 'DejaVu'
        else:
            # Если шрифты не найдены, используем стандартный
            self.font_family = 'Arial'

    def header(self):
        """Создаёт шапку для каждой страницы"""
        self.set_font(self.font_family, 'B', 15)
        self.cell(0, 10, 'Аналитический отчёт по дорожной обстановке', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.set_font(self.font_family, '', 8)
        self.cell(0, 5, f'Дата генерации: {datetime.date.today().strftime("%d.%m.%Y")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        """Добавляет номера страниц в подвале"""
        self.set_y(-15)
        self.set_font(self.font_family, 'B', 8)
        self.cell(0, 10, f'Страница {self.page_no()}', border=0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

    def chapter_title(self, title):
        """Создаёт заголовок раздела"""
        self.set_font(self.font_family, 'B', 12)
        self.cell(0, 10, title, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)

    def chapter_body(self, body):
        """Добавляет основной текст"""
        self.set_font(self.font_family, '', 10)
        self.multi_cell(0, 5, body)
        self.ln()
    
    def add_image_section(self, title, image_path, stats_text):
        """Добавляет секцию с изображением и статистикой"""
        self.add_page()
        self.chapter_title(title)

        # Центрируем изображение на странице
        image_width = 100
        page_width = self.w - 2 * self.l_margin
        x_position = (page_width - image_width) / 2 + self.l_margin
        self.image(image_path, x=x_position, y=None, w=image_width)
        self.ln(5)
        self.set_font(self.font_family, '', 10) 
        self.multi_cell(0, 5, stats_text)

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

    if args.mode == 'experiment':
        print(f"experiment mode")

        TARGET_CLASSES = ['car', 'truck']

        image_paths = get_valid_image_paths('data')

        model = YOLO('yolov8n.pt')
        
        all_reports = []

        for path in tqdm(image_paths, desc=f"Анализ [conf={args.conf}]"):
            try:
                image = cv2.imread(path)
                h, w, _ = image.shape
                
                results = model(image, conf=args.conf, verbose=False)
                
                img_area = w * h
                metrics = analyze_image_metrics(results[0].boxes, img_area, model.names, TARGET_CLASSES)
                
                metrics['filename'] = os.path.basename(path)
                all_reports.append(metrics)
            except Exception as e:
                print(f"\nКритическая ошибка при обработке файла {path}: {e}")

        if all_reports:
            os.makedirs('experiments', exist_ok=True)
            csv_path = os.path.join('experiments', f'analysis_conf_{args.conf}.csv')

            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_reports[0].keys())
                writer.writeheader()
                writer.writerows(all_reports)

    elif args.mode == 'report':
        print(f"report mode")

        THRESHOLDS = {
            'jam_count': 10, 'jam_density': 0.3,
            'heavy_count': 5, 'single_density': 0.15,
        }
        TARGET_CLASSES = ['car', 'truck']
        SOURCE_DIR = 'data'
        REPORT_OUTPUT_DIR = 'report_output'

        model = YOLO('yolov8n.pt')
        image_paths = get_valid_image_paths(SOURCE_DIR)
        
        all_reports = []
        for path in tqdm(image_paths, desc="Анализ изображений"):
            try:
                image = cv2.imread(path)
                h, w, _ = image.shape
                results = model(image, conf=args.conf, verbose=False)
                img_area = w * h
                metrics = analyze_image_metrics(results[0].boxes, img_area, model.names, TARGET_CLASSES)
                metrics['scene_type'] = classify_scene(metrics, THRESHOLDS)
                metrics['filename'] = os.path.basename(path)
                all_reports.append(metrics)
            except Exception as e:
                print(f"\nКритическая ошибка при обработке файла {path}: {e}")

        if not all_reports:
            exit()

        top_examples = find_highlight_examples(all_reports)
        annotated_examples = generate_visualizations(model, top_examples, SOURCE_DIR, REPORT_OUTPUT_DIR, args.conf)

        pdf = PDFReport()
        pdf.add_page()

        pdf.chapter_title("1. Общая сводка по проанализированным данным")
        scene_types = [r['scene_type'] for r in all_reports]
        summary_text = (
            f"Всего обработано изображений: {len(all_reports)}\n"
            f"Использованный порог уверенности: {args.conf}\n\n"
            f"ОБЩАЯ СТАТИСТИКА ТРАНСПОРТА:\n"
            f"  - Всего найдено ТС: {sum(r['total_vehicles'] for r in all_reports)}\n"
            f"  - Легковые автомобили: {sum(r.get('car', 0) for r in all_reports)}\n"
            f"  - Грузовики: {sum(r.get('truck', 0) for r in all_reports)}\n\n"
            f"КЛАССИФИКАЦИЯ СЦЕН:\n"
            f"  - Пробка/Затор: {scene_types.count('Traffic Jam')} изображений\n"
            f"  - Плотное движение: {scene_types.count('Heavy Traffic')} изображений\n"
            f"  - Свободная дорога: {scene_types.count('Sparse Traffic')} изображений\n"
            f"  - Аномалии (крупный объект): {scene_types.count('Single Big Object')} изображений\n"
            f"  - Пустые сцены: {scene_types.count('Empty')} изображений"
        )
        pdf.chapter_body(summary_text)

        if annotated_examples:
            pdf.chapter_title("Примеры показательных сцен")
            sorted_examples = sorted(annotated_examples, key=lambda x: x['report']['density'], reverse=True)
            for i, example in enumerate(sorted_examples):
                title = f"Пример #{i+1}: {example['report']['filename']}"
                pdf.add_image_section(title, example['path'], example['stats'])

        pdf_output_path = os.path.join(REPORT_OUTPUT_DIR, "traffic_analysis_report.pdf")
        pdf.output(pdf_output_path)

        print(f"Результат сохранён в: {pdf_output_path}")