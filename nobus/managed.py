from __future__ import annotations

import filecmp
import hashlib

from pathlib import Path
from typing import Callable

def hash_md5(path: Path) -> str:
    """指定したファイルのハッシュ値を計算して返す。

    Parameters
    ----------
    path : Path
        ハッシュ値を計算したいファイルのパス。

    Returns
    -------
    str
        ハッシュ値。

    Raises
    ------
    FileNotFoundError
        指定されたパスにファイルが存在しないか、パスで指定された対象がファイルではない。
    """
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"No such file: '{path}'.")

    with open(str(path), 'rb') as f:
        data = f.read()
    return hashlib.md5(data).hexdigest()

class ManagedFile:
    def __init__(self, path: Path):
        self.path = Path(path)
    
    def compare(self, other: str | Path | ManagedFile, shallow: bool=True):
        if isinstance(other, ManagedFile):
            mf = other
        elif isinstance(other, (str, Path)):
            mf = ManagedFile(other)
        else:
            raise TypeError("other must be instance of (str, Path, ManagedFile)")
        
        return filecmp.cmp(self.path, mf.path, shallow=shallow)
    
    def hash(self):
        return hash_md5(self.path)

class ManagedDirectory:
    """管理対象となるファイルをディレクトリ単位で扱うためのクラス。
    デフォルトで `__pycache__` と `.ipynb_checkpoints` を含むファイル名は無視する。
    これらのディレクトリにあるファイルを管理対象に含めたい場合は ignore を明示的に指定する。

    Attributes
    ----------
    path : Path, immutable
        管理対象となるディレクトリのパス。
    glob : str, optional, immutable
        管理対象となるファイルを列挙するときの glob pattern。(by default '**/*')
        path.glob(pattern) に指定する pattern。
    group : str, optional, immutable
        管理グループが存在する場合、そのグループ名。(by default None)
    ignore : str, set[str], Callable[[Path], bool], optional, immutable
        列挙されたファイルの parts にこの引数の中にある文字列が含まれるとき列挙から除外する。(by default None)
        None が指定された場合は "__pycache__" と ".ipynb_checkpoints" を無視する。
    """
    def __init__(self, root_dir: Path, glob: str, ignore: str | set[str] | Callable[[Path], bool] | None='default'):
        """
        
        """
        self._root_dir = Path(root_dir)
        self._glob = glob

        ignore_set = {'__pycache__', '.ipynb_checkpoints'}

        if ignore is None:
            self.ignore = (lambda x: False)
        elif ignore == 'default':
            self.ignore = (lambda x: (len(set(x.parts) & ignore_set)) != 0)
        elif isinstance(ignore, set):
            ignore_set |= ignore
            self.ignore = (lambda x: (len(set(x.parts) & ignore_set)) != 0)
        elif isinstance(ignore, Callable):
            self.ignore = ignore
        else:
            raise TypeError(f"ignore must be instance of Union[str, set[str], Callable[[Path], bool], None].")

    @property
    def root_dir(self):
        return self._root_dir

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.path}', glob='{self.glob}', ignore={self.ignore})"

    def glob(self) -> list[Path]:
        """条件で指定されたすべてのファイルを取得する。

        Returns
        -------
        list[Path]
            条件で指定されたすべてのファイル。
        """
        return sorted([
            path for path in self.root_dir.glob(self._glob) 
                    if not self.ignore(path)
        ])

class Resource(ManagedDirectory):
    def __init__(self, root_dir: Path, glob: str, ignore: str | set[str] | Callable[[Path], bool] | None='default'):
        super.__init__(root_dir, glob, ignore)
        