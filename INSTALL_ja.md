# インストールガイド — PyCC2 **v0.6.10**

> **このドキュメントはv0.6.10に更新されています。以前のバージョン情報はGit履歴を参照してください。**

PyCC2 v0.6.10の全サポートプラットフォームにおける完全なインストール手順。

### バージョン履歴

| バージョン | 日付 | メモ |
|------------|------|------|
| v2.0 | 2026-06-14 | v0.4.0に更新: テスト~3513, 起動方法 `pycc2`, コア依存関係(pygame/numpy/pydantic) |
| v1.8 | 2026-05-19 | P5/P6/P7完了: キャンペーンコア(~60%)、戦闘深度(~85%)、コンテンツ拡張(M6-M10)、CC2フィデリティ~71%、1566テスト、10ミッション、10マップ |
| v1.7 | 2026-05-19 | CC2ギャップ分析、ロードマップをP5キャンペーンコアに修正、夜戦システム、対戦車装甲、気象レンダリング、3言語ドキュメント、1377テスト |
| v1.6 | 2026-05-19 | P4第2週: キャンペーンが5ミッションに拡張、チュートリアルシステム、パフォーマンス最適化、1270テスト |
| v1.5 | 2026-05-18 | P4第1週: GameLoop分解、設定メニュー、セキュリティ強化、1163テスト |
| v1.4 | 2025-05-18 | P3修正: 4つの重要なバグ修正（武器/ロード/AI/エントリ） |
| v1.3 | 2026-05-17 | 完全版ベースライン |

---

## 目次

