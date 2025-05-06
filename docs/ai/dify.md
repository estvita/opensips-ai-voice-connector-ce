# Dify.ai Workflows

These workflows can be used as function call handlers during a user's conversation with the voice bot.

For example, by registering a function called `get_time` and using the provided [template](https://github.com/estvita/dify-templates/blob/main/opensips/demo%20function.yml), your voice bot can call the Dify.ai server, which will return the current time in a specified time zone.

## Configuration

The following parameters can be tuned for this engine:

| Section  | Parameter    | Environment | Mandatory | Description | Default |
|----------|--------------|-------------|-----------|-------------|---------|

| `dify` | `dify_url`  | `DIFY_API_URL` | no | difi api base url | https://api.dify.ai/v1 |
| `dify` | `dify_key`  | `DIFY_API_KEY` | **yes** | workflow api-key | not set |