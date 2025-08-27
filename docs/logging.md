# Call-Specific Logging System

## Overview

The voice connector now supports per-call logging, where each call creates its own log file instead of writing to a shared log. This provides better organization and easier debugging of individual calls.

## Directory Structure

```
logs/
├── app.log (general server log)
├── 2025-08-24/
│   ├── bot_123/
│   │   ├── call_B2B.502.79.1756047989.2127904424.log
│   │   └── call_B2B.179.218.1756047597.1337560528.log
│   ├── bot_456/
│   │   └── call_B2B.123.45.1756048000.1111111111.log
│   └── bot_789/
│       └── call_B2B.111.222.1756048200.3333333333.log
├── 2025-08-25/
│   └── bot_123/
│       └── call_B2B.444.555.1756134400.4444444444.log
└── ...
```

## File Naming Convention

### Path Format
```
logs/{YYYY-MM-DD}/bot_{bot_id}/call_{call_id}.log
```

### Examples
- `logs/2025-08-24/bot_123/call_B2B.502.79.1756047989.2127904424.log`
- `logs/2025-08-24/bot_456/call_B2B.179.218.1756047597.1337560528.log`

## Log Content

### General Log (`app.log`)
- Server startup/shutdown
- General errors
- System statistics
- Configuration issues
- **Note**: Call-specific logs are completely separated and do not appear here

### Call-Specific Logs (`call_{id}.log`)
- Call initialization
- WebSocket connections
- MCP interactions
- Audio processing
- Call-specific errors
- Call termination
- **Note**: These logs are completely isolated from the general log

## Implementation Details

### CallLogger Class

The `CallLogger` class manages individual call logging:

```python
from call_logger import create_call_logger

# Create logger for a call
call_logger = create_call_logger(call_id, bot_id)
logger = call_logger.get_logger()

# Log messages
logger.info("Call started")
logger.error("Connection failed")

# Cleanup when call ends
call_logger.cleanup()
```

### Integration Points

1. **Call Class**: Creates call-specific logger in constructor
2. **AIEngine**: Receives logger instance and uses it for all logging
3. **OpenAI API**: Uses call logger for all OpenAI-related messages
4. **MCP Client**: Logs are captured through the AI engine

### Log Isolation

Call-specific loggers are completely isolated from the general application log:

- **Logger Names**: Call loggers use names like `call_B2B.502.79.1756047989.2127904424`
- **Propagation Disabled**: `logger.propagate = False` prevents messages from going to root logger
- **Separate Handlers**: Each call logger has its own file handler
- **No Cross-Contamination**: Call logs never appear in `app.log`

## Configuration

### Log Rotation
- **Max file size**: 10MB per call log
- **Backup count**: 3 files per call
- **Encoding**: UTF-8

### Log Format
```
%(asctime)s - tid: %(thread)d - %(levelname)s - %(message)s
```

Example:
```
2025-08-24 20:20:05,589 - tid: 140204331655232 - INFO - Call started - ID: B2B.502.79.1756047989.2127904424, Bot: 123
```

## Benefits

1. **Better Organization**: Each call has its own log file
2. **Easier Debugging**: No need to filter through shared logs
3. **Performance**: Reduced contention on shared log file
4. **Retention**: Individual call logs can be managed separately
5. **Analysis**: Easy to analyze specific calls or bots

## Maintenance

### Automatic Cleanup
- Call logs are automatically cleaned up when calls end
- Old log directories can be removed based on date
- Log rotation prevents unlimited disk usage

### Manual Cleanup
```bash
# Remove logs older than 30 days
find logs/ -type d -name "2025-*" -mtime +30 -exec rm -rf {} \;

# Remove empty bot directories
find logs/ -type d -empty -delete
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure write permissions on logs directory
2. **Disk Space**: Monitor log directory size and implement cleanup
3. **Missing Bot ID**: Calls without bot_id use "unknown" as default

### Debug Mode
Enable debug logging for more detailed information:
```bash
python3 main.py --loglevel DEBUG
```
