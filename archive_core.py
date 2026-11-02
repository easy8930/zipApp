"""Local ZIP operations, independent of the desktop interface."""
from pathlib import Path, PurePosixPath
import os
import shutil
import tempfile
import zipfile


def compress(paths, destination):
    sources = [Path(p).resolve() for p in paths]
    target = Path(destination).resolve()
    if not sources:
        raise ValueError('ファイルまたはフォルダーを選択してください。')
    entries = []
    names = set()
    for source in sources:
        if not source.exists() or source.is_symlink():
            raise ValueError('存在しないファイルやリンクは圧縮できません。')
        if source == target or (source.is_dir() and source in target.parents):
            raise ValueError('保存先は選択したフォルダーの外にしてください。')
        for item in [source, *sorted(source.rglob('*'))] if source.is_dir() else [source]:
            if item.is_symlink():
                raise ValueError('リンクを含むフォルダーは圧縮できません。')
            name = item.relative_to(source.parent).as_posix()
            key = name.casefold()
            if key in names:
                raise ValueError('同名の項目が含まれています。選択を見直してください。')
            names.add(key)
            entries.append((item, name))
    fd, temporary = tempfile.mkstemp(dir=target.parent, suffix='.zip')
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for item, name in entries:
                archive.write(item, name)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def extract(source, destination):
    """Extract to a new directory; refuse unsafe Windows paths and zip bombs."""
    target = Path(destination).resolve()
    if target.exists():
        raise ValueError('解凍先には、まだ存在しない新しいフォルダー名を指定してください。')
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > 100000 or sum(m.file_size for m in members) > 10 * 1024**3:
            raise ValueError('安全のため、10 GB または10万項目を超える ZIP は解凍できません。')
        seen = set()
        for member in members:
            name = member.filename.replace('\\', '/')
            parts = PurePosixPath(name).parts
            if not parts or name.startswith('/') or any(
                p in ('.', '..') or p.endswith((' ', '.')) or
                any(c in p for c in ':<>"|?*') or any(ord(c) < 32 for c in p) or
                p.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]}
                for p in parts
            ) or (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('安全に解凍できないパスやリンクが含まれています。')
            key = '/'.join(parts).casefold()
            if key in seen or member.flag_bits & 1:
                raise ValueError('重複した名前、または未対応の暗号化 ZIP が含まれています。')
            seen.add(key)
        temporary = Path(tempfile.mkdtemp(dir=target.parent, prefix='.zipapp-'))
        try:
            for member in members:
                output = temporary.joinpath(*PurePosixPath(member.filename.replace('\\', '/')).parts)
                if member.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                else:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as src, output.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
            if target.exists():
                raise ValueError('解凍先が既に存在します。')
            temporary.rename(target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return len(members)
