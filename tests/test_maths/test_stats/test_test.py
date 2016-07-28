"""Unit tests for statistical tests and utility functions.
"""
from cogent3.util.unit_test import TestCase, main
from cogent3.maths.stats.test import tail, G_2_by_2, G_fit, likelihoods,\
    posteriors, bayes_updates, t_paired, t_one_sample, t_two_sample, \
    mc_t_two_sample, _permute_observations, t_one_observation, correlation, \
    correlation_test, correlation_matrix, z_test, z_tailed_prob, \
    t_tailed_prob, sign_test, reverse_tails, ZeroExpectedError, combinations, \
    multiple_comparisons, multiple_inverse, multiple_n, fisher, regress, \
    regress_major, f_value, f_two_sample, calc_contingency_expected, \
    G_fit_from_Dict2D, chi_square_from_Dict2D, MonteCarloP, \
    regress_residuals, safe_sum_p_log_p, G_ind, regress_origin, stdev_from_mean, \
    regress_R2, permute_2d, mantel, mantel_test, _flatten_lower_triangle, \
    pearson, spearman, _get_rank, kendall_correlation, std, median, \
    get_values_from_matrix, get_ltm_cells, distance_matrix_permutation_test, \
    ANOVA_one_way, mw_test, mw_boot, is_symmetric_and_hollow

from numpy import array, concatenate, fill_diagonal, reshape, arange, matrix, \
    ones, testing, tril, cov, sqrt
from cogent3.util.dict2d import Dict2D
import math
from cogent3.maths.stats.util import Numbers

__author__ = "Rob Knight"
__copyright__ = "Copyright 2007-2011, The Cogent Project"
__credits__ = ["Rob Knight", "Catherine Lozupone", "Gavin Huttley",
               "Sandra Smit", "Daniel McDonald", "Jai Ram Rideout",
               "Michael Dwan"]
__license__ = "GPL"
__version__ = "3.0.prealpha"
__maintainer__ = "Rob Knight"
__email__ = "rob@spot.colorado.edu"
__status__ = "Production"


class TestsHelper(TestCase):
    """Class with utility methods useful for other tests."""

    def setUp(self):
        """Sets up variables used in the tests."""
        # How many times a p-value should be tested to fall in a given range
        # before failing the test.
        self.p_val_tests = 10

    def assertCorrectPValue(self, exp_min, exp_max, fn, args=None,
                            kwargs=None, p_val_idx=0):
        """Tests that the stochastic p-value falls in the specified range.

        Performs the test self.p_val_tests times and fails if the observed
        p-value does not fall into the specified range at least once. Each
        p-value is also tested that it falls in the range 0.0 to 1.0.

        This method assumes that fn is callable, and will unpack and pass args
        and kwargs to fn if they are provided. It also assumes that fn returns
        a single value (the p-value to be tested) or a tuple of results (any
        length greater than or equal to 1), with the p-value at position
        p_val_idx.

        This is primarily used for testing the Mantel and correlation_test
        functions.
        """
        found_match = False
        for i in range(self.p_val_tests):
            if args is not None and kwargs is not None:
                obs = fn(*args, **kwargs)
            elif args is not None:
                obs = fn(*args)
            elif kwargs is not None:
                obs = fn(**kwargs)
            else:
                obs = fn()

            try:
                p_val = float(obs)
            except TypeError:
                p_val = obs[p_val_idx]

            self.assertIsProb(p_val)
            if p_val >= exp_min and p_val <= exp_max:
                found_match = True
                break
        self.assertTrue(found_match)


class TestsTests(TestCase):
    """Tests miscellaneous functions."""

    def test_std(self):
        """Should produce a standard deviation of 1.0 for a std normal dist"""
        expected = 1.58113883008
        self.assertFloatEqual(std(array([1, 2, 3, 4, 5])), expected)

        expected_a = array([expected, expected, expected, expected, expected])
        a = array([[1, 2, 3, 4, 5], [5, 1, 2, 3, 4], [
                  4, 5, 1, 2, 3], [3, 4, 5, 1, 2], [2, 3, 4, 5, 1]])
        self.assertFloatEqual(std(a, axis=0), expected_a)
        self.assertFloatEqual(std(a, axis=1), expected_a)
        self.assertRaises(ValueError, std, a, 5)

    def test_std_2d(self):
        """Should produce from 2darray the same stdevs as scipy.stats.std"""
        inp = array([[1, 2, 3], [4, 5, 6]])
        exps = (  # tuple(scipy_std(inp, ax) for ax in [None, 0, 1])
            1.8708286933869707,
            array([2.12132034, 2.12132034, 2.12132034]),
            array([1., 1.]))
        results = tuple(std(inp, ax) for ax in [None, 0, 1])
        for obs, exp in zip(results, exps):
            testing.assert_almost_equal(obs, exp)

    def test_std_3d(self):
        """Should produce from 3darray the same std devs as scipy.stats.std"""
        inp3d = array(  # 2,2,3
            [[[0, 2, 2],
              [3, 4, 5]],

             [[1, 9, 0],
              [9, 10, 1]]])
        exp3d = (  # for axis None, 0, 1, 2: calc from scipy.stats.std
            3.63901418552,
            array([[0.70710678, 4.94974747, 1.41421356],
                   [4.24264069, 4.24264069, 2.82842712]]),
            array([[2.12132034, 1.41421356, 2.12132034],
                   [5.65685425, 0.70710678, 0.70710678]]),
            array([[1.15470054, 1.],
                   [4.93288286, 4.93288286]]))
        res = tuple(std(inp3d, ax) for ax in [None, 0, 1, 2])
        for obs, exp in zip(res, exp3d):
            testing.assert_almost_equal(obs, exp)

    def test_median(self):
        """_median should work similarly to numpy.mean (in terms of axis)"""
        m = array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        expected = 6.5
        observed = median(m, axis=None)
        self.assertEqual(observed, expected)

        expected = array([5.5, 6.5, 7.5])
        observed = median(m, axis=0)
        self.assertEqual(observed, expected)

        expected = array([2.0, 5.0, 8.0, 11.0])
        observed = median(m, axis=1)
        self.assertEqual(observed, expected)

        self.assertRaises(ValueError, median, m, 10)

    def test_tail(self):
        """tail should return x/2 if test is true; 1-(x/2) otherwise"""
        self.assertFloatEqual(tail(0.25, 'a' == 'a'), 0.25 / 2)
        self.assertFloatEqual(tail(0.25, 'a' != 'a'), 1 - (0.25 / 2))

    def test_combinations(self):
        """combinations should return correct binomial coefficient"""
        self.assertFloatEqual(combinations(5, 3), 10)
        self.assertFloatEqual(combinations(5, 2), 10)
        # only one way to pick no items or the same number of items
        self.assertFloatEqual(combinations(123456789, 0), 1)
        self.assertFloatEqual(combinations(123456789, 123456789), 1)
        # n ways to pick one item
        self.assertFloatEqual(combinations(123456789, 1), 123456789)
        # n(n-1)/2 ways to pick 2 items
        self.assertFloatEqual(combinations(123456789, 2),
                              123456789 * 123456788 / 2)
        # check an arbitrary value in R
        self.assertFloatEqual(combinations(1234567, 12), 2.617073e64)

    def test_multiple_comparisons(self):
        """multiple_comparisons should match values from R"""
        self.assertFloatEqual(multiple_comparisons(1e-7, 10000), 1 - 0.9990005)
        self.assertFloatEqual(multiple_comparisons(0.05, 10), 0.4012631)
        self.assertFloatEqual(multiple_comparisons(1e-20, 1), 1e-20)
        self.assertFloatEqual(multiple_comparisons(1e-300, 1), 1e-300)
        self.assertFloatEqual(multiple_comparisons(
            0.95, 3), 0.99987499999999996)
        self.assertFloatEqual(multiple_comparisons(
            0.75, 100), 0.999999999999679)
        self.assertFloatEqual(multiple_comparisons(0.5, 1000), 1)
        self.assertFloatEqual(multiple_comparisons(
            0.01, 1000), 0.99995682875259)
        self.assertFloatEqual(multiple_comparisons(0.5, 5), 0.96875)
        self.assertFloatEqual(multiple_comparisons(1e-20, 10), 1e-19)

    def test_multiple_inverse(self):
        """multiple_inverse should invert multiple_comparisons results"""
        # NOTE: multiple_inverse not very accurate close to 1
        self.assertFloatEqual(multiple_inverse(1 - 0.9990005, 10000), 1e-7)
        self.assertFloatEqual(multiple_inverse(0.4012631, 10), 0.05)
        self.assertFloatEqual(multiple_inverse(1e-20, 1), 1e-20)
        self.assertFloatEqual(multiple_inverse(1e-300, 1), 1e-300)
        self.assertFloatEqual(multiple_inverse(0.96875, 5), 0.5)
        self.assertFloatEqual(multiple_inverse(1e-19, 10), 1e-20)

    def test_multiple_n(self):
        """multiple_n should swap parameters in multiple_comparisons"""
        self.assertFloatEqual(multiple_n(1e-7, 1 - 0.9990005), 10000)
        self.assertFloatEqual(multiple_n(0.05, 0.4012631), 10)
        self.assertFloatEqual(multiple_n(1e-20, 1e-20), 1)
        self.assertFloatEqual(multiple_n(1e-300, 1e-300), 1)
        self.assertFloatEqual(multiple_n(0.95, 0.99987499999999996), 3)
        self.assertFloatEqual(multiple_n(0.5, 0.96875), 5)
        self.assertFloatEqual(multiple_n(1e-20, 1e-19), 10)

    def test_fisher(self):
        """fisher results should match p 795 Sokal and Rohlf"""
        self.assertFloatEqual(fisher([0.073, 0.086, 0.10, 0.080, 0.060]),
                              0.0045957946540917905)

    def test_regress(self):
        """regression slope, intercept should match p 459 Sokal and Rohlf"""
        x = [0, 12, 29.5, 43, 53, 62.5, 75.5, 85, 93]
        y = [8.98, 8.14, 6.67, 6.08, 5.90, 5.83, 4.68, 4.20, 3.72]
        self.assertFloatEqual(regress(x, y), (-0.05322, 8.7038), 0.001)
        # higher precision from OpenOffice
        self.assertFloatEqual(regress(x, y), (-0.05322215, 8.70402730))

        # add test to confirm no overflow error with large numbers
        x = [32119, 33831]
        y = [2.28, 2.43]
        exp = (8.761682243E-05, -5.341209112E-01)
        self.assertFloatEqual(regress(x, y), exp, 0.001)

    def test_regress_origin(self):
        """regression slope constrained through origin should match Excel"""
        x = array([1, 2, 3, 4])
        y = array([4, 2, 6, 8])
        self.assertFloatEqual(regress_origin(x, y), (1.9333333, 0))

        # add test to confirm no overflow error with large numbers
        x = [32119, 33831]
        y = [2.28, 2.43]
        exp = (7.1428649481939822e-05, 0)
        self.assertFloatEqual(regress_origin(x, y), exp, 0.001)

    def test_regress_R2(self):
        """regress_R2 returns the R^2 value of a regression"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.1, 4.2, 5.9, 8.4, 9.6]
        result = regress_R2(x, y)
        self.assertFloatEqual(result, 0.99171419347896)

    def test_regress_residuals(self):
        """regress_residuals reprts error for points in linear regression"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.1, 4.2, 5.9, 8.4, 9.6]
        result = regress_residuals(x, y)
        self.assertFloatEqual(result, [-0.1, 0.08, -0.14, 0.44, -0.28])

    def test_stdev_from_mean(self):
        """stdev_from_mean returns num std devs from mean for each val in x"""
        x = [2.1, 4.2, 5.9, 8.4, 9.6]
        result = stdev_from_mean(x)
        self.assertFloatEqual(result, [-1.292463399014413, -0.60358696806764478, -
                              0.045925095396451399, 0.77416589382589174, 1.1678095686526162])

    def test_regress_major(self):
        """major axis regression should match p 589 Sokal and Rohlf"""
        # Note that the Sokal and Rohlf example flips the axes, such that the
        # equation is for explaining x in terms of y, not y in terms of x.
        # Behavior here is the reverse, for easy comparison with regress.
        y = [159, 179, 100, 45, 384, 230, 100, 320, 80, 220, 320, 210]
        x = [14.40, 15.20, 11.30, 2.50, 22.70, 14.90, 1.41, 15.81, 4.19, 15.39,
             17.25, 9.52]
        self.assertFloatEqual(regress_major(x, y), (18.93633, -32.55208))

    def test_sign_test(self):
        """sign_test, should match values from R"""
        v = [("two sided", 26, 50, 0.88772482734078251),
             ("less", 26, 50, 0.6641),
             ("l", 10, 50, 1.193066583837777e-05),
             ("hi", 30, 50, 0.1013193755322703),
             ("h", 0, 50, 1.0),
             ("2", 30, 50, 0.20263875106454063),
             ("h", 49, 50, 4.5297099404706387e-14),
             ("h", 50, 50, 8.8817841970012543e-16)
             ]
        for alt, success, trials, p in v:
            result = sign_test(success, trials, alt=alt)
            self.assertFloatEqual(result, p, eps=1e-5)

    def test_permute_2d(self):
        """permute_2d permutes rows and cols of a matrix."""
        a = reshape(arange(9), (3, 3))
        self.assertEqual(permute_2d(a, [0, 1, 2]), a)
        self.assertEqual(permute_2d(a, [2, 1, 0]),
                         array([[8, 7, 6], [5, 4, 3], [2, 1, 0]]))
        self.assertEqual(permute_2d(a, [1, 2, 0]),
                         array([[4, 5, 3], [7, 8, 6], [1, 2, 0]]))


