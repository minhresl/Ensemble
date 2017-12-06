# -*- coding: utf-8 -*-
import argparse
import logging
import sys

import genetic_algorithm.forecast as forecast
import numpy as np
import pandas as pd
import tqdm
from estimators import NaiveEstimator, ArEstimator, \
    ArmaEstimator, ArimaEstimator, EtsEstimator
from sklearn.model_selection import cross_val_score, TimeSeriesSplit

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('data', type=str, help='Path to dataset (output of forecast.py)')
parser.add_argument('result_path', type=str, help='Destination to save result')
args = parser.parse_args()

# Initialize logger
logger = logging.getLogger(__name__)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class EnsembleCrossValidation:
    def __init__(self, file_path, test_size=342):
        """
        Initializes data required by cross validation ensemble
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
        eval_series = self.series[:-test_size]
        self.test_series = self.series[-test_size:].copy()

        logger.warning("Deciding best algorithm")

        # Calculate mean score of 10-fold evaluation
        score = dict()
        score['naive'] = cross_val_score(NaiveEstimator(), eval_series,
                                         cv=TimeSeriesSplit(n_splits=10).split(eval_series)).mean()
        score['ar'] = cross_val_score(ArEstimator(), eval_series,
                                      cv=TimeSeriesSplit(n_splits=10).split(eval_series)).mean()
        score['arma'] = cross_val_score(ArmaEstimator(), eval_series,
                                        cv=TimeSeriesSplit(n_splits=10).split(eval_series)).mean()
        score['arima'] = cross_val_score(ArimaEstimator(), eval_series,
                                         cv=TimeSeriesSplit(n_splits=10).split(eval_series)).mean()
        score['ets'] = cross_val_score(EtsEstimator(), eval_series,
                                       cv=TimeSeriesSplit(n_splits=10).split(eval_series)).mean()

        # Find algo with max. score
        self.best_algo = max(score, key=score.get)

        logger.warning("Best Algorithm: %s" % self.best_algo)

    def run_test(self, result_path):
        algo = forecast.ForecastAlgorithms()

        # run on test data
        results = np.array([])
        if self.best_algo == 'naive':
            logger.warning("Running Naive Algorithm on Test Data")
            for i in tqdm.tqdm(range(self.test_size)):
                results = np.append(results,
                                    algo.naive_forecast(data=self.test_series[i:]))
        elif self.best_algo == 'ar':
            logger.warning("Running AR Algorithm on Test Data")
            for i in tqdm.tqdm(range(self.test_size)):
                results = np.append(results,
                                    algo.ar_forecast(data=self.test_series[i:]))
        elif self.best_algo == 'arma':
            logger.warning("Running ARMA Algorithm on Test Data")
            for i in tqdm.tqdm(range(self.test_size)):
                results = np.append(results,
                                    algo.arma_forecast(data=self.test_series[i:]))
        elif self.best_algo == 'arima':
            logger.warning("Running ARIMA Algorithm on Test Data")
            for i in tqdm.tqdm(range(self.test_size)):
                results = np.append(results,
                                    algo.arima_forecast(data=self.test_series[i:]))
        elif self.best_algo == 'ets':
            logger.warning("Running ETS Algorithm on Test Data")
            for i in tqdm.tqdm(range(self.test_size)):
                results = np.append(results,
                                    algo.ets_forecast(data=self.test_series[i:]))
        else:
            assert False

        pd.Series(results).to_csv(result_path, header=False, index=False)


def main():
    logger.warning("Starting Ensemble Cross Validation")

    # Initialize algo
    algo = EnsembleCrossValidation(file_path=args.data, test_size=342)

    # Run test
    algo.run_test(result_path=args.result_path)

    logger.warning("Stopping Ensemble Cross Validation")


if __name__ == '__main__':
    main()
