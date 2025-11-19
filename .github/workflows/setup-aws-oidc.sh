#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  AWS OIDC Setup for GitHub Actions - Jarvis${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if jq is installed (for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed. Some features may not work.${NC}"
    echo "Install with: brew install jq (macOS) or apt-get install jq (Linux)"
fi

# Get AWS Account ID
echo -e "${YELLOW}Fetching AWS Account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Could not fetch AWS Account ID. Are you logged in?${NC}"
    exit 1
fi
echo -e "${GREEN}AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"
echo ""

# Get GitHub Repository Information
read -p "Enter your GitHub organization/username: " GITHUB_ORG
read -p "Enter your repository name (default: jarvis): " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-jarvis}

echo ""
echo -e "${YELLOW}Creating OIDC Provider...${NC}"

# Check if OIDC provider already exists
OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_PROVIDER_ARN" &> /dev/null; then
    echo -e "${GREEN}OIDC Provider already exists${NC}"
else
    # Create OIDC provider
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
        || echo -e "${YELLOW}Warning: OIDC provider creation failed (may already exist)${NC}"
    echo -e "${GREEN}OIDC Provider created${NC}"
fi

echo ""
echo -e "${YELLOW}Creating IAM Role Trust Policy...${NC}"

# Create trust policy JSON
cat > /tmp/github-actions-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

echo -e "${GREEN}Trust policy created${NC}"

echo ""
echo -e "${YELLOW}Creating IAM Role...${NC}"

ROLE_NAME="GitHubActionsDeployRole"

# Check if role already exists
if aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo -e "${YELLOW}Role already exists. Updating trust policy...${NC}"
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file:///tmp/github-actions-trust-policy.json
else
    # Create role
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/github-actions-trust-policy.json \
        --description "Role for GitHub Actions to deploy Jarvis application"
    echo -e "${GREEN}IAM Role created${NC}"
fi

echo ""
echo -e "${YELLOW}Creating deployment policy...${NC}"

# Create deployment policy JSON
cat > /tmp/deployment-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "iam:GetRole",
        "iam:PassRole",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:CreateServiceLinkedRole",
        "ec2:*",
        "ecs:*",
        "ecr:*",
        "logs:*",
        "apigateway:*",
        "dynamodb:*",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:PutParameter",
        "secretsmanager:GetSecretValue",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
EOF

echo -e "${GREEN}Deployment policy created${NC}"

echo ""
echo -e "${YELLOW}Attaching policies to role...${NC}"

POLICY_NAME="GitHubActionsDeploymentPolicy"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

# Check if policy exists
if aws iam get-policy --policy-arn "$POLICY_ARN" &> /dev/null; then
    echo -e "${YELLOW}Policy already exists${NC}"

    # Get the default version
    DEFAULT_VERSION=$(aws iam get-policy --policy-arn "$POLICY_ARN" --query 'Policy.DefaultVersionId' --output text)

    # Create a new version
    echo -e "${YELLOW}Creating new policy version...${NC}"
    aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document file:///tmp/deployment-policy.json \
        --set-as-default || echo -e "${YELLOW}Warning: Could not update policy${NC}"
else
    # Create policy
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/deployment-policy.json \
        --description "Permissions for GitHub Actions to deploy Jarvis"
    echo -e "${GREEN}Policy created${NC}"
fi

# Attach policy to role
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$POLICY_ARN" \
    2>/dev/null || echo -e "${YELLOW}Policy already attached to role${NC}"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Get Role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)

echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "1. Add the following secrets to your GitHub repository:"
echo "   Go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo -e "   ${YELLOW}AWS_ACCOUNT_ID${NC}:"
echo "   ${AWS_ACCOUNT_ID}"
echo ""
echo -e "   ${YELLOW}AWS_ROLE_ARN${NC}:"
echo "   ${ROLE_ARN}"
echo ""
echo "2. Create a GitHub Environment named 'production':"
echo "   Go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/environments"
echo ""
echo "3. (Optional) Add protection rules to the production environment"
echo ""
echo "4. Bootstrap CDK in your AWS account (if not already done):"
echo "   cd infrastructure"
echo "   npx cdk bootstrap aws://${AWS_ACCOUNT_ID}/us-east-1"
echo ""
echo "5. Push to main branch to trigger the deployment!"
echo ""
echo -e "${GREEN}==================================================${NC}"

# Cleanup
rm -f /tmp/github-actions-trust-policy.json
rm -f /tmp/deployment-policy.json
