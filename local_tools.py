import json
import os

from core.tool_provider import registry


# 1. 注册本地工具


@registry.tool(name="ask_user", description="Ask the user for input")
def ask_user(question: str) -> str:
    return input(question)


@registry.tool(name="add", description="Add two integers")
def add(a: int, b: int) -> int:
    return a + b


@registry.tool(name="read_file",
               description="Read the entire content of a text file. Returns the file content as string.")
def read_file(file_path: str) -> str:
    """
    读取文件内容。
    :param file_path: 相对于工作目录的路径，例如 "notes/readme.txt"
    """
    path = registry.safe_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist")
    if not path.is_file():
        raise IsADirectoryError(f"{file_path} is a directory, not a file")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        # 如果不是文本文件，返回提示
        return f"[Binary file: {file_path}, cannot display as text]"


@registry.tool(name="write_file",
               description="Write content to a text file (overwrites if exists). Creates parent directories if needed.")
def write_file(file_path: str, content: str) -> str:
    """
    写入文件内容。
    :param file_path: 目标文件路径
    :param content: 要写入的字符串内容
    """
    path = registry.safe_path(file_path)
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully wrote {len(content)} characters to {file_path}"


@registry.tool(name="list_directory",
               description="List all files and directories inside a directory. Returns a JSON string listing names and types.")
def list_directory(dir_path: str = ".") -> str:
    """
    列出目录内容。
    :param dir_path: 目录路径，默认为工作目录
    """
    path = registry.safe_path(dir_path, os.getcwd())
    if not path.exists():
        raise FileNotFoundError(f"Directory {dir_path} does not exist")
    if not path.is_dir():
        raise NotADirectoryError(f"{dir_path} is not a directory")
    items = []
    for item in path.iterdir():
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None
        })
    return json.dumps(items, indent=2, ensure_ascii=False)


@registry.tool(name="delete_file", description="Delete a file or empty directory. Use with caution.")
def delete_file(target_path: str) -> str:
    """
    删除文件或空目录。
    :param target_path: 要删除的路径
    """
    path = registry.safe_path(target_path)
    if not path.exists():
        raise FileNotFoundError(f"{target_path} does not exist")
    if path.is_file():
        path.unlink()
        return f"Deleted file: {target_path}"
    elif path.is_dir():
        # 为了安全，只允许删除空目录
        if any(path.iterdir()):
            raise PermissionError(f"Directory {target_path} is not empty. Use recursive deletion if needed.")
        path.rmdir()
        return f"Deleted empty directory: {target_path}"
    else:
        return f"Cannot delete {target_path} (unknown type)"


@registry.tool(name="append_file",
               description="Append content to the end of a text file. Creates file if it does not exist.")
def append_file(file_path: str, content: str) -> str:
    """
    追加内容到文件末尾。
    :param file_path: 文件路径
    :param content: 追加的字符串
    """
    path = registry.safe_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended {len(content)} characters to {file_path}"


# 可选：移动/重命名文件
@registry.tool(name="move_file",
               description="Move or rename a file/directory. Source and destination are relative to workspace.")
def move_file(source: str, destination: str) -> str:
    """
    移动或重命名文件/目录。
    :param source: 源路径
    :param destination: 目标路径
    """
    src = registry.safe_path(source)
    dst = registry.safe_path(destination)
    if not src.exists():
        raise FileNotFoundError(f"Source {source} does not exist")
    # 确保目标目录存在
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return f"Moved/renamed {source} to {destination}"
