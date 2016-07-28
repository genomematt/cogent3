#!/usr/bin/env python
import warnings
warnings.filterwarnings('ignore', 'Not using MPI as mpi4py not found')

import numpy
# hides the warning from taking log of -ve determinant
numpy.seterr(invalid='ignore')

from cogent3.util.unit_test import TestCase, main
from cogent3 import LoadSeqs, DNA, RNA, PROTEIN
from cogent3.evolve.pairwise_distance import get_moltype_index_array, \
    seq_to_indices, _fill_diversity_matrix, \
    _jc69_from_matrix, JC69Pair, _tn93_from_matrix, TN93Pair, LogDetPair, \
    ParalinearPair
from cogent3.evolve._pairwise_distance import \
    _fill_diversity_matrix as pyx_fill_diversity_matrix

__author__ = "Gavin Huttley, Yicheng Zhu and Ben Kaehler"
__copyright__ = "Copyright 2007-2016, The Cogent Project"
__credits__ = ["Gavin Huttley", "Yicheng Zhu", "Ben Kaehler"]
__license__ = "GPL"
__version__ = "3.0.prealpha"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "Production"


class TestPair(TestCase):
    dna_char_indices = get_moltype_index_array(DNA)
    rna_char_indices = get_moltype_index_array(RNA)
    alignment = LoadSeqs(data=[('s1', 'ACGTACGTAC'),
                               ('s2', 'GTGTACGTAC')], moltype=DNA)

    ambig_alignment = LoadSeqs(data=[('s1', 'RACGTACGTACN'),
                                     ('s2', 'AGTGTACGTACA')], moltype=DNA)

    diff_alignment = LoadSeqs(data=[('s1', 'ACGTACGTTT'),
                                    ('s2', 'GTGTACGTAC')], moltype=DNA)

    def test_char_to_index(self):
        """should correctly recode a DNA & RNA seqs into indices"""
        seq = 'TCAGRNY?-'
        expected = [0, 1, 2, 3, -9, -9, -9, -9, -9]
        indices = seq_to_indices(seq, self.dna_char_indices)
        self.assertEqual(indices, expected)
        seq = 'UCAGRNY?-'
        indices = seq_to_indices(seq, self.rna_char_indices)
        self.assertEqual(indices, expected)

    def test_fill_diversity_matrix_all(self):
        """make correct diversity matrix when all chars valid"""
        s1 = seq_to_indices('ACGTACGTAC', self.dna_char_indices)
        s2 = seq_to_indices('GTGTACGTAC', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        # self-self should just be an identity matrix
        _fill_diversity_matrix(matrix, s1, s1)
        self.assertEqual(matrix.sum(), len(s1))
        self.assertEqual(matrix,
                         numpy.array([[2, 0, 0, 0],
                                      [0, 3, 0, 0],
                                      [0, 0, 3, 0],
                                      [0, 0, 0, 2]], float))

        # small diffs
        matrix.fill(0)
        _fill_diversity_matrix(matrix, s1, s2)
        self.assertEqual(matrix,
                         numpy.array([[2, 0, 0, 0],
                                      [1, 2, 0, 0],
                                      [0, 0, 2, 1],
                                      [0, 0, 0, 2]], float))

    def test_fill_diversity_matrix_some(self):
        """make correct diversity matrix when not all chars valid"""
        s1 = seq_to_indices('RACGTACGTACN', self.dna_char_indices)
        s2 = seq_to_indices('AGTGTACGTACA', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        # small diffs
        matrix.fill(0)
        _fill_diversity_matrix(matrix, s1, s2)
        self.assertEqual(matrix,
                         numpy.array([[2, 0, 0, 0],
                                      [1, 2, 0, 0],
                                      [0, 0, 2, 1],
                                      [0, 0, 0, 2]], float))

    def test_python_vs_cython_fill_matrix(self):
        """python & cython fill_diversity_matrix give same answer"""
        s1 = seq_to_indices('RACGTACGTACN', self.dna_char_indices)
        s2 = seq_to_indices('AGTGTACGTACA', self.dna_char_indices)
        matrix1 = numpy.zeros((4, 4), float)
        _fill_diversity_matrix(matrix1, s1, s2)
        matrix2 = numpy.zeros((4, 4), float)
        pyx_fill_diversity_matrix(matrix2, s1, s2)
        self.assertFloatEqual(matrix1, matrix2)

    def test_jc69_from_matrix(self):
        """compute JC69 from diversity matrix"""
        s1 = seq_to_indices('ACGTACGTAC', self.dna_char_indices)
        s2 = seq_to_indices('GTGTACGTAC', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        _fill_diversity_matrix(matrix, s1, s2)
        total, p, dist, var = _jc69_from_matrix(matrix)
        self.assertEqual(total, 10.0)
        self.assertEqual(p, 0.2)

    def test_jc69_from_alignment(self):
        """compute JC69 dists from an alignment"""
        calc = JC69Pair(DNA, alignment=self.alignment)
        calc.run(show_progress=False)
        self.assertEqual(calc.lengths['s1', 's2'], 10)
        self.assertEqual(calc.proportions['s1', 's2'], 0.2)
        # value from OSX MEGA 5
        self.assertFloatEqual(calc.dists['s1', 's2'], 0.2326161962)
        # value**2 from OSX MEGA 5
        self.assertFloatEqual(calc.variances['s1', 's2'],
                              0.029752066125078681)
        # value from OSX MEGA 5
        self.assertFloatEqual(calc.stderr['s1', 's2'], 0.1724878724)

        # same answer when using ambiguous alignment
        calc.run(self.ambig_alignment, show_progress=False)
        self.assertFloatEqual(calc.dists['s1', 's2'], 0.2326161962)

        # but different answer if subsequent alignment is different
        calc.run(self.diff_alignment, show_progress=False)
        self.assertTrue(calc.dists['s1', 's2'] != 0.2326161962)

    def test_tn93_from_matrix(self):
        """compute TN93 distances"""
        calc = TN93Pair(DNA, alignment=self.alignment)
        calc.run(show_progress=False)
        self.assertEqual(calc.lengths['s1', 's2'], 10)
        self.assertEqual(calc.proportions['s1', 's2'], 0.2)
        # value from OSX MEGA 5
        self.assertFloatEqual(calc.dists['s1', 's2'], 0.2554128119)
        # value**2 from OSX MEGA 5
        self.assertFloatEqual(calc.variances['s1', 's2'], 0.04444444445376601)
        # value from OSX MEGA 5
        self.assertFloatEqual(calc.stderr['s1', 's2'], 0.2108185107)

        # same answer when using ambiguous alignment
        calc.run(self.ambig_alignment, show_progress=False)
        self.assertFloatEqual(calc.dists['s1', 's2'], 0.2554128119)

        # but different answer if subsequent alignment is different
        calc.run(self.diff_alignment, show_progress=False)
        self.assertTrue(calc.dists['s1', 's2'] != 0.2554128119)

    def test_distance_pair(self):
        """get distances dict"""
        calc = TN93Pair(DNA, alignment=self.alignment)
        calc.run(show_progress=False)
        dists = calc.get_pairwise_distances()
        dist = 0.2554128119
        expect = {('s1', 's2'): dist, ('s2', 's1'): dist}
        self.assertEqual(list(dists.keys()), list(expect.keys()))
        self.assertFloatEqual(list(dists.values()), list(expect.values()))

    def test_logdet_pair_dna(self):
        """logdet should produce distances that match MEGA"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()
        all_expected = {('Human', 'NineBande'): 0.075336929999999996,
                        ('NineBande', 'DogFaced'): 0.0898575452,
                        ('DogFaced', 'Human'): 0.1061747919,
                        ('HowlerMon', 'DogFaced'): 0.0934480008,
                        ('Mouse', 'HowlerMon'): 0.26422862920000001,
                        ('NineBande', 'Human'): 0.075336929999999996,
                        ('HowlerMon', 'NineBande'): 0.062202897899999998,
                        ('DogFaced', 'NineBande'): 0.0898575452,
                        ('DogFaced', 'HowlerMon'): 0.0934480008,
                        ('Human', 'DogFaced'): 0.1061747919,
                        ('Mouse', 'Human'): 0.26539976700000001,
                        ('NineBande', 'HowlerMon'): 0.062202897899999998,
                        ('HowlerMon', 'Human'): 0.036571181899999999,
                        ('DogFaced', 'Mouse'): 0.2652555144,
                        ('HowlerMon', 'Mouse'): 0.26422862920000001,
                        ('Mouse', 'DogFaced'): 0.2652555144,
                        ('NineBande', 'Mouse'): 0.22754789210000001,
                        ('Mouse', 'NineBande'): 0.22754789210000001,
                        ('Human', 'Mouse'): 0.26539976700000001,
                        ('Human', 'HowlerMon'): 0.036571181899999999}
        for pair in dists:
            got = dists[pair]
            expected = all_expected[pair]
            self.assertFloatEqual(got, expected)

    def test_logdet_tk_adjustment(self):
        """logdet using tamura kumar differs from classic"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        tk = logdet_calc.get_pairwise_distances()
        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        not_tk = logdet_calc.get_pairwise_distances()
        self.assertNotEqual(tk, not_tk)

    def test_logdet_pair_aa(self):
        """logdet shouldn't fail to produce distances for aa seqs"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        aln = aln.get_translation()
        logdet_calc = LogDetPair(moltype=PROTEIN, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()

    def test_logdet_missing_states(self):
        """should calculate logdet measurement with missing states"""
        data = [('seq1', "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2', "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTNTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)

        dists = logdet_calc.get_pairwise_distances()
        self.assertTrue(list(dists.values())[0] is not None)

        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()
        self.assertTrue(list(dists.values())[0] is not None)

    def test_logdet_variance(self):
        """calculate logdet variance consistent with hand calculation"""
        data = [('seq1', "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2', "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        self.assertEqual(logdet_calc.variances[1, 1], None)

        index = dict(list(zip('ACGT', list(range(4)))))
        J = numpy.zeros((4, 4))
        for p in zip(data[0][1], data[1][1]):
            J[index[p[0]], index[p[1]]] += 1
        for i in range(4):
            if J[i, i] == 0:
                J[i, i] += 0.5
        J /= J.sum()
        M = numpy.linalg.inv(J)
        var = 0.
        for i in range(4):
            for j in range(4):
                var += M[j, i]**2 * J[i, j] - 1
        var /= 16 * len(data[0][1])

        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()
        self.assertFloatEqual(logdet_calc.variances[1, 1], var, eps=1e-3)

    def test_logdet_for_determinant_lte_zero(self):
        """returns distance of None if the determinant is <= 0"""
        data = dict(seq1="AGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT",
                    seq2="TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")
        aln = LoadSeqs(data=data, moltype=DNA)

        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()
        self.assertTrue(list(dists.values())[0] is None)
        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()
        self.assertTrue(list(dists.values())[0] is None)

    def test_paralinear_pair_aa(self):
        """paralinear shouldn't fail to produce distances for aa seqs"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        aln = aln.get_translation()
        paralinear_calc = ParalinearPair(moltype=PROTEIN, alignment=aln)
        paralinear_calc.run(show_progress=False)
        dists = paralinear_calc.get_pairwise_distances()

    def test_paralinear_distance(self):
        """calculate paralinear variance consistent with hand calculation"""
        data = [('seq1', "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2', "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)

        index = dict(list(zip('ACGT', list(range(4)))))
        J = numpy.zeros((4, 4))
        for p in zip(data[0][1], data[1][1]):
            J[index[p[0]], index[p[1]]] += 1
        for i in range(4):
            if J[i, i] == 0:
                J[i, i] += 0.5
        J /= J.sum()
        M = numpy.linalg.inv(J)
        f = J.sum(1), J.sum(0)
        dist = -0.25 * numpy.log( numpy.linalg.det(J) /
                                  numpy.sqrt(f[0].prod() * f[1].prod()))

        self.assertFloatEqual(paralinear_calc.dists[1, 1], dist, eps=1e-3)

    def test_paralinear_variance(self):
        """calculate paralinear variance consistent with hand calculation"""
        data = [('seq1', "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2', "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)

        index = dict(list(zip('ACGT', list(range(4)))))
        J = numpy.zeros((4, 4))
        for p in zip(data[0][1], data[1][1]):
            J[index[p[0]], index[p[1]]] += 1
        for i in range(4):
            if J[i, i] == 0:
                J[i, i] += 0.5
        J /= J.sum()
        M = numpy.linalg.inv(J)
        f = J.sum(1), J.sum(0)
        var = 0.
        for i in range(4):
            for j in range(4):
                var += M[j, i]**2 * J[i, j]
            var -= 1 / numpy.sqrt(f[0][i] * f[1][i])
        var /= 16 * len(data[0][1])

        self.assertFloatEqual(paralinear_calc.variances[1, 1], var, eps=1e-3)

    def test_paralinear_for_determinant_lte_zero(self):
        """returns distance of None if the determinant is <= 0"""
        data = dict(seq1="AGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT",
                    seq2="TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")
        aln = LoadSeqs(data=data, moltype=DNA)

        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)
        dists = paralinear_calc.get_pairwise_distances()
        self.assertTrue(list(dists.values())[0] is None)
        paralinear_calc.run(show_progress=False)
        dists = paralinear_calc.get_pairwise_distances()
        self.assertTrue(list(dists.values())[0] is None)

    def test_paralinear_pair_dna(self):
        """calculate paralinear distance consistent with logdet distance"""
        data = [('seq1', 'TAATTCATTGGGACGTCGAATCCGGCAGTCCTGCCGCAAAAGCTTCCGGAATCGAATTTTGGCA'),
                ('seq2', 'AAAAAAAAAAAAAAAACCCCCCCCCCCCCCCCTTTTTTTTTTTTTTTTGGGGGGGGGGGGGGGG')]
        aln = LoadSeqs(data=data, moltype=DNA)
        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(show_progress=False)

        self.assertFloatEqual(logdet_calc.dists[1, 1],
                              paralinear_calc.dists[1, 1], eps=1e-3)
        self.assertFloatEqual(paralinear_calc.variances[1, 1],
                              logdet_calc.variances[1, 1], eps=1e-3)

if __name__ == '__main__':
    main()
