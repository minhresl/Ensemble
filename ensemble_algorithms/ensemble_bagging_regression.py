# -*- coding: utf-8 -*-

import argparse
import collections
import logging
import sys

import numpy as np
import pandas as pd
from estimators import NaiveBaggingEstimator, ArBaggingEstimator, \
    ArmaBaggingEstimator, ArimaBaggingEstimator, EtsBaggingEstimator
from sklearn.model_selection import cross_val_score, TimeSeriesSplit

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('data', type=str, help='Path to processed dataset')
parser.add_argument('result_path', type=str, help='Destination to save result')
args = parser.parse_args()

# Initialize logger
logger = logging.getLogger(__name__)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class EnsembleBagging:
    def __init__(self, file_path, test_size=342):
        """
        Initializes data required by bagging ensemble
        :param file_path: path to processed dataset
        :param test_size: last test_size hours will be treated as test set
        """
        # Read data frame
        self.series = pd.read_csv(
            file_path,
            header=None,  # contains no header
            index_col=0,  # set datetime column as index
            names=['datetime', 'requests'],  # name the columns
            converters={'datetime':  # custom datetime parser
                            lambda x: pd.to_datetime(x, format='%Y-%m-%d %H:%M:%S')},
            squeeze=True,  # convert to Series
            dtype={'requests': np.float64},  # https://git.io/vdbyk
        )

        # Save test_size
        if test_size <= 0:
            raise ValueError
        self.test_size = test_size

        # exclude test data
        self.eval_series = self.series[:-test_size]
        self.test_series = self.series[-test_size:].copy()

        # be sure
        assert len(self.test_series) == test_size
        assert len(self.test_series) + len(self.eval_series) == len(self.series)

        logger.warning("Deciding best algorithm...")

        # Calculate mean score of 10-fold evaluation
        score = dict()
        logger.warning("Scoring Naive Bagging")
        score['naive'] = cross_val_score(NaiveBaggingEstimator(), self.eval_series,
                                         cv=TimeSeriesSplit(n_splits=10).split(self.eval_series), verbose=3).mean()
        logger.warning("Scoring AR Bagging")
        score['ar'] = cross_val_score(ArBaggingEstimator(), self.eval_series,
                                      cv=TimeSeriesSplit(n_splits=10).split(self.eval_series), verbose=3).mean()
        logger.warning("Scoring ARMA Bagging")
        score['arma'] = cross_val_score(ArmaBaggingEstimator(), self.eval_series,
                                        cv=TimeSeriesSplit(n_splits=10).split(self.eval_series), verbose=3).mean()
        logger.warning("Scoring ARIMA Bagging")
        score['arima'] = cross_val_score(ArimaBaggingEstimator(), self.eval_series,
                                         cv=TimeSeriesSplit(n_splits=10).split(self.eval_series), verbose=3).mean()
        logger.warning("Scoring ETS Bagging")
        score['ets'] = cross_val_score(EtsBaggingEstimator(), self.eval_series,
                                       cv=TimeSeriesSplit(n_splits=10).split(self.eval_series), verbose=3).mean()

        logger.warning(score)

        # Find algo with min. score
        self.best_algo = min(score, key=score.get)

        logger.warning("Best Algorithm: %s" % self.best_algo)

    def run_test(self, result_path):
        # assign estimator
        if self.best_algo == 'naive':
            logger.warning("Running Naive Bagging on Test Data")
            estimator = NaiveBaggingEstimator()
        elif self.best_algo == 'ar':
            logger.warning("Running AR Bagging on Test Data")
            estimator = ArBaggingEstimator()
        elif self.best_algo == 'arma':
            logger.warning("Running ARMA Bagging on Test Data")
            estimator = ArmaBaggingEstimator()
        elif self.best_algo == 'arima':
            logger.warning("Running ARIMA Bagging on Test Data")
            estimator = ArimaBaggingEstimator()
        elif self.best_algo == 'ets':
            logger.warning("Running ETS Bagging on Test Data")
            estimator = EtsBaggingEstimator()
        else:
            assert False

        # Makes eval series available for prediction
        estimator.fit(self.eval_series)

        # Run step-by-step prediction
        results = estimator.predict(self.test_series)

        # score
        score = estimator.score(self.test_series)
        logger.warning("Estimator Score: %s" % score)

        df_data = collections.OrderedDict()
        df_data['Observation'] = self.test_series
        df_data['Prediction'] = results
        pd.DataFrame(df_data, columns=df_data.keys()) \
            .to_csv(result_path, index=False, na_rep='NaN')


def main():
    logger.warning("Starting Ensemble Bagging")

    # Initialize algo
    algo = EnsembleBagging(file_path=args.data)

    # Run test
    algo.run_test(result_path=args.result_path)

    logger.warning("Stopping Ensemble Bagging")


if __name__ == '__main__':
    main()
