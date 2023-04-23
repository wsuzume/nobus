from abc import ABC
from types import MethodType

class TypeChecker:
    def __init__(self, function):
        self._function = function
    
    def __repr__(self):
        return f"TypeChecker({self._function.__name__})"

    def __call__(self, x) -> bool:
        return self._function(x)

def typechecker(function):
    return TypeChecker(function)

class Typed:
    @staticmethod
    def typecheck(value, type_, optional):
        if value is None:
            if optional:
                # optional で None なら OK
                return
            # optional じゃないのに value が None である 
            raise TypeError(f"value is None even though it is not optional.")
        
        # 以降は value が None ではない
        if (type_ is not None):
            # 型が指定されてるならチェックを入れる
            if isinstance(type_, TypeChecker):
                if type_(value):
                    return
                raise TypeError(f"typechecking by '{type_}' returned False.")

            if isinstance(value, type_):
                return True
            raise TypeError(f"value must be instance of {type_} but actual type {type(value)}.")

        return

    def __init__(self, value, type_=None, optional=False):
        self.typecheck(value, type_, optional)

        self._value = value
        self._type = type_
        self._optional = optional

    def __repr__(self):
        xs = f"{self.__class__.__name__}(value={self.value.__repr__()}"
        if self.type is not None:
            xs += f", type_={self.type}"
        xs += f", optional={self.optional.__repr__()}"
        xs += ")"
        return xs
        
    @property
    def value(self):
        return self._value
    
    @property
    def type(self):
        return self._type
    
    @property
    def optional(self):
        return self._optional
    
    @value.setter
    def value(self, value):
        # value が Typed で、自身の型とマッチしない場合はエラー
        if isinstance(value, Typed) and (value.type is not None):
            if (self.type is not None) and (self.type != value.type):
                raise TypeError(f"value must be instance of {self.type} but actual type {value.type}.")
        
        if isinstance(value, Typed):
            value = value.value

        # value に対して型チェック
        self.typecheck(value, self.type, self.optional)

        self._value = value
    
class Immutable(Typed):
    def __init__(self, value, type_=None, optional=False):
        super().__init__(value, type_, optional)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        raise AttributeError(f"immutable attribute 'value' cannot be rewritten.")

class Protected(Typed):
    def __init__(self, value, type_=None, optional=False):
        super().__init__(value, type_, optional)

def typed(value, type_=None, optional=False):
    return Typed(value, type_, optional)

def immutable(value, type_=None, optional=False):
    return Immutable(value, type_, optional)

def protected(value, type_=None, optional=False):
    return Protected(value, type_, optional)    

