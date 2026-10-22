# plugin-arbiter(仮称)

Claude Code のプラグイン同士の衝突を検出し、プロジェクトごとに「どのプラグイン・スキル・MCPを優先するか」を整理して設定に落とし込むプラグイン。
OSSとして公開し、ポートフォリオにすることが目的。

## 解決したい問題

- プラグインが増えると、スキル名や説明文の重複、同じイベントへのフック、機能が重なるMCPなどが干渉する
- 既存ツールは「名前の重複チェック」「オン/オフ切り替え」「ルーティング」がバラバラ
- このプロジェクトの差別化:**指示文の中身レベルの矛盾を検出し、設定(enabledPlugins・CLAUDE.md・フック)まで一気通貫で提案する**

## 設計方針

- 機械的に判定できることはPythonスクリプトで決定的に処理する(テスト可能にするため)
- 意味の判断(本当に矛盾しているか、どちらを優先すべきか)だけをClaudeに任せる。候補ペアに絞って渡し、コンテキストを無駄にしない
- 常駐させない。コマンドで呼んだときだけ動く(管理役自身がコンテキストを圧迫しないため)
- ユーザーの設定ファイルを書き換えるときは必ず差分を見せて承認を得る。自動で書き込まない

## ロードマップ

- v0.1 `/audit`:衝突候補の機械的検出とレポート出力
  - スキル名の重複
  - スキル説明文の類似度(まずはトークン重複ベースで十分)
  - 同じイベント・matcherに登録されたフック
  - 名前・説明が似たMCPツール
- v0.2 意味レベルの判定:候補ペアをClaudeに読ませ、矛盾の有無と優先案を出す
- v0.3 `/apply`:プロジェクト向けの enabledPlugins と CLAUDE.md の優先ルールを差分付きで提案し、承認後に書き込む
- v0.4 PreToolUseフックで、優先度の低いMCPの呼び出しを止める(任意)

## 読み込み対象(想定)

- `~/.claude/plugins/installed_plugins.json` とキャッシュ内の各プラグイン
- 各プラグインの `.claude-plugin/plugin.json`、`skills/*/SKILL.md`、`hooks/hooks.json`、`.mcp.json`
- プロジェクトの `.claude/settings.json`、`.claude/settings.local.json`、`.mcp.json`、`CLAUDE.md`
- ファイル構成は Claude Code のバージョンで変わりうるので、パスは1か所にまとめて定義し、見つからない場合は落ちずにスキップしてレポートに記載する

## 想定構成

```
.claude-plugin/plugin.json
skills/audit/SKILL.md
scripts/arbiter/        # Pythonパッケージ(scan, detect, report)
tests/
  fixtures/             # わざと衝突させたダミープラグイン群
  test_*.py
pyproject.toml
README.md
LICENSE
```

## 開発ルール

- Python 3.10以上、標準ライブラリ中心。依存を増やすときは理由を書く
- テストは pytest。検出ロジックには必ずフィクスチャを使ったテストを付ける
- コード、README、コミットメッセージは英語(OSSとして読まれるため)。このCLAUDE.mdと議論は日本語でよい
- コミットは機能の区切りごとに小さく分ける
- 動作確認は `claude --plugin-dir .` で開発中のプラグインを読み込んで行う

## 参考にした既存プロジェクト(差別化の確認用)

- ccplug:プロジェクトごとのプラグイン有効化管理
- ccmcp:MCP・プラグインのスコープ横断管理
- check-skill-conflicts:スキル名の重複検出
- Smart Router / cowork-router:インストール済みプラグインからのルーティング・優先順位付け