class GTests(TestCase):
    """Tests implementation of the G tests for fit and independence."""

    def test_G_2_by_2_2tailed_equal(self):
        """G_2_by_2 should return 0 if all cell counts are equal"""
        self.assertFloatEqual(0, G_2_by_2(1, 1, 1, 1, False, False)[0])
        self.assertFloatEqual(0, G_2_by_2(100, 100, 100, 100, False, False)[0])
        self.assertFloatEqual(0, G_2_by_2(100, 100, 100, 100, True, False)[0])

    def test_G_2_by_2_bad_data(self):
        """G_2_by_2 should raise ValueError if any counts are negative"""
        self.assertRaises(ValueError, G_2_by_2, 1, -1, 1, 1)

    def test_G_2_by_2_2tailed_examples(self):
        """G_2_by_2 values should match examples in Sokal & Rohlf"""
        # example from p 731, Sokal and Rohlf (1995)
        # without correction
        self.assertFloatEqual(G_2_by_2(12, 22, 16, 50, False, False)[0],
                              1.33249, 0.0001)
        self.assertFloatEqual(G_2_by_2(12, 22, 16, 50, False, False)[1],
                              0.24836, 0.0001)
        # with correction
        self.assertFloatEqual(G_2_by_2(12, 22, 16, 50, True, False)[0],
                              1.30277, 0.0001)
        self.assertFloatEqual(G_2_by_2(12, 22, 16, 50, True, False)[1],
                              0.25371, 0.0001)

    def test_G_2_by_2_1tailed_examples(self):
        """G_2_by_2 values should match values from codon_binding program"""
        # first up...the famous arginine case
        self.assertFloatEqualAbs(G_2_by_2(36, 16, 38, 106), (29.111609, 0),
                                 0.00001)
        # then some other miscellaneous positive and negative values
        self.assertFloatEqualAbs(G_2_by_2(0, 52, 12, 132), (-7.259930, 0.996474),
                                 0.00001)
        self.assertFloatEqualAbs(G_2_by_2(5, 47, 14, 130), (-0.000481, 0.508751),
                                 0.00001)
        self.assertFloatEqualAbs(G_2_by_2(5, 47, 36, 108), (-6.065167, 0.993106),
                                 0.00001)

    def test_calc_contingency_expected(self):
        """calcContingencyExpected returns new matrix with expected freqs"""
        matrix = Dict2D({'rest_of_tree': {'env1': 2, 'env3': 1, 'env2': 0},
                         'b': {'env1': 1, 'env3': 1, 'env2': 3}})
        result = calc_contingency_expected(matrix)
        self.assertFloatEqual(result['rest_of_tree']['env1'], [2, 1.125])
        self.assertFloatEqual(result['rest_of_tree']['env3'], [1, 0.75])
        self.assertFloatEqual(result['rest_of_tree']['env2'], [0, 1.125])
        self.assertFloatEqual(result['b']['env1'], [1, 1.875])
        self.assertFloatEqual(result['b']['env3'], [1, 1.25])
        self.assertFloatEqual(result['b']['env2'], [3, 1.875])

    def test_Gfit_unequal_lists(self):
        """Gfit should raise errors if lists unequal"""
        # lists must be equal
        self.assertRaises(ValueError, G_fit, [1, 2, 3], [1, 2])

    def test_Gfit_negative_observeds(self):
        """Gfit should raise ValueError if any observeds are negative."""
        self.assertRaises(ValueError, G_fit, [-1, 2, 3], [1, 2, 3])

    def test_Gfit_nonpositive_expecteds(self):
        """Gfit should raise ZeroExpectedError if expecteds are zero/negative"""
        self.assertRaises(ZeroExpectedError, G_fit, [1, 2, 3], [0, 1, 2])
        self.assertRaises(ZeroExpectedError, G_fit, [1, 2, 3], [-1, 1, 2])

    def test_Gfit_good_data(self):
        """Gfit tests for fit should match examples in Sokal and Rohlf"""
        # example from p. 699, Sokal and Rohlf (1995)
        obs = [63, 31, 28, 12, 39, 16, 40, 12]
        exp = [67.78125, 22.59375, 22.59375, 7.53125, 45.18750,
                15.06250, 45.18750, 15.06250]
        # without correction
        self.assertFloatEqualAbs(G_fit(obs, exp, False)[0], 8.82397, 0.00002)
        self.assertFloatEqualAbs(G_fit(obs, exp, False)[1], 0.26554, 0.00002)
        # with correction
        self.assertFloatEqualAbs(G_fit(obs, exp)[0], 8.76938, 0.00002)
        self.assertFloatEqualAbs(G_fit(obs, exp)[1], 0.26964, 0.00002)

        # example from p. 700, Sokal and Rohlf (1995)
        obs = [130, 46]
        exp = [132, 44]
        # without correction
        self.assertFloatEqualAbs(G_fit(obs, exp, False)[0], 0.12002, 0.00002)
        self.assertFloatEqualAbs(G_fit(obs, exp, False)[1], 0.72901, 0.00002)
        # with correction
        self.assertFloatEqualAbs(G_fit(obs, exp)[0], 0.11968, 0.00002)
        self.assertFloatEqualAbs(G_fit(obs, exp)[1], 0.72938, 0.00002)

    def test_safe_sum_p_log_p(self):
        """safe_sum_p_log_p should ignore zero elements, not raise error"""
        m = array([2, 4, 0, 8])
        self.assertEqual(safe_sum_p_log_p(m, 2), 2 * 1 + 4 * 2 + 8 * 3)

    def test_G_ind(self):
        """G test for independence should match Sokal and Rohlf p 738 values"""
        a = array([[29, 11], [273, 191], [8, 31], [64, 64]])
        self.assertFloatEqual(G_ind(a)[0], 28.59642)
        self.assertFloatEqual(G_ind(a, True)[0], 28.31244)

    def test_G_fit_from_Dict2D(self):
        """G_fit_from_Dict2D runs G-fit on data in a Dict2D
        """
        matrix = Dict2D({'Marl': {'val': [2, 5.2]},
                         'Chalk': {'val': [10, 5.2]},
                         'Sandstone': {'val': [8, 5.2]},
                         'Clay': {'val': [2, 5.2]},
                         'Limestone': {'val': [4, 5.2]}
                         })
        g_val, prob = G_fit_from_Dict2D(matrix)
        self.assertFloatEqual(g_val, 9.84923)
        self.assertFloatEqual(prob, 0.04304536)

    def test_chi_square_from_Dict2D(self):
        """chi_square_from_Dict2D calcs a Chi-Square and p value from Dict2D"""
        # test1
        obs_matrix = Dict2D({'rest_of_tree': {'env1': 2, 'env3': 1, 'env2': 0},
                             'b': {'env1': 1, 'env3': 1, 'env2': 3}})
        input_matrix = calc_contingency_expected(obs_matrix)
        test, csp = chi_square_from_Dict2D(input_matrix)
        self.assertFloatEqual(test, 3.0222222222222221)
        # test2
        test_matrix_2 = Dict2D({'Marl': {'val': [2, 5.2]},
                                'Chalk': {'val': [10, 5.2]},
                                'Sandstone': {'val': [8, 5.2]},
                                'Clay': {'val': [2, 5.2]},
                                'Limestone': {'val': [4, 5.2]}
                                })
        test2, csp2 = chi_square_from_Dict2D(test_matrix_2)
        self.assertFloatEqual(test2, 10.1538461538)
        self.assertFloatEqual(csp2, 0.0379143890013)
        # test3
        matrix3_obs = Dict2D({'AIDS': {'Males': 4, 'Females': 2, 'Both': 3},
                              'No_AIDS': {'Males': 3, 'Females': 16, 'Both': 2}
                              })
        matrix3 = calc_contingency_expected(matrix3_obs)
        test3, csp3 = chi_square_from_Dict2D(matrix3)
        self.assertFloatEqual(test3, 7.6568405139833722)
        self.assertFloatEqual(csp3, 0.0217439383468)


