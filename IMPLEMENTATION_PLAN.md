# vLLM Bot - Planner/Tool Runner/Responder 実装計画

## 📋 設計サマリー

ユーザーが提案された設計：
- **目的**: vLLM の Chat Completions を使用したOS操作エージェント
- **3段構成**: Planner（LLM） → Tool Runner（ホスト） → Responder（LLM）
- **ループ制御**: 最大5ループ、各ループで ChatCompletion 2回
- **状態管理**: MEMORY（長期）、STATE（短期）、RUNLOG（監査）
- **安全制約**: パス制限、コマンド制限、リソース制限

---

## 🎯 実装フェーズ

### Phase 1: 基本データ構造（Week 1）

#### 1.1 MEMORY システム（src/memory.py）
```python
class Memory:
    """長期記憶：ユーザの好み・環境・決定"""
    - user_preferences: dict  # 言語、出力粒度、禁止事項
    - environment: dict       # OS、作業ディレクトリ、ネットワーク可否
    - repeated_decisions: dict # よく使うコマンド、命名規則
    - load_from_file()
    - append_fact(category, key, value)  # ホストが追記
    - to_context() -> str  # LLMプロンプト用
```

#### 1.2 STATE システム（src/state.py）
```python
class AgentState:
    """短期状態：1会話内の進行管理"""
    - loop_count: int
    - history: list[LoopRecord]  # Planner意図、ツール、結果
    - facts: list[str]           # 得られた事実
    - remaining_tasks: list[str] # 未解決事項
    - last_tool_results: dict    # 直近のツール結果
    
class LoopRecord:
    - loop_id: int
    - planner_response: dict  # Plannerの出力JSON
    - tool_calls_made: list
    - tool_results: list
    - responder_output: str
```

#### 1.3 RUNLOG システム（src/audit_log.py）
```python
class AuditLog:
    """監査ログ：何がいつ、どう実行されたか"""
    - log_entry(timestamp, loop_id, tool_name, args, result, exit_code, duration)
    - get_history() -> list
    - export_to_json()
```

### Phase 2: Planner モジュール（Week 1-2）

#### 2.1 Planner クラス（src/planner.py）
```python
class Planner(VLLMProvider):
    """ツール選択・手順設計"""
    - system_prompt: str  # TOOL情報 + ベストプラクティス
    - memory: Memory
    - state: AgentState
    
    def plan(self, user_request: str) -> PlannerOutput:
        """
        入力: ユーザ要求 + MEMORY + STATE要約
        出力: JSON
        {
          "need_tools": bool,
          "tool_calls": [
            {"tool_name": "read_file", "args": {"path": "..."}},
            ...
          ],
          "reason_brief": "...",
          "stop_condition": "得られたらResponderで回答可能"
        }
        """
        
        prompt = self._build_prompt(user_request)
        response = self.chat_completion(prompt)
        output = self._parse_json(response)
        
        return output
    
    def _build_prompt(self, user_request: str) -> str:
        """TOOL情報 + MEMORY + STATE をプロンプトに組み込み"""
        return f"""
        ## System Instructions
        You are a planning agent. Your role is to decide which tools to call next.
        
        ## Available Tools
        {self._format_tool_specs()}
        
        ## Long-term Memory
        {self.memory.to_context()}
        
        ## Current State
        Loop {self.state.loop_count}/5
        Facts gathered: {len(self.state.facts)}
        Remaining tasks: {self.state.remaining_tasks}
        
        ## User Request
        {user_request}
        
        ## Your Response (JSON only)
        Return a JSON object with: need_tools, tool_calls, reason_brief, stop_condition
        """
```

#### 2.2 Planner Output パースと検証
```python
class PlannerOutput:
    - need_tools: bool
    - tool_calls: list[ToolCall]
    - reason_brief: str
    - stop_condition: str
    
    @staticmethod
    def from_json(json_str: str) -> 'PlannerOutput':
        """JSON パース + バリデーション"""
        ...
```

---

### Phase 3: Tool Runner モジュール（Week 2）