class SafeAttrABC(ABC):
    @staticmethod
    def typed(x, type_=None, optional=False):
        return Typed(x, type_, optional)
    
    @staticmethod
    def immutable(x, type_=None, optional=False):
        return Immutable(x, type_, optional)

    @staticmethod
    def protected(x, type_=None, optional=False):
        return Protected(x, type_, optional)
    
    def _safeattr_derive(self):
        if self.is_safeattr_derived_class:
            return
        
        cls = self.__class__
        super().__setattr__('_is_safeattr_derived_class', True)
        super().__setattr__('__class__', type(cls.__name__, (cls,), {}))
    
    def __init__(self):
        self._safeattr_derive()
    
    @property
    def is_safeattr_derived_class(self):
        if not hasattr(self, '_is_safeattr_derived_class'):
            return False
        return self._is_safeattr_derived_class
    
    def __getattribute__(self, name):
        if not name.startswith('_') or name.startswith('_safeattr_'):
            # 隠蔽されたメンバに対するアクセスではないか、
            # 隠蔽されたメンバの実体に対する直アクセス
            return super().__getattribute__(name)
        
        # ユーザが隠蔽されたメンバ '_x' にアクセスするときは '_safeattr_x' が実体になる
        try:
            # 実体を探してみて存在すればそこから読み取って返す
            hidden_name = '_safeattr' + name
            ret = super().__getattribute__(hidden_name)
            if isinstance(ret, Typed):
                return ret.value
            return ret
        except AttributeError:
            # なければ '_x' というメンバにアクセスしてみる
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        # 隠蔽されていないメンバに対するアクセスで Typed を使わない
        if not name.startswith('_') and not isinstance(value, Typed):
            # 通常通りの挙動
            # または管理下にあるものの場合は property の setter が呼び出される
            super().__setattr__(name, value)
            return
        
        # name が '_x' の形式か、value が Typed のインスタンス

        if name.startswith('_safeattr_'):
            # SafeAttr の管理下にあることを示す予約変数名
            # そのままのアクセスを許すが、
            # ユーザが直に書き換えてもそれだけでは管理対象とはならない
            super().__setattr__(name, value)

        if name.startswith('_'):
            # ユーザがアクセスしようとしているメンバは隠蔽されており、
            # SafeAttr の管理下にあるかもしれない
            hidden_name = '_safeattr' + name
            if not hasattr(self, hidden_name):
                # SafeAttrABC の管理下にない '_x' という名前の変数名である
                super().__setattr__(name, value)
            else:
                # SafeAttrABC の管理下にあるかもしれない
                # 少なくとも '_safeattr_x' という名前のメンバが存在している
                attr = getattr(self, hidden_name)
                if isinstance(attr, Immutable):
                    # 書き換え不能なメンバを書き換えようとしている
                    raise AttributeError(f"immutable attribute '{name}' cannot be rewritten.")
                elif isinstance(attr, Typed):
                    # 型付きのメンバを書き換えようとしているので書き換えを試行する（型チェックが入る）
                    attr.value = value
                else:
                    # 存在するものの Typed で管理していないメンバにアクセスしようとしている
                    super().__setattr__(hidden_name, value)
            return
        
        # 変数名が '_x' という形式である可能性はここまでで省いた
        # ここから変数名は 'x' のように '_' で始まらない形式である
        # ユーザは通常のメンバを SafeAttrABC の管理下に置こうとしている

        # SafeAttrABC の管理下に置かれるメンバの本体は隠蔽される
        hidden_name = '_safeattr_' + name
        
        if hasattr(self, hidden_name):
            # 既に隠蔽されたメンバが存在している
            attr = getattr(self, hidden_name)
            if isinstance(attr, Immutable):
                # immutable を書き換えようとしたからエラー
                raise AttributeError(f"immutable attribute '{name}' cannot be rewritten.")
            elif isinstance(attr, Protected):
                # protected に通常の名前でアクセスして書き換えようとしたのでエラー
                raise AttributeError(f"protected attribute '{name}' cannot be rewritten.")
            elif isinstance(attr, Typed):
                # typed は隠蔽されたメンバに対する書き込みは許可する
                attr.value = value
                return

        # 隠蔽されたメンバは存在しなかった、
        # あるいは隠蔽されたメンバは管理下になかったのでそのまま上書きするのだが、
        # 上書きした時点で '_x' という名前のメンバは unreachable になるので消しておく
        # （下手したらメモリリークとかするかもしれないので）
        _name = '_' + name
        if hasattr(self, _name):
            super().__delattr__(_name)
        super().__setattr__(hidden_name, value)
        
        # 管理のためのプロパティを追加する（これを行うことで管理下に入る）
        
        # プロパティの動的な追加はクラスを書き換えるしかないので、
        # 同じ名前の子クラスを作って自身の親をその子クラスにする
        self._safeattr_derive()
        
        # 取得に対してはラッピングを解除すればよい
        def getter_of(name):
            def getter(self):
                value = getattr(self, '_safeattr_' + name)
                return value.value
            return getter
        
        # 上書きに対しては若干複雑になる
        def setter_of(name):
            def setter(self, value):
                attr = getattr(self, '_safeattr_' + name)
                if isinstance(attr, Immutable):
                    # immutable を書き換えようとしているのでエラー
                    raise AttributeError(f"immutable attribute '{name}' cannot be rewritten.")
                elif isinstance(attr, Protected):
                    # protected に通常の名前でアクセスして書き換えようとしていたのでエラー
                    raise AttributeError(f"protected attribute '{name}' cannot be rewritten.")
                
                if not isinstance(attr, Typed):
                    # 管理下にあるはずなのにここで Typed でなかったら
                    # 直アクセスとかで変な値を入れられている
                    raise RuntimeError(f"Unrecognized typed attribute: '{name}' of type {type(name)}.")
                
                # Typed の書き込みは許可する
                attr.value = value                

            return setter
        
        # getter と setter をセットする
        setattr(self.__class__, name, property(getter_of(name), setter_of(name)))
        
        # メソッドの引数を優先して返す
        def selector_of(name):
            def arg_override(self, x=None, f=None):
                if x is not None:
                    if f is not None:
                        return f(x)
                    return x
                return getattr(self, name)
            return arg_override
        
        # arg_override を追加する
        super().__setattr__('arg_' + name, MethodType(selector_of(name), self))
