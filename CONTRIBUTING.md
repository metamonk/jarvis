# Contributing to Jarvis MVP

## Development Guidelines

### Commit Message Rules

**IMPORTANT**: For security and professional reasons, do NOT include any AI tool attribution in commits:

❌ **DO NOT** include:
- References to Claude, Claude Code, or Anthropic
- "Generated with Claude" or similar phrases
- "Co-Authored-By: Claude" or AI co-author credits
- Any AI tool attribution in commit messages or code comments

✅ **DO** write commits as if written by the developer:
```bash
git commit -m "feat: implement voice pipeline with Pipecat"
git commit -m "fix: resolve WebSocket connection timeout"
git commit -m "docs: update API documentation"
```

### Commit Message Format

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
git commit -m "feat(backend): add Deepgram integration for STT"
git commit -m "fix(frontend): resolve audio capture permissions"
git commit -m "docs(readme): update setup instructions"
```

## Dependency Management

### Using Context7 for Documentation

**ALWAYS check Context7 for the latest dependency documentation before implementation.**

Context7 provides up-to-date library documentation and examples. Use it to:
1. Verify correct API usage
2. Check for breaking changes
3. Find best practices
4. Get current code examples

#### Example Workflow

Before implementing a new dependency:

```bash
# 1. Check Context7 for documentation
# Use MCP tool: mcp__context7__resolve-library-id
# Then: mcp__context7__get-library-docs

# 2. Review latest API documentation
# 3. Implement using current best practices
# 4. Test thoroughly
```

#### Supported Libraries

Context7 has documentation for major libraries including:
- React, Vite, TypeScript
- FastAPI, Pipecat, Python packages
- AWS CDK, AWS services
- And many more

Always check Context7 first to ensure you're using the latest patterns.

## Code Review Process

### Before Committing

1. **Test locally**: Ensure all tests pass
2. **Check formatting**: Run linters/formatters
3. **Review changes**: Use `git diff` to review all changes
4. **Write clear commit message**: Follow format above
5. **No AI attribution**: Double-check commit message

### Pull Request Guidelines

1. **Title**: Use conventional commit format
2. **Description**:
   - Summarize what changed
   - Explain why it changed
   - Link to any relevant tasks or issues
3. **Testing**: Describe how you tested the changes
4. **Screenshots**: Include if UI changes

**Example PR Description**:
```markdown
## Summary
Implements the Pipecat voice pipeline with Deepgram, OpenAI, and ElevenLabs integrations.

## Changes
- Added Pipecat pipeline configuration
- Integrated Deepgram STT service
- Connected OpenAI GPT-4 for LLM
- Added ElevenLabs TTS streaming
- Implemented WebSocket transport

## Testing
- Tested with 50+ voice queries
- Verified P90 latency <500ms
- Checked error handling for API failures
- Validated audio quality

## Task Reference
Completes Task 2: Pipecat Backend Implementation
```

## Branch Naming

Use descriptive branch names with type prefix:

```bash
feature/pipecat-integration
fix/websocket-timeout
docs/api-documentation
refactor/audio-processing
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow code style guidelines
- Write tests for new features
- Update documentation as needed
- Check Context7 for dependency docs

### 3. Test Locally

```bash
# Backend tests
cd backend && python test_setup.py

# Frontend tests
cd frontend && npm run build

# Infrastructure tests
cd infrastructure && npx cdk synth
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: your feature description"
# NO AI attribution in commit message!
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
gh pr create --title "feat: your feature" --body "Description..."
```

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Max line length: 100 characters
- Use Black for formatting
- Use docstrings for functions

```python
async def process_audio(audio_data: bytes) -> str:
    """
    Process audio data through the Pipecat pipeline.

    Args:
        audio_data: Raw audio bytes from client

    Returns:
        Transcribed text string
    """
    # Implementation
```

### TypeScript (Frontend/Infrastructure)

- Follow Airbnb style guide
- Use ES6+ features
- Max line length: 100 characters
- Use Prettier for formatting
- Use JSDoc for complex functions

```typescript
/**
 * Establishes WebSocket connection to backend
 * @param url - WebSocket URL
 * @returns WebSocket instance
 */
function connectWebSocket(url: string): WebSocket {
  // Implementation
}
```

## Testing Standards

### Backend Tests

- Unit tests for all functions
- Integration tests for API endpoints
- Test error handling
- Test edge cases

### Frontend Tests

- Component tests
- Integration tests
- E2E tests for critical flows
- Accessibility tests

### Performance Tests

- Measure P90/P95 latency
- Test under load
- Profile memory usage
- Monitor API rate limits

## Security Guidelines

1. **Never commit secrets**: Use environment variables
2. **Validate all inputs**: Sanitize user data
3. **Use HTTPS/WSS**: No unencrypted connections in production
4. **Keep dependencies updated**: Regular security audits
5. **Follow OWASP guidelines**: Check OWASP Top 10

## Documentation

### When to Update Docs

- New features added
- API changes
- Configuration changes
- Breaking changes
- Setup process changes

### Documentation Files

- `README.md`: Project overview and setup
- `SETUP.md`: Quick start guide
- Component READMEs: Specific instructions
- Code comments: Complex logic only
- API docs: All endpoints

## Questions or Issues?

- Check existing documentation first
- Review Context7 for dependency docs
- Ask in team chat
- Create an issue for bugs
- Submit PR for improvements

---

**Remember**:
- No AI attribution in commits
- Use Context7 for dependency docs
- Write clean, tested code
- Follow conventional commits
