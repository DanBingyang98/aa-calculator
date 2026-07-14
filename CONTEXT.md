# CONTEXT — AccountBook

## Glossary

- **Event** — 一次多人活动（聚餐、旅行、团建等），参与者各自垫付花销后需要结算。每个 Event 独立核算。
- **Participant** — 活动的参与者。一个 Event 有多个 Participant，每个 Participant 可以录入多笔 Expense。
- **Expense** — 一笔花销记录。由某个 Participant 垫付，包含金额和用途，归属到某个 Event。默认均摊给 Event 所有参与者，可指定只分摊给部分参与者。
- **Settlement** — 一次结算结果。通过净额清算，保证每对人之间最多一笔 Transfer（一人可转给多人，但给同一个人只转一次）。
- **Transfer** — Settlement 中的一条转账指令，指明 谁 → 谁，多少钱。
- **Entry** — 参与者在微信群里发的一条记账消息。格式：`<金额> <用途> [@某人 ...]`。脚本解析聊天记录提取 Entry。
