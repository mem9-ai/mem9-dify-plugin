# mem9 – Long-term Memory for Dify

mem9 plugin gives your Dify agents and workflows persistent, long-term memory. It lets your AI remember facts, preferences, and prior context across conversations.

## Setup

Install the plugin in Dify, then go to **Tools > mem9 > Authorize** and fill in the following credentials:

| Credential | Required | Description |
|---|---|---|
| **API Key** | Yes | Your mem9 API key. You can get one at [mem9.ai](https://mem9.ai). |
| **API Base URL** | No | Defaults to `https://api.mem9.ai`. Change this only if you are using a self-hosted mem9 instance. |
| **Agent ID** | No | Defaults to `dify`. Use a custom value to separate memory namespaces when multiple apps share the same mem9 space. |

Enter the API key into configuration.

![Configuration](./_assets/configuration.png)

If you don't have an API key, run this command.

```bash
curl -X POST https://api.mem9.ai/v1alpha1/mem9s
```

## Tools

### Memory Search

Search for relevant memories based on a query.

![Search](./_assets/memory-search.png)

### Memory Store

Store information into long-term memory. mem9 automatically extracts and reconciles key facts from the content you provide — you don't need to pre-process it.

![Search](./_assets/memory-store.png)

## Session ID (optional)

Session ID controls memory isolation. When set, searches and stores are scoped to that session.

**Recommended setup:** bind Session ID to Dify's built-in `sys.conversation_id` variable. This gives each conversation its own memory scope while still allowing cross-session recall when Session ID is left empty.

- **In Agent apps** — set Session ID to `{{sys.conversation_id}}` in the tool configuration.
- **In Workflow apps** — pass the `sys.conversation_id` variable to the Session ID field of the Memory Search / Memory Store nodes.

If you don't set a Session ID, memories are stored and searched globally within your mem9 space.