#### 3.1 Tool Runner（src/tool_runner.py）
```python
class ToolRunner:
    """Plannerの tool_calls を実行"""
    - tools: dict[str, Callable]  # tool_name -> 実装
    - audit_log: AuditLog
    - constraints: ToolConstraints
    
    def execute_calls(self, calls: list[ToolCall], loop_id: int) -> list[ToolResult]:
        """
        各ツール呼び出しを実行し、結果を構造化して返す
        """
        results = []
        for call in calls:
            try:
                result = self._execute_single(call, loop_id)
            except Exception as e:
                result = ToolResult.error(str(e))
            results.append(result)
        return results
    
    def _execute_single(self, call: ToolCall, loop_id: int) -> ToolResult:
        """個別ツール実行 + 安全柵適用"""
        # 1. バリデーション（パス、コマンド許可等）
        self._validate_call(call)
        
        # 2. 実行
        start = time.time()
        result = self.tools[call.tool_name](call.args)
        duration = time.time() - start
        
        # 3. ログ記録
        self.audit_log.log_entry(
            timestamp=datetime.now(),
            loop_id=loop_id,
            tool_name=call.tool_name,
            args=call.args,
            result=result.output,
            exit_code=result.exit_code,
            duration=duration
        )
        
        return result
```

#### 3.2 ToolConstraints（安全制約）
```python
class ToolConstraints:
    """ホストが強制する安全制約"""
    - allowed_root: Path          # 許可ルート（例: /home/agent/）
    - command_allowlist: set      # 許可コマンド
    - timeout_sec: int            # タイムアウト
    - max_output_size: int        # stdout 上限
    - max_stderr_size: int        # stderr 上限
    
    def validate_path(self, path: str) -> bool:
        """パスが許可ルート内か確認"""
        ...
    
    def validate_command(self, cmd: str) -> bool:
        """コマンドが allowlist に含まれるか"""
        ...
```

#### 3.3 ツール実装の拡張
```python
class ToolImplementation:
    """最小ツール群"""
    - list_dir(path: str) -> list[str]
    - read_file(path: str, offset?: int, limit?: int) -> str
    - write_file(path: str, content: str) -> bool
    - exec_cmd(cmd: str, args?: list[str]) -> (str, int)  # stdout, exit_code
    - grep(pattern: str, path: str) -> list[str]
```

---

### Phase 4: Responder モジュール（Week 2-3）

#### 4.1 Responder クラス（src/responder.py）
```python
class Responder(VLLMProvider):
    """ツール結果を踏まえた自然言語回答"""
    - system_prompt: str
    - memory: Memory
    - state: AgentState
    
    def respond(
        self,
        user_request: str,
        tool_results: list[ToolResult],
        loop_id: int
    ) -> ResponderOutput:
        """
        入力: MEMORY + STATE + ツール結果
        出力: 自然言語回答 + 続行判定
        {
          "response": "...",  # ユーザ向け回答
          "summary": "...",   # 実行した操作の要約
          "next_action": "..." # 未解決なら次の一手
        }
        """
        
        prompt = self._build_prompt(
            user_request,
            tool_results,
            loop_id
        )
        response = self.chat_completion(prompt)
        output = self._parse_output(response)
        
        return output
    
    def _build_prompt(self, user_request, tool_results, loop_id) -> str:
        """tool_results を含めてプロンプト構築"""
        return f"""
        ## System Instructions
        You are a response agent. Your role is to explain tool results to the user.
        
        ## User Request
        {user_request}
        
        ## Tool Results from Loop {loop_id}
        {self._format_results(tool_results)}
        
        ## Current Facts
        {self.state.facts}
        
        ## Your Response
        1. Explain what was executed
        2. Summarize the results
        3. If unresolved, show next steps
        4. Do NOT make assumptions beyond tool results
        """
```

---

### Phase 5: ループ制御とエラーハンドリング（Week 3）

#### 5.1 Agent Loop（src/agent_loop.py）
```python
class AgentLoop:
    """Planner-ToolRunner-Responder の実行ループ"""
    - planner: Planner
    - tool_runner: ToolRunner
    - responder: Responder
    - state: AgentState
    - max_loops: int = 5
    - loop_timeout_sec: int = 300
    
    def run(self, user_request: str) -> str:
        """
        ループを実行し、最終回答を返す
        """
        self.state.reset()
        
        for loop_id in range(1, self.max_loops + 1):
            # Step 1: Planner
            plan = self.planner.plan(user_request)
            
            # Step 2: Tool Runner
            if plan.need_tools:
                tool_results = self.tool_runner.execute_calls(
                    plan.tool_calls,
                    loop_id
                )
            else:
                tool_results = []
            
            # Step 3: Responder
            responder_out = self.responder.respond(
                user_request,
                tool_results,
                loop_id
            )
            
            # Step 4: 状態更新
            self.state.add_loop_record(
                loop_id, plan, tool_results, responder_out
            )
            
            # Step 5: 終了判定
            if self._should_stop(responder_out, plan):
                return responder_out.response
            
            # ループ前ワイト（LLMレート制限対策）
            time.sleep(0.5)
        
        # 5ループ到達時の最終回答
        return self._final_response_on_limit()
    
    def _should_stop(self, responder_out, plan) -> bool:
        """終了条件チェック"""
        return (
            not plan.need_tools or
            len(self.state.remaining_tasks) == 0 or
            responder_out.is_final_answer
        )
    
    def _final_response_on_limit(self) -> str:
        """ループ上限到達時の回答"""
        return f"""
        5 iterations completed. Reached limits.
        
        Facts gathered:
        {self.state.facts}
        
        Remaining tasks:
        {self.state.remaining_tasks}
        
        Check logs for details:
        {self.state.audit_log_path}
        """
```

