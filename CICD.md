# CI/CD Pipeline for Jarvis

## Overview

This document describes the CI/CD pipeline for the Jarvis voice assistant application. The pipeline uses GitHub Actions for automated testing and deployment to AWS using secure OIDC authentication.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Actions                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Test Backend │  │Test Frontend │  │Test Infra    │          │
│  │   (Python)   │  │ (React/Next) │  │  (AWS CDK)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
│                    ┌───────▼────────┐                            │
│                    │ Deploy to AWS  │                            │
│                    │  (via OIDC)    │                            │
│                    └───────┬────────┘                            │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                             │ OIDC Auth (No Credentials)
                             │
                             ▼
              ┌──────────────────────────────┐
              │         AWS Cloud            │
              ├──────────────────────────────┤
              │  • CloudFormation            │
              │  • Lambda / ECS              │
              │  • S3, API Gateway           │
              │  • DynamoDB, CloudWatch      │
              └──────────────────────────────┘
```

## Pipeline Stages

### 1. Testing Phase (Parallel)

#### Backend Tests
- **Purpose**: Validate Python backend environment and dependencies
- **Steps**:
  - Set up Python 3.11
  - Install dependencies from `requirements.txt`
  - Run `test_setup.py` to verify environment

#### Frontend Tests
- **Purpose**: Validate React/Next.js application
- **Steps**:
  - Set up Node.js 20 and pnpm
  - Install dependencies
  - Run ESLint
  - Build the application

#### Infrastructure Tests
- **Purpose**: Validate AWS CDK infrastructure code
- **Steps**:
  - Install CDK dependencies
  - Build TypeScript code
  - Run `cdk synth` to validate CloudFormation templates

### 2. Deployment Phase (Sequential)

**Only runs on push to main/master branch**

- Configure AWS credentials via OIDC (no secrets!)
- Verify AWS access
- Install all dependencies
- Deploy CDK stack to AWS
- Generate deployment summary

### 3. Notification Phase

- Report deployment success/failure
- Generate GitHub summary with deployment details

## Security Features

### OIDC Authentication
- **No stored credentials**: Uses OpenID Connect for temporary credentials
- **Principle of least privilege**: IAM role with minimal required permissions
- **Automatic expiration**: Credentials expire after each workflow run
- **Audit trail**: All actions logged in CloudTrail

### GitHub Security
- **Environment protection**: Production environment with optional approvals
- **Branch protection**: Required checks before merge
- **Secret scanning**: GitHub automatically scans for exposed secrets
- **Dependency scanning**: Dependabot alerts for vulnerable dependencies

## Setup Instructions

### Quick Setup (Recommended)

1. **Run the automated setup script:**
   ```bash
   cd .github/workflows
   ./setup-aws-oidc.sh
   ```

2. **Follow the prompts** to configure AWS OIDC

3. **Add secrets to GitHub** (script provides exact values):
   - `AWS_ACCOUNT_ID`
   - `AWS_ROLE_ARN`

4. **Create GitHub Environment** named `production`

5. **Bootstrap CDK** (first time only):
   ```bash
   cd infrastructure
   npx cdk bootstrap
   ```

### Manual Setup

See detailed instructions in `.github/workflows/README.md`

## Usage

### Automatic Deployments

Push to `main` or `master` branch:
```bash
git push origin main
```

The pipeline will automatically:
1. Run all tests
2. Deploy to AWS if tests pass
3. Report status

### Manual Deployments

Trigger via GitHub UI:
1. Go to **Actions** tab
2. Select **Deploy Jarvis Application**
3. Click **Run workflow**
4. Select branch
5. Click **Run workflow** button

### Pull Requests

When you create a PR:
- All tests run automatically
- Deployment does NOT occur
- Must pass all tests before merge

## Monitoring

### GitHub Actions

View workflow runs:
```
https://github.com/YOUR_ORG/jarvis/actions
```

Each run shows:
- Test results for all components
- Deployment status
- Logs for troubleshooting

### AWS Console

Monitor deployed resources:
- **CloudFormation**: View stack status and resources
- **CloudWatch**: View application logs
- **Lambda/ECS**: Monitor function/container execution
- **X-Ray**: Trace requests (if enabled)

### Notifications

Current notification methods:
- GitHub Actions summary
- Workflow status badges

Future enhancements:
- Slack notifications
- Email alerts
- PagerDuty integration

## Environment Variables

### Pipeline Variables
- `AWS_REGION`: Target region (default: us-east-1)
- `NODE_VERSION`: Node.js version (20)
- `PYTHON_VERSION`: Python version (3.11)

### Required Secrets
- `AWS_ACCOUNT_ID`: Your AWS account ID
- `AWS_ROLE_ARN`: ARN of the GitHub Actions IAM role

### Optional Secrets
- Add any application-specific secrets as needed

## Troubleshooting

### Common Issues

#### 1. OIDC Authentication Fails

**Error Message:**
```
Error: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

**Solution:**
- Verify trust policy in IAM role includes correct GitHub repo
- Check OIDC provider exists in AWS account
- Ensure `AWS_ROLE_ARN` secret is correct

#### 2. CDK Bootstrap Required

**Error Message:**
```
Stack does not exist
```

**Solution:**
```bash
cd infrastructure
npx cdk bootstrap aws://ACCOUNT_ID/REGION
```

#### 3. Permission Denied

