# Form & Function Calc Engine

A Python-based structural calculation engine for steel beam analysis using NumPy, Pandas, and SciPy. This service communicates with the Form & Function Go API exclusively via gRPC for optimal performance and type safety.

## Features

- **Steel Beam Analysis**: Comprehensive structural analysis including:
  - Bending moment calculations
  - Shear force analysis  
  - Deflection calculations
  - Stress utilization checks
  - Eurocode 3 compliance
- **Load Types**: Support for uniform distributed loads and point loads
- **Material Grades**: S235, S275, S355, S460 steel grades
- **Optimal Beam Selection**: Automatically find the most economical beam for given loads
- **Safety Checks**: Configurable safety factors and serviceability limits
- **RESTful API**: FastAPI-based web service with automatic OpenAPI documentation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Web     │───▶│   Go gRPC       │───▶│  Steel Beam     │
│   Frontend      │    │   Server        │    │  Data           │
│   (Vercel)      │    │   (Port 9090)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      ▲
         │                      │ gRPC
         │              ┌─────────────────┐
         └─────────────▶│  Python Calc    │
                        │  Engine         │
                        │  (Port 8081)    │
                        │  gRPC Client    │
                        └─────────────────┘
```

## Prerequisites

- Python 3.8 or higher
- Go gRPC server running (port 9090)
- Virtual environment support
- [Docker](https://docker.com) (for containerization)
- gRPC dependencies (protobuf, grpcio)

## Quick Start

### Local Development

#### Option 1: Docker Compose (Recommended)

```bash
# From itsformandfunction directory
docker-compose up --build
```

This starts both the Go gRPC server (port 9090) and Python calc engine (port 8081).

#### Option 2: Manual Setup

1. **Start the Go gRPC server first:**
   ```bash
   cd ../formandfunction-api
   export GRPC_PORT=9090
   go run .
   ```

2. **Start the calc engine:**
   ```bash
   ./start.sh
   ```

2. **Access the API documentation:**
   Open http://localhost:8081/docs in your browser

3. **Run tests:**
   ```bash
   python test_calc.py
   ```

### Production Deployment (Railway)

1. **Deploy to Railway:**
   ```bash
   railway up
   # or via Railway Dashboard - connect GitHub repository
   ```

2. **Access production API:**
   - Production URL: https://engine.itsformfunction.com
   - API docs: https://engine.itsformfunction.com/docs
   - Health check: https://engine.itsformfunction.com/health

3. **Docker deployment:**
   ```bash
   docker build -t calc-engine .
   docker run -p 8081:8081 calc-engine
   ```

## Manual Installation

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export API_BASE_URL="http://localhost:8080"
export PORT="8081"

# Start the service
python main.py
```

## API Endpoints

### Development URLs (Local)
- Base URL: `http://localhost:8081`
- API Docs: `http://localhost:8081/docs`

### Production URLs (Railway)
- Base URL: `https://engine.itsformfunction.com`
- API Docs: `https://engine.itsformfunction.com/docs`

### Health & Information

- `GET /` - Service information
- `GET /health` - Detailed health check including API connectivity
- `GET /beams` - Get all available steel beams from the Go API
- `GET /beams/{designation}` - Get specific beam information

### Calculations

- `POST /analyze` - Perform comprehensive beam analysis

#### Analysis Request Format

```json
{
  "beam_designation": "UB406x178x74",  // Optional - if not provided, optimal beam is selected
  "applied_load": 15.0,                // kN or kN/m depending on load_type
  "span_length": 6.0,                  // meters
  "load_type": "uniform",              // "uniform" or "point"
  "safety_factor": 1.6,                // Safety factor for design
  "material_grade": "S355"             // Steel grade: S235, S275, S355, S460
}
```

#### Analysis Response Format

```json
{
  "beam": {
    "section_designation": "UB406x178x74",
    "mass_per_metre": 74.6,
    // ... full beam properties
  },
  "applied_load": 15.0,
  "span_length": 6.0,
  "max_moment": 67.5,                  // kNm
  "max_shear": 45.0,                   // kN  
  "max_deflection": 12.34,             // mm
  "stress_utilization": 0.756,         // Ratio (should be ≤ 1.0)
  "deflection_limit_check": true,      // Passes L/250 limit
  "is_adequate": true,                 // Overall adequacy
  "safety_margin": 24.4,               // Percentage
  "recommendations": [
    "PASS: Beam is adequate for the applied loading."
  ]
}
```

## Engineering Calculations

### Bending Moments

- **Uniform Load**: M = wL²/8
- **Point Load (center)**: M = PL/4

### Deflections  

- **Uniform Load**: δ = 5wL⁴/(384EI)
- **Point Load (center)**: δ = PL³/(48EI)

### Stress Check

- Utilization = (Actual Stress) / (Allowable Stress)
- Allowable Stress = fy / Safety Factor
- Actual Stress = M / W (elastic section modulus)

### Serviceability Limits

- Deflection limit: L/250 (general construction)
- Can be customized for specific applications

