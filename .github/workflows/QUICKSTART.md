# CI/CD Quick Start Guide

## 🚀 5-Minute Setup

### Prerequisites
- AWS account with admin access
- AWS CLI installed and configured
- GitHub repository with admin access

### Step 1: Run Setup Script (2 minutes)

```bash
cd .github/workflows
./setup-aws-oidc.sh
```

**What it does:**
- Creates AWS OIDC provider
- Creates IAM role for GitHub Actions
- Attaches deployment permissions
- Provides secrets to add to GitHub

### Step 2: Add GitHub Secrets (1 minute)

The script outputs two secrets. Add them to GitHub:

1. Go to: `https://github.com/YOUR_ORG/jarvis/settings/secrets/actions`
2. Click "New repository secret"
3. Add:
   - **Name:** `AWS_ACCOUNT_ID`
     **Value:** [from script output]

   - **Name:** `AWS_ROLE_ARN`
     **Value:** [from script output]

### Step 3: Create Environment (1 minute)

1. Go to: `https://github.com/YOUR_ORG/jarvis/settings/environments`
2. Click "New environment"
3. Name: `production`
4. Click "Configure environment"
5. (Optional) Add protection rules:
   - ✅ Required reviewers
   - ✅ Wait timer: 5 minutes
   - ✅ Deployment branches: main/master only

### Step 4: Bootstrap CDK (1 minute)

```bash
cd ../../infrastructure
npx cdk bootstrap
```

This creates the S3 bucket and other resources CDK needs.

### Step 5: Test Pipeline! (push to trigger)

```bash
# From project root
git push origin main
```

Then watch it work:
- Go to `https://github.com/YOUR_ORG/jarvis/actions`
- Click on the running workflow
- Watch the magic happen! ✨

---

## ✅ That's It!

Your CI/CD pipeline is now live and will automatically:
- Test all code on every PR
- Deploy to AWS on every push to main/master
- Provide deployment summaries

---

## 🔧 Troubleshooting

### "Role cannot be assumed"
- Double-check the `AWS_ROLE_ARN` secret matches the script output exactly
- Verify the trust policy includes your repository path

### "Bootstrap required"
```bash
cd infrastructure
npx cdk bootstrap
```

### "Permission denied"
- The IAM role needs more permissions
- Edit the policy in AWS Console → IAM → Policies → GitHubActionsDeploymentPolicy

---

## 📚 Full Documentation

For detailed information:
- **Setup Details:** `.github/workflows/README.md`
- **Architecture:** `CICD.md` (in project root)
- **Status:** `.github/CICD_STATUS.md`

---

## 🎯 Next Steps

1. **Add Protection Rules**: Require reviews before production deploys
2. **Add Notifications**: Set up Slack/email alerts
3. **Add Staging**: Create a staging environment
4. **Add Tests**: Expand test coverage

---

## 💬 Need Help?

- Check `.github/workflows/README.md` for detailed troubleshooting
- Open an issue in the repository
- Review GitHub Actions logs for specific errors

---

**Happy Deploying! 🚢**
