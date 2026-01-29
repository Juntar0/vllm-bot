# Clawdbot vs vLLM Bot - ツール統合の比較

## Clawdbot のツール統合方法

### 1. ツール定義の仕組み

Clawdbotは**2つのレイヤー**でツールを扱います：

#### レイヤー1: pi-coding-agent ベース

```typescript
// @mariozechner/pi-coding-agent から提供
interface ToolDefinition {
  name: string;
  label?: string;
  description: string;
  parameters: TypeBoxSchema;  // TypeBox形式のスキーマ
  execute: (toolCallId, params, signal, onUpdate) => Promise<ToolResult>;
}
```

**提供されるツール**:
- `readTool` - ファイル読み取り
- `writeTool` - ファイル書き込み
- `editTool` - ファイル編集

#### レイヤー2: Clawdbot拡張ツール

```typescript
// dist/agents/bash-tools.js
createExecTool()   // コマンド実行
createProcessTool() // プロセス管理
createApplyPatchTool() // パッチ適用

// dist/agents/clawdbot-tools.js
cron, gateway, message, sessions_*, canvas, browser, nodes等
```

### 2. LLMプロバイダーへの送信

Clawdbotは**プロバイダーごとに異なる形式**でツールを送信します：

#### Anthropic (Claude)

```typescript
// Anthropic API形式
{
  "model": "claude-sonnet-4-5",
  "messages": [...],
  "tools": [
    {
      "name": "read",
      "description": "Read file contents",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "File path"
          }
        },
        "required": ["path"]
      }
    }
  ]
}
```

**実装場所**: `dist/agents/pi-tools.js`

```javascript
function createClawdbotCodingTools(options) {
  // ツールポリシー解決
  const { globalPolicy, agentPolicy, groupPolicy } = 
    resolveEffectiveToolPolicy(options);
  
  // pi-coding-agentツール作成
  const readTool = createReadTool(...);
  const writeTool = createWriteTool(...);
  const editTool = createEditTool(...);
  
  // Clawdbot拡張ツール
  const execTool = createExecTool(...);
  const processTool = createProcessTool(...);
  
  // ポリシーでフィルタリング
  const filtered = filterToolsByPolicy(allTools, [
    globalPolicy,
    agentPolicy,
    groupPolicy
  ]);
  
  return filtered;
}
```

#### OpenAI (ChatGPT)

```typescript
// OpenAI API形式
{
  "model": "gpt-5.2",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read",
        "description": "Read file contents",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "File path"
            }
          },
          "required": ["path"]
        }
      }
    }
  ]
}
```

### 3. ツールポリシーシステム

Clawdbotの**最大の特徴**は多層ポリシーシステム：

```typescript
// dist/agents/pi-tools.policy.js

// 優先順位（上が優先）:
1. Profile Policy       // プロファイル固有
2. Provider Profile     // プロバイダー×プロファイル
3. Global Policy        // グローバル設定
4. Global Provider      // グローバル×プロバイダー
5. Agent Policy         // エージェント固有
6. Agent Provider       // エージェント×プロバイダー
7. Group Policy         // グループチャット
8. Sandbox Policy       // サンドボックス制限
9. Subagent Policy      // サブエージェント制限
```

**設定例** (`clawdbot.json`):

```json
{
  "tools": {
    "policy": {
      "default": {
        "allow": ["read", "write", "exec"],
        "deny": []
      },
      "minimal": {
        "allow": ["read"],
        "deny": ["exec", "gateway"]
      }
    },
    "exec": {
      "host": "sandbox",
      "security": "allowlist",
      "ask": "on-miss"
    }
  },
  
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "policy": "default"
        }
      }
    ]
  }
}
```

### 4. パラメータ正規化

**Claude Code互換性**のため、パラメータ名を自動変換：

```typescript
// dist/agents/pi-tools.read.js
export function normalizeToolParams(params) {
  const normalized = { ...params };
  
  // file_path → path (Claude Code形式)
  if ("file_path" in normalized && !("path" in normalized)) {
    normalized.path = normalized.file_path;
    delete normalized.file_path;
  }
  
  // old_string → oldText
  if ("old_string" in normalized && !("oldText" in normalized)) {
    normalized.oldText = normalized.old_string;
    delete normalized.old_string;
  }
  
  // new_string → newText
  if ("new_string" in normalized && !("newText" in normalized)) {
    normalized.newText = normalized.new_string;
    delete normalized.new_string;
  }
  
  return normalized;
}
```

**理由**: Claude Codeで学習したモデルがツールコールループに陥るのを防ぐ

### 5. ツールスキーマ変換

プロバイダーごとに異なるスキーマ形式に対応：

