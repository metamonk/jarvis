# Jarvis CI/CD Pipeline Documentation

## Overview

This directory contains GitHub Actions workflows for automated testing and deployment of the Jarvis voice assistant application to AWS using secure OIDC authentication.

## Workflow: `deploy.yml`

The main deployment workflow consists of the following jobs:

1. **test-backend**: Tests the Python backend (Pipecat pipeline)
2. **test-frontend**: Lints and builds the React/Next.js frontend
3. **test-infrastructure**: Validates AWS CDK infrastructure code
4. **deploy**: Deploys to AWS (only on push to main/master)
5. **notify-failure**: Reports deployment failures

### Triggers

- **Push to main/master**: Runs full test suite and deploys to production
- **Pull requests**: Runs tests only (no deployment)
- **Manual trigger**: Via workflow_dispatch

## AWS OIDC Setup

### Why OIDC?

OpenID Connect (OIDC) allows GitHub Actions to authenticate with AWS without storing long-lived AWS credentials as secrets. This is more secure and follows AWS best practices.

### Prerequisites

1. AWS Account with administrative access
2. GitHub repository with Actions enabled
3. AWS CLI installed locally (for setup)

### Step-by-Step OIDC Configuration

#### 1. Create the OIDC Identity Provider in AWS

```bash
# Configure AWS CLI with your credentials
aws configure

# Create the OIDC provider (one-time setup per AWS account)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

#### 2. Create IAM Role for GitHub Actions

Create a file named `github-actions-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/jarvis:*"
        }
      }
    }
  ]
}
```

**Replace:**
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `YOUR_GITHUB_ORG` with your GitHub organization/username

Create the role:

```bash
# Create the IAM role
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://github-actions-trust-policy.json \
  --description "Role for GitHub Actions to deploy Jarvis application"
```

#### 3. Attach Permissions to the Role

Create a file named `deployment-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "iam:*",
        "ec2:*",
        "ecs:*",
        "ecr:*",
        "logs:*",
        "apigateway:*",
        "dynamodb:*",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "secretsmanager:GetSecretValue",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Attach the policy:

```bash
# Create the policy
aws iam create-policy \
  --policy-name GitHubActionsDeploymentPolicy \
  --policy-document file://deployment-policy.json

# Attach the policy to the role
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsDeploymentPolicy
```

**Note:** For production, you should restrict these permissions to only what's needed. The above is a starting point.

#### 4. Configure GitHub Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

1. **AWS_ACCOUNT_ID**: Your AWS account ID (12 digits)
2. **AWS_ROLE_ARN**: The ARN of the role created above
   - Format: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsDeployRole`

To get your AWS Account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

To get the Role ARN:
```bash
aws iam get-role --role-name GitHubActionsDeployRole --query Role.Arn --output text
```

#### 5. Create GitHub Environment

1. Go to **Settings → Environments** in your GitHub repository
2. Create a new environment named `production`
3. (Optional) Add protection rules:
   - Required reviewers
   - Wait timer
   - Deployment branches (limit to main/master)

### Verification

After setup, you can verify OIDC is working by:

1. Making a commit to your main branch
2. Checking the Actions tab in GitHub
3. The "Configure AWS credentials using OIDC" step should succeed
4. The "Verify AWS credentials" step should show your assumed role

## Environment Variables

The workflow uses the following environment variables:

- `AWS_REGION`: Target AWS region (default: us-east-1)
- `NODE_VERSION`: Node.js version for frontend and infrastructure
- `PYTHON_VERSION`: Python version for backend

## Local Testing

### Test Backend Locally

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python test_setup.py
```

### Test Frontend Locally

```bash
cd scira
pnpm install
pnpm run lint
pnpm run build
```

### Test Infrastructure Locally

```bash
cd infrastructure
npm install
npm run build
npx cdk synth
```

## Troubleshooting

### OIDC Authentication Fails

**Error:** "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Solutions:**
1. Verify the trust policy has the correct GitHub repository path
2. Check that the OIDC provider is created in your AWS account
3. Ensure the role ARN secret is correct

### CDK Deployment Fails

**Error:** "Stack does not exist"

**Solution:** Run the initial deployment manually:
```bash
cd infrastructure
npx cdk bootstrap aws://ACCOUNT_ID/REGION
npx cdk deploy
```

### Permission Denied Errors

**Solution:** Review and expand the IAM policy attached to the GitHub Actions role to include the missing permissions.

## Security Best Practices

1. **Use OIDC** instead of long-lived credentials
2. **Limit role permissions** to only what's needed
3. **Use GitHub Environments** with protection rules
4. **Enable branch protection** on main/master
5. **Review deployment logs** regularly
6. **Rotate secrets** if accidentally exposed
7. **Use separate AWS accounts** for staging/production

## Monitoring

### GitHub Actions Dashboard

Monitor deployments at: `https://github.com/YOUR_ORG/jarvis/actions`

### AWS CloudWatch

View deployment logs in CloudWatch:
```bash
aws logs tail /aws/lambda/YOUR_FUNCTION_NAME --follow
```

### Deployment History

Check CloudFormation stack events:
```bash
aws cloudformation describe-stack-events --stack-name JarvisStack
```

## Rollback Procedure

If a deployment fails or causes issues:

1. **Immediate rollback via AWS Console:**
   - Go to CloudFormation
   - Select the JarvisStack
   - Choose "Roll back"

2. **Rollback via CLI:**
```bash
cd infrastructure
npx cdk deploy --rollback
```

3. **Revert via Git:**
```bash
git revert HEAD
git push origin main
# This triggers a new deployment with the previous code
```

## Performance Optimization

### Caching

The workflow uses caching for:
- Python pip packages
- Node.js npm/pnpm packages
- CDK assets

### Parallel Jobs

Tests run in parallel to reduce total workflow time:
- Backend tests
- Frontend tests
- Infrastructure tests

All must pass before deployment proceeds.

## Future Enhancements

Potential improvements to the CI/CD pipeline:

1. **Staging Environment**: Add a staging deployment step
2. **Integration Tests**: Add end-to-end tests
3. **Performance Tests**: Add load testing
4. **Security Scanning**: Add SAST/DAST tools
5. **Automated Rollback**: Implement automatic rollback on health check failures
6. **Slack/Email Notifications**: Add deployment notifications
7. **Blue-Green Deployments**: Implement zero-downtime deployments

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Check AWS CloudWatch logs
4. Open an issue in the repository

## References

- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