#### 5.2 エラーハンドリング
```python
class ToolError(Exception):
    """ツール実行エラー"""
    - tool_name: str
    - original_error: str
    - suggestion: str  # 代替案

def handle_tool_error(error: ToolError, loop_id: int):
    """
    1. エラーを構造化
    2. Responder に材料として返す
    3. 次ループで探索方針を強制
    """
    ...
```

---

### Phase 6: コンフィグレーション（Week 3）

#### 6.1 config.json 拡張
```json
{
  "vllm": {...},
  "agent": {
    "max_loops": 5,
    "loop_timeout_sec": 300,
    "enable_function_calling": true
  },
  "memory": {
    "path": "./data/memory.json",
    "auto_backup": true
  },
  "tool_constraints": {
    "allowed_root": "./workspace",
    "command_allowlist": ["ls", "cat", "grep", "find", "echo"],
    "timeout_sec": 30,
    "max_output_size": 200000
  },
  "audit": {
    "enabled": true,
    "log_path": "./data/runlog.jsonl"
  }
}
```

---

## 📁 ファイル構成（完成形）

```
vllm-bot/
├── src/
│   ├── __init__.py
│   ├── vllm_provider.py       # (既存) vLLM API通信
│   ├── tools.py               # (既存) ツール実装
│   ├── memory.py              # (新規) 長期記憶
│   ├── state.py               # (新規) 短期状態
│   ├── audit_log.py           # (新規) 監査ログ
│   ├── planner.py             # (新規) Planner LLM
│   ├── responder.py           # (新規) Responder LLM
│   ├── tool_runner.py         # (新規) Tool Runner + 安全制約
│   ├── agent_loop.py          # (新規) ループ制御
│   └── agent.py               # (改訂) Agent クラス統合
├── config/
│   ├── config.json            # (改訂) 設定拡張
│   └── prompts/
│       ├── planner.txt        # Planner システムプロンプト
│       └── responder.txt      # Responder システムプロンプト
├── data/
│   ├── memory.json            # (新規) 長期記憶
│   └── runlog.jsonl           # (新規) 監査ログ
├── tests/
│   ├── test_agent_loop.py     # (新規) ループテスト
│   ├── test_planner.py        # (新規) Planner テスト
│   └── test_responder.py      # (新規) Responder テスト
├── AGENT_DESIGN.md            # (新規) 設計ドキュメント
└── ...
```

---

## 🚀 実装優先順位

1. **Phase 1** (最優先): データ構造（Memory, State, AuditLog）
   - 他のモジュール全てがこれに依存
   
2. **Phase 2**: Planner モジュール
   - LLM 側の責務を明確化
   
3. **Phase 3**: Tool Runner + 安全制約
   - ホスト側の責務を明確化
   
4. **Phase 4**: Responder モジュール
   - ユーザ向け出力品質
   
5. **Phase 5**: ループ制御
   - 統合と制御
   
6. **Phase 6**: コンフィグと最適化

---

## ✅ 検証ポイント

各フェーズ完了時：
- [ ] ユニットテスト（各モジュール独立）
- [ ] 統合テスト（ループ全体）
- [ ] 実際のOS操作テスト（read/write/exec）
- [ ] エラーケース（権限エラー、タイムアウト等）
- [ ] メモリ・ログ機能確認

---

## 📊 推定工数

- Phase 1: 2-3日（データ構造の設計・実装）
- Phase 2: 2-3日（Planner）
- Phase 3: 2-3日（Tool Runner + 制約）
- Phase 4: 2日（Responder）
- Phase 5: 2日（ループ制御）
- Phase 6: 1日（コンフィグ・最適化）

**合計: 2週間程度**

---

## 次のステップ

1. ✅ この計画をレビュー・修正
2. Phase 1（Memory/State/AuditLog）の実装開始
3. 各フェーズごとにテスト・ドキュメント
4. 最後に統合テストと動作確認
