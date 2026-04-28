# Privacy Policy

Last updated: 2026-04-28

This Privacy Policy describes how the mem9 Dify Plugin handles information when it is used in Dify.

## Overview

The mem9 Dify Plugin is a tool plugin that lets Dify agents and workflows search and store long-term memories through a configured mem9 API endpoint.

The plugin itself is a thin HTTP client. It does not run analytics, use advertising trackers, set cookies, store memory data locally, or log request or response bodies locally. It transmits the data required for the selected tool call to the mem9 API endpoint configured by the Dify workspace administrator.

By default, the plugin uses the hosted mem9 service at `https://api.mem9.ai`. Users may configure a custom `mem9_base_url` for self-hosted mem9 deployments.

## Information Processed and Transmitted

The plugin may process and transmit the following information:

1. Memory store content
   - Text submitted to the `memory_store` tool.
   - This may include conversation content, user preferences, project context, facts, decisions, or other information selected by the Dify application or agent for long-term memory.
   - This content may contain personal data if users or applications include it.

2. Memory search queries
   - Search text submitted to the `memory_search` tool.
   - Queries are sent to mem9 to retrieve relevant stored memories.

3. Session identifiers
   - Optional `session_id` values, such as a Dify conversation ID, may be sent to mem9 to scope memories by conversation or session.
   - These identifiers are indirect identifiers and should not be controlled by the language model.

4. Agent identifiers
   - The configured `mem9_agent_id` is sent to mem9 to identify the calling agent or integration.

5. API credentials
   - The `mem9_api_key` is stored by the Dify instance as a plugin credential and transmitted to the configured mem9 API endpoint in the `X-API-Key` header for authentication and tenant identification.
   - When the plugin is configured in Multi-space Authorization Mode, an additional API Key may be supplied as a parameter on each workflow node (`api_key`). The plugin reads it only at call time and passes it to mem9 in the `X-API-Key` header. The plugin does not persist this node-level API Key beyond the call. Operators may bind this parameter to a Dify workspace environment variable so the actual key value is not stored in the workflow definition.
   - The plugin does not intentionally expose API keys to language model outputs or store API keys as memories.

Following Dify's privacy classification guidance, this plugin may process indirect identifiers such as session IDs and agent IDs, and may process user-provided content that can be combined with other data to identify a person if such content is submitted to the memory tools.

## How Information Is Used

The plugin uses the transmitted information only to provide mem9 memory functionality:

- `memory_store` sends text to mem9 smart ingest so mem9 can extract, reconcile, embed, and store useful long-term memory.
- `memory_search` sends a query to mem9 so mem9 can retrieve relevant memories and return a concise ranked result list.
- `session_id` and `mem9_agent_id` are used to scope, organize, and retrieve memories.
- API Key(s) — the provider-level `mem9_api_key` and, in Multi-space mode, any per-node `api_key` parameter — are used for authentication and tenant identification.

## Hosted mem9 Service

When the plugin is configured with the default hosted endpoint, data sent through the plugin is transmitted to mem9's hosted service.

mem9 may use infrastructure and subprocessors to provide memory extraction, embedding, storage, search, and related service operations. For more information about mem9's security and trust model, see:

https://mem9.ai/docs/#security-and-trust

## Self-Hosted Deployments

If the Dify workspace administrator configures `mem9_base_url` to point to a self-hosted mem9 deployment, the plugin sends requests to that configured endpoint instead of the hosted mem9 service.

In self-hosted deployments, data storage, access control, retention, security, subprocessors, and compliance practices are determined by the user's own mem9 deployment and infrastructure configuration.

## Data Storage and Retention

The plugin itself does not store memory content. Dify stores plugin credentials according to the Dify instance's credential storage configuration. Workflow node parameters (including any per-node API Key in Multi-space mode) are stored as part of the Dify workflow definition by the Dify instance.

Memory content and derived memory records are stored by the configured mem9 service. For hosted mem9, memories are retained in the user's mem9 workspace until deleted by the user or workspace administrator via the mem9 API or dashboard. For self-hosted mem9, retention is controlled by the user's deployment and database configuration.

## Data Deletion

The current plugin version provides memory search and memory store tools. It does not expose a delete tool in Dify.

Users or workspace administrators can delete memories through the mem9 API or the mem9 dashboard where supported. In self-hosted deployments, deletion is governed by the user's own mem9 deployment and storage configuration.

## User Control and Responsibilities

Users and Dify workspace administrators are responsible for:

- Configuring the correct `mem9_base_url`, Authorization Mode, and any required API Key(s).
- Selecting an appropriate Authorization Mode (Single space or Multi-space) for the workflow.
- In Multi-space Authorization Mode, providing per-node API Keys via Dify workspace environment variables when possible, rather than pasting plain-text keys into workflow nodes.
- Deciding when Dify agents or workflows call `memory_store`.
- Avoiding storage of sensitive information that should not become long-term memory.
- Configuring `session_id` appropriately, for example by binding it to Dify's conversation ID for per-conversation isolation.
- Managing access control, retention, and compliance policies for their mem9 workspace or self-hosted deployment.

## Contact

If you have questions about this Privacy Policy or the mem9 Dify Plugin, contact:

mem9@pingcap.com

## Changes to This Policy

This Privacy Policy may be updated from time to time. Updates will be reflected in the plugin repository and package metadata.
