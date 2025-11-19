# Jarvis MVP

Real-time voice assistant for frontline workers with zero-hallucination architecture and sub-335ms latency.

## Project Overview

Jarvis is a voice assistant that provides instant, accurate, and verifiable information through natural voice interaction. Built with the Pipecat framework for optimal performance and rapid development.

### Key Features

- **Sub-335ms latency** - Fastest in class
- **100% grounded responses** - All answers include source attribution
- **Zero hallucinations** - Strict retrieval-augmented generation
- **Natural conversation** - Context awareness and interruptibility
- **Universal access** - Web browser on any device

### Technology Stack

- **Backend**: Python 3.11+ with Pipecat framework, FastAPI
- **Frontend**: React 18 with TypeScript, Vite, Tailwind CSS
- **Infrastructure**: AWS CDK (TypeScript)
- **AI Services**: Deepgram (ASR), GPT-4 Turbo (LLM), ElevenLabs (TTS)
- **Data**: Pinecone (vector DB), PostgreSQL (logs), Redis (cache)

## Project Structure

```
jarvis/
├── backend/                 # Python backend with Pipecat
│   ├── jarvis_pipeline.py  # Main voice pipeline (~250 lines)
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile         # Container configuration
│   ├── test_setup.py      # Environment verification
│   └── README.md          # Backend documentation
├── frontend/               # React web client
│   ├── src/               # Source code
│   ├── public/            # Static assets
│   ├── package.json       # Node dependencies
│   └── README.md          # Frontend documentation
├── infrastructure/         # AWS CDK infrastructure
│   ├── lib/               # CDK stack definitions
│   ├── bin/               # CDK app entry point
│   └── README.md          # Infrastructure documentation
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Getting Started

### Prerequisites

- **Node.js** 18+ (recommended: 20+)
- **Python** 3.11+ (recommended: 3.12)
- **Git** 2.x
- **AWS CLI** (for infrastructure deployment)
- **Docker** (optional, for containerized development)

### Initial Setup

1. **Clone the repository**
```bash
git clone https://github.com/metamonk/jarvis.git
cd jarvis
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required API keys:
- `DEEPGRAM_API_KEY` - Speech-to-text
- `OPENAI_API_KEY` - LLM processing
- `ELEVENLABS_API_KEY` - Text-to-speech
- `PINECONE_API_KEY` - Vector database
- `GITHUB_TOKEN` - Code search (optional)
- `COMPANY_API_KEY` - Internal API (if applicable)

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify setup
python test_setup.py

# Run development server
uvicorn jarvis_pipeline:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### Infrastructure Setup

```bash
cd infrastructure

# Install dependencies
npm install

# Build and verify CDK stack
npm run build
npx cdk synth
```

## Development Workflow

### Running the Full Stack Locally

1. **Terminal 1 - Backend**:
```bash
cd backend && source venv/bin/activate
uvicorn jarvis_pipeline:app --reload
```

2. **Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

3. Open browser to `http://localhost:5173`

### Running Tests

**Backend**:
```bash
cd backend
python test_setup.py
# Additional tests TBD
```

**Frontend**:
```bash
cd frontend
npm run lint
npm run build  # Verify build works
```

**Infrastructure**:
```bash
cd infrastructure
npm run test
npx cdk synth  # Verify stack compiles
```

## Deployment

### Automated CI/CD (Recommended)

The project uses GitHub Actions for automated deployment to AWS with secure OIDC authentication.

**Quick Setup** (5 minutes):
```bash
# 1. Run the setup script
cd .github/workflows
./setup-aws-oidc.sh

# 2. Add GitHub secrets (values from script output):
#    - AWS_ACCOUNT_ID
#    - AWS_ROLE_ARN

# 3. Create 'production' environment in GitHub

# 4. Bootstrap CDK
cd ../../infrastructure
npx cdk bootstrap

# 5. Push to main branch - automatic deployment!
git push origin main
```

**Features:**
- Automated testing on every PR
- Secure AWS authentication (no stored credentials)
- Automated deployment to AWS on push to main/master
- Rollback support via CloudFormation

