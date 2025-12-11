import base64
import json
import mimetypes

from functools import cache
from io import BytesIO

from pathlib import Path
from urllib.parse import urlparse

import requests


def load_json_from_file(file_path: str | Path) -> dict | None:
    # 将字符串路径转换为 Path 对象
    path = Path(file_path)

    # 检查文件是否存在
    if not path.is_file():
        print(f"File not found: {file_path}")
        return None

    try:
        # 读取 JSON 文件
        with path.open('r', encoding='utf-8') as file:
            data = json.load(file)
            print(f'File exists: {file_path}')
            return data
    except json.JSONDecodeError:
        print(f"Error decoding JSON from file: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def save_json_2_file(file_path: str, data: dict) -> None:
    create_file_path(file_path)
    save_str_2_file(file_path, json.dumps(data, indent=2, ensure_ascii=False))


def create_file_path(file_path):
    # 将字符串路径转换为 Path 对象
    path = Path(file_path)

    # 创建父目录（如果不存在）
    path.parent.mkdir(parents=True, exist_ok=True)

    # 创建文件（如果不存在）
    path.touch(exist_ok=True)


def save_str_2_file(file_path: str, data: str) -> None:
    create_file_path(file_path)

    path = Path(file_path)

    path.write_text(data)


def merage_json_file_datas(p: Path, update_data: dict):
    result = {**update_data}

    if p.exists():
        desc_dict = json.load(p.open())
        desc_dict.update(result)

        result = {**desc_dict}

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=4), encoding='utf-8')

    return result


@cache
def get_image_suffixes():
    import mimetypes

    # 初始化
    mimetypes.init()

    # 获取所有已知的 MIME 类型中，以 "image/" 开头的后缀
    image_extensions = {ext for ext, kind in mimetypes.types_map.items() if kind.startswith('image/')}

    return image_extensions


def is_image_file(file_path: Path) -> bool:
    """
    检查文件是否为图像文件
    """
    return file_path.suffix.lower() in get_image_suffixes()


_REQ_SESSIONS = requests.Session()


def _is_url(value: str) -> bool:
    parsed_url = urlparse(value)
    return parsed_url.scheme in {'http', 'https'}


def get_file_data_by_path(fp: str | Path):
    _fp = Path(fp)
    if _fp.is_file():
        return _fp.read_bytes()
    else:
        req = _REQ_SESSIONS.get(fp)
        data_bytes = BytesIO(req.content)
        return data_bytes.getvalue()


def guess_image_mime_type(image_path: Path) -> str:
    mime_type = mimetypes.guess_type(image_path.name)[0]
    if mime_type and mime_type.startswith('image/'):
        return mime_type
    return 'image/png'


def find_existing_image_path(path_without_suffix: Path) -> Path | None:
    if not path_without_suffix.parent.is_dir():
        return None

    for image_path in sorted(path_without_suffix.parent.iterdir()):
        if not image_path.is_file():
            continue
        if image_path.stem != path_without_suffix.name:
            continue
        if not is_image_file(image_path):
            continue
        return image_path
    return None


def get_image_output_path_without_suffix(source_image: str | Path, suffix_name: str) -> Path:
    source_image = str(source_image)
    if _is_url(source_image):
        raise ValueError(
            f'source_image is url, cannot save {suffix_name} to the same local directory'
        )

    source_image_path = Path(source_image)
    return source_image_path.with_name(f'{source_image_path.stem}-{suffix_name}')


def get_image_suffix(mime_type: str) -> str:
    suffix = mime_type.split('/')[-1] or 'png'
    if suffix == 'jpeg':
        suffix = 'jpg'
    return suffix


def write_image(image_bytes: bytes, mime_type: str, output_path_without_suffix: Path) -> Path:
    output_path_without_suffix.parent.mkdir(parents=True, exist_ok=True)
    output_path = output_path_without_suffix.with_suffix(f'.{get_image_suffix(mime_type)}')
    output_path.write_bytes(image_bytes)
    return output_path


def read_image(fp: str | Path) -> tuple[bytes, str]:
    fp = str(fp)
    if _is_url(fp):
        response = requests.get(fp, timeout=60)
        response.raise_for_status()
        mime_type = response.headers.get('Content-Type', 'image/png').split(';')[0].strip()
        if not mime_type.startswith('image/'):
            mime_type = 'image/png'
        return response.content, mime_type

    image_path = Path(fp)
    if not image_path.is_file():
        raise FileNotFoundError(f'image not found: {image_path}')
    return image_path.read_bytes(), guess_image_mime_type(image_path)


def to_data_url(data: bytes, mime_type: str) -> str:
    data_b64 = base64.b64encode(data).decode()
    return f'data:{mime_type};base64,{data_b64}'


def image_to_model_url(fp: str | Path) -> str:
    fp = str(fp)
    if _is_url(fp):
        return fp

    image_bytes, mime_type = read_image(fp)
    return to_data_url(image_bytes, mime_type)