class LikelihoodTests(TestCase):
    """Tests implementations of likelihood calculations."""

    def test_likelihoods_unequal_list_lengths(self):
        """likelihoods should raise ValueError if input lists unequal length"""
        self.assertRaises(ValueError, likelihoods, [1, 2], [1])

    def test_likelihoods_equal_priors(self):
        """likelihoods should equal Pr(D|H) if priors the same"""
        equal = [0.25, 0.25, 0.25, 0.25]
        unequal = [0.5, 0.25, 0.125, 0.125]
        equal_answer = [1, 1, 1, 1]
        unequal_answer = [2, 1, 0.5, 0.5]
        for obs, exp in zip(likelihoods(equal, equal), equal_answer):
            self.assertFloatEqual(obs, exp)

        for obs, exp in zip(likelihoods(unequal, equal), unequal_answer):
            self.assertFloatEqual(obs, exp)

    def test_likelihoods_equal_evidence(self):
        """likelihoods should return vector of 1's if evidence equal for all"""
        equal = [0.25, 0.25, 0.25, 0.25]
        unequal = [0.5, 0.25, 0.125, 0.125]
        equal_answer = [1, 1, 1, 1]
        unequal_answer = [2, 1, 0.5, 0.5]
        not_unity = [0.7, 0.7, 0.7, 0.7]

        for obs, exp in zip(likelihoods(equal, unequal), equal_answer):
            self.assertFloatEqual(obs, exp)

        # should be the same if evidences don't sum to 1
        for obs, exp in zip(likelihoods(not_unity, unequal), equal_answer):
            self.assertFloatEqual(obs, exp)

    def test_likelihoods_unequal_evidence(self):
        """likelihoods should update based on weighted sum if evidence unequal"""
        not_unity = [1, 0.5, 0.25, 0.25]
        unequal = [0.5, 0.25, 0.125, 0.125]
        products = [1.4545455, 0.7272727, 0.3636364, 0.3636364]

        # if priors and evidence both unequal, likelihoods should change
        #(calculated using StarCalc)
        for obs, exp in zip(likelihoods(not_unity, unequal), products):
            self.assertFloatEqual(obs, exp)

    def test_posteriors_unequal_lists(self):
        """posteriors should raise ValueError if input lists unequal lengths"""
        self.assertRaises(ValueError, posteriors, [1, 2, 3], [1])

    def test_posteriors_good_data(self):
        """posteriors should return products of paired list elements"""
        first = [0, 0.25, 0.5, 1, 0.25]
        second = [0.25, 0.5, 0, 0.1, 1]
        product = [0, 0.125, 0, 0.1, 0.25]
        for obs, exp in zip(posteriors(first, second), product):
            self.assertFloatEqual(obs, exp)


class BayesUpdateTests(TestCase):
    """Tests implementation of Bayes calculations"""

    def setUp(self):
        first = [0.25, 0.25, 0.25]
        second = [0.1, 0.75, 0.3]
        third = [0.95, 1e-10, 0.2]
        fourth = [0.01, 0.9, 0.1]
        bad = [1, 2, 1, 1, 1]
        self.bad = [first, bad, second, third]
        self.test = [first, second, third, fourth]
        self.permuted = [fourth, first, third, second]
        self.deleted = [second, fourth, third]
        self.extra = [first, second, first, third, first, fourth, first]

        # BEWARE: low precision in second item, so need to adjust threshold
        # for assertFloatEqual accordingly (and use assertFloatEqualAbs).
        self.result = [0.136690646154, 0.000000009712, 0.863309344133]

    def test_bayes_updates_bad_data(self):
        """bayes_updates should raise ValueError on unequal-length lists"""
        self.assertRaises(ValueError, bayes_updates, self.bad)

    def test_bayes_updates_good_data(self):
        """bayes_updates should match hand calculations of probability updates"""
        # result for first -> fourth calculated by hand
        for obs, exp in zip(bayes_updates(self.test), self.result):
            self.assertFloatEqualAbs(obs, exp, 1e-11)

    def test_bayes_updates_permuted(self):
        """bayes_updates should not be affected by order of inputs"""
        for obs, exp in zip(bayes_updates(self.permuted), self.result):
            self.assertFloatEqualAbs(obs, exp, 1e-11)

    def test_bayes_update_nondiscriminating(self):
        """bayes_updates should be unaffected by extra nondiscriminating data"""
        # deletion of non-discriminating evidence should not affect result
        for obs, exp in zip(bayes_updates(self.deleted), self.result):
            self.assertFloatEqualAbs(obs, exp, 1e-11)
        # additional non-discriminating evidence should not affect result
        for obs, exp in zip(bayes_updates(self.extra), self.result):
            self.assertFloatEqualAbs(obs, exp, 1e-11)


