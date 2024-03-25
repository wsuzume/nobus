from __future__ import annotations

import hashlib
import uuid

from copy import deepcopy
from datetime import datetime
from filecmp import cmp
from io import StringIO
from pathlib import Path
from shutil import copy2, rmtree
from tqdm.auto import tqdm
from typing import Any, Callable, Iterable, Mapping

from .randname import generate_random_name

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
    def __init__(self, path: str | Path, *, root_dir: str | Path | None=None):
        self._path = Path(path)
        self._root_dir = Path(root_dir) if root_dir is not None else None

    def __repr__(self) -> str:
        if self.root_dir is not None:
            return f"{self.__class__.__name__}('{self._path}', root_dir='{self._root_dir}')"    
        return f"{self.__class__.__name__}('{self._path}')"

    def __hash__(self):
        return hash(self.path)
    
    def __eq__(self, other):
        if isinstance(other, ManagedFile):
            return self.path == other.path
        return False

    @property
    def path(self) -> Path:
        if self.root_dir is not None:
            return self._root_dir / self._path
        return self._path

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def hash(self):
        return hash_md5(self.path)

    def compare(self, other: str | Path | ManagedFile, shallow: bool=True):
        if isinstance(other, ManagedFile):
            mf = other
        elif isinstance(other, (str, Path)):
            mf = ManagedFile(other)
        else:
            raise TypeError("other must be instance of (str, Path, ManagedFile)")
        
        return cmp(self.path, mf.path, shallow=shallow)
    
    def save(self, dest_dir: Path, copy_function=copy2):
        dest_dir = Path(dest_dir)
        dest_path = dest_dir / self._path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        copy_function(src=self.path, dst=dest_path)

        return dest_path

