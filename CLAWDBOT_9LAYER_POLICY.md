# Clawdbot 9層ポリシーシステム 完全解説

## 概要

Clawdbotの**最も重要な特徴**は、9層の多層ポリシーシステムです。これにより、以下のシナリオで柔軟にツールアクセスを制御できます：

- 個人チャット vs グループチャット
- メインエージェント vs サブエージェント
- プロバイダーごと（Anthropic vs OpenAI）
- モデルごと（Claude Sonnet vs GPT-5）
- サンドボックス vs ホスト実行

---

## 9層の階層構造

### 優先順位（上が優先）

```
1. Profile Policy          (プロファイル固有)
2. Provider Profile        (プロバイダー×プロファイル)
3. Global Policy           (グローバル設定)
4. Global Provider         (グローバル×プロバイダー)
5. Agent Policy            (エージェント固有)
6. Agent Provider          (エージェント×プロバイダー)
7. Group Policy            (グループチャット)
8. Sandbox Policy          (サンドボックス制限)
9. Subagent Policy         (サブエージェント制限)
```

**判定方法**: すべてのポリシーが`allow`を返した場合のみツール実行可能。

```typescript
// dist/agents/pi-tools.policy.js
function isToolAllowedByPolicies(name, policies) {
  return policies.every((policy) => 
    isToolAllowedByPolicyName(name, policy)
  );
}
```

---

## 各層の詳細

### 1. Profile Policy（プロファイル）

**目的**: 事前定義された設定テンプレート

**設定例**:

```json
{
  "tools": {
    "policy": {
      "minimal": {
        "allow": ["read"],
        "deny": ["exec", "gateway", "sessions_spawn"]
      },
      "default": {
        "allow": ["read", "write", "edit", "exec"],
        "deny": ["gateway"]
      },
      "full": {
        "allow": ["*"],
        "deny": []
      }
    },
    "profile": "default"  // グローバルデフォルト
  }
}
```

**使用例**: 制限モードと通常モードの切り替え

---

### 2. Provider Profile（プロバイダー×プロファイル）

**目的**: プロバイダーごとに異なるプロファイルを適用

**設定例**:

```json
{
  "tools": {
    "byProvider": {
      "anthropic": {
        "profile": "full",
        "allow": ["*"]
      },
      "openai": {
        "profile": "minimal",
        "deny": ["exec"]
      }
    }
  }
}
```

**実装**:

```typescript
// dist/agents/pi-tools.policy.js
function resolveProviderToolPolicy(params) {
  const provider = params.modelProvider;  // "anthropic"
  const modelId = params.modelId;         // "claude-sonnet-4-5"
  
  // フルモデルID: "anthropic/claude-sonnet-4-5"
  const fullModelId = `${provider}/${modelId}`;
  
  // 候補: ["anthropic/claude-sonnet-4-5", "anthropic"]
  for (const key of [fullModelId, provider]) {
    if (byProvider[key]) return byProvider[key];
  }
}
```

---

### 3. Global Policy（グローバル設定）

**目的**: システム全体のデフォルト

**設定例**:

```json
{
  "tools": {
    "allow": ["read", "write", "edit", "exec"],
    "deny": ["gateway"]
  }
}
```

**特徴**: すべてのエージェント・セッションに適用される基本ポリシー

---

### 4. Global Provider（グローバル×プロバイダー）

**目的**: プロバイダーごとのグローバル制限

**設定例**:

```json
{
  "tools": {
    "byProvider": {
      "anthropic": {
        "allow": ["*"]
      },
      "openai": {
        "deny": ["sessions_spawn"]
      },
      "gemini": {
        "deny": ["apply_patch"]  // Gemini非対応
      }
    }
  }
}
```

**使用ケース**: 
- Geminiは`apply_patch`非対応（enumをサポートしないため）
- OpenAIは`sessions_spawn`を制限（コスト制御）

---

### 5. Agent Policy（エージェント固有）

**目的**: 特定のエージェントに制限を設ける

**設定例**:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["*"],
          "deny": []
        }
      },
      {
        "id": "worker",
        "tools": {
          "allow": ["read", "write", "exec"],
          "deny": ["gateway", "cron", "sessions_spawn"]
        }
      }
    ]
  }
}
```

**使用ケース**: 
- `main`: フルアクセス
- `worker`: タスク実行のみ（システム管理不可）

---

### 6. Agent Provider（エージェント×プロバイダー）

**目的**: エージェントごとにプロバイダー制限を変える

**設定例**:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "byProvider": {
            "openai": {
              "deny": ["sessions_spawn"]  // コスト削減
            },
            "anthropic": {
              "allow": ["*"]  // Claude は全機能使用
            }
          }
        }
      }
    ]
  }
}
```