class StatTests(TestsHelper):
    """Tests that the t and z tests are implemented correctly"""

    def setUp(self):
        super(StatTests, self).setUp()

        self.x = [
            7.33, 7.49, 7.27, 7.93, 7.56,
            7.81, 7.46, 6.94, 7.49, 7.44,
            7.95, 7.47, 7.04, 7.10, 7.64,
        ]

        self.y = [
            7.53, 7.70, 7.46, 8.21, 7.81,
            8.01, 7.72, 7.13, 7.68, 7.66,
            8.11, 7.66, 7.20, 7.25, 7.79,
        ]

    def test_t_paired_2tailed(self):
        """t_paired should match values from Sokal & Rohlf p 353"""
        x, y = self.x, self.y
        # check value of t and the probability for 2-tailed
        self.assertFloatEqual(t_paired(y, x)[0], 19.7203, 1e-4)
        self.assertFloatEqual(t_paired(y, x)[1], 1.301439e-11, 1e-4)

    def test_t_paired_no_variance(self):
        """t_paired should return None if lists are invariant"""
        x = [1, 1, 1]
        y = [0, 0, 0]
        self.assertEqual(t_paired(x, x), (None, None))
        self.assertEqual(t_paired(x, y), (None, None))

    def test_t_paired_1tailed(self):
        """t_paired should match pre-calculated 1-tailed values"""
        x, y = self.x, self.y
        # check probability for 1-tailed low and high
        self.assertFloatEqual(
            t_paired(y, x, "low")[1], 1 - (1.301439e-11 / 2), 1e-4)
        self.assertFloatEqual(
            t_paired(x, y, "high")[1], 1 - (1.301439e-11 / 2), 1e-4)
        self.assertFloatEqual(
            t_paired(y, x, "high")[1], 1.301439e-11 / 2, 1e-4)
        self.assertFloatEqual(
            t_paired(x, y, "low")[1], 1.301439e-11 / 2, 1e-4)

    def test_t_paired_specific_difference(self):
        """t_paired should allow a specific difference to be passed"""
        x, y = self.x, self.y
        # difference is 0.2, so test should be non-significant if 0.2 passed
        self.assertFalse(t_paired(y, x, exp_diff=0.2)[0] > 1e-10)
        # same, except that reversing list order reverses sign of difference
        self.assertFalse(t_paired(x, y, exp_diff=-0.2)[0] > 1e-10)
        # check that there's no significant difference from the true mean
        self.assertFloatEqual(
            t_paired(y, x, exp_diff=0.2)[1], 1, 1e-4)

    def test_t_paired_bad_data(self):
        """t_paired should raise ValueError on lists of different lengths"""
        self.assertRaises(ValueError, t_paired, self.y, [1, 2, 3])

    def test_t_two_sample(self):
        """t_two_sample should match example on p.225 of Sokal and Rohlf"""
        I = array([7.2, 7.1, 9.1, 7.2, 7.3, 7.2, 7.5])
        II = array([8.8, 7.5, 7.7, 7.6, 7.4, 6.7, 7.2])
        self.assertFloatEqual(t_two_sample(I, II), (-0.1184, 0.45385 * 2),
                              0.001)

    def test_t_two_sample_no_variance(self):
        """t_two_sample should properly handle lists that are invariant"""
        # By default should return (None, None) to mimic R's t.test.
        x = array([1, 1., 1])
        y = array([0, 0, 0.0])
        self.assertEqual(t_two_sample(x, x), (None, None))
        self.assertEqual(t_two_sample(x, y), (None, None))

        # Test none_on_zero_variance=False on various tail types. We use
        # self.assertEqual instead of self.assertFloatEqual because the latter
        # sees inf and -inf as being equal.

        # Two tailed: a < b
        self.assertEqual(t_two_sample(y, x, none_on_zero_variance=False),
                         (float('-inf'), 0.0))

        # Two tailed: a > b
        self.assertEqual(t_two_sample(x, y, none_on_zero_variance=False),
                         (float('inf'), 0.0))

        # One-tailed 'high': a < b
        self.assertEqual(t_two_sample(y, x, tails='high',
                                      none_on_zero_variance=False),
                         (float('-inf'), 1.0))

        # One-tailed 'high': a > b
        self.assertEqual(t_two_sample(x, y, tails='high',
                                      none_on_zero_variance=False),
                         (float('inf'), 0.0))

        # One-tailed 'low': a < b
        self.assertEqual(t_two_sample(y, x, tails='low',
                                      none_on_zero_variance=False),
                         (float('-inf'), 0.0))

        # One-tailed 'low': a > b
        self.assertEqual(t_two_sample(x, y, tails='low',
                                      none_on_zero_variance=False),
                         (float('inf'), 1.0))

        # Should still receive (None, None) if the lists have no variance and
        # have the same single value.
        self.assertEqual(t_two_sample(x, x, none_on_zero_variance=False),
                         (None, None))
        self.assertEqual(t_two_sample(x, [1, 1], none_on_zero_variance=False),
                         (None, None))

    def test_t_two_sample_invalid_input(self):
        """t_two_sample should raise an error on invalid input."""
        self.assertRaises(ValueError, t_two_sample, [1, 2, 3], [4, 5, 6],
                          tails='foo')

    def test_t_one_sample(self):
        """t_one_sample results should match those from R"""
        x = array(list(range(-5, 5)))
        y = array(list(range(-1, 10)))
        self.assertFloatEqualAbs(t_one_sample(x), (-0.5222, 0.6141), 1e-4)
        self.assertFloatEqualAbs(t_one_sample(y), (4, 0.002518), 1e-4)
        # do some one-tailed tests as well
        self.assertFloatEqualAbs(t_one_sample(
            y, tails='low'), (4, 0.9987), 1e-4)
        self.assertFloatEqualAbs(t_one_sample(
            y, tails='high'), (4, 0.001259), 1e-4)

    def test_t_two_sample_switch(self):
        """t_two_sample should call t_one_observation if 1 item in sample."""
        sample = array([4.02, 3.88, 3.34, 3.87, 3.18])
        x = array([3.02])
        self.assertFloatEqual(t_two_sample(x, sample), (-1.5637254, 0.1929248))
        self.assertFloatEqual(t_two_sample(sample, x), (1.5637254, 0.1929248))

        # can't do the test if both samples have single item
        self.assertEqual(t_two_sample(x, x), (None, None))

        # Test special case if t=0.
        self.assertFloatEqual(t_two_sample([2], [1, 2, 3]), (0.0, 1.0))
        self.assertFloatEqual(t_two_sample([1, 2, 3], [2]), (0.0, 1.0))

    def test_t_one_observation(self):
        """t_one_observation should match p. 228 of Sokal and Rohlf"""
        sample = array([4.02, 3.88, 3.34, 3.87, 3.18])
        x = 3.02
        # note that this differs after the 3rd decimal place from what's in the
        # book, because Sokal and Rohlf round their intermediate steps...
        self.assertFloatEqual(t_one_observation(x, sample),
                              (-1.5637254, 0.1929248))

    def test_t_one_observation_no_variance(self):
        """t_one_observation should correctly handle an invariant list."""
        sample = array([1.0, 1.0, 1.0])

        # Can't perform test if invariant list's single value matches x,
        # regardless of none_on_zero_variance.
        self.assertEqual(t_one_observation(1, sample), (None, None))
        self.assertEqual(t_one_observation(1, sample,
                                           none_on_zero_variance=False), (None, None))

        # Test correct handling of none_on_zero_variance.
        self.assertEqual(t_one_observation(2, sample), (None, None))
        self.assertEqual(t_one_observation(2, sample,
                                           none_on_zero_variance=False), (float('inf'), 0.0))
        self.assertEqual(t_one_observation(2, sample,
                                           none_on_zero_variance=False, tails='low'), (float('inf'), 1.0))

    def test_mc_t_two_sample(self):
        """Test gives correct results with valid input data."""
        # Verified against R's t.test() and Deducer::perm.t.test().

        # With numpy array as input.
        exp = (-0.11858541225631833, 0.90756579317867436)
        I = array([7.2, 7.1, 9.1, 7.2, 7.3, 7.2, 7.5])
        II = array([8.8, 7.5, 7.7, 7.6, 7.4, 6.7, 7.2])
        obs = mc_t_two_sample(I, II)
        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 999)
        self.assertCorrectPValue(0.8, 0.9, mc_t_two_sample, [I, II],
                                 p_val_idx=3)

        # With python list as input.
        exp = (-0.11858541225631833, 0.90756579317867436)
        I = [7.2, 7.1, 9.1, 7.2, 7.3, 7.2, 7.5]
        II = [8.8, 7.5, 7.7, 7.6, 7.4, 6.7, 7.2]
        obs = mc_t_two_sample(I, II)
        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 999)
        self.assertCorrectPValue(0.8, 0.9, mc_t_two_sample, [I, II],
                                 p_val_idx=3)

        exp = (-0.11858541225631833, 0.45378289658933718)
        obs = mc_t_two_sample(I, II, tails='low')
        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 999)
        self.assertCorrectPValue(0.4, 0.47, mc_t_two_sample, [I, II],
                                 {'tails': 'low'}, p_val_idx=3)

        exp = (-0.11858541225631833, 0.54621710341066287)
        obs = mc_t_two_sample(I, II, tails='high', permutations=99)
        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 99)
        self.assertCorrectPValue(0.4, 0.62, mc_t_two_sample, [I, II],
                                 {'tails': 'high', 'permutations': 99}, p_val_idx=3)

        exp = (-2.8855783649036986, 0.99315596652421401)
        obs = mc_t_two_sample(I, II, tails='high', permutations=99, exp_diff=1)
        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 99)
        self.assertCorrectPValue(0.55, 0.99, mc_t_two_sample, [I, II],
                                 {'tails': 'high', 'permutations': 99, 'exp_diff': 1}, p_val_idx=3)

    def test_mc_t_two_sample_unbalanced_obs(self):
        """Test gives correct results with unequal number of obs per sample."""
        # Verified against R's t.test() and Deducer::perm.t.test().
        exp = (-0.10302479888889175, 0.91979753020527177)
        I = array([7.2, 7.1, 9.1, 7.2, 7.3, 7.2])
        II = array([8.8, 7.5, 7.7, 7.6, 7.4, 6.7, 7.2])
        obs = mc_t_two_sample(I, II)
        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 999)
        self.assertCorrectPValue(0.8, 0.9, mc_t_two_sample, [I, II],
                                 p_val_idx=3)

    def test_mc_t_two_sample_single_obs_sample(self):
        """Test works correctly with one sample having a single observation."""
        sample = array([4.02, 3.88, 3.34, 3.87, 3.18])
        x = array([3.02])
        exp = (-1.5637254, 0.1929248)
        obs = mc_t_two_sample(x, sample)
        self.assertFloatEqual(obs[:2], exp)
        self.assertFloatEqual(len(obs[2]), 999)
        self.assertIsProb(obs[3])

        exp = (1.5637254, 0.1929248)
        obs = mc_t_two_sample(sample, x)
        self.assertFloatEqual(obs[:2], exp)
        self.assertFloatEqual(len(obs[2]), 999)
        self.assertIsProb(obs[3])

        # Test the case where we can have no variance in the permuted lists.
        x = array([1, 1, 2])
        y = array([1])
        exp = (0.5, 0.666666666667)
        obs = mc_t_two_sample(x, y)
        self.assertFloatEqual(obs[:2], exp)
        self.assertFloatEqual(len(obs[2]), 999)
        self.assertIsProb(obs[3])

    def test_mc_t_two_sample_no_perms(self):
        """Test gives empty permutation results if no perms are given."""
        exp = (-0.11858541225631833, 0.90756579317867436, [], None)
        I = array([7.2, 7.1, 9.1, 7.2, 7.3, 7.2, 7.5])
        II = array([8.8, 7.5, 7.7, 7.6, 7.4, 6.7, 7.2])
        obs = mc_t_two_sample(I, II, permutations=0)
        self.assertFloatEqual(obs, exp)

    def test_mc_t_two_sample_no_mc(self):
        """Test no MC stats if initial t-test is bad."""
        x = array([1, 1, 1])
        y = array([0, 0, 0])
        self.assertEqual(mc_t_two_sample(x, x), (None, None, [], None))

    def test_mc_t_two_sample_no_variance(self):
        """Test input with no variance. Should match Deducer::perm.t.test."""
        x = array([1, 1, 1])
        y = array([2, 2, 2])

        exp = (float('-inf'), 0.0)
        obs = mc_t_two_sample(x, y, permutations=10000)

        self.assertEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 10000)
        self.assertCorrectPValue(0.09, 0.11, mc_t_two_sample, [x, y],
                                 {'permutations': 10000}, p_val_idx=3)

        exp = (float('inf'), 0.0)
        obs = mc_t_two_sample(y, x, permutations=10000)

        self.assertEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 10000)
        self.assertCorrectPValue(0.09, 0.11, mc_t_two_sample, [y, x],
                                 {'permutations': 10000}, p_val_idx=3)

        exp = (float('-inf'), 1.0)
        obs = mc_t_two_sample(x, y, permutations=10000, tails='high')

        self.assertEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 10000)
        self.assertCorrectPValue(0.9999, 1.0, mc_t_two_sample, [x, y],
                                 {'permutations': 10000, 'tails': 'high'},
                                 p_val_idx=3)

        exp = (float('-inf'), 0.0)
        obs = mc_t_two_sample(x, y, permutations=10000, tails='low')

        self.assertEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 10000)
        self.assertCorrectPValue(0.04, 0.051, mc_t_two_sample, [x, y],
                                 {'permutations': 10000, 'tails': 'low'},
                                 p_val_idx=3)

    def test_mc_t_two_sample_no_permuted_variance(self):
        """Test with chance of getting no variance with some perms."""
        # Verified against R's t.test() and Deducer::perm.t.test().
        x = array([1, 1, 2])
        y = array([2, 2, 1])

        exp = (-0.70710678118654791, 0.51851851851851838)
        obs = mc_t_two_sample(x, y, permutations=10000)

        self.assertFloatEqual(obs[:2], exp)
        self.assertEqual(len(obs[2]), 10000)
        self.assertCorrectPValue(0.97, 1.0, mc_t_two_sample, [x, y],
                                 {'permutations': 10000}, p_val_idx=3)

    def test_mc_t_two_sample_invalid_input(self):
        """Test fails on various invalid input."""
        self.assertRaises(ValueError, mc_t_two_sample, [1, 2, 3], [4., 5., 4.],
                          tails='foo')
        self.assertRaises(ValueError, mc_t_two_sample, [1, 2, 3], [4., 5., 4.],
                          permutations=-1)
        self.assertRaises(ValueError, mc_t_two_sample, [1], [4.])
        self.assertRaises(ValueError, mc_t_two_sample, [1, 2], [])

    def test_permute_observations(self):
        """Test works correctly on small input dataset."""
        I = [10, 20., 1]
        II = [2, 4, 5, 7]
        obs = _permute_observations(I, II, 1)
        self.assertEqual(len(obs[0]), 1)
        self.assertEqual(len(obs[1]), 1)
        self.assertEqual(len(obs[0][0]), len(I))
        self.assertEqual(len(obs[1][0]), len(II))
        self.assertFloatEqual(sorted(concatenate((obs[0][0], obs[1][0]))),
                              sorted(I + II))

    def test_reverse_tails(self):
        """reverse_tails should return 'high' if tails was 'low' or vice versa"""
        self.assertEqual(reverse_tails('high'), 'low')
        self.assertEqual(reverse_tails('low'), 'high')
        self.assertEqual(reverse_tails(None), None)
        self.assertEqual(reverse_tails(3), 3)

    def test_tail(self):
        """tail should return prob/2 if test is true, or 1-(prob/2) if false"""
        self.assertFloatEqual(tail(0.25, True), 0.125)
        self.assertFloatEqual(tail(0.25, False), 0.875)
        self.assertFloatEqual(tail(1, True), 0.5)
        self.assertFloatEqual(tail(1, False), 0.5)
        self.assertFloatEqual(tail(0, True), 0)
        self.assertFloatEqual(tail(0, False), 1)

    def test_z_test(self):
        """z_test should give correct values"""
        sample = array([1, 2, 3, 4, 5])
        self.assertFloatEqual(z_test(sample, 3, 1), (0, 1))
        self.assertFloatEqual(z_test(sample, 3, 2, 'high'), (0, 0.5))
        self.assertFloatEqual(z_test(sample, 3, 2, 'low'), (0, 0.5))
        # check that population mean and variance, and tails, can be set OK.
        self.assertFloatEqual(z_test(sample, 0, 1), (6.7082039324993694,
                                                     1.9703444711798951e-11))
        self.assertFloatEqual(z_test(sample, 1, 10), (0.44721359549995793,
                                                      0.65472084601857694))
        self.assertFloatEqual(z_test(sample, 1, 10, 'high'),
                              (0.44721359549995793, 0.65472084601857694 / 2))
        self.assertFloatEqual(z_test(sample, 1, 10, 'low'),
                              (0.44721359549995793, 1 - (0.65472084601857694 / 2)))


