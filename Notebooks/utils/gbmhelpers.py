import lightgbm as lgb
import numpy as np
from onnxmltools.convert import convert_lightgbm
from onnxconverter_common import FloatTensorType
from scipy.stats import spearmanr


class GBMHelper:
    def __init__(
        self,
        params: dict = None,
        num_boost_round: int = 1000,
        early_stopping_rounds: int = 50,
        LOOKBACK: int = 200,
        HORIZON: int = 1,
        N_SPLITS: int = 4,
        TRANSACTION_COST: float = 0.0001,
    ):
        self.params = (
            params
            if params is not None
            else {
                "objective": "regression",
                "metric": "rmse",
                "boosting_type": "gbdt",
                "learning_rate": 0.01,
                "num_leaves": 31,
                "max_depth": -1,
                "min_data_in_leaf": 20,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "verbosity": -1,
                "seed": 42,
            }
        )
        self.num_boost_round = num_boost_round
        self.early_stopping_rounds = early_stopping_rounds
        self.LOOKBACK = LOOKBACK
        self.HORIZON = HORIZON
        self.N_SPLITS = N_SPLITS
        self.TRANSACTION_COST = TRANSACTION_COST

    def create_lagged_features(self, df, lookback=200):
        """Create lagged features for time series prediction"""
        features = df.copy()
        target = features["Close_log_return"].shift(-self.HORIZON)

        for lag in [1, 2, 3, 5, 10, 20, 60, 120, 200]:
            if lag <= lookback:
                features[f"close_log_return_lag_{lag}"] = features[
                    "Close_log_return"
                ].shift(lag)

        for window in [5, 10, 20, 60]:
            if window <= lookback:
                features[f"close_log_return_mean_{window}"] = (
                    features["Close_log_return"].shift(1).rolling(window).mean()
                )
                features[f"close_log_return_std_{window}"] = (
                    features["Close_log_return"].shift(1).rolling(window).std()
                )

        features = features.drop(columns=["Close_log_return"])
        valid_idx = ~(target.isna() | features.isna().any(axis=1))
        features = features[valid_idx]
        target = target[valid_idx]

        return features, target

    def export_model_to_onnx(self, model, n_features, export_path):
        """
        Export LightGBM model to ONNX format

        Args:
            model: Trained LightGBM model
            n_features: Number of input features
            export_path: Path to save the ONNX model
        """
        try:
            initial_type = [("float_input", FloatTensorType([None, n_features]))]

            onnx_model = convert_lightgbm(
                model, initial_types=initial_type, target_opset=12
            )

            with open(export_path, "wb") as f:
                f.write(onnx_model.SerializeToString())

            print(f"  ✓ ONNX model saved: {export_path}")
            return True
        except Exception as e:
            print(f"  ✗ ONNX export failed: {e}")
            return False

    def calculate_ic(self, predictions, actuals):
        """Information Coefficient"""
        ic, _ = spearmanr(predictions, actuals)
        return ic

    def calculate_directional_accuracy(self, predictions, actuals):
        """Directional accuracy"""
        pred_direction = np.sign(predictions)
        actual_direction = np.sign(actuals)
        return (pred_direction == actual_direction).mean()

    def backtest_strategy(self, predictions, actuals, transaction_cost=0.0001):
        """Walk-forward backtest"""
        positions = np.sign(predictions)
        strategy_returns = positions * actuals
        position_changes = np.diff(positions, prepend=0) != 0
        transaction_costs = position_changes * transaction_cost
        strategy_returns = strategy_returns - transaction_costs
        cumulative_pnl = np.cumsum(strategy_returns)

        if strategy_returns.std() > 0:
            sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
        else:
            sharpe = 0

        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_dd = drawdown.min()
        hit_rate = (strategy_returns > 0).mean()

        return cumulative_pnl, sharpe, max_dd, hit_rate

    def assess_performance(self, ic, dir_acc, sharpe):
        """
        Classify model performance with realistic financial market standards

        In FX markets:
        - IC > 0.03 is strong
        - Dir Acc > 52% is profitable
        - Sharpe > 0.5 is acceptable, > 1.0 is good, > 1.5 is excellent
        """
        if ic > 0.04 and dir_acc > 0.53 and sharpe > 1.5:
            return "Exceptional"
        elif ic > 0.03 and dir_acc > 0.52 and sharpe > 1.0:
            return "Strong"
        elif ic > 0.02 and dir_acc > 0.51 and sharpe > 0.5:
            return "Acceptable"
        elif ic > 0.01 and dir_acc > 0.50 and sharpe > 0.0:
            return "Marginal"
        else:
            return "Weak"


# Module-level functions for convenience
def create_lagged_features(df, lookback=200):
    helper = GBMHelper()
    return helper.create_lagged_features(df, lookback)


def export_model_to_onnx(model, n_features, export_path):
    helper = GBMHelper()
    return helper.export_model_to_onnx(model, n_features, export_path)


def calculate_ic(predictions, actuals):
    helper = GBMHelper()
    return helper.calculate_ic(predictions, actuals)


def calculate_directional_accuracy(predictions, actuals):
    helper = GBMHelper()
    return helper.calculate_directional_accuracy(predictions, actuals)


def backtest_strategy(predictions, actuals, transaction_cost=0.0001):
    helper = GBMHelper()
    return helper.backtest_strategy(predictions, actuals, transaction_cost)


def assess_performance(ic, dir_acc, sharpe):
    helper = GBMHelper()
    return helper.assess_performance(ic, dir_acc, sharpe)