## Example Usage

### Python Client

```python
import requests

# Analyze a specific beam
response = requests.post("http://localhost:8081/analyze", json={
    "beam_designation": "UB406x178x74",
    "applied_load": 12.0,
    "span_length": 8.0,
    "load_type": "uniform",
    "material_grade": "S355"
})

result = response.json()
print(f"Beam adequate: {result['is_adequate']}")
print(f"Stress utilization: {result['stress_utilization']}")
```

### cURL

```bash
curl -X POST "http://localhost:8081/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "applied_load": 20.0,
       "span_length": 6.0,
       "load_type": "uniform",
       "material_grade": "S355"
     }'
```

## Integration with Web Frontend

The calc engine is designed to be called from the React frontend with automatic environment switching:

```typescript
const analyzeBeam = async (loadData: CalculationRequest) => {
  const calcEngineUrl = process.env.NODE_ENV === 'development'
    ? 'http://localhost:8081'
    : 'https://engine.itsformfunction.com';
    
  const response = await fetch(`${calcEngineUrl}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loadData)
  });
  return response.json();
};
```

## Configuration

### Environment Variables

**Local Development:**
- `API_BASE_URL`: Go API base URL (default: http://localhost:8080)
- `PORT`: Port for calc engine (default: 8081)

**Production (Railway):**
- `API_BASE_URL`: Production Go API URL (set in Railway dashboard)
- `PORT`: Automatically set by Railway
- Container-based deployment with auto-scaling
- Custom domain: `engine.itsformfunction.com`

### Railway Configuration

The `railway.json` and `Dockerfile` configure containerized deployment:
- Python 3.11 slim image
- FastAPI with Uvicorn server
- Health checks and auto-restart
- Environment variable support

## Development

### Running Tests

**Local Testing:**
```bash
# Run all tests (includes gRPC tests)
python test_calc.py

# Test gRPC-only setup
python ../test_grpc_only.py

# Test specific functionality  
python -c "from main import BeamAnalysis; analyzer = BeamAnalysis(); print(analyzer.fetch_beams_from_api())"

# Test health check
curl http://localhost:8081/health
```

**Production Testing:**
```bash
# Test production health
curl https://engine.itsformfunction.com/health

# Test production calculation
curl -X POST https://engine.itsformfunction.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"applied_load": 10.0, "span_length": 6.0, "load_type": "uniform", "material_grade": "S355"}'
```

### Deployment Workflow

```bash
# Local development
./start.sh

# Build and test Docker image
docker build -t calc-engine .
docker run -p 8081:8081 calc-engine

# Deploy to Railway
railway up

# Check deployment logs
railway logs
```

### Adding New Calculations

1. Add calculation method to `BeamAnalysis` class in `main.py`
2. Update the analysis workflow in `perform_analysis()`
3. Add corresponding tests in `test_calc.py`
4. Test locally with Docker
5. Deploy to Railway for production

### Code Quality

```bash
# Format code
black main.py test_calc.py

# Lint code
flake8 main.py test_calc.py

# Run with type checking
mypy main.py
```

## Troubleshooting

### Local Development Issues

1. **"Unable to fetch beam data from API"**
   - Ensure Go API is running on port 8080
   - Check network connectivity
   - Verify API endpoint responds: `curl http://localhost:8080/beams`

2. **Import errors**
   - Activate virtual environment: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`

3. **Port already in use**
   - Change port: `export CALC_ENGINE_PORT=8082`
   - Kill existing process: `lsof -ti:8081 | xargs kill`

### Production (Railway) Issues

1. **Deployment failures**
   - Check `Dockerfile` and `railway.json` configuration
   - Verify `requirements.txt` has correct dependencies
   - Check build logs in Railway dashboard

2. **Runtime errors**
   - Check Railway logs: `railway logs`
   - Verify environment variables are set
   - Test API connectivity from container environment

3. **Performance issues**
   - Monitor resource usage in Railway dashboard
   - Optimize calculation algorithms
   - Consider upgrading to Railway Pro plan

### Debug Mode

**Local debugging:**
```bash
export LOG_LEVEL=DEBUG
python main.py
```

**Production debugging:**
```bash
# View deployment logs
railway logs

# Check deployment status
railway status

# Test container locally
docker run -it calc-engine /bin/bash
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is part of the Form & Function engineering platform.

## Railway Deployment

For detailed Railway deployment instructions, see [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md).

### Quick Railway Setup

1. **Create Railway project:**
   - Connect GitHub repository
   - Set `API_BASE_URL` environment variable
   - Deploy automatically triggers

2. **Local Docker testing:**
   ```bash
   docker build -t calc-engine .
   docker run -p 8081:8081 -e API_BASE_URL=http://host.docker.internal:8080 calc-engine
   ```

3. **Production monitoring:**
   - Health checks: Built into Docker container
   - Logs: Available in Railway dashboard
   - Metrics: CPU, memory, and response times# formandfunction-calcengine