---

### 7. Group Policy（グループチャット）

**目的**: グループチャットでのツール制限

**設定例**:

```json
{
  "channels": {
    "discord": {
      "groups": {
        "tools": {
          "default": {
            "deny": ["exec", "gateway", "cron"]
          },
          "byGroupId": {
            "123456789": {
              "allow": ["*"]  // 特定グループのみフル許可
            }
          }
        }
      }
    }
  }
}
```

**実装**:

```typescript
// dist/agents/pi-tools.policy.js
function resolveGroupToolPolicy(params) {
  const { channel, groupId } = resolveGroupContextFromSessionKey(
    params.sessionKey
  );
  
  // グループIDからポリシー解決
  const channelConfig = config.channels[channel];
  const groupTools = channelConfig?.groups?.tools;
  
  // byGroupId優先、なければdefault
  return groupTools?.byGroupId?.[groupId] ?? groupTools?.default;
}
```

**使用ケース**:
- 公開グループ: `exec`禁止
- プライベートグループ: フルアクセス

---

### 8. Sandbox Policy（サンドボックス制限）

**目的**: サンドボックス実行時の追加制限

**設定例**:

```json
{
  "sandbox": {
    "enabled": true,
    "tools": {
      "deny": ["gateway", "nodes"]  // サンドボックス内では禁止
    }
  }
}
```

**実装**:

```typescript
// dist/agents/pi-tools.js
const sandbox = options?.sandbox?.enabled ? options.sandbox : undefined;

const allowBackground = isToolAllowedByPolicies("process", [
  profilePolicy,
  providerProfilePolicy,
  globalPolicy,
  globalProviderPolicy,
  agentPolicy,
  agentProviderPolicy,
  groupPolicy,
  sandbox?.tools,  // ← サンドボックスポリシー
  subagentPolicy,
]);
```

**使用ケース**:
- Dockerサンドボックス内では`gateway`操作禁止
- `nodes`（デバイス制御）もサンドボックスから不可

---

### 9. Subagent Policy（サブエージェント制限）

**目的**: サブエージェントの権限を制限

**デフォルト拒否リスト**:

```typescript
// dist/agents/pi-tools.policy.js
const DEFAULT_SUBAGENT_TOOL_DENY = [
  // セッション管理 - メインエージェントが統括
  "sessions_list",
  "sessions_history",
  "sessions_send",
  "sessions_spawn",
  
  // システム管理 - サブエージェントには危険
  "gateway",
  "agents_list",
  
  // インタラクティブ設定 - タスクではない
  "whatsapp_login",
  
  // ステータス・スケジューリング - メインが調整
  "session_status",
  "cron",
  
  // メモリ - spawn時のプロンプトで渡すべき
  "memory_search",
  "memory_get",
];
```

**設定でカスタマイズ可能**:

```json
{
  "tools": {
    "subagents": {
      "tools": {
        "allow": ["read", "write", "exec"],
        "deny": ["gateway", "sessions_spawn"]
      }
    }
  }
}
```

**理由**:
- サブエージェントは特定タスク実行のみ
- メインエージェントがオーケストレーション
- 無限再帰防止（`sessions_spawn`禁止）

---

## ポリシーの評価順序

### 実際の評価フロー

```typescript
// dist/agents/pi-tools.js
export function createClawdbotCodingTools(options) {
  // 1-2. プロファイル解決
  const profile = agentTools?.profile ?? globalTools?.profile;
  const profilePolicy = resolveToolProfilePolicy(profile);
  
  // 2. プロバイダープロファイル
  const providerProfilePolicy = resolveToolProfilePolicy(providerProfile);
  
  // 3-6. EffectivePolicy解決
  const {
    globalPolicy,
    globalProviderPolicy,
    agentPolicy,
    agentProviderPolicy,
  } = resolveEffectiveToolPolicy(options);
  
  // 7. グループポリシー
  const groupPolicy = resolveGroupToolPolicy(options);
  
  // 8. サンドボックス
  const sandbox = options?.sandbox?.enabled ? options.sandbox : undefined;
  
  // 9. サブエージェント
  const subagentPolicy = isSubagentSessionKey(options?.sessionKey)
    ? resolveSubagentToolPolicy(options.config)
    : undefined;
  
  // 全ポリシーをチェック
  const allowTool = isToolAllowedByPolicies("tool_name", [
    profilePolicy,           // 1
    providerProfilePolicy,   // 2
    globalPolicy,            // 3
    globalProviderPolicy,    // 4
    agentPolicy,             // 5
    agentProviderPolicy,     // 6
    groupPolicy,             // 7
    sandbox?.tools,          // 8
    subagentPolicy,          // 9
  ]);
}
```

