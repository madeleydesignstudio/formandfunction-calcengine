# Railway Deployment Guide - Form & Function Calc Engine

This guide walks you through deploying the Python calculation engine to Railway as a containerized application.

## Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli) installed (optional)
- [Railway account](https://railway.app)
- Go API deployed and accessible (for beam data)
- Docker installed locally (for testing)

## Quick Deployment via Railway Dashboard

### 1. Create New Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub repository
5. Select the `formandfunction-calcengine` repository

### 2. Configure Environment Variables

In the Railway dashboard, add these environment variables:

**Required:**
- `API_BASE_URL` - URL of your Go API (e.g., `https://your-go-api.railway.app`)

**Optional:**
- `BEAM_API_TIMEOUT` - API timeout in seconds (default: 10)
- `DEFAULT_SAFETY_FACTOR` - Default safety factor (default: 1.6)
- `LOG_LEVEL` - Logging level (default: INFO)

### 3. Custom Domain Setup

1. Go to your Railway project settings
2. Navigate to Networking > Custom Domain
3. Add `engine.itsformfunction.com`
4. Configure DNS:
   ```
   Type: CNAME
   Name: engine
   Value: your-project.railway.app
   ```

## Deployment via Railway CLI

### Step 1: Install Railway CLI

```bash
# macOS
brew install railway

# npm
npm install -g @railway/cli

# Other platforms - download from https://railway.app/cli
```

### Step 2: Login and Initialize

```bash
# Login to Railway
railway login

# Navigate to project directory
cd formandfunction-calcengine

# Initialize Railway project
railway init

# Link to existing project (if already created)
railway link [project-id]
```

### Step 3: Configure Environment Variables

```bash
# Set required environment variables
railway variables set API_BASE_URL=https://your-go-api.railway.app

# Optional variables
railway variables set BEAM_API_TIMEOUT=10
railway variables set DEFAULT_SAFETY_FACTOR=1.6
railway variables set LOG_LEVEL=INFO
```

### Step 4: Deploy

```bash
# Deploy to Railway
railway up

# Check deployment status
railway status

# View logs
railway logs
```

## Project Structure for Railway

```
formandfunction-calcengine/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── railway.json           # Railway deployment config
├── test_calc.py           # Test suite
├── start.sh               # Local development script
├── .env.example           # Environment variables template
├── LICENSE                # MIT License
└── RAILWAY_DEPLOYMENT.md  # This file
```

## Environment Configuration

### Development (Local)
```bash
export API_BASE_URL=http://localhost:8080
export CALC_ENGINE_PORT=8081
python main.py
```

### Production (Railway)
- `PORT` - Automatically set by Railway
- `API_BASE_URL` - Set via Railway dashboard or CLI
- Automatic HTTPS and scaling
- Container health checks enabled

## Testing Deployment

### Local Docker Testing

```bash
# Build Docker image
docker build -t calc-engine .

# Run container
docker run -p 8081:8081 -e API_BASE_URL=http://host.docker.internal:8080 calc-engine

# Test endpoints
curl http://localhost:8081/health
```

### Production Testing

```bash
# Health check
curl https://engine.itsformfunction.com/health

# Get beams
curl https://engine.itsformfunction.com/beams

# Test calculation
curl -X POST https://engine.itsformfunction.com/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "applied_load": 10.0,
    "span_length": 6.0,
    "load_type": "uniform",
    "material_grade": "S355"
  }'
```

## Monitoring and Logs

### View Logs
```bash
# Via CLI
railway logs

# Via dashboard
# Go to project > Deployments > Click deployment > View logs
```

### Health Monitoring

Railway automatically monitors:
- Container health via Docker HEALTHCHECK
- HTTP endpoint availability
- Resource usage (CPU, Memory, Network)
- Crash detection and auto-restart

## Scaling and Performance

### Automatic Scaling
- Railway handles horizontal scaling automatically
- Scales based on CPU and memory usage
- Handles traffic spikes gracefully

### Performance Optimization

**1. Memory Management**
```python
# Optimize NumPy operations
import numpy as np
np.seterr(all='raise')  # Catch numerical errors early

# Use vectorized operations
calculations = np.vectorize(calculate_function)
```

**2. Database Connection Pooling**
```python
# If adding database later
from sqlalchemy.pool import QueuePool
engine = create_engine(url, poolclass=QueuePool, pool_size=20)
```

**3. Caching (Future Enhancement)**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_expensive_operation(params):
    # Cache frequently used calculations
    pass
```

## Troubleshooting

### Common Issues

**1. Port Binding Errors**
```
Error: Address already in use
```
Solution: Railway automatically sets PORT environment variable. Ensure your app uses it:
```python
PORT = int(os.getenv("PORT", "8081"))
```

**2. API Connection Failures**
```
Error: Unable to fetch beam data from API
```
Solutions:
- Verify `API_BASE_URL` environment variable
- Check Go API deployment status
- Test API connectivity: `curl $API_BASE_URL/beams`

**3. Memory Issues**
```
Error: Container killed (OOM)
```
Solutions:
- Optimize NumPy operations
- Use Railway Pro for more memory
- Implement result caching

**4. Build Failures**
```
Error: Failed to install requirements
```
Solutions:
- Check requirements.txt format
- Verify Python version compatibility
- Review Dockerfile for missing system dependencies

### Debugging Commands

```bash
# Check deployment status
railway status

# View environment variables
railway variables

# Connect to container shell (if available)
railway shell

# Check resource usage
railway metrics
```

### Performance Monitoring

**Key Metrics to Monitor:**
- Response time for `/analyze` endpoint
- Memory usage during calculations
- API connectivity to Go backend
- Error rates and types

**Railway Dashboard provides:**
- Real-time metrics
- Historical performance data
- Error tracking
- Resource usage graphs

## Security Considerations

### Environment Variables
- Never commit secrets to Git
- Use Railway's environment variable system
- Different variables for different environments
- Rotate API keys regularly

### Container Security
```dockerfile
# Non-root user in Dockerfile
RUN useradd --create-home --shell /bin/bash calc-engine
USER calc-engine
```

### CORS Configuration
```python
# Production CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://itsformfunction.com", "https://www.itsformfunction.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Cost Optimization

### Railway Pricing Tiers

**Hobby Plan (Free)**
- $5 credit monthly
- Good for development and testing
- Limited resources

**Pro Plan ($20/month)**
- Unlimited projects
- Priority support
- Higher resource limits
- Custom domains included

**Team Plan ($20/user/month)**
- Team collaboration
- Role-based access
- Advanced monitoring

### Cost Monitoring

```bash
# Check current usage
railway metrics

# View billing information
railway billing
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: railway/cli@v2
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
      - run: railway up --detach
```

### Automated Testing

```bash
# Add to deployment pipeline
python -m pytest test_calc.py
python -m flake8 main.py
python -m black --check main.py
```

## Integration with Frontend

Update your React frontend to use the Railway URL:

```typescript
const calcEngineUrl = process.env.NODE_ENV === 'development'
  ? 'http://localhost:8081'
  : 'https://engine.itsformfunction.com';
```

## Support and Resources

- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)
- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)

## Maintenance Checklist

### Weekly
- [ ] Check deployment health
- [ ] Review error logs
- [ ] Monitor resource usage
- [ ] Test API endpoints

### Monthly
- [ ] Update dependencies
- [ ] Review security settings
- [ ] Optimize performance bottlenecks
- [ ] Check cost usage

### Quarterly
- [ ] Security audit
- [ ] Performance benchmarking
- [ ] Infrastructure review
- [ ] Backup and disaster recovery testing

---

**Railway Deployment Complete! 🚂**

Your calc engine is now running on Railway at https://engine.itsformfunction.com