**Error Message:**
```
User is not authorized to perform: [some AWS action]
```

**Solution:**
- Review IAM policy attached to GitHub Actions role
- Add missing permissions
- Re-run the setup script

#### 4. Build Failures

**Backend:**
```bash
cd backend
python test_setup.py
```

**Frontend:**
```bash
cd scira
pnpm install
pnpm run build
```

**Infrastructure:**
```bash
cd infrastructure
npm run build
npx cdk synth
```

### Debug Mode

Enable debug logging in GitHub Actions:

1. Go to **Settings → Secrets → Actions**
2. Add secret: `ACTIONS_STEP_DEBUG` = `true`
3. Add secret: `ACTIONS_RUNNER_DEBUG` = `true`
4. Re-run workflow

## Performance

### Typical Run Times

- **Test Phase**: 3-5 minutes (parallel)
- **Deployment Phase**: 5-10 minutes (sequential)
- **Total**: 8-15 minutes

### Optimization Strategies

1. **Caching**: pip, npm, and pnpm caches reduce install time
2. **Parallel Tests**: Backend, frontend, and infrastructure tests run simultaneously
3. **Incremental Deploys**: CDK only updates changed resources
4. **Docker Layer Caching**: If using containers, layers are cached

## Best Practices

### Development Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Push and create PR**:
   ```bash
   git push origin feature/my-feature
   ```

4. **Wait for tests** to pass in PR

5. **Merge to main** after approval

6. **Automatic deployment** occurs

### Deployment Best Practices

1. **Small, incremental changes**: Deploy frequently with small changes
2. **Test locally first**: Run tests before pushing
3. **Monitor after deployment**: Check logs and metrics
4. **Keep secrets secret**: Never commit credentials
5. **Use environment protection**: Require approvals for production
6. **Tag releases**: Create git tags for important deployments

### Rollback Strategy

If deployment causes issues:

**Option 1: Revert Commit**
```bash
git revert HEAD
git push origin main
```
This triggers a new deployment with the previous code.

**Option 2: CloudFormation Rollback**
```bash
aws cloudformation rollback-stack --stack-name JarvisStack
```

**Option 3: Manual Rollback**
- Go to CloudFormation console
- Select JarvisStack
- Choose "Roll back" option

## Cost Optimization

### GitHub Actions
- **Free tier**: 2,000 minutes/month for public repos
- **Private repos**: 2,000 minutes/month on free plan
- **Caching**: Reduces compute time and costs

### AWS Resources
- **CDK**: No additional cost (uses CloudFormation)
- **Lambda**: Pay per request (free tier: 1M requests/month)
- **S3**: Pay for storage (first 5GB free)
- **CloudWatch**: Pay for logs and metrics

### Tips to Reduce Costs
1. Use caching to minimize build times
2. Set retention policies on CloudWatch logs
3. Use Lambda instead of always-on servers
4. Clean up unused CloudFormation stacks
5. Monitor AWS Cost Explorer regularly

## Compliance and Governance

### Security Compliance
- ✅ No long-lived credentials
- ✅ Least privilege IAM policies
- ✅ Encryption in transit (HTTPS/TLS)
- ✅ Audit logging (CloudTrail)
- ✅ Secret scanning enabled

### Access Control
- **GitHub**: Branch protection, required reviews
- **AWS**: IAM roles with limited permissions
- **Environments**: Protection rules, manual approvals

### Audit Trail
- **GitHub**: All commits, PRs, and deployments logged
- **AWS**: CloudTrail logs all API calls
- **CloudWatch**: Application logs retained

## Maintenance

### Regular Tasks

**Weekly:**
- Review deployment logs
- Check for failed workflows
- Monitor AWS costs

**Monthly:**
- Update dependencies
- Review IAM permissions
- Test rollback procedure

**Quarterly:**
- Security audit
- Performance review
- Update documentation

### Dependency Updates

**Dependabot** automatically creates PRs for:
- npm packages (frontend/infrastructure)
- pip packages (backend)
- GitHub Actions versions

Review and merge these PRs regularly.

## Future Improvements

### Planned Enhancements

1. **Multi-environment support**
   - Development
   - Staging
   - Production

2. **Advanced testing**
   - Integration tests
   - E2E tests with Playwright
   - Load testing with k6

3. **Enhanced monitoring**
   - Application Performance Monitoring (APM)
   - Real User Monitoring (RUM)
   - Synthetic monitoring

4. **Deployment strategies**
   - Blue-green deployments
   - Canary releases
   - Feature flags

5. **Security enhancements**
   - SAST scanning (Snyk, SonarQube)
   - DAST scanning
   - Container scanning
   - License compliance checks

6. **Notifications**
   - Slack integration
   - Email notifications
   - Status page updates

## Resources

### Documentation
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [AWS CDK Guide](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)

### Repository Files
- `.github/workflows/deploy.yml` - Main workflow
- `.github/workflows/README.md` - Detailed setup guide
- `.github/workflows/setup-aws-oidc.sh` - Automated setup script

### Support
- GitHub Issues: Report bugs or request features
- GitHub Discussions: Ask questions
- AWS Support: For AWS-specific issues

## Changelog

### v1.0.0 - Initial Release
- GitHub Actions workflow with OIDC
- Automated testing for backend, frontend, infrastructure
- AWS CDK deployment
- Comprehensive documentation
- Setup automation script