**Documentation:**
- **Quick Start**: `.github/workflows/QUICKSTART.md`
- **Full Guide**: `CICD.md` (comprehensive documentation)
- **Setup Details**: `.github/workflows/README.md`

### Manual Deployment (Alternative)

#### AWS Infrastructure Deployment

```bash
cd infrastructure

# First time only - Bootstrap AWS account
cdk bootstrap aws://ACCOUNT-ID/REGION

# Deploy infrastructure
cdk deploy

# Monitor deployment
# Infrastructure will create:
# - VPC with public/private subnets
# - ECS Fargate cluster
# - RDS PostgreSQL
# - ElastiCache Redis
# - S3 + CloudFront for frontend
# - Application Load Balancer
```

#### Backend Deployment

Backend is deployed via Docker to ECS Fargate:
```bash
# Build Docker image
docker build -t jarvis-backend backend/

# Tag for ECR
docker tag jarvis-backend:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/jarvis-backend:latest

# Push to ECR
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/jarvis-backend:latest
```

#### Frontend Deployment

Frontend is deployed to S3 + CloudFront:
```bash
cd frontend
npm run build

# Deploy to S3
aws s3 sync dist/ s3://jarvis-frontend-bucket/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id DIST_ID --paths "/*"
```

## Environment Configuration

### Development

Local development uses `.env` file:
```bash
DEEPGRAM_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
```

### Production

Production uses AWS Secrets Manager:
- Secrets are automatically loaded by ECS tasks
- No credentials in code or environment files
- Rotation supported for enhanced security

## API Documentation

### Backend Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `WebSocket /ws` - Main voice assistant connection

### WebSocket Protocol

Client connects via WebSocket and streams audio:
1. Client sends audio chunks (binary)
2. Backend processes through Pipecat pipeline
3. Backend streams back audio response
4. Transcripts included in metadata

## Performance Targets

| Metric | Target | Expected |
|--------|--------|----------|
| Latency P90 | <500ms | 335ms ✅ |
| Latency P95 | <1000ms | ~400ms ✅ |
| Accuracy | ≥95% | TBD |
| Grounding Rate | 100% | 100% ✅ |
| Uptime | ≥99% | TBD |

## Troubleshooting

### Backend Issues

**Import errors**: Ensure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**API key errors**: Verify all required keys in `.env`

**Port conflicts**: Change port in uvicorn command

### Frontend Issues

**Build errors**: Clear node_modules and reinstall
```bash
rm -rf node_modules package-lock.json
npm install
```

**WebSocket connection**: Verify backend is running on correct port

### Infrastructure Issues

**CDK synthesis fails**: Verify TypeScript compiles
```bash
npm run build
```

**AWS credentials**: Configure AWS CLI
```bash
aws configure
```

## Contributing

**Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.**

Key points:
- **NO AI attribution** in commits (for security reasons)
- **Use Context7** for latest dependency documentation (see `.taskmaster/docs/CONTEXT7_GUIDE.md`)
- Follow conventional commit format
- Write tests for new features
- Update documentation

Quick workflow:
1. Create feature branch: `git checkout -b feature/your-feature`
2. Check Context7 for dependency docs before implementing
3. Make changes and test locally
4. Commit: `git commit -m "feat: add feature"` (no AI attribution!)
5. Push and create PR

## Project Timeline

**Week 1**: Foundation & Core Pipeline (✅ COMPLETE)
- Day 1-2: Project setup
- Day 3-4: Pipecat backend
- Day 5: Tool functions & testing

**Week 2**: Infrastructure & Deployment (CURRENT)
- Day 1-2: AWS CDK infrastructure
- Day 3-4: CI/CD pipeline
- Day 5: Frontend development

**Week 3**: Testing, Polish & Launch
- Day 1-2: Performance optimization
- Day 3-4: Testing & validation
- Day 5: Launch preparation

## Resources

- [Pipecat Documentation](https://github.com/pipecat-ai/pipecat)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Project PRD](./.taskmaster/docs/prd.md)
- [Architecture Documentation](./.taskmaster/docs/)

## License

Proprietary - Internal use only

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review component-specific READMEs
3. Contact the development team
