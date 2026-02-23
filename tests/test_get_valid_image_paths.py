import os


def get_valid_image_paths(source_dir: str) -> list[str]:
    image_paths = []
    allowed_extensions = {'.jpg', '.jpeg', '.png'}

    files = os.listdir(source_dir)
    if files is None or len(files) == 0:
        raise Exception("files is None or len(files) > 0")
    
    allowed_extensions_tuple = tuple(allowed_extensions)
    for file in files:
        if file.endswith(allowed_extensions_tuple):
            image_paths.append(file)
    
    return image_paths 

res = get_valid_image_paths('./data/')
print(res)