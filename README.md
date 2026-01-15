# Forex Time Series Forecasting - Complete MLOps Pipeline

This project implements a comprehensive MLOps pipeline for forecasting foreign exchange (FX) rates using advanced machine learning techniques. It includes hyperparameter tuning with Ray Tune, experiment tracking with MLflow, model serving, monitoring, and CI/CD automation.

## 🚀 Key Features

### Core ML Pipeline
* **Data Acquisition:** Automated download of historical FX rates for 10+ currency pairs using `yfinance`
* **Advanced Feature Engineering:** 200+ features including lagged prices, technical indicators, and cross-currency correlations
* **No Data Leakage:** Rigorous feature engineering ensuring no future information leaks into training
* **Time Series Cross-Validation:** Proper evaluation using expanding window validation

### MLOps Enhancements
* **🔍 Hyperparameter Tuning:** Ray Tune with ASHA scheduler and Optuna search for optimal model parameters
* **📊 Experiment Tracking:** MLflow for comprehensive logging of metrics, parameters, and artifacts
* **🏷️ Model Registry:** Version control and staging for trained models
* **🔄 Model Serving:** REST API with FastAPI for real-time predictions
* **📈 Monitoring:** Prometheus metrics and data drift detection
* **🐳 Containerization:** Docker and Docker Compose for reproducible deployments
* **🔄 CI/CD:** GitHub Actions for automated testing, training, and deployment
* **📋 Ensemble Models:** Multiple model aggregation for improved predictions

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Feature Eng.   │───▶│  Model Training │
│   (yfinance)    │    │  (No Leakage)   │    │  (Ray Tune)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MLflow UI     │    │   Model Registry │    │   API Serving   │
│ (Experiments)   │    │   (Versioning)  │    │   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   CI/CD Pipeline │    │   Docker        │
│ (Prometheus)    │    │ (GitHub Actions) │    │ (Compose)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Technologies Used

### Core ML & Data
- **Python 3.9+** - Primary programming language
- **XGBoost** - Gradient boosting for classification
- **scikit-learn** - Data preprocessing and evaluation
- **pandas/numpy** - Data manipulation
- **yfinance** - Financial data acquisition

### MLOps Stack
- **Ray Tune** - Distributed hyperparameter tuning
- **MLflow** - Experiment tracking and model management
- **FastAPI** - High-performance API serving
- **Docker** - Containerization
- **Kafka** - Event streaming for monitoring
- **Prometheus** - Metrics collection
- **GitHub Actions** - CI/CD automation

## 📊 Model Performance

| Ticker   | Accuracy | Sharpe Ratio | Win Rate |
|----------|----------|--------------|----------|
| EURUSD=X | 0.511    | -0.41        | 38.8%    |
| GBPUSD=X | 0.503    | -0.01        | 39.5%    |
| USDJPY=X | 0.491    | 0.32         | 37.7%    |
| USDCHF=X | 0.494    | -0.26        | 38.6%    |
| USDCAD=X | 0.497    | 0.19         | 38.9%    |
| AUDUSD=X | 0.498    | -0.47        | 40.9%    |
| NZDUSD=X | 0.506    | -0.25        | 41.3%    |

*Results from 5-fold time series cross-validation with hyperparameter tuning*

## 🚀 Quick Start

### Local Development

1. **Clone and setup:**
```bash
git clone https://github.com/MohamedIKenedy/Forex-Time-Series-Forecasting.git
cd forex-time-series-forecasting
```

2. **Start the full stack:**
```bash
docker-compose up -d
```

3. **Access services:**
- MLflow UI: http://localhost:5000
- API: http://localhost:8000
- Monitoring: http://localhost:9090
- Kafka: localhost:9092

### Training Models

```bash
# Run hyperparameter tuning and training
docker-compose --profile training up training

# Or run locally
pip install -r api/requirements.txt
python -c "exec(open('Notebooks/forex_forecasting_v1.ipynb').read())"
```

### API Usage

```python
import requests

# Get prediction for EURUSD
response = requests.post("http://localhost:8000/predict", json={
    "ticker": "EURUSD=X",
    "features": {...}  # Feature dictionary
})

prediction = response.json()
print(f"Signal: {prediction['signal']}, Confidence: {prediction['confidence']}")
```

## 📁 Project Structure

```
├── Notebooks/                 # Jupyter notebooks
│   └── forex_forecasting_v1.ipynb
├── api/                       # FastAPI application
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
├── scripts/                   # Utility scripts
│   ├── model_serving.py
│   └── monitoring.py
├── models/                    # Trained models
├── scalers/                   # Feature scalers
├── mlruns/                    # MLflow experiments
├── docker-compose.yml         # Local development stack
├── Dockerfile                 # Container definitions
└── .github/workflows/         # CI/CD pipelines
```

## 🔧 Configuration

### Environment Variables

```bash
# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# API
API_HOST=0.0.0.0
API_PORT=8000

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Ray
RAY_ADDRESS=auto
```

### Model Configuration

Models are automatically tuned using Ray Tune with the following search spaces:

- `n_estimators`: 50-500
- `max_depth`: 3-10
- `learning_rate`: 0.01-0.3 (log scale)
- `subsample`: 0.6-1.0
- `colsample_bytree`: 0.6-1.0
- `scale_pos_weight`: 0.5-2.0

## 📊 Monitoring & Observability

### Metrics Collected

- **Model Performance:** Accuracy, precision, Sharpe ratio, win rate
- **System Health:** API response time, error rates
- **Data Quality:** Data drift scores, missing values
- **Business Metrics:** Prediction confidence, trading signals

### Dashboards

Access monitoring dashboards:
- **Prometheus:** http://localhost:9090
- **MLflow:** http://localhost:5000
- **API Health:** http://localhost:8000/docs

## 🔄 CI/CD Pipeline

### Automated Workflows

1. **Code Quality:** Linting, formatting, and testing
2. **Model Training:** Automated retraining on new data
3. **Model Deployment:** Rolling updates with canary deployments
4. **Monitoring:** Automated alerts for model drift

### Deployment Targets

- **Development:** Local Docker Compose
- **Staging:** Azure ML or similar cloud service
- **Production:** Kubernetes with Istio service mesh

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper tests
4. Submit a pull request

### Development Guidelines

- Use `black` for code formatting
- Write tests for new features
- Update documentation
- Follow semantic versioning

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Yahoo Finance for market data
- Ray, MLflow, and FastAPI communities
- Open source ML ecosystem

---

**Note:** This system is for educational and research purposes. Always perform thorough backtesting and risk management before using in live trading.