class CorrelationTests(TestsHelper):
    """Tests of correlation coefficients and Mantel test."""

    def setUp(self):
        """Sets up variables used in the tests."""
        super(CorrelationTests, self).setUp()

        # For testing spearman and correlation_test using method='spearman'.
        # Taken from the Spearman wikipedia article. Also used for testing
        # Pearson (verified with R).
        self.data1 = [106, 86, 100, 101, 99, 103, 97, 113, 112, 110]
        self.data2 = [7, 0, 27, 50, 28, 29, 20, 12, 6, 17]

        # For testing spearman.
        self.a = [1, 2, 4, 3, 1, 6, 7, 8, 10, 4]
        self.b = [2, 10, 20, 1, 3, 7, 5, 11, 6, 13]
        self.c = [7, 1, 20, 13, 3, 57, 5, 121, 2, 9]
        self.r = (1.7, 10, 20, 1.7, 3, 7, 5, 11, 6.5, 13)
        self.x = (1, 2, 4, 3, 1, 6, 7, 8, 10, 4, 100, 2, 3, 77)

        # Ranked copies for testing spearman.
        self.b_ranked = [2, 7, 10, 1, 3, 6, 4, 8, 5, 9]
        self.c_ranked = [5, 1, 8, 7, 3, 9, 4, 10, 2, 6]

    def test_mantel(self):
        """mantel should be significant for same matrix, not for random"""
        a = reshape(arange(25), (5, 5))
        a = tril(a) + tril(a).T
        fill_diagonal(a, 0)
        b = a.copy()
        # closely related -- should be significant
        self.assertCorrectPValue(0.0, 0.049, mantel, (a, b, 1000))

        c = reshape(ones(25), (5, 5))
        c[0, 1] = 3.0
        c[1, 0] = 3.0
        fill_diagonal(c, 0)
        # not related -- should not be significant
        self.assertCorrectPValue(0.06, 1.0, mantel, (a, c, 1000))

    def test_mantel_test_one_sided_greater(self):
        """Test one-sided mantel test (greater)."""
        # This test output was verified by R (their mantel function does a
        # one-sided greater test).
        m1 = array([[0, 1, 2], [1, 0, 3], [2, 3, 0]])
        m2 = array([[0, 2, 7], [2, 0, 6], [7, 6, 0]])
        p, stat, perms = mantel_test(m1, m1, 999, alt='greater')
        self.assertFloatEqual(stat, 1.0)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.09, 0.25, mantel_test, (m1, m1, 999),
                                 {'alt': 'greater'})

        p, stat, perms = mantel_test(m1, m2, 999, alt='greater')
        self.assertFloatEqual(stat, 0.755928946018)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.2, 0.5, mantel_test, (m1, m2, 999),
                                 {'alt': 'greater'})

    def test_mantel_test_one_sided_less(self):
        """Test one-sided mantel test (less)."""
        # This test output was verified by R (their mantel function does a
        # one-sided greater test, but I modified their output to do a one-sided
        # less test).
        m1 = array([[0, 1, 2], [1, 0, 3], [2, 3, 0]])
        m2 = array([[0, 2, 7], [2, 0, 6], [7, 6, 0]])
        m3 = array([[0, 0.5, 0.25], [0.5, 0, 0.1], [0.25, 0.1, 0]])
        p, stat, perms = mantel_test(m1, m1, 999, alt='less')
        self.assertFloatEqual(p, 1.0)
        self.assertFloatEqual(stat, 1.0)
        self.assertEqual(len(perms), 999)

        p, stat, perms = mantel_test(m1, m2, 999, alt='less')
        self.assertFloatEqual(stat, 0.755928946018)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.6, 1.0, mantel_test, (m1, m2, 999),
                                 {'alt': 'less'})

        p, stat, perms = mantel_test(m1, m3, 999, alt='less')
        self.assertFloatEqual(stat, -0.989743318611)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.1, 0.25, mantel_test, (m1, m3, 999),
                                 {'alt': 'less'})

    def test_mantel_test_two_sided(self):
        """Test two-sided mantel test."""
        # This test output was verified by R (their mantel function does a
        # one-sided greater test, but I modified their output to do a two-sided
        # test).
        m1 = array([[0, 1, 2], [1, 0, 3], [2, 3, 0]])
        m2 = array([[0, 2, 7], [2, 0, 6], [7, 6, 0]])
        m3 = array([[0, 0.5, 0.25], [0.5, 0, 0.1], [0.25, 0.1, 0]])
        p, stat, perms = mantel_test(m1, m1, 999, alt='two sided')
        self.assertFloatEqual(stat, 1.0)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.20, 0.45, mantel_test, (m1, m1, 999),
                                 {'alt': 'two sided'})

        p, stat, perms = mantel_test(m1, m2, 999, alt='two sided')
        self.assertFloatEqual(stat, 0.755928946018)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.6, 0.75, mantel_test, (m1, m2, 999),
                                 {'alt': 'two sided'})

        p, stat, perms = mantel_test(m1, m3, 999, alt='two sided')
        self.assertFloatEqual(stat, -0.989743318611)
        self.assertEqual(len(perms), 999)
        self.assertCorrectPValue(0.2, 0.45, mantel_test, (m1, m3, 999),
                                 {'alt': 'two sided'})

    def test_mantel_test_invalid_distance_matrix(self):
        """Test mantel test with invalid distance matrix."""
        # Single asymmetric, non-hollow distance matrix.
        self.assertRaises(ValueError, mantel_test, array([[1, 2], [3, 4]]),
                          array([[0, 0], [0, 0]]), 999)

        # Two asymmetric distance matrices.
        self.assertRaises(ValueError, mantel_test, array([[0, 2], [3, 0]]),
                          array([[0, 1], [0, 0]]), 999)

    def test_mantel_test_invalid_input(self):
        """Test mantel test with invalid input."""
        self.assertRaises(ValueError, mantel_test, array([[1]]), array([[1]]),
                          999, alt='foo')
        self.assertRaises(ValueError, mantel_test, array([[1]]),
                          array([[1, 2], [3, 4]]), 999)
        self.assertRaises(ValueError, mantel_test, array([[1]]),
                          array([[1]]), 0)
        self.assertRaises(ValueError, mantel_test, array([[1]]),
                          array([[1]]), -1)

    def test_is_symmetric_and_hollow(self):
        """Should correctly test for symmetry and hollowness of dist mats."""
        self.assertTrue(is_symmetric_and_hollow(array([[0, 1], [1, 0]])))
        self.assertTrue(is_symmetric_and_hollow(matrix([[0, 1], [1, 0]])))
        self.assertTrue(is_symmetric_and_hollow(matrix([[0.0, 0], [0.0, 0]])))
        self.assertTrue(not is_symmetric_and_hollow(
            array([[0.001, 1], [1, 0]])))
        self.assertTrue(not is_symmetric_and_hollow(
            array([[0, 1.1], [1, 0]])))
        self.assertTrue(not is_symmetric_and_hollow(
            array([[0.5, 1.1], [1, 0]])))

    def test_flatten_lower_triangle(self):
        """Test flattening various dms' lower triangulars."""
        self.assertEqual(_flatten_lower_triangle(array([[8]])), [])
        self.assertEqual(_flatten_lower_triangle(array([[1, 2], [3, 4]])), [3])
        self.assertEqual(_flatten_lower_triangle(array([[1, 2, 3], [4, 5, 6],
                                                        [7, 8, 9]])), [4, 7, 8])

    def test_pearson(self):
        """Test pearson correlation method on valid data."""
        # This test output was verified by R.
        self.assertFloatEqual(pearson([1, 2], [1, 2]), 1.0)
        self.assertFloatEqual(pearson([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertFloatEqual(pearson([1, 2, 3], [1, 2, 4]), 0.9819805)

    def test_pearson_invalid_input(self):
        """Test running pearson on bad input."""
        self.assertRaises(ValueError, pearson, [1.4, 2.5], [5.6, 8.8, 9.0])
        self.assertRaises(ValueError, pearson, [1.4], [5.6])

    def test_spearman(self):
        """Test the spearman function with valid input."""
        # One vector has no ties.
        exp = 0.3719581
        obs = spearman(self.a, self.b)
        self.assertFloatEqual(obs, exp)

        # Both vectors have no ties.
        exp = 0.2969697
        obs = spearman(self.b, self.c)
        self.assertFloatEqual(obs, exp)

        # Both vectors have ties.
        exp = 0.388381
        obs = spearman(self.a, self.r)
        self.assertFloatEqual(obs, exp)

        exp = -0.17575757575757578
        obs = spearman(self.data1, self.data2)
        self.assertFloatEqual(obs, exp)

    def test_spearman_no_variation(self):
        """Test the spearman function with a vector having no variation."""
        exp = 0.0
        obs = spearman([1, 1, 1], [1, 2, 3])
        self.assertFloatEqual(obs, exp)

    def test_spearman_ranked(self):
        """Test the spearman function with a vector that is already ranked."""
        exp = 0.2969697
        obs = spearman(self.b_ranked, self.c_ranked)
        self.assertFloatEqual(obs, exp)

    def test_spearman_one_obs(self):
        """Test running spearman on a single observation."""
        self.assertRaises(ValueError, spearman, [1.0], [5.0])

    def test_spearman_invalid_input(self):
        """Test the spearman function with invalid input."""
        self.assertRaises(ValueError, spearman, [], [])
        self.assertRaises(ValueError, spearman, self.a, [])
        self.assertRaises(TypeError, spearman, {0: 2}, [1, 2, 3])

    def test_get_rank(self):
        """Test the _get_rank function with valid input."""
        exp = ([1.5, 3.5, 7.5, 5.5, 1.5, 9.0, 10.0, 11.0, 12.0, 7.5, 14.0, 3.5, 5.5, 13.0],
               4)
        obs = _get_rank(self.x)
        self.assertFloatEqual(exp, obs)

        exp = ([1.5, 3.0, 5.5, 4.0, 1.5, 7.0, 8.0, 9.0, 10.0, 5.5], 2)
        obs = _get_rank(self.a)
        self.assertFloatEqual(exp, obs)

        exp = ([2, 7, 10, 1, 3, 6, 4, 8, 5, 9], 0)
        obs = _get_rank(self.b)
        self.assertFloatEqual(exp, obs)

        exp = ([1.5, 7.0, 10.0, 1.5, 3.0, 6.0, 4.0, 8.0, 5.0, 9.0], 1)
        obs = _get_rank(self.r)
        self.assertFloatEqual(exp, obs)

        exp = ([], 0)
        obs = _get_rank([])
        self.assertEqual(exp, obs)

    def test_get_rank_invalid_input(self):
        """Test the _get_rank function with invalid input."""
        vec = [1, 'a', 3, 2.5, 3, 1]
        self.assertRaises(TypeError, _get_rank, vec)

        vec = [1, 2, {1: 2}, 2.5, 3, 1]
        self.assertRaises(TypeError, _get_rank, vec)

        vec = [1, 2, [23, 1], 2.5, 3, 1]
        self.assertRaises(TypeError, _get_rank, vec)

        vec = [1, 2, (1,), 2.5, 3, 1]
        self.assertRaises(TypeError, _get_rank, vec)

    def test_correlation(self):
        """Correlations and significance should match R's cor.test()"""
        x = [1, 2, 3, 5]
        y = [0, 0, 0, 0]
        z = [1, 1, 1, 1]
        a = [2, 4, 6, 8]
        b = [1.5, 1.4, 1.2, 1.1]
        c = [15, 10, 5, 20]

        bad = [1, 2, 3]  # originally gave r = 1.0000000002

        self.assertFloatEqual(correlation(x, x), (1, 0))
        self.assertFloatEqual(correlation(x, y), (0, 1))
        self.assertFloatEqual(correlation(y, z), (0, 1))
        self.assertFloatEqualAbs(correlation(x, a), (0.9827076, 0.01729), 1e-5)
        self.assertFloatEqualAbs(correlation(
            x, b), (-0.9621405, 0.03786), 1e-5)
        self.assertFloatEqualAbs(correlation(x, c), (0.3779645, 0.622), 1e-3)
        self.assertEqual(correlation(bad, bad), (1, 0))

    def test_correlation_test_pearson(self):
        """Test correlation_test using pearson on valid input."""
        # These results were verified with R.

        # Test with non-default confidence level and permutations.
        obs = correlation_test(self.data1, self.data2, method='pearson',
                               confidence_level=0.90, permutations=990)
        self.assertFloatEqual(obs[:2], (-0.03760147, 0.91786297277172868))
        self.assertEqual(len(obs[2]), 990)
        for r in obs[2]:
            self.assertTrue(r >= -1.0 and r <= 1.0)
        self.assertCorrectPValue(0.9, 0.93, correlation_test,
                                 (self.data1, self.data2),
                                 {'method': 'pearson', 'confidence_level': 0.90,
                                  'permutations': 990}, p_val_idx=3)
        self.assertFloatEqual(obs[4], (-0.5779077, 0.5256224))

        # Test with non-default tail type.
        obs = correlation_test(self.data1, self.data2, method='pearson',
                               confidence_level=0.90, permutations=990,
                               tails='low')
        self.assertFloatEqual(obs[:2], (-0.03760147, 0.45893148638586434))
        self.assertEqual(len(obs[2]), 990)
        for r in obs[2]:
            self.assertTrue(r >= -1.0 and r <= 1.0)
        self.assertCorrectPValue(0.41, 0.46, correlation_test,
                                 (self.data1, self.data2),
                                 {'method': 'pearson', 'confidence_level': 0.90,
                                  'permutations': 990, 'tails': 'low'}, p_val_idx=3)
        self.assertFloatEqual(obs[4], (-0.5779077, 0.5256224))

    def test_correlation_test_spearman(self):
        """Test correlation_test using spearman on valid input."""
        # This example taken from Wikipedia page:
        # http://en.wikipedia.org/wiki/Spearman's_rank_correlation_coefficient
        obs = correlation_test(self.data1, self.data2, method='spearman',
                               tails='high')
        self.assertFloatEqual(obs[:2], (-0.17575757575757578, 0.686405827612))
        self.assertEqual(len(obs[2]), 999)
        for rho in obs[2]:
            self.assertTrue(rho >= -1.0 and rho <= 1.0)
        self.assertCorrectPValue(0.67, 0.7, correlation_test,
                                 (self.data1, self.data2),
                                 {'method': 'spearman', 'tails': 'high'}, p_val_idx=3)
        self.assertFloatEqual(obs[4],
                              (-0.7251388558041697, 0.51034422964834503))

        # The p-value is off because the example uses a one-tailed test, while
        # we use a two-tailed test. Someone confirms the answer that we get
        # here for a two-tailed test:
        # http://stats.stackexchange.com/questions/22816/calculating-p-value-
        #     for-spearmans-rank-correlation-coefficient-example-on-wikip
        obs = correlation_test(self.data1, self.data2, method='spearman',
                               tails=None)
        self.assertFloatEqual(obs[:2],
                              (-0.17575757575757578, 0.62718834477648433))
        self.assertEqual(len(obs[2]), 999)
        for rho in obs[2]:
            self.assertTrue(rho >= -1.0 and rho <= 1.0)
        self.assertCorrectPValue(0.60, 0.64, correlation_test,
                                 (self.data1, self.data2),
                                 {'method': 'spearman', 'tails': None}, p_val_idx=3)
        self.assertFloatEqual(obs[4],
                              (-0.7251388558041697, 0.51034422964834503))

    def test_correlation_test_invalid_input(self):
        """Test correlation_test using invalid input."""
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          method='foo')
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          tails='foo')
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          permutations=-1)
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          confidence_level=-1)
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          confidence_level=1.1)
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          confidence_level=0)
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          confidence_level=0.0)
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          confidence_level=1)
        self.assertRaises(ValueError, correlation_test, self.data1, self.data2,
                          confidence_level=1.0)

    def test_correlation_test_no_permutations(self):
        """Test correlation_test with no permutations."""
        # These results were verified with R.
        exp = (-0.2581988897471611, 0.7418011102528389, [], None,
               (-0.97687328610475876, 0.93488023560400879))
        obs = correlation_test([1, 2, 3, 4], [1, 2, 1, 1], permutations=0)
        self.assertFloatEqual(obs, exp)

    def test_correlation_test_perfect_correlation(self):
        """Test correlation_test with perfectly-correlated input vectors."""
        # These results were verified with R.
        obs = correlation_test([1, 2, 3, 4], [1, 2, 3, 4])
        self.assertFloatEqual(obs[:2],
                              (0.99999999999999978, 2.2204460492503131e-16))
        self.assertEqual(len(obs[2]), 999)
        for r in obs[2]:
            self.assertTrue(r >= -1.0 and r <= 1.0)
        self.assertCorrectPValue(0.06, 0.09, correlation_test,
                                 ([1, 2, 3, 4], [1, 2, 3, 4]), p_val_idx=3)
        self.assertFloatEqual(obs[4], (0.99999999999998879, 1.0))

    def test_correlation_test_small_obs(self):
        """Test correlation_test with a small number of observations."""
        # These results were verified with R.
        obs = correlation_test([1, 2, 3], [1, 2, 3])
        self.assertFloatEqual(obs[:2], (1.0, 0))
        self.assertEqual(len(obs[2]), 999)
        for r in obs[2]:
            self.assertTrue(r >= -1.0 and r <= 1.0)
        self.assertCorrectPValue(0.3, 0.4, correlation_test,
                                 ([1, 2, 3], [1, 2, 3]), p_val_idx=3)
        self.assertFloatEqual(obs[4], (None, None))

        obs = correlation_test([1, 2, 3], [1, 2, 3], method='spearman')
        self.assertFloatEqual(obs[:2], (1.0, 0))
        self.assertEqual(len(obs[2]), 999)
        for r in obs[2]:
            self.assertTrue(r >= -1.0 and r <= 1.0)
        self.assertCorrectPValue(0.3, 0.4, correlation_test,
                                 ([1, 2, 3], [1, 2, 3]), {'method': 'spearman'}, p_val_idx=3)
        self.assertFloatEqual(obs[4], (None, None))

    def test_correlation_matrix(self):
        """Correlations in matrix should match values from R"""
        a = [2, 4, 6, 8]
        b = [1.5, 1.4, 1.2, 1.1]
        c = [15, 10, 5, 20]
        m = correlation_matrix([a, b, c])
        self.assertFloatEqual(m[0, 0], [1.0])
        self.assertFloatEqual([m[1, 0], m[1, 1]], [correlation(b, a)[0], 1.0])
        self.assertFloatEqual(m[2], [correlation(c, a)[0], correlation(c, b)[0],
                                     1.0])


