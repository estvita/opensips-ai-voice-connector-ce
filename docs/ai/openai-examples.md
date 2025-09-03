# OpenAI Flavor - Examples and Use Cases

This document provides practical examples and use cases for the OpenAI flavor's advanced features including Function Calling and MCP server integration.

## Function Calling Examples

### Basic Call Management

The OpenAI flavor automatically provides built-in functions for call management:

```ini
[openai]
# Configure transfer destinations
transfer_to = sip:operator@company.com
transfer_by = sip:bot@company.com
```

When a user says "transfer me to an operator" or "I need help", the AI can automatically use the `transfer_call` function to redirect the call.

### Custom API Functions

You can define custom functions to integrate with your business logic:

```ini
[openai]
functions = [
    {
        "name": "check_account_balance",
        "description": "Check user's account balance",
        "parameters": {
            "type": "object",
            "properties": {
                "account_number": {
                    "type": "string",
                    "description": "User's account number"
                }
            },
            "required": ["account_number"]
        }
    },
    {
        "name": "schedule_appointment",
        "description": "Schedule a new appointment",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Preferred date (YYYY-MM-DD)"
                },
                "time": {
                    "type": "string",
                    "description": "Preferred time (HH:MM)"
                },
                "service": {
                    "type": "string",
                    "description": "Type of service needed"
                }
            },
            "required": ["date", "time", "service"]
        }
    }
]
```

## MCP Server Integration Examples

### Simple MCP Server Setup

Basic configuration for a single MCP server:

```ini
[openai]
mcp_server_url = https://your-mcp-server.com/mcp
mcp_api_key = your-secret-key
```

### Advanced MCP Configuration

Multiple MCP servers with different approval levels:

```ini
[openai]
mcp_servers = [
    {
        "url": "https://internal-tools.company.com/mcp",
        "label": "internal_tools",
        "require_approval": "never",
        "api_key": "internal-key"
    },
    {
        "url": "https://external-apis.company.com/mcp",
        "label": "external_apis",
        "require_approval": "always",
        "api_key": "external-key"
    },
    {
        "url": "https://database.company.com/mcp",
        "label": "database_access",
        "require_approval": "always"
    }
]
```

### Common MCP Server Use Cases

1. **Customer Database Integration**
   - Access customer information
   - Update customer records
   - Check order status

2. **External API Integration**
   - Weather services
   - News feeds
   - Payment processing
   - Shipping calculations

3. **Business Logic Automation**
   - Appointment scheduling
   - Inventory checks
   - Price calculations
   - Document generation

## Complete Configuration Example

Here's a comprehensive example combining all features:

```ini
[openai]
disabled = false
model = gpt-4o-realtime-preview-2024-10-01
key = your-openai-api-key
voice = alloy
temperature = 0.8
max_tokens = 4096

# Welcome message
welcome_message = Hello! I'm your AI assistant. How can I help you today?

# Instructions for the AI
instructions = You are a helpful customer service AI. You can transfer calls, check account information, and schedule appointments. Always be polite and professional.

# Call transfer configuration
transfer_to = sip:support@company.com
transfer_by = sip:ai-assistant@company.com

# Custom functions
functions = [
    {
        "name": "get_customer_info",
        "description": "Retrieve customer information by phone number",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Customer's phone number"
                }
            },
            "required": ["phone_number"]
        }
    }
]

# MCP server integration
mcp_servers = [
    {
        "url": "https://crm.company.com/mcp",
        "label": "crm_system",
        "require_approval": "never",
        "api_key": "crm-api-key"
    },
    {
        "url": "https://billing.company.com/mcp",
        "label": "billing_system",
        "require_approval": "always",
        "api_key": "billing-api-key"
    }
]
```

## Best Practices

1. **Function Design**: Keep functions simple and focused on single tasks
2. **Parameter Validation**: Always define required parameters and their types
3. **MCP Security**: Use approval requirements for sensitive operations
4. **Error Handling**: Implement proper error handling in your MCP servers
5. **Testing**: Test functions and MCP integrations thoroughly before production use

## Troubleshooting

### Common Issues

1. **Function not working**: Check that the function name matches exactly in your configuration
2. **MCP connection failed**: Verify the MCP server URL and API key
3. **Permission denied**: Check the `require_approval` settings for MCP servers

### Debug Mode

Enable detailed logging to troubleshoot issues:

```ini
[engine]
log_level = DEBUG
```

This will provide detailed information about function calls and MCP server interactions.