```typescript
// dist/agents/pi-tools.schema.js

// Gemini用: enumを削除
function cleanToolSchemaForGemini(schema) {
  // Gemini doesn't support enum in tool schemas
  const cleaned = { ...schema };
  if (cleaned.properties) {
    for (const prop of Object.values(cleaned.properties)) {
      if (prop.enum) delete prop.enum;
    }
  }
  return cleaned;
}

// Claude用: パラメータグループを調整
function patchToolSchemaForClaudeCompatibility(tool, groups) {
  // Claude prefers unified parameter keys
  // file_path + path → allow both
}
```

---

## vLLM Bot のツール統合方法

### 1. シンプルな2層構造

```python
# src/tools.py
TOOL_DEFINITIONS = [
  {
    "type": "function",
    "function": {
      "name": "read",
      "description": "Read file contents",
      "parameters": { ... }
    }
  }
]
```

**特徴**:
- ✅ 単一の真実の情報源
- ✅ ハードコードなし
- ✅ プロバイダー非依存（OpenAI互換形式固定）

### 2. デュアルモード検出

```python
# src/agent.py
if self.enable_function_calling:
    # Function Calling API
    response = vllm.chat_completion(conversation, tools=TOOL_DEFINITIONS)
    tool_calls = vllm.extract_tool_calls(response)
    if not tool_calls:
        # フォールバック: テキストパース
        tool_calls = self._parse_tool_calls(assistant_message)
else:
    # テキストパースのみ
    response = vllm.chat_completion(conversation, tools=None)
    tool_calls = self._parse_tool_calls(assistant_message)
```

### 3. 簡易ポリシー

```json
{
  "security": {
    "exec_enabled": true,
    "allowed_commands": ["ls", "cat", "grep"]
  }
}
```

**Clawdbotとの違い**:
- ❌ 多層ポリシーなし
- ❌ プロファイルなし
- ❌ グループポリシーなし
- ✅ シンプルなallowlist

---

## 比較表

| 機能 | Clawdbot | vLLM Bot |
|------|----------|----------|
| **ツール定義** | TypeBox + pi-coding-agent | OpenAI Function形式 |
| **プロバイダー対応** | Anthropic, OpenAI, Gemini等 | OpenAI互換のみ |
| **ポリシー** | 9層の多層ポリシー | 単純allowlist |
| **パラメータ正規化** | あり（Claude Code互換） | なし |
| **スキーマ変換** | プロバイダーごと | 固定 |
| **サンドボックス** | Docker + ポリシー | パス検証のみ |
| **承認システム** | あり（ask mode） | なし |
| **複雑度** | 高 | 低 |
| **拡張性** | 高 | 中 |

---

## Clawdbotから学べること

### 1. ツールポリシーの重要性

複数のシナリオでツール制御が必要：
- メインセッション vs サブエージェント
- グループチャット vs DM
- プロバイダーごとの制限
- サンドボックス vs ホスト実行

### 2. プロバイダー互換性

各LLMプロバイダーには独自の特性：
- Anthropic: `input_schema`
- OpenAI: `function.parameters`
- Gemini: `enum`非対応

### 3. パラメータ正規化の必要性

モデルの学習データに応じて、異なるパラメータ名を使う：
- Claude Code: `file_path`, `old_string`
- pi-coding-agent: `path`, `oldText`

### 4. エラーハンドリング

```typescript
// Clawdbot: dist/agents/pi-tool-definition-adapter.js
execute: async (toolCallId, params, onUpdate, _ctx, signal) => {
  try {
    return await tool.execute(toolCallId, params, signal, onUpdate);
  } catch (err) {
    if (signal?.aborted) throw err;
    logError(`[tools] ${name} failed: ${err.message}`);
    return jsonResult({
      status: "error",
      tool: name,
      error: err.message
    });
  }
}
```

**vLLM Botへの適用可能性**: ✅ 今後追加すべき

---

## まとめ

### Clawdbotの強み

1. **エンタープライズ対応** - 多層ポリシー、承認システム
2. **プロバイダー中立** - Anthropic, OpenAI, Gemini等に対応
3. **高度なセキュリティ** - サンドボックス、ホワイトリスト、承認
4. **互換性** - Claude Code等の既存ツールと互換

### vLLM Botの強み

1. **シンプル** - 理解しやすい、保守しやすい
2. **拡張性** - 単一の真実の情報源
3. **デュアルモード** - Function Calling + テキストパース
4. **学習コスト低** - 43コンポーネント vs 5モジュール

### 推奨される改善（vLLM Bot）

1. ✅ エラーハンドリング強化
2. ✅ プロバイダー互換性レイヤー（将来）
3. ⚠️ ポリシーシステムは必要に応じて
4. ⚠️ パラメータ正規化は互換性が必要なら

**vLLM Botの現在の設計は、シンプルさと機能性のバランスが取れています。**
Clawdbotのような複雑さは、大規模展開や複数プロバイダー対応が必要になってから追加すべきです。