ManagedDirectoryPathArgType = str | Path | Mapping[str | Path, str]

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
    def __init__(self,
                 path: ManagedDirectoryPathArgType,
                 glob: str | Iterable[str] | None=None,
                 *,
                 root_dir: Path | None=None,
                 ignore: str | set[str] | Callable[[Path], bool] | None='default'):
        """
        
        """
        if isinstance(path, Mapping):
            if glob is not None:
                raise TypeError("glob must be None when path is instance of Mapping.")
            self._path = { Path(_path): [ _glob ] for _path, _glob in path.items() }
        elif isinstance(path, (str, Path)):
            if glob is None:
                raise TypeError(f"glob must be specified when path is instance of 'str' or 'Path'.")
            elif isinstance(glob, str):
                self._path = { Path(path): [ glob ] }
            elif isinstance(glob, Iterable):
                self._path = { Path(path): list(glob) }
            else:
                raise TypeError(f"glob must be instance of 'str' or 'Iterable[str]' but actual type '{type(glob)}'.")
        else:
            raise TypeError(f"path must be instance of 'str', 'Path', 'Mapping[str | Path, str]' but actual type '{type(path)}'.")

        self._root_dir = Path(root_dir) if root_dir is not None else None

        ignore_set = {'__pycache__', '.ipynb_checkpoints'}

        if ignore is None:
            self._ignore_set = None
            self.ignore = (lambda x: False)
        elif ignore == 'default':
            self._ignore_set = ignore_set
            self.ignore = (lambda x: (len(set(x.parts) & self._ignore_set)) != 0)
        elif isinstance(ignore, set):
            self._ignore_set = ignore_set | ignore
            self.ignore = (lambda x: (len(set(x.parts) & self._ignore_set)) != 0)
        elif isinstance(ignore, Callable):
            self._ignore_set = f"{ignore}"
            self.ignore = ignore
        else:
            raise TypeError(f"ignore must be instance of Union[str, set[str], Callable[[Path], bool], None].")

    @property
    def path(self):
        return self._path

    @property
    def root_dir(self):
        return self._root_dir

    def __repr__(self):
        if self.root_dir is not None:
            return f"{self.__class__.__name__}({self.path}, root_dir={self.root_dir}, ignore={self._ignore_set})"
        return f"{self.__class__.__name__}({self.path}, ignore={self._ignore_set})"

    def glob(self) -> list[Path]:
        """条件で指定されたすべてのファイルを取得する。

        Returns
        -------
        list[Path]
            条件で指定されたすべてのファイル。
        """
        root_dir = self.root_dir if self.root_dir is not None else Path('.')
        ret = []
        for _path, _glob_list in self.path.items():
            for _glob in _glob_list:
                ret.extend([
                    path for path in (root_dir / _path).glob(_glob) 
                        if not self.ignore(path)
                ])
        return sorted(ret)

    @property
    def managed_files(self):
        if self.root_dir is None:
            return [ ManagedFile(path) for path in self.glob() ]

        root_parts = self.root_dir.parts
        N = len(root_parts)

        def detach_root(path):
            ps = path.parts
            if any([ ps[i] != root_parts[i] for i in range(N) ]):
                raise ValueError(f"Unknown error while detaching root_dir from path: path='{path}', root_dir='{self.root_dir}'.")
            return Path(*ps[N:])
        
        return [ ManagedFile(detach_root(path), root_dir=self.root_dir) for path in self.glob() ]
    
    @property
    def hash_dict(self):
        return { mf.path: mf.hash for mf in self.managed_files }
    
    @property
    def hash(self):
        with StringIO() as f:
            for mf in self.managed_files:
                f.write(mf.hash)
            data = f.getvalue()
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def _zip_apply(self, dest_dir: Path, function: Callable[[Path, Path], Path | None], verbose: bool):
        dest_dir = Path(dest_dir)

        if dest_dir.resolve() == self.root_dir.resolve():
            raise ValueError(f"dest_dir must be different from self.root_dir: the absolute path is '{self.root_dir.resolve()}'.")
        
        managed_files = self.managed_files if not verbose else tqdm(self.managed_files)

        ret = []
        for mf in managed_files:
            dest_path = dest_dir / mf._path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            p = function(src=mf.path, dst=dest_path)

            if p is not None:
                ret.append(p)
        
        return ret

    def compare(self, dest_dir: Path, *, verbose: bool=False, compare_function=cmp):
        def wrapper(src, dst):
            if compare_function(src, dst):
                return src
            else:
                return None
        return self._zip_apply(dest_dir=dest_dir, verbose=verbose, function=wrapper)
    
    def diff(self, dest_dir: Path, *, verbose: bool=False, compare_function=cmp):
        def wrapper(src, dst):
            if not compare_function(src, dst):
                return src
            else:
                return None
        return self._zip_apply(dest_dir=dest_dir, verbose=verbose, function=wrapper)

    def save(self, dest_dir: Path, *, verbose: bool=False, copy_function=copy2):
        def wrapper(src, dst):
            copy_function(src, dst)
            return dst
        return self._zip_apply(dest_dir=dest_dir, verbose=verbose, function=wrapper)

def get_project_root(name: str) -> Path | None:
    cwd = Path.cwd()

    for i, subname in enumerate(cwd.parts):
        if subname == name:
            return Path(*cwd.parts[:i+1])
    
    return None

def get_git_root() -> Path | None:
    cwd = Path.cwd()

    if (cwd / '.git').exists():
        return cwd

    for p in cwd.parents:
        if (p / '.git').exists():
            return p
    
    return None

def generate_random_tag():
    dt = datetime.now()
    randname = generate_random_name()
    uid = uuid.uuid4().hex[:8]
    return f"{dt.strftime('%Y%m%d-%H%M%S-%f')}_{randname}_{uid}"

