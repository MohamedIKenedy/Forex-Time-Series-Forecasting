# Foreign Exchange (FX) Rate Forecasting with LSTM and MLflow

This project focuses on building and evaluating Long Short-Term Memory (LSTM) neural network models for forecasting foreign exchange (FX) rates. It encompasses data acquisition, exploratory data analysis (EDA), feature engineering, model training using time series cross-validation, and experiment tracking with MLflow.

## Project Overview

The goal of this project is to develop predictive models for several major currency pairs. Historical data is obtained using `yfinance`, cleaned, and transformed to create features suitable for time series forecasting. LSTM models are trained and evaluated, with all experiments meticulously tracked using MLflow to ensure reproducibility and easy comparison of model performance.

**Key Features:**

*   **Data Acquisition:** Automated download of historical FX rates for multiple currency pairs.
*   **Data Cleaning & EDA:** Comprehensive analysis to handle missing values, detect outliers, and understand data distributions and trends.
*   **Feature Engineering:** Creation of relevant time-series features such as logarithmic prices, price differences, and logarithmic returns.
*   **LSTM Model Development:** Implementation of a custom LSTM neural network architecture for sequence-to-sequence forecasting.
*   **Time Series Cross-Validation:** Robust model evaluation using `TimeSeriesSplit` to simulate real-world forecasting scenarios.
*   **MLflow Experiment Tracking:** Logging of model parameters, metrics (MAE, RMSE, MAPE, R²), and artifacts (plots, trained models) for each experiment.

**Currency Pairs Analyzed:**

*   `EURUSD=X`
*   `GBPUSD=X`
*   `USDJPY=X`
*   `USDCHF=X`
*   `USDCAD=X`
*   `AUDUSD=X`
*   `NZDUSD=X`
*   `EURMAD=X`
*   `EURRUB=X`
*   `RUBUSD=X`

## Technologies Used

*   **Python:** Primary programming language.
*   **`yfinance`:** For downloading historical market data.
*   **`pandas` & `numpy`:** For data manipulation and numerical operations.
*   **`matplotlib` & `seaborn`:** For data visualization.
*   **`scikit-learn`:** For data preprocessing (e.g., `StandardScaler`), and metrics calculation.
*   **`torch`:** PyTorch framework for building and training LSTM neural networks.
*   **`mlflow`:** For experiment tracking, model logging, and model management.
*   **`pyngrok`:** To expose the local MLflow UI to a public URL in a Colab environment.

## Project Workflow

1.  **Data Ingestion:** Historical FX data is fetched using `yfinance` for a specified list of tickers and date range.
2.  **Exploratory Data Analysis (EDA):** Initial inspection of data types, missing values, and descriptive statistics. Visualizations such as line plots of closing prices, box plots for outlier detection, and KDE plots for distribution analysis are generated.
3.  **Data Preprocessing & Feature Engineering:**
    *   Missing values are handled using forward and backward fill methods.
    *   Outlier detection is performed using Z-scores, and binary `_is_outlier` flags are created for each price type.
    *   New features like logarithmic prices (`_log`), price differences (`_diff`), and logarithmic returns (`_log_return`) are computed.
4.  **Model Training and Evaluation:**
    *   For each currency ticker, an LSTM model is trained.
    *   Data is split into training and testing sets using `TimeSeriesSplit` to maintain temporal order.
    *   Features and targets are scaled using `StandardScaler`.
    *   Data is transformed into sequences and windows suitable for LSTM input using `create_sequences` utility.
    *   LSTM models are trained over multiple epochs, and performance (MAE, RMSE, MAPE, R²) is evaluated on test sets.
5.  **MLflow Tracking:** All training runs, parameters (e.g., hidden size, number of layers, learning rate), evaluation metrics, and resulting plots (train/test split, loss curves, actual vs. predicted) are logged to MLflow. The trained PyTorch LSTM models are also logged as artifacts.

## Next Steps: Deploying for Real-time Inference with UI Integration

The current phase focuses on model development and evaluation. The logical next steps involve operationalizing these models to enable real-time predictions and provide an interactive user interface.

### 1. Model Deployment for Real-time Inference

The goal is to make the trained LSTM models accessible via an API endpoint for making predictions on new, unseen data.

*   **Environment Setup:** Set up a production environment, potentially on a cloud platform (e.g., Google Cloud AI Platform, AWS SageMaker, Azure Machine Learning) or using containerization technologies (Docker, Kubernetes).
*   **Model Packaging:** Utilize MLflow's built-in deployment tools to package the best-performing models. MLflow allows for easy export of models in various formats suitable for deployment and can generate Docker images or serverless function deployments.
*   **API Endpoint Creation:** Deploy the packaged model as a REST API. This API will receive real-time FX data (or features derived from it) as input and return the forecasted FX rates.
*   **Scalability & Monitoring:** Implement auto-scaling mechanisms to handle varying loads and integrate monitoring tools to track model performance, latency, and resource utilization in real-time.

### 2. UI Integration

To provide an intuitive way for end-users to interact with the forecasting models, a user interface will be developed.

*   **Frontend Development:** Choose a suitable framework for building the UI (e.g., Streamlit for rapid prototyping, Flask/Django with a custom frontend using React/Vue.js, or Dash for interactive dashboards).
*   **User Input:** The UI will allow users to select currency pairs, specify the forecast horizon, and potentially input recent market data if needed for feature generation (though ideally, this data would be fetched automatically).
*   **Real-time Prediction Request:** The UI will communicate with the deployed model's API endpoint to send input data and retrieve predictions.
*   **Interactive Visualization:** Display the real-time forecasts graphically, showing the predicted future FX rates alongside historical data. This could include confidence intervals for the predictions.
*   **Feedback Mechanism:** Optionally, incorporate a feedback loop where users can rate the predictions or provide additional context, which could be used to further improve the models.

This deployment and UI integration will transform the experimental models into a functional tool for FX rate analysis and decision-making.