class Ftest(TestCase):
    """Tests for the F test"""

    def test_f_value(self):
        """f_value: should calculate the correct F value if possible"""
        a = array([1, 3, 5, 7, 9, 8, 6, 4, 2])
        b = array([5, 4, 6, 3, 7, 6, 4, 5])
        self.assertEqual(f_value(a, b), (8, 7, 4.375))
        self.assertFloatEqual(f_value(b, a), (7, 8, 0.2285714))
        too_short = array([4])
        self.assertRaises(ValueError, f_value, too_short, b)

    def test_f_two_sample(self):
        """f_two_sample should match values from R"""

        # The expected values in this test are obtained through R.
        # In R the F test is var.test(x,y) different alternative hypotheses
        # can be specified (two sided, less, or greater).
        # The vectors are random samples from a particular normal distribution
        #(mean and sd specified).

        # a: 50 elem, mean=0 sd=1
        a = [-0.70701689, -1.24788845, -1.65516470, 0.10443876, -0.48526915,
             -0.71820656, -1.02603596, 0.03975982, -2.23404324, -0.21509363,
             0.08438468, -0.01970062, -0.67907971, -0.89853667, 1.11137131,
             0.05960496, -1.51172084, -0.79733957, -1.60040659, 0.80530639,
             -0.81715836, -0.69233474, 0.95750665, 0.99576429, -1.61340216,
             -0.43572590, -1.50862327, 0.92847551, -0.68382338, -1.12523522,
             -0.09147488, 0.66756023, -0.87277588, -1.36539039, -0.11748707,
             -1.63632578, -0.31343078, -0.28176086, 0.33854483, -0.51785630,
             2.25360559, -0.80761191, 1.18983499, 0.57080342, -1.44601700,
             -0.53906955, -0.01975266, -1.37147915, -0.31537616, 0.26877544]

        # b: 50 elem, mean=0, sd=1.2
        b = [0.081418743, 0.276571612, -1.864316504, 0.675213612, -0.769202643,
           0.140372825, -1.426250184, 0.058617884, -0.819287409, -0.007701916,
           -0.782722020, -0.285891593, 0.661980419, 0.383225191, 0.622444946,
           -0.192446150, 0.297150571, 0.408896059, -0.167359383, -0.552381362,
           0.982168338, 1.439730446, 1.967616101, -0.579607307, 1.095590943,
           0.240591302, -1.566937143, -0.199091349, -1.232983905, 0.362378169,
           1.166061081, -0.604676222, -0.536560206, -0.303117595, 1.519222792,
           -0.319146503, 2.206220810, -0.566351124, -0.720397392, -0.452001377,
           0.250890097, 0.320685395, -1.014632725, -3.010346273, -1.703955054,
           0.592587381, -1.237451255, 0.172243366, -0.452641122, -0.982148581]

        # c: 60 elem, mean=5, sd=1
        c = [4.654329, 5.242129, 6.272640, 5.781779, 4.391241, 3.800752,
           4.559463, 4.318922, 3.243020, 5.121280, 4.126385, 5.541131,
           4.777480, 5.646913, 6.972584, 3.817172, 6.128700, 4.731467,
           6.762068, 5.082983, 5.298511, 5.491125, 4.532369, 4.265552,
           5.697317, 5.509730, 2.935704, 4.507456, 3.786794, 5.548383,
           3.674487, 5.536556, 5.297847, 2.439642, 4.759836, 5.114649,
           5.986774, 4.517485, 4.579208, 4.579374, 2.502890, 5.190955,
           5.983194, 6.766645, 4.905079, 4.214273, 3.950364, 6.262393,
           8.122084, 6.330007, 4.767943, 5.194029, 3.503136, 6.039079,
           4.485647, 6.116235, 6.302268, 3.596693, 5.743316, 6.860152]

        # d: 30 elem, mean=0, sd =0.05
        d = [0.104517366, 0.023039678, 0.005579091, 0.052928250, 0.020724823,
            -0.060823243, -0.019000890, -0.064133996, -0.016321594, -0.008898334,
            -0.027626992, -0.051946186, 0.085269587, -0.031190678, 0.065172938,
            -0.054628573, 0.019257306, -0.032427056, -0.058767356, 0.030927400,
            0.052247357, -0.042954937, 0.031842104, 0.094130522, -0.024828465,
            0.011320453, -0.016195062, 0.015631245, -0.050335598, -0.031658335]

        a, b, c, d = list(map(array, [a, b, c, d]))
        self.assertEqual(list(map(len, [a, b, c, d])), [50, 50, 60, 30])

        # allowed error. This big, because results from R
        # are rounded at 4 decimals
        error = 1e-4

        self.assertFloatEqual(f_two_sample(a, a), (49, 49, 1, 1), eps=error)
        self.assertFloatEqual(f_two_sample(a, b), (49, 49, 0.8575, 0.5925),
                              eps=error)
        self.assertFloatEqual(f_two_sample(b, a), (49, 49, 1.1662, 0.5925),
                              eps=error)
        self.assertFloatEqual(f_two_sample(a, b, tails='low'),
                              (49, 49, 0.8575, 0.2963), eps=error)
        self.assertFloatEqual(f_two_sample(a, b, tails='high'),
                              (49, 49, 0.8575, 0.7037), eps=error)
        self.assertFloatEqual(f_two_sample(a, c),
                              (49, 59, 0.6587, 0.1345), eps=error)
        # p value very small, so first check df's and F value
        self.assertFloatEqualAbs(f_two_sample(d, a, tails='low')[0:3],
                                 (29, 49, 0.0028), eps=error)
        assert f_two_sample(d, a, tails='low')[3] < 2.2e-16  # p value

    def test_MonteCarloP(self):
        """MonteCarloP calcs a p-value from a val and list of random vals"""
        val = 3.0
        random_vals = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]

        # test for "high" tail (larger values than expected by chance)
        p_val = MonteCarloP(val, random_vals, 'high')
        self.assertEqual(p_val, 0.7)

        # test for "low" tail (smaller values than expected by chance)
        p_val = MonteCarloP(val, random_vals, 'low')
        self.assertEqual(p_val, 0.4)