class Resource:
    @staticmethod
    def from_git_root(path: ManagedDirectoryPathArgType | None=None,
                 glob: str | Iterable[str] | None=None,
                 *,
                 ignore: str | set[str] | Callable[[Path], bool] | None='default'):
        root_dir = get_git_root()
        if root_dir is None:
            raise FileNotFoundError(f"This directory is not managed by git.")
        
        return Resource(path, glob, root_dir=root_dir, ignore=ignore)
    
    @staticmethod
    def from_project_name(name):
        root_dir = get_project_root(name)
        if root_dir is None:
            raise FileNotFoundError(f"project root no found: '{name}'")
        
        return Resource(root_dir=root_dir)

    def __init__(self,
                 path: ManagedDirectoryPathArgType | None=None,
                 glob: str | Iterable[str] | None=None,
                 *,
                 root_dir: Path | None=None,
                 ignore: str | set[str] | Callable[[Path], bool] | None='default'):
        self._objects = []

        self._root_dir = Path(root_dir) if root_dir is not None else None

        if isinstance(path, (str, Path)):
            _path = Path(path)
            if self.root_dir is not None:
                _path = self.root_dir / _path

            if not _path.exists():
                raise FileNotFoundError(f"The initializer for Resource cannot accept a path to a non-existent file: '{path}'.")
            if _path.is_file():
                self.file(path, root_dir=root_dir)
            elif _path.is_dir():
                self.directory(path, glob, root_dir=root_dir, ignore=ignore)
            else:
                raise FileNotFoundError(f"The specified path is neither a file nor a directory: '{path}'.")
    
    def __repr__(self):
        if self.root_dir is not None:
            return f"{self.__class__.__name__}({self.objects}, root_dir='{self.root_dir}')"
        return f"{self.__class__.__name__}({self.objects})"

    @property
    def root_dir(self):
        return self._root_dir

    @property
    def objects(self):
        return self._objects

    def file(self, path: Path, root_dir: Path=None):
        if root_dir is None:
            root_dir = self.root_dir
        self._objects.append(ManagedFile(path=path, root_dir=root_dir))

        return self
    
    def directory(self,
                  path: ManagedDirectoryPathArgType,
                  glob: str | Iterable[str] | None=None,
                  *,
                  root_dir: Path | None=None,
                  ignore: str | set[str] | Callable[[Path], bool] | None='default'):
        if root_dir is None:
            root_dir = self.root_dir
        self._objects.append(ManagedDirectory(path=path, glob=glob, root_dir=root_dir, ignore=ignore))
    
        return self

    def glob(self):
        ret = []
        for obj in self.objects:
            if isinstance(obj, ManagedFile):
                ret.append(obj.path)
            elif isinstance(obj, ManagedDirectory):
                ret.extend(obj.glob())
        return ret
    
    @property
    def managed_files(self) -> list[ManagedFile]:
        ret = []
        for obj in self.objects:
            if isinstance(obj, ManagedFile):
                ret.append(obj)
            elif isinstance(obj, ManagedDirectory):
                ret.extend(obj.managed_files)
        return ret

    @property
    def hash_dict(self):
        return { mf.path: mf.hash for mf in self.managed_files }
    
    @property
    def hash(self):
        with StringIO() as f:
            for mf in self.managed_files:
                f.write(mf.hash)
            data = f.getvalue()
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def get_unique_tag(self):
        dt = datetime.now()
        xs = self.hash
        randname = generate_random_name(seed=bytes.fromhex(xs))
        uid = uuid.uuid4().hex[:8]
        return f"{dt.strftime('%Y%m%d-%H%M%S-%f')}_{randname}_{xs[:8]}_{uid}"
    
    def cache_dirs(self, cache_root_dir: Path):
        cache_root_dir = Path(cache_root_dir)
        ignode_set = {'__pycache__', '.ipynb_checkpoints'}

        cache_dirs = sorted([ path for path in cache_root_dir.glob('*')
                                if path.is_dir() and path.name not in ignode_set ])
        
        return cache_dirs

    def last_cache_dir(self, cache_root_dir: Path):
        cache_dirs = self.cache_dirs(cache_root_dir=cache_root_dir)

        if len(cache_dirs) == 0:
            return None
        
        return cache_dirs[-1]

    def _select_cache_dir(self, *, cache_dir: Path | None=None, cache_root_dir: Path | None=None) -> Path:
        if ((cache_dir is None) and (cache_root_dir is None)) \
            or ((cache_dir is not None) and (cache_root_dir is not None)):
            raise ValueError(f"Please specify either cache_dir or cache_root_dir, not both.")
        
        if cache_dir is not None:
            cache_dir = Path(cache_dir)
        elif cache_root_dir is not None:
            cache_dir = self.last_cache_dir(cache_root_dir=cache_root_dir)
        else:
            raise RuntimeError(f"unknown error.")
        
        return cache_dir

    def resolve(self, *, cache_dir: Path | None=None, cache_root_dir: Path | None=None):
        cache_dir = self._select_cache_dir(cache_dir=cache_dir, cache_root_dir=cache_root_dir)

        ret = {}
        for mf in self.managed_files:
            cache_path = cache_dir / mf._path
            if not cache_path.exists():
                ret[mf] = None
            elif cache_path.is_file():
                # resolve refers to the path of the target if it is a symbolic link
                ret[mf] = cache_path.resolve()
            else:
                raise FileExistsError("cache must be a file.")
        
        return ret
    
    def calc_cache(self, *, cache_dir: Path | None=None, cache_root_dir: Path | None=None):
        cache_dir = self._select_cache_dir(cache_dir=cache_dir, cache_root_dir=cache_root_dir)

        resolved = self.resolve(cache_dir=cache_dir)
        
        cache = {}
        for mf, path in resolved.items():
            if path is None:
                # cache doesn't exist
                cache[mf] = None
            elif mf.compare(path):
                # cache exists and file haven't been changed
                cache[mf] = path
            else:
                # cache exists but file was changed
                cache[mf] = None
        
        return cache

    def save_cache(self, *,
                   save_dir: Path | None=None,
                   cache_dir: Path | None=None,
                   cache_root_dir: Path | None=None,
                   copy_function=copy2,
                   prevent_duplication=False,
                   overwrite: bool=False,
                   verbose: bool=False):
        save_dir = Path(save_dir)

        if (cache_dir is None) and (cache_root_dir is None):
            # 参照がなければすべて保存対象にする
            cache = { mf: None for mf in self.managed_files }
        else:
            # 参照があればそれをもとにキャッシュすべきファイルを計算する
            cache_dir = self._select_cache_dir(cache_dir=cache_dir, cache_root_dir=cache_root_dir)
            cache = self.calc_cache(cache_dir=cache_dir)

            if prevent_duplication and all([ v is not None for v in cache.values() ]):
                # すべてキャッシュが存在しているなら新規作成はしない
                return cache_dir

        # 保存先に既にファイルかディレクトリがあれば、エラーにするか消すかする
        is_save_dir_exists = save_dir.exists()

        if (not overwrite) and is_save_dir_exists:
            raise FileExistsError(f"file or directory already exists at '{save_dir}'.")

        if is_save_dir_exists:
            rmtree(str(save_dir))

        cache_items = cache.items() if not verbose else tqdm(cache.items())

        for mf, path in cache_items:
            if path is None:
                mf.save(dest_dir=save_dir, copy_function=copy_function)
            else:
                save_path = save_dir / mf._path
                if save_path.exists():
                    raise FileExistsError(f"file or directory already exists ad '{save_path}'.")
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.symlink_to(path)
        
        return save_dir
        
    def create_cache(self, cache_root_dir: Path | None=None,
                     copy_function=copy2,
                     unique_tag: bool=False,
                     prevent_duplication: bool=True,
                     verbose: bool=False):
        cache_root_dir = Path(cache_root_dir)

        if isinstance(unique_tag, bool):
            if unique_tag:
                utag = self.get_unique_tag()
            else:
                utag = generate_random_tag()
        else:
            utag = unique_tag

        save_dir = cache_root_dir / utag
        
        return self.save_cache(
            save_dir=save_dir,
            cache_root_dir=cache_root_dir,
            copy_function=copy_function,
            prevent_duplication=prevent_duplication,
            overwrite=False,
            verbose=verbose,
        )