1. [システム要件](#システム要件)
2. [Pythonセットアップ](#pythonセットアップ)
3. [標準インストール](#標準インストール)
4. [プラットフォーム固有の注意事項](#プラットフォーム固有の注意事項)
5. [検証](#検証)
6. [トラブルシューティング](#トラブルシューティング)
7. [開発環境セットアップ](#開発環境セットアップ)
8. [アンインストール](#アンインストール)

---

## システム要件

### 最低要件

| コンポーネント | 要件 |
|---------------|------|
| OS | macOS 12+, Ubuntu 22.04+, Windows 10+ |
| Python | 3.11以降（3.12+推奨） |
| RAM | 4 GB |
| ディスク | 200 MB空き容量 |
| ディスプレイ | 1280x720最低、1440x900推奨 |
| 入力 | マウス + キーボード |

### 推奨仕様

| コンポーネント | 要件 |
|---------------|------|
| OS | macOS 14+ (Apple Silicon M1/M2/M3) |
| Python | 3.12または3.13 |
| RAM | 8 GB |
| ディスプレイ | 1440x900以上、Retinaディスプレイ |

---

## Pythonセットアップ

### Pythonバージョンの確認

```bash
python3 --version
# 期待値: Python 3.11.x, 3.12.x, または3.13.x
```

Python 3.10以前が表示された場合、アップグレードが必要です：

**macOS (Homebrew)**:
```bash
brew install python@3.12
```

**Linux (apt)**:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**Windows**:
https://www.python.org/downloads/ からダウンロード

### pipの確認

```bash
python3 -m pip --version
# 期待値: pip 24.x from Python 3.12
```

---

## 標準インストール

### ステップ1: ソースコードを取得

```bash
git clone https://github.com/lulin70/PyCC2.git
cd PyCC2
```

### ステップ2: 仮想環境（強く推奨）

```bash
# 作成
python3 -m venv .venv

# アクティベーション
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows CMD
# .venv\Scripts\Activate.ps1    # PowerShell
```

アクティブになると、ターミナルプロンプトに `(.venv)` が表示されます。

### ステップ3: パッケージをインストール

```bash
pip install -e .
```

これによりPyCC2が「編集可能」モードでインストールされます — ソースコードへの変更は再インストールなしで即座に利用可能になります。

**自動的にインストールされるコア依存関係**:
- `pygame>=2.2` — 2Dゲームフレームワーク（レンダリング、入力、SDL2経由のオーディオ）
- `numpy>=1.26` — 数値演算（マップグリッド、ベクトル計算）
- `pydantic>=2.0` — データ検証（セーブファイル、構成スキーマ）

### ステップ4: 検証

```bash
python -c "import pycc2; print('PyCC2 imported successfully')"
python -m pytest tests/ -q --tb=no
# 期待値: ~6536 passed
```

---

## プラットフォーム固有の注意事項

### macOS (Apple Silicon M1/M2/M3)

特別な手順は不要 — pygame 2.2+はSDL2経由でApple Siliconをネイティブにサポートしています。

**Retinaディスプレイ**: PyCC2はRetinaモードを自動検出し、適切にスケーリングします。1440x900の物理ディスプレイでは、実質2880x1800での鮮明なHiDPIレンダリングが得られます。

**オーディオ**: pygame経由でCoreAudioを使用します。音が聞こえない場合：
```bash
# pygameオーディオを個別にテスト
python -c "import pygame; pygame.init(); pygame.mixer.init(); print('Audio OK')"
```

**Pythonバージョン**: プロジェクトは`match/case`構文（Python 3.10+が必要）とタイプパラメータ構文を使用しています。すべての機能との互換性を最大にするにはPython 3.12が推奨されます。

### Linux (Ubuntu/Debian)

pygameのSDL2バックエンド用のシステム依存関係をインストールします：

```bash
sudo apt install \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libpng-dev
```

その後、標準インストール手順に進みます。

**SDL_VIDEODRIVERに関する注意**: 表示エラーが発生した場合、試してください：
```bash
export SDL_VIDEODRIVER=x11
```

### Windows (WSL2推奨)

最高の結果を得るには、X11転送付きWSL2を使用します：

```bash
# WSLターミナル内
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip libsdl2-dev
# その後標準インストール手順に従う
```

**ネイティブWindows**も動作します：
```cmd
# PowerShellまたはCMD内
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pycc2
```

---

## 検証

### テストスイート

```bash
# 完全なテストスイート（~6536個すべて通過するはず）
python -m pytest tests/ -q

# クイックスモークテスト（インポートが機能することのみ確認）
python -c "
from pycc2.domain.entities.unit import Unit, Faction, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
print('All core modules importable')
"
```

### デモの起動

```bash
# ゲームを開始
pycc2

# またはPythonモジュールとして実行
python -m pycc2.main
```

以下が表示されるはずです：
1. ウィンドウが開く（1440x900または画面解像度）
2. ゲーム構成を示すコンソール出力
3. 緑色（連合軍）と灰色（枢軸軍）のユニットがある戦場
4. インタラクティブ操作（クリックで選択、右クリックで移動/攻撃）

期待されるコンソール出力：
- ディメンションとDPI情報
- アクティブなP3機能リスト
- 連合軍と枢軸軍のユニット名簿
- AI構成の詳細
- オーディオとセーブシステムのステータス

---

## トラブルシューティング

### `ModuleNotFoundError: No module named 'pycc2'`

編集可能モードでのインストールを忘れています：
```bash
pip install -e .
```

### `pygame.error: No video device available`

ディスプレイ/サーバーの問題。試してください：
```bash
# macOS: システム環境設定 > セキュリティとプライバシー > プライバシーでTerminalへのアクセスを許可
# Linux: export DISPLAY=:0 && export SDL_VIDEODRIVER=x11
# WSL: VcXsrvをインストールするかWSLgを使用（Windows 11以降ビルトイン）
```

### テストが`ModuleNotFoundError`で失敗する

仮想環境をアクティベートし、dev依存関係をインストールしていることを確認してください：
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### オーディオが動作しない

PyCC2は手続き的オーディオを使用します（数学的に音声を生成）。静かな場合：
1. システムボリュームがミュートされていないか確認
2. 試す：`python -c "import pygame; pygame.mixer.init(); print(pygame.mixer.get_init())"`
3. 一部のCI/ヘッドレス環境ではオーディオハードウェアがありません — これは予期されており致命的ではありません

### パフォーマンスが遅く感じる

1. ネイティブPythonを実行していることを確認（Apple Silicon MacでのRosetta翻訳ではない）
2. ウィンドウサイズを縮小：設定メニュー（F10）で変更
3. 低品質プリセット：設定メニュー（F10）で変更

### `SyntaxError: expected ':'`またはmatch/caseエラー

Pythonバージョンが古すぎます。PyCC2には**Python 3.11+**が必要です（`match/case`ステートメントを使用）：
```bash
python3 --version # 3.11+である必要があります
```

---

## 開発環境セットアップ

### Dev依存関係のインストール

```bash
pip install -e ".[dev]"
```

これにより追加ツールがインストールされます：
- **pytest>=7.4** + プラグイン — カバレッジ、モッキング、ランダム化付きテストランナー
- **ruff>=0.1** — リンタおよびフォーマッター（極めて高速、Rustベース）
- **mypy>=1.7** — 静的タイプチェッカー
- **pre-commit>=3.5** — 自動品質チェック用Gitフック
- **hypothesis>=6.100** — プロパティベーステスト
- **freezegun**, **scipy** — テストユーティリティ

### コード品質ツール

```bash
# リント
ruff check src/ tests/

# フォーマット
ruff format src/ tests/

# タイプチェック（オプション、誤検知がある場合あり）
mypy src/pycc2/domain/  # ドメイン層は完全に型付けされているはず

# Pre-commitフック
pre-commit install
pre-commit run --all-files
```

### テストの実行

```bash
# すべてのテスト
pytest tests/ -v

# カテゴリ別
pytest tests/unit/ -q              # 最速：純粋なロジックテスト
pytest tests/integration/ -q        # 連携して動作するシステム
pytest tests/e2e/ -q                 # 完全パイプラインテスト

# HTMLカバレッジレポート付き
pytest tests/ --cov=src/pycc2 --cov-report=html
open htmlcov/index.html             # ブラウザで表示
```

---

## アンインストール

```bash
# まず仮想環境を非アクティブ化
deactivate

# パッケージを削除
pip uninstall pycc2 -y

# オプション：環境を削除
rm -rf .venv

# またはプロジェクトディレクトリ全体を削除
cd ..
rm -rf PyCC2
```