class MannWhitneyTests(TestCase):
    """check accuracy of Mann-Whitney implementation"""
    x = list(map(int, "104 109 112 114 116 118 118 119 121 123 125 126"
                 " 126 128 128 128".split()))
    y = list(map(int, "100 105 107 107 108 111 116 120 121 123".split()))

    def test_mw_test(self):
        """mann-whitney test results should match Sokal & Rohlf"""
        U, p = mw_test(self.x, self.y)
        self.assertFloatEqual(U, 123.5)
        self.assertTrue(0.02 <= p <= 0.05)

    def test_mw_boot(self):
        """excercising the Monte-carlo variant of mann-whitney"""
        U, p = mw_boot(self.x, self.y, 10)
        self.assertFloatEqual(U, 123.5)
        self.assertTrue(0 <= p <= 0.5)


class KendallTests(TestCase):
    """check accuracy of Kendall tests against values from R"""

    def do_test(self, x, y, alt_expecteds):
        """conducts the tests for each alternate hypothesis against expecteds"""
        for alt, exp_p, exp_tau in alt_expecteds:
            tau, p_val = kendall_correlation(x, y, alt=alt, warn=False)
            self.assertFloatEqual(tau, exp_tau, eps=1e-3)
            self.assertFloatEqual(p_val, exp_p, eps=1e-3)

    def test_exact_calcs(self):
        """calculations of exact probabilities should match R"""
        x = (44.4, 45.9, 41.9, 53.3, 44.7, 44.1, 50.7, 45.2, 60.1)
        y = (2.6, 3.1, 2.5, 5.0, 3.6, 4.0, 5.2, 2.8, 3.8)
        expecteds = [["gt", 0.05972, 0.4444444],
                     ["lt", 0.9624, 0.4444444],
                     ["ts", 0.1194, 0.4444444]]
        self.do_test(x, y, expecteds)

    def test_with_ties(self):
        """tied values calculated from normal approx"""
        # R example with ties in x
        x = (44.4, 45.9, 41.9, 53.3, 44.4, 44.1, 50.7, 45.2, 60.1)
        y = (2.6, 3.1, 2.5, 5.0, 3.6, 4.0, 5.2, 2.8, 3.8)
        expecteds = [  # ["gt", 0.05793, 0.4225771],
                     ["lt", 0.942, 0.4225771],
                     ["ts", 0.1159, 0.4225771]]
        self.do_test(x, y, expecteds)

        # R example with ties in y
        x = (44.4, 45.9, 41.9, 53.3, 44.7, 44.1, 50.7, 45.2, 60.1)
        y = (2.6, 3.1, 2.5, 5.0, 3.1, 4.0, 5.2, 2.8, 3.8)
        expecteds = [["gt", 0.03737, 0.4789207],
                     ["lt", 0.9626, 0.4789207],
                     ["ts", 0.07474, 0.4789207]]
        self.do_test(x, y, expecteds)
        # R example with ties in x and y
        x = (44.4, 45.9, 41.9, 53.3, 44.7, 44.1, 50.7, 44.4, 60.1)
        y = (2.6, 3.6, 2.5, 5.0, 3.6, 4.0, 5.2, 2.8, 3.8)
        expecteds = [["gt", 0.02891, 0.5142857],
                   ["lt", 0.971, 0.5142857],
                   ["ts", 0.05782, 0.5142857]]
        self.do_test(x, y, expecteds)

    def test_bigger_vectors(self):
        """docstring for test_bigger_vectors"""
        # q < expansion
        x = (0.118583104633, 0.227860069338, 0.143856130991, 0.935362617582,
            0.0471303856799, 0.659819202174, 0.739247965907, 0.268929000278,
            0.848250568194, 0.307764819102, 0.733949480141, 0.271662210481,
            0.155903098872)
        y = (0.749762144455, 0.407571703468, 0.934176427266, 0.188638794706,
            0.184844781493, 0.391485553856, 0.735504815302, 0.363655952442,
            0.18489971978, 0.851075466765, 0.139932273818, 0.333675110224,
            0.570250937033)
        expecteds = [["gt", 0.9183, -0.2820513],
                     ["lt", 0.1022, -0.2820513],
                     ["ts", 0.2044, -0.2820513]]
        self.do_test(x, y, expecteds)
        # q > expansion
        x = (0.2602556958, 0.441506392849, 0.930624643531, 0.728461775775,
            0.234341774892, 0.725677256368, 0.354788882728, 0.475882541956,
            0.347533553428, 0.608578046857, 0.144697962102, 0.784502692164,
            0.872607603407)
        y = (0.753056395718, 0.454332072011, 0.791882395707, 0.622853579015,
            0.127030232518, 0.232086215578, 0.586604349918, 0.0139051260749,
            0.579079370051, 0.0550643809812, 0.94798878249, 0.318410679439,
            0.86725134615)
        expecteds = [["gt", 0.4762, 0.02564103],
                     ["lt", 0.5711, 0.02564103],
                     ["ts", 0.9524, 0.02564103]]
        self.do_test(x, y, expecteds)


