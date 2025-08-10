# API Setup Guide

## OpenAI API Configuration

### Getting Your API Key

1. **Create an OpenAI Account**
   - Visit [OpenAI Platform](https://platform.openai.com)
   - Sign up or log in to your account

2. **Generate API Key**
   - Navigate to API Keys section
   - Click "Create new secret key"
   - Copy the key immediately (it won't be shown again)

3. **Add Credits**
   - Go to Billing section
   - Add payment method
   - Purchase credits ($5-10 is good for testing)

### Setting Up Your Environment

1. **Create .env file**
   ```bash
   cp .env.example .env
   ```

2. **Add your API key**
   ```bash
   # Edit .env file
   OPENAI_API_KEY=sk-proj-YOUR-ACTUAL-KEY-HERE
   ```

3. **Verify setup**
   ```bash
   python -c "import os; print('API Key configured!' if os.getenv('OPENAI_API_KEY') else 'No API key found')"
   ```

### Security Best Practices

#### DO:
- Keep .env file in .gitignore
- Use environment variables
- Rotate keys regularly
- Set usage limits in OpenAI dashboard
- Monitor your usage

#### DON'T:
- Commit API keys to git
- Share keys publicly
- Use production keys for testing
- Hardcode keys in source files
- Use same key across projects

### Cost Management

#### GPT-4 Pricing (as of 2024)
- Input: $0.03 per 1K tokens
- Output: $0.06 per 1K tokens
- Average query: ~500-2000 tokens

#### Cost Optimization Tips
1. **Use GPT-3.5 for testing**
   ```python
   # In config.py
   MODEL_NAME = "gpt-3.5-turbo"  # 10x cheaper
   ```

2. **Set usage limits**
   - Monthly budget in OpenAI dashboard
   - Per-request limits in code

3. **Cache responses**
   - Avoid duplicate API calls
   - Store common queries

### Troubleshooting

#### Common Issues

1. **"Invalid API Key"**
   - Check for typos
   - Ensure key starts with `sk-`
   - Verify .env is loaded

2. **"Rate limit exceeded"**
   - Wait 1 minute
   - Upgrade tier if needed
   - Implement exponential backoff

3. **"Insufficient credits"**
   - Add payment method
   - Purchase more credits
   - Check usage dashboard

#### Debug Commands

```bash
# Check if API key is loaded
python -c "from config import OPENAI_API_KEY; print(f'Key loaded: {bool(OPENAI_API_KEY)}')"

# Test API connection
python -c "
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-3.5-turbo', temperature=0)
print(llm.invoke('Say hello').content)
"
```

### API Key Rotation

If your key is compromised:

1. **Immediately revoke the key**
   - OpenAI dashboard → API keys → Revoke

2. **Generate new key**
   - Create new secret key
   - Update .env file

3. **Update deployments**
   - All local environments
   - Any cloud deployments
   - CI/CD variables

### Alternative Models

You can use other models by modifying `config.py`:

```python
# GPT-3.5 (Faster, cheaper)
MODEL_NAME = "gpt-3.5-turbo"

# GPT-4 (Better quality)
MODEL_NAME = "gpt-4"

# GPT-4 Turbo (Best for complex analysis)
MODEL_NAME = "gpt-4-turbo-preview"
```

### Rate Limits

Default limits for new accounts:
- 3 requests per minute (RPM)
- 200 requests per day
- 40,000 tokens per minute

To increase limits:
1. Add payment method
2. Generate some usage
3. Request increase in dashboard

### Monitoring Usage

Track your API usage:

```python
# Add to your code
import tiktoken

def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# Log token usage
tokens_used = count_tokens(prompt) + count_tokens(response)
print(f"Tokens used: {tokens_used} (${tokens_used * 0.00003:.4f})")
```

### Environment Variables

Complete list for the project:

```bash
# Required
OPENAI_API_KEY=sk-proj-...

# Optional
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0
OPENAI_MAX_TOKENS=2000
```

### Support

- [OpenAI Documentation](https://platform.openai.com/docs)
- [API Reference](https://platform.openai.com/docs/api-reference)
- [Community Forum](https://community.openai.com)
- [Status Page](https://status.openai.com)