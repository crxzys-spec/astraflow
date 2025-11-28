# Middleware 节点化升级

## 当前状态
- 后端/协议：Schema/OpenAPI 已加入 `role`/`middlewares`，调度/WS 支持 middleware 派发与 `middleware.next_request/response`，run 取消返回 `next_cancelled`，并携带 `host_node_id`/`middleware_chain`/`chain_index` 元数据；next 错误码 `next_*` 已整理并导出供前端/SDK 使用；子图定义与 UUID 均已字符串化以便回放。
- Worker：SDK 暴露 `ctx.next(...)`，任务取消会上报 `E.RUNNER.CANCELLED` 并终止挂起的 next；链路元数据写入 ExecutionContext。
- 前端：Palette 按角色分组；Inspector 支持 middlewares 列表；画布节点展示 middleware 胶囊；Runs 详情可按链路顺序查看 middleware trace 并过滤；Runs 列表可筛选含 middleware 的运行。

## 核心设计（摘要）
- 角色：节点 manifest `role`（node/container/middleware，默认 node）。
- 挂载：节点字段 `middlewares: string[]`（同一 workflow ID，按顺序串行）。
- 执行链：调度按 `mw... → host` 派发；middleware 内 `ctx.next()` 触发下一环节，可多次调用。
- Ready 判定：宿主 ready = 自身依赖 + 所有挂载 middleware 及其依赖 ready；middlewares 自动串行依赖。
- Trace：调度收集 middleware/host 状态，UI 按链路顺序展示。

## 收尾与维护建议
- 测试回归：覆盖空链/单链/多链、失败/取消/超时、重复 `next`、深链高并发性能。
- Worker 收尾：如有长时间挂起的 `ctx.next`，补充资源清理/超时 abort 钩子以便业务接入。
- 前端迭代：画布黏附/拖拽体验优化，Runs trace 文案/耗时汇总，消费 `next_*` 错误码提示。
