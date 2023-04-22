import pytest

from nobus.safeattr import Immutable, Protected, Typed, SafeAttrABC

delete_check = False

class DeleteCheck:
    def __init__(self):
        pass

    def __del__(self):
        global delete_check
        
        delete_check = True

class Hoge(SafeAttrABC):
    def __init__(self, piyo):
        self.fuga = 'fuga'
        self.piyo = piyo

        self.ika = self.immutable('ika')
        self.tako = self.immutable('tako', str)
        self.ebi = self.immutable(None, str, optional=True)

        self.inu = self.protected('inu')
        self.neko = self.protected('neko', str)
        self.tori = self.protected(None, str, optional=True)

        self.ushi = self.typed('ushi')
        self.uma = self.typed('uma', str)
        self.yagi = self.typed(None, str, optional=True)

        self._x = DeleteCheck()

def test_SafeAttrABC():
    hoge = Hoge('piyo')

    # 通常のメンバに対する動作テスト
    ## 追加テスト
    hoge.poyo = 'poyo'

    ## 参照テスト
    assert hoge.fuga == 'fuga'
    assert hoge.piyo == 'piyo'
    assert hoge.poyo == 'poyo'

    ## 書き換えテスト
    hoge.fuga = 3
    hoge.piyo = 4
    hoge.poyo = 5

    assert hoge.fuga == 3
    assert hoge.piyo == 4
    assert hoge.poyo == 5

    ## 隠しメンバが作成されていないことのチェック
    assert not hasattr(hoge, '_fuga')
    assert not hasattr(hoge, '_piyo')
    assert not hasattr(hoge, '_poyo')
    assert not hasattr(hoge, '_safeattr_fuga')
    assert not hasattr(hoge, '_safeattr_piyo')
    assert not hasattr(hoge, '_safeattr_poyo')

    # immutable メンバに対する動作テスト
    ## 追加テスト
    hoge.kani = Immutable('kani')

    assert hoge.ika == 'ika'
    assert hoge.tako == 'tako'
    assert hoge.ebi is None
    assert hoge.kani == 'kani'

    ## 隠しメンバに対する参照チェック
    assert hoge._ika == 'ika'
    assert hoge._tako == 'tako'
    assert hoge._ebi is None
    assert hoge._kani == 'kani'

    assert isinstance(hoge._safeattr_ika, Immutable)
    assert isinstance(hoge._safeattr_tako, Immutable)
    assert isinstance(hoge._safeattr_ebi, Immutable)
    assert isinstance(hoge._safeattr_kani, Immutable)

    ## 書き換えテスト
    with pytest.raises(AttributeError):
        hoge.ika = 3
    with pytest.raises(AttributeError):
        hoge.tako = 4
    with pytest.raises(AttributeError):
        hoge.ebi = 5
    with pytest.raises(AttributeError):
        hoge.kani = 6

    with pytest.raises(AttributeError):
        hoge._ika = 3
    with pytest.raises(AttributeError):
        hoge._tako = 4
    with pytest.raises(AttributeError):
        hoge._ebi = 5
    with pytest.raises(AttributeError):
        hoge._kani = 6

    # protected メンバに対する動作テスト
    ## 追加テスト
    hoge.hebi = Protected('hebi')

    assert hoge.inu == 'inu'
    assert hoge.neko == 'neko'
    assert hoge.tori is None
    assert hoge.hebi == 'hebi'

    ## 隠しメンバに対する参照チェック
    assert hoge._inu == 'inu'
    assert hoge._neko == 'neko'
    assert hoge._tori is None
    assert hoge._hebi == 'hebi'

    assert isinstance(hoge._safeattr_inu, Protected)
    assert isinstance(hoge._safeattr_neko, Protected)
    assert isinstance(hoge._safeattr_tori, Protected)
    assert isinstance(hoge._safeattr_hebi, Protected)

    ## 書き換えテスト
    with pytest.raises(AttributeError):
        hoge.inu = 3
    with pytest.raises(AttributeError):
        hoge.neko = 4
    with pytest.raises(AttributeError):
        hoge.tori = 5
    with pytest.raises(AttributeError):
        hoge.hebi = 6

    hoge._inu = 'Woof!'
    hoge._neko = 'Meow!'
    hoge._tori = 'Tweet!'
    hoge._hebi = 'Hiss!'

    hoge._inu = 3
    with pytest.raises(TypeError):
        hoge._neko = 4
    with pytest.raises(TypeError):
        hoge._tori = 5
    hoge._hebi = 6

    # typed なメンバに対する動作テスト
    ## 追加テスト
    hoge.buta = Typed('buta')

    assert hoge.ushi == 'ushi'
    assert hoge.uma == 'uma'
    assert hoge.yagi is None
    assert hoge.buta == 'buta'

    ## 隠しメンバに対する参照チェック
    assert hoge._ushi == 'ushi'
    assert hoge._uma == 'uma'
    assert hoge._yagi is None
    assert hoge._buta == 'buta'

    assert isinstance(hoge._safeattr_ushi, Typed)
    assert isinstance(hoge._safeattr_uma, Typed)
    assert isinstance(hoge._safeattr_yagi, Typed)
    assert isinstance(hoge._safeattr_buta, Typed)

    ## 書き換えテスト
    hoge.ushi = 3
    with pytest.raises(TypeError):
        hoge.uma = 4
    with pytest.raises(TypeError):
        hoge.yagi = 5
    hoge.buta = 6

    hoge._ushi = 'Moo!'
    hoge._uma = 'Neigh!'
    hoge._yagi = 'Baa!'
    hoge._buta = 'Oink!'

    hoge._ushi = 3
    with pytest.raises(TypeError):
        hoge._uma = 4
    with pytest.raises(TypeError):
        hoge._yagi = 5
    hoge._buta = 6

    # unreachable の削除チェック
    assert isinstance(hoge._x, DeleteCheck)
    assert not delete_check

    hoge.x = Immutable(5)

    assert delete_check
    assert hoge._x == 5
