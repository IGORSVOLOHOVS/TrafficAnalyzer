import os

import cv2


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

def test_get_valid_image_paths():
    test_dir = "tests/test_sandbox"
    
    # Файлы, которые должны быть найдены
    expected_files = ["11.jpg", "22.PNG"]
    # Файлы, которые должны быть проигнорированы
    ignored_files = ["img1.zip"]
    

    # Вызываем тестируемую функцию
    result_paths = get_valid_image_paths(test_dir)
    
    # Проверяем результаты с помощью assert
    assert len(result_paths) == len(expected_files), \
        f"ОШИБКА: Ожидалось {len(expected_files)} файла, но найдено {len(result_paths)}"

    result_filenames = sorted([os.path.basename(p) for p in result_paths])
    expected_filenames = sorted(expected_files)
    assert result_filenames == expected_filenames, \
        f"ОШИБКА: Имена файлов не совпадают. Найдено: {result_filenames}, Ожидалось: {expected_filenames}"


    # Добавился вызов в основной цикл функции для теста
test_get_valid_image_paths()