class TestDistMatrixPermutationTest(TestCase):
    """Tests of distance_matrix_permutation_test"""

    def setUp(self):
        """sets up variables for testing"""
        self.matrix = array([[1, 2, 3, 4], [5, 6, 7, 8], [
                            9, 10, 11, 12], [13, 14, 15, 16]])
        self.cells = [(0, 1), (1, 3)]
        self.cells2 = [(0, 2), (2, 3)]

    def test_get_ltm_cells(self):
        "get_ltm_cells converts indices to be below the diagonal"
        cells = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1),
                  (1, 2), (2, 0), (2, 1), (2, 2)]
        result = get_ltm_cells(cells)
        self.assertEqual(result, [(2, 0), (1, 0), (2, 1)])
        cells = [(0, 1), (0, 2)]
        result = get_ltm_cells(cells)
        self.assertEqual(result, [(2, 0), (1, 0)])

    def test_get_values_from_matrix(self):
        """get_values_from_matrix returns the special and other values from matrix"""
        matrix = self.matrix
        cells = [(1, 0), (0, 1), (2, 0), (2, 1)]
        # test that works for a symmetric matrix
        cells_sym = get_ltm_cells(cells)
        special_vals, other_vals = get_values_from_matrix(matrix, cells_sym,
                                                          cells2=None, is_symmetric=True)
        special_vals.sort()
        other_vals.sort()
        self.assertEqual(special_vals, [5, 9, 10])
        self.assertEqual(other_vals, [13, 14, 15])

        # test that work for a non symmetric matrix
        special_vals, other_vals = get_values_from_matrix(matrix, cells,
                                                          cells2=None, is_symmetric=False)
        special_vals.sort()
        other_vals.sort()
        self.assertEqual(special_vals, [2, 5, 9, 10])
        self.assertEqual(
            other_vals, [1, 3, 4, 6, 7, 8, 11, 12, 13, 14, 15, 16])

        # test that works on a symmetric matrix when cells2 is defined
        cells2 = [(3, 0), (3, 2), (0, 3)]
        cells2_sym = get_ltm_cells(cells2)
        special_vals, other_vals = get_values_from_matrix(matrix, cells_sym,
                                                          cells2=cells2_sym, is_symmetric=True)
        special_vals.sort()
        other_vals.sort()
        self.assertEqual(special_vals, [5, 9, 10])
        self.assertEqual(other_vals, [13, 15])

        # test that works when cells2 is defined and not symmetric
        special_vals, other_vals = get_values_from_matrix(matrix, cells, cells2=cells2,
                                                          is_symmetric=False)
        special_vals.sort()
        other_vals.sort()
        self.assertEqual(special_vals, [2, 5, 9, 10])
        self.assertEqual(other_vals, [4, 13, 15])

    def test_distance_matrix_permutation_test_non_symmetric(self):
        """ evaluate empirical p-values for a non symmetric matrix 

            To test the empirical p-values, we look at a simple 3x3 matrix 
             b/c it is easy to see what t score every permutation will 
             generate -- there's only 6 permutations. 
             Running dist_matrix_test with n=1000, we expect that each 
             permutation will show up 160 times, so we know how many 
             times to expect to see more extreme t scores. We therefore 
             know what the empirical p-values will be. (n=1000 was chosen
             empirically -- smaller values seem to lead to much more frequent
             random failures.)


        """
        def make_result_list(*args, **kwargs):
            return [distance_matrix_permutation_test(*args, **kwargs)[2]
                    for i in range(10)]

        m = arange(9).reshape((3, 3))
        n = 100
        # looks at each possible permutation n times --
        # compare first row to rest
        r = make_result_list(
            m, [(0, 0), (0, 1), (0, 2)], n=n, is_symmetric=False)
        self.assertSimilarMeans(r, 0. / 6.)
        r = make_result_list(m, [(0, 0), (0, 1), (0, 2)], n=n, is_symmetric=False,
                             tails='high')
        self.assertSimilarMeans(r, 4. / 6.)
        r = make_result_list(m, [(0, 0), (0, 1), (0, 2)], n=n, is_symmetric=False,
                             tails='low')
        self.assertSimilarMeans(r, 0. / 6.)

        # looks at each possible permutation n times --
        # compare last row to rest
        r = make_result_list(
            m, [(2, 0), (2, 1), (2, 2)], n=n, is_symmetric=False)
        self.assertSimilarMeans(r, 0. / 6.)
        r = make_result_list(m, [(2, 0), (2, 1), (2, 2)], n=n, is_symmetric=False,
                             tails='high')
        self.assertSimilarMeans(r, 0. / 6.)
        r = make_result_list(m, [(2, 0), (2, 1), (2, 2)], n=n, is_symmetric=False,
                             tails='low')
        self.assertSimilarMeans(r, 4. / 6.)

    def test_distance_matrix_permutation_test_symmetric(self):
        """ evaluate empirical p-values for symmetric matrix

            See test_distance_matrix_permutation_test_non_symmetric 
            doc string for a description of how this test works. 

        """
        def make_result_list(*args, **kwargs):
            return [distance_matrix_permutation_test(*args)[2] for i in range(10)]

        m = array([[0, 1, 3], [1, 2, 4], [3, 4, 5]])
        # looks at each possible permutation n times --
        # compare first row to rest
        n = 100

        # looks at each possible permutation n times --
        # compare first row to rest
        r = make_result_list(m, [(0, 0), (0, 1), (0, 2)], n=n)
        self.assertSimilarMeans(r, 2. / 6.)
        r = make_result_list(m, [(0, 0), (0, 1), (0, 2)], n=n, tails='high')
        self.assertSimilarMeans(r, 0.77281447417149496, 0)
        r = make_result_list(m, [(0, 0), (0, 1), (0, 2)], n=n, tails='low')
        self.assertSimilarMeans(r, 2. / 6.)

        # The following lines are not part of the test code, but are useful in
        # figuring out what t-scores all of the permutations will yield.
        # permutes = [[0, 1, 2], [0, 2, 1], [1, 0, 2],\
        # [1, 2, 0], [2, 0, 1], [2, 1, 0]]
        #results = []
        # for p in permutes:
        #    p_m = permute_2d(m,p)
        #    results.append(t_two_sample(\
        #     [p_m[0,1],p_m[0,2]],[p_m[2,1]],tails='high'))
        # print results

    def test_distance_matrix_permutation_test_alt_stat(self):
        def fake_stat_test(a, b, tails=None):
            return 42., 42.
        m = array([[0, 1, 3], [1, 2, 4], [3, 4, 5]])
        self.assertEqual(distance_matrix_permutation_test(m,
                                                          [(0, 0), (0, 1), (0, 2)], n=5, f=fake_stat_test), (42., 42., 0.))

    def test_distance_matrix_permutation_test_return_scores(self):
        """ return_scores=True functions as expected """
        # use alt statistical test to make results simple
        def fake_stat_test(a, b, tails=None):
            return 42., 42.
        m = array([[0, 1, 3], [1, 2, 4], [3, 4, 5]])
        self.assertEqual(distance_matrix_permutation_test(
            m, [(0, 0), (0, 1), (0, 2)],
            n=5, f=fake_stat_test, return_scores=True), (42., 42., 0., [42.] * 5))

    def test_ANOVA_one_way(self):
        """ANOVA one way returns same values as ANOVA on a stats package
        """
        g1 = Numbers([10.0, 11.0, 10.0, 5.0, 6.0])
        g2 = Numbers([1.0, 2.0, 3.0, 4.0, 1.0, 2.0])
        g3 = Numbers([6.0, 7.0, 5.0, 6.0, 7.0])
        i = [g1, g2, g3]
        dfn, dfd, F, between_MS, within_MS, group_means, prob = ANOVA_one_way(
            i)
        self.assertEqual(dfn, 2)
        self.assertEqual(dfd, 13)
        self.assertFloatEqual(F, 18.565450643776831)
        self.assertFloatEqual(between_MS, 55.458333333333343)
        self.assertFloatEqual(within_MS, 2.9871794871794868)
        self.assertFloatEqual(
            group_means, [8.4000000000000004, 2.1666666666666665, 6.2000000000000002])
        self.assertFloatEqual(prob, 0.00015486238993089464)

# execute tests if called from command line
if __name__ == '__main__':
    main()