---

## ポリシー記法

### allow / deny

```json
{
  "tools": {
    "allow": ["read", "write", "exec"],
    "deny": ["gateway", "sessions_*"]
  }
}
```

### ワイルドカード

```json
{
  "allow": ["*"],           // すべて許可
  "deny": ["sessions_*"]    // sessions_で始まるもの拒否
}
```

### 正規表現変換

```typescript
// dist/agents/pi-tools.policy.js
function compilePattern(pattern) {
  if (pattern === "*") return { kind: "all" };
  
  if (!pattern.includes("*")) {
    return { kind: "exact", value: pattern };
  }
  
  // "sessions_*" → /^sessions_.*$/
  const regex = new RegExp(`^${pattern.replace("*", ".*")}$`);
  return { kind: "regex", value: regex };
}
```

### 優先順位ルール

```
deny > allow
```

**例**:

```json
{
  "allow": ["*"],
  "deny": ["exec"]
}
```

→ `exec`以外すべて許可

---

## 実例：複雑なシナリオ

### シナリオ1: グループチャットでのサブエージェント

**状況**:
- Discord グループチャット
- メインエージェントがサブエージェント spawn
- プロバイダー: OpenAI

**適用されるポリシー**:

```typescript
1. Profile: "default"
   allow: ["read", "write", "exec"]
   
2. Provider Profile: (なし)

3. Global Policy:
   deny: ["gateway"]
   
4. Global Provider (openai):
   deny: ["sessions_spawn"]  // コスト制御
   
5. Agent Policy: (なし)

6. Agent Provider: (なし)

7. Group Policy (Discord):
   deny: ["exec"]  // グループでは危険
   
8. Sandbox: (無効)

9. Subagent:
   deny: ["sessions_spawn", "gateway", "cron", ...]
```

**結果**:

| ツール | 判定 | 理由 |
|--------|------|------|
| `read` | ✅ 許可 | すべてのポリシーがOK |
| `write` | ✅ 許可 | すべてのポリシーがOK |
| `exec` | ❌ 拒否 | Group Policyで拒否 |
| `gateway` | ❌ 拒否 | Global + Subagent で拒否 |
| `sessions_spawn` | ❌ 拒否 | Provider + Subagent で拒否 |

---

### シナリオ2: 個人チャット、Anthropic、サンドボックス

**状況**:
- Telegram DM
- プロバイダー: Anthropic
- サンドボックス有効

**適用されるポリシー**:

```typescript
1. Profile: "full"
   allow: ["*"]
   
2. Provider Profile (anthropic):
   allow: ["*"]
   
3. Global Policy:
   deny: []
   
4. Global Provider: (なし)

5. Agent Policy: (なし)

6. Agent Provider: (なし)

7. Group Policy: (なし - DMのため)

8. Sandbox:
   deny: ["gateway", "nodes"]
   
9. Subagent: (なし - メインエージェント)
```

**結果**:

| ツール | 判定 | 理由 |
|--------|------|------|
| `read` | ✅ 許可 | すべてのポリシーがOK |
| `exec` | ✅ 許可 | すべてのポリシーがOK |
| `gateway` | ❌ 拒否 | Sandboxで拒否 |
| `nodes` | ❌ 拒否 | Sandboxで拒否 |
| `sessions_spawn` | ✅ 許可 | すべてのポリシーがOK |

---

## まとめ

### なぜ9層も必要？

1. **柔軟性**: あらゆるシナリオに対応
2. **セキュリティ**: 多層防御
3. **運用性**: 環境ごとに細かく制御
4. **エンタープライズ**: 組織の要求に対応

### デメリット

1. **複雑**: 理解・設定が困難
2. **デバッグ困難**: どのポリシーが原因かわかりにくい
3. **過剰**: 個人利用では不要

### vLLM Botでは不要な理由

- 単一プロバイダー（vLLM）
- 個人利用想定
- シンプルさ優先
- 必要十分な`allowed_commands`で対応可能

---

## Clawdbotのデバッグ方法

ツールが拒否された場合、どのポリシーが原因かログで確認：

```bash
DEBUG=1 clawdbot gateway start
```

ログ例:

```
[DEBUG] Tool exec denied by group policy (discord:group:123)
```

---

## 参考実装

Clawdbotのソースコード:
- `dist/agents/pi-tools.policy.js` - ポリシー解決
- `dist/agents/pi-tools.js` - ツール作成・フィルタリング
- `dist/agents/tool-policy.js` - ポリシー正規化
