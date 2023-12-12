from inspect import signature, isfunction, ismethod
from functools import wraps

def typecheck(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        def _typecheck(arg, annot, v):
            if isfunction(annot) or ismethod(annot):
                # 型アノテーションが関数やメソッドで与えられているとき
                if not annot(arg):
                    raise TypeError(f"{v} does not satisfy condition {annot.__name__}.")
            elif not isinstance(arg, annot):
                # それ以外は isinstance で処理
                raise TypeError(f"{v} must be instance of {annot} but actual type {type(arg)}.")
        
        # 型シグネチャを取得
        sgnt = signature(f)
        # 与えられた引数をパラメータにバインド
        bind = sgnt.bind(*args, **kwargs)
        # デフォルト引数をバインド
        bind.apply_defaults()

        for p, arg in bind.arguments.items():
            # パラメータに対応する型アノテーションを取得
            param = sgnt.parameters[p]
            annot = param.annotation
            
            if annot is param.empty:
                # 型アノテーションがなければ無視
                continue

            _typecheck(arg, annot, v=p)

        # 関数を実行
        ret = f(*args, **kwargs)

        # 戻り値の型アノテーションを取得
        annot = sgnt.return_annotation
        if annot is not sgnt.empty:
            # 戻り値に型アノテーションが存在するとき
            _typecheck(ret, annot, v="return value")
        
        return ret

    return wrapper
