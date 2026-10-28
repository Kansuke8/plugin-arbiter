# プラグイン検証の手順

Gmail仕分けアプリ(実験台)にプラグインを段階的に入れ、実際に起きる衝突を記録して plugin-arbiter の改善に使うための手順。

## 位置づけ

- これは **v0.2 に入る前に1周だけやる実地調査**。目的は v0.1 の検証ではなく、v0.2(意味レベルの判定)の**正解データ集め**
- 観察した衝突はメモで終わらせず、**フィクスチャとテストに変える**(各グループ共通の流れの手順7)。1周したあとは、実験台ではなくフィクスチャとテストで開発を回す
- v0.2 の判定(答えが毎回揺れる部分)は pytest ではなく `claude plugin eval` で測る。導入は v0.2 の実装を始めるとき

## 基本ルール

- インストールはすべて **local scope**(「Install for you, in this repo only」)。他のプロジェクトに影響させない
- **1グループずつ**追加する。一度に全部入れると、どのプラグインが原因かわからなくなる
- グループは**積み上げ式**(前のグループのプラグインは入れたまま)。困った度合いが「高」の衝突が出たときだけ、関係するプラグイン以外を一時的に無効にして切り分ける
- 検証中は**本物のGmailにつながない**。ダミーデータだけで作業する
- フック系のプラグインはローカルでコードを実行する。実験台のフォルダ以外で起動しない
- 入れるのは公式マーケットプレイス(claude-plugins-official)のものだけ
- コマンドは手で打つ(コピー時に `❯` などの記号が混ざらないように)

## 準備

1. 実験台のフォルダを作り、git を初期化する(GitHubに上げる場合は noreply アドレスの設定を忘れずに)
2. フォルダで `claude` を起動
3. 記録用に `notes/plugin-log.md` を作る(テンプレートは末尾)

## グループ0:ベースライン(追加なし)

すでにユーザー単位で入っているプラグイン(ponytail など)だけの状態で始める。

1. アプリは最小構成にする:ダミーメールの JSON を読み込み、ルールで仕分ける関数が1つあれば十分(`/audit` は静的スキャンなので、アプリの機能は結果に影響しない)
2. `python <plugin-arbiter のパス>/scripts/audit.py --project . > notes/audit-group0.md` で生の出力を保存する
3. この状態でコミット(以降の比較の基準になる)

## 各グループ共通の流れ

1. プラグインをインストール(local scope を選ぶ)
2. `/reload-plugins`
3. 入れたプラグインの名前とバージョンを記録(`/plugin` の Installed タブで確認)
4. そのグループが働く作業を実際にやる(下の「試す作業」)
5. 気づいたことをメモ:どちらが動いたか、意図と違ったこと、指示がぶつかったこと
   - どのスキル・フックが実際に呼ばれたかは、感想ではなくセッションの記録(`~/.claude/projects/` の jsonl)で確かめる
   - 困った度合いが「高」のものは、同じ依頼を2〜3回繰り返し、毎回再現するかを見る
   - 各衝突を3つの層に分類する(テンプレート参照)
6. `python <plugin-arbiter のパス>/scripts/audit.py --project . > notes/audit-groupN.md` で生の出力を保存し、前のグループとの差分とメモを比べる
7. 見逃し・誤検出を plugin-arbiter 側に戻す:1件ずつ `tests/fixtures/plugins/` の最小ダミープラグインに**書き直し**(実物の原文はコピーしない)、まだ通らないテストを1本足す
8. メモとコードをコミット

### Verify against the official docs before adding a gap

Before turning an observation into a fixture and a failing test, check the intended behavior in the official Claude Code docs. An observation may be expected behavior, not a gap.

Example: a command that shares its name with a bundled skill looked like a conflict. The docs say plugin commands are invoked with a namespace (`/plugin-name:command`), so they do not replace the bundled one. It was not a conflict, and arbiter does not report it.

## グループ1:コードレビュー系

```
/plugin install code-review@claude-plugins-official
/plugin install pr-review-toolkit@claude-plugins-official
```

**試す作業**:仕分けルールに機能を1つ足してから「この変更をレビューして」と頼む。どのレビュー機能が使われたか、組み込みの `/code-review` や ponytail のレビューと混ざっていないかを見る。

## グループ2:開発の進め方系

```
/plugin install superpowers@claude-plugins-official
/plugin install feature-dev@claude-plugins-official
```

**試す作業**:「ラベルごとの件数を集計する機能を追加して」と頼む。どちらの手順(ブレインストーミングから入るか、TDDか、feature-dev の段階か)に従ったか、ponytail の「最小の変更」と矛盾していないかを見る。

## グループ3:フック系

```
/plugin install security-guidance@claude-plugins-official
/plugin install hookify@claude-plugins-official
```

**試す作業**:設定ファイルの読み込み部分を編集する。警告やフックが何回・どの順で動いたか、重複して出ていないかを見る。v0.1 のフック重複検出を実地で確かめられる唯一のグループなので、省略しない。

## 任意:ponytail なしの比較

ponytail はユーザー単位で常に有効なので、衝突の原因が ponytail かどうかを切り分けられない。グループ2で ponytail との衝突が「高」だった場合だけ、ponytail を無効にして同じ依頼を1回やり直す。

## 任意のグループ

v0.2 の範囲を決めるのに必要な場合だけ行う。

### グループ4:git系

```
/plugin install commit-commands@claude-plugins-official
```

**試す作業**:変更をコミットしてもらう。コミットメッセージの書き方や手順が、組み込みの動きや他のプラグインの指示とぶつからないかを見る。

github プラグイン(MCP)は GitHub の認証が必要なので任意。実験台を GitHub に置いた場合だけ追加する。

### グループ5:単純化系

```
/plugin install code-simplifier@claude-plugins-official
```

**試す作業**:「このモジュールを整理して」と頼む。ponytail の方針や superpowers の手順とどう絡むかを見る。

## うまくいかないとき

- 「プラグインが見つからない」と出たら、`/plugin marketplace update claude-plugins-official` で一覧を更新するか、`/plugin` の Discover タブで名前を検索する
- 名前が変わっている・見つからないものは、無理に探さず記録して次へ進む

## 後片付け

検証が終わったプラグインは次で外せる。

```
/plugin uninstall <プラグイン名>@claude-plugins-official
```

## 記録テンプレート(notes/plugin-log.md)

```markdown
## グループN:〇〇系(YYYY-MM-DD)

### 環境
- Claude Code のバージョン:
- 入れたプラグイン:名前@マーケットプレイス:バージョン

### 試した作業
- 

### 気づいた衝突・違和感
- 場面:
  - 起きたこと:
  - 原因と思われるプラグイン:
  - 根拠(jsonl の該当箇所):
  - 再現回数(N回中M回):
  - 困った度合い(高/中/低):
  - 層:(a) v0.1 で拾えるはず / (b) 意味の判定が必要(v0.2) / (c) 静的には見えない(実行時の注入文・組み込み機能など)

### /audit の結果(notes/audit-groupN.md)
- 検出された件数:
- メモにあって /audit が見逃したもの:
- /audit が出したが実際は問題なかったもの:
- フィクスチャとテストにしたもの:
```
