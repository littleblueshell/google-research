# coding=utf-8
# Copyright 2019 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf-8 -*-
"""so8_supergravity.ipynb

Automatically generated by Colaboratory.

Copyright 2019 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools
import numpy
import tensorflow as tf
from tensorflow.contrib import opt as contrib_opt


### Lie Algebra definitions for Spin(8), SU(8), E7.

def permutation_sign(p):
  q = [x for x in p]  # Copy to list.
  parity = 1
  for n in range(len(p)):
    while n != q[n]:
      qn = q[n]
      q[n], q[qn] = q[qn], q[n]  # Swap to make q[qn] = qn.
      parity = -parity
  return parity


class Spin8(object):
  """Container class for Spin(8) tensor invariants."""

  def __init__(self):
    r8 = range(8)
    self.gamma_vsc = gamma_vsc = self._get_gamma_vsc()
    #
    # The gamma^{ab}_{alpha beta} tensor that translates between antisymmetric
    # matrices over vectors [ij] and antisymmetric matrices over spinors [sS].
    # (These expressions could be shortened, but we want to keep
    # symmetric-looking formulas.)
    self.gamma_vvss = 0.5 * (
        numpy.einsum('isc,jSc->ijsS', gamma_vsc, gamma_vsc) -
        numpy.einsum('jsc,iSc->ijsS', gamma_vsc, gamma_vsc))
    # The gamma^{ab}_{alpha* beta*} tensor that translates between antisymmetric
    # matrices over vectors [ij] and antisymmetric matrices over cospinors [cC].
    self.gamma_vvcc = 0.5 * (
        numpy.einsum('isc,jsC->ijcC', gamma_vsc, gamma_vsc) -
        numpy.einsum('jsc,isC->ijcC', gamma_vsc, gamma_vsc))
    #
    # The gamma^{ijkl}_{alpha beta} tensor that translates between antisymmetric
    # 4-forms [ijkl] and symmetric traceless matrices over the spinors (sS).
    g_ijsS = numpy.einsum('isc,jSc->ijsS', self.gamma_vsc, self.gamma_vsc)
    g_ijcC = numpy.einsum('isc,jsC->ijcC', self.gamma_vsc, self.gamma_vsc)
    g_ijklsS = numpy.einsum('ijst,kltS->ijklsS', g_ijsS, g_ijsS)
    g_ijklcC = numpy.einsum('ijcd,kldC->ijklcC', g_ijcC, g_ijcC)
    gamma_vvvvss = numpy.zeros([8] * 6)
    gamma_vvvvcc = numpy.zeros([8] * 6)
    for perm in itertools.permutations(range(4)):
      perm_ijkl = ''.join('ijkl'[p] for p in perm)
      sign = permutation_sign(perm)
      gamma_vvvvss += sign * numpy.einsum(perm_ijkl + 'sS->ijklsS', g_ijklsS)
      gamma_vvvvcc += sign * numpy.einsum(perm_ijkl + 'cC->ijklcC', g_ijklcC)
    self.gamma_vvvvss = gamma_vvvvss / 24.0
    self.gamma_vvvvcc = gamma_vvvvcc / 24.0

  def _get_gamma_vsc(self):
    """Computes SO(8) gamma-matrices."""
    # Conventions match Green, Schwarz, Witten's, but with index-counting
    # starting at zero.
    entries = (
        "007+ 016- 025- 034+ 043- 052+ 061+ 070- "
        "101+ 110- 123- 132+ 145+ 154- 167- 176+ "
        "204+ 215- 226+ 237- 240- 251+ 262- 273+ "
        "302+ 313+ 320- 331- 346- 357- 364+ 375+ "
        "403+ 412- 421+ 430- 447+ 456- 465+ 474- "
        "505+ 514+ 527+ 536+ 541- 550- 563- 572- "
        "606+ 617+ 624- 635- 642+ 653+ 660- 671- "
        "700+ 711+ 722+ 733+ 744+ 755+ 766+ 777+")
    ret = numpy.zeros([8, 8, 8])
    for ijkc in entries.split():
      ijk = tuple(map(int, ijkc[:-1]))
      ret[ijk] = +1 if ijkc[-1] == '+' else -1
    return ret


class SU8(object):
  """Container class for su(8) tensor invariants."""

  def __init__(self):
    # Tensor that translates between adjoint indices 'a' and
    # (vector) x (vector) indices 'ij'
    ij_map = [(i, j) for i in range(8) for j in range(8) if i < j]
    #
    # We also need the mapping between 8 x 8 and 35 representations, using
    # common conventions for a basis of the 35-representation, and likewise
    # for 8 x 8 and 28.
    m_35_8_8 = numpy.zeros([35, 8, 8], dtype=numpy.complex128)
    m_28_8_8 = numpy.zeros([28, 8, 8], dtype=numpy.complex128)
    for n in range(7):
      m_35_8_8[n, n, n] = +1.0
      m_35_8_8[n, n + 1, n + 1] = -1.0
    for a, (m, n) in enumerate(ij_map):
      m_35_8_8[a + 7, m, n] = m_35_8_8[a + 7, n, m] = 1.0
      m_28_8_8[a, m, n] = 1.0
      m_28_8_8[a, n, m] = -1.0
    #
    # The su8 'Generator Matrices'.
    t_aij = numpy.zeros([63, 8, 8], dtype=numpy.complex128)
    t_aij[:35, :, :] = 1.0j * m_35_8_8
    for a, (i, j) in enumerate(ij_map):
      t_aij[a + 35, i, j] = -1.0
      t_aij[a + 35, j, i] = 1.0
    self.ij_map = ij_map
    self.m_35_8_8 = m_35_8_8
    self.m_28_8_8 = m_28_8_8
    self.t_aij = t_aij


class E7(object):
  """Container class for e7 tensor invariants."""

  def __init__(self, spin8, su8):
    self._spin8 = spin8
    self._su8 = su8
    ij_map = su8.ij_map
    t_a_ij_kl = numpy.zeros([133, 56, 56], dtype=numpy.complex128)
    for a in range(35):
      # In order to speed up initialization, we are splitting X x Y x Z
      # tensor products, which numpy.einsum() would compute without generating
      # intermediate products, into sequences of X x Y tensor products.
      t_a_ij_kl[:35, 28:, :28] = (1 / 8.0) * (
          numpy.einsum('qIkl,Kkl->qIK',
                       numpy.einsum(
                           'ijklq,Iij->qIkl',
                           numpy.einsum('ijklsS,qsS->ijklq',
                                        spin8.gamma_vvvvss, su8.m_35_8_8),
                           su8.m_28_8_8),
                       su8.m_28_8_8))
      t_a_ij_kl[:35, :28, 28:] = (1 / 8.0) * (
          numpy.einsum('qIkl,Kkl->qIK',
                       numpy.einsum(
                           'ijklq,Iij->qIkl',
                           numpy.einsum('ijklsS,qsS->ijklq',
                                        spin8.gamma_vvvvss, su8.m_35_8_8),
                           su8.m_28_8_8),
                       su8.m_28_8_8))
      #
      t_a_ij_kl[35:70, 28:, :28] = (1.0j / 8.0) * (
          numpy.einsum('qIkl,Kkl->qIK',
                       numpy.einsum(
                           'ijklq,Iij->qIkl',
                           numpy.einsum('ijklcC,qcC->ijklq',
                                        spin8.gamma_vvvvcc, su8.m_35_8_8),
                           su8.m_28_8_8),
                       su8.m_28_8_8))
      t_a_ij_kl[35:70, :28, 28:] = (-1.0j / 8.0) * (
          numpy.einsum('qIkl,Kkl->qIK',
                       numpy.einsum(
                           'ijklq,Iij->qIkl',
                           numpy.einsum('ijklcC,qcC->ijklq',
                                        spin8.gamma_vvvvcc, su8.m_35_8_8),
                           su8.m_28_8_8),
                       su8.m_28_8_8))
      #
      # We need to find the action of the su(8) algebra on the
      # 28-representation.
      su8_28 = 2 * (
          numpy.einsum(
              'aIjn,Jjn->aIJ',
              numpy.einsum(
                  'aimjn,Iim->aIjn',
                  numpy.einsum(
                      'aij,mn->aimjn',
                      su8.t_aij,
                      numpy.eye(8, dtype=numpy.complex128)),
                  su8.m_28_8_8),
              su8.m_28_8_8))
      t_a_ij_kl[70:, :28, :28] = su8_28
      t_a_ij_kl[70:, 28:, 28:] = su8_28.conjugate()
      self.t_a_ij_kl = t_a_ij_kl


spin8 = Spin8()
su8 = SU8()
e7 = E7(spin8, su8)

def get_proj_35_8888(want_selfdual=True):
  """Computes the (35, 8, 8, 8, 8)-projector to the (anti)self-dual 4-forms."""
  # We first need some basis for the 35 self-dual 4-forms.
  # Our convention is that we lexicographically list those 8-choose-4
  # combinations that contain the index 0.
  sign_selfdual = 1 if want_selfdual else -1
  ret = numpy.zeros([35, 8, 8, 8, 8], dtype=numpy.float64)
  #
  def get_selfdual(ijkl):
    mnpq = tuple(n for n in range(8) if n not in ijkl)
    return (sign_selfdual * permutation_sign(ijkl + mnpq),
            ijkl, mnpq)
  selfduals = [get_selfdual(ijkl)
               for ijkl in itertools.combinations(range(8), 4)
               if 0 in ijkl]
  for num_sd, (sign_sd, ijkl, mnpq) in enumerate(selfduals):
    for abcd in itertools.permutations(range(4)):
      sign_abcd = permutation_sign(abcd)
      ret[num_sd,
          ijkl[abcd[0]],
          ijkl[abcd[1]],
          ijkl[abcd[2]],
          ijkl[abcd[3]]] = sign_abcd
      ret[num_sd,
          mnpq[abcd[0]],
          mnpq[abcd[1]],
          mnpq[abcd[2]],
          mnpq[abcd[3]]] = sign_abcd * sign_sd
  return ret / 24.0


### Supergravity.

def tf_so8_sugra_stationarity(t_a1, t_a2):
  """Computes the stationarity-condition tensor."""
  # See: https://arxiv.org/pdf/1302.6219.pdf, text after (3.2).
  t_x0 = (
      +4.0 * tf.einsum('mi,mjkl->ijkl', t_a1, t_a2)
      -3.0 * tf.einsum('mnij,nklm->ijkl', t_a2, t_a2))
  t_x0_real = tf.real(t_x0)
  t_x0_imag = tf.imag(t_x0)
  tc_sd = tf.constant(get_proj_35_8888(True))
  tc_asd = tf.constant(get_proj_35_8888(False))
  t_x_real_sd = tf.einsum('aijkl,ijkl->a', tc_sd, t_x0_real)
  t_x_imag_asd = tf.einsum('aijkl,ijkl->a', tc_asd, t_x0_imag)
  return (tf.einsum('a,a->', t_x_real_sd, t_x_real_sd) +
          tf.einsum('a,a->', t_x_imag_asd, t_x_imag_asd))


def tf_so8_sugra_potential(t_v70):
  """Returns dict with key tensors from the SUGRA potential's TF graph."""
  tc_28_8_8 = tf.constant(su8.m_28_8_8)
  t_e7_generator_v70 = tf.einsum(
      'v,vIJ->JI',
      tf.complex(t_v70, tf.constant([0.0] * 70, dtype=tf.float64)),
      tf.constant(e7.t_a_ij_kl[:70, :, :], dtype=tf.complex128))
  t_complex_vielbein = tf.linalg.expm(t_e7_generator_v70)
  def expand_ijkl(t_ab):
    return 0.5 * tf.einsum(
        'ijB,BIJ->ijIJ',
        tf.einsum('AB,Aij->ijB', t_ab, tc_28_8_8),
        tc_28_8_8)
  #
  t_u_ijIJ = expand_ijkl(t_complex_vielbein[:28, :28])
  t_u_klKL = expand_ijkl(t_complex_vielbein[28:, 28:])
  t_v_ijKL = expand_ijkl(t_complex_vielbein[:28, 28:])
  t_v_klIJ = expand_ijkl(t_complex_vielbein[28:, :28])
  #
  t_uv = t_u_klKL + t_v_klIJ
  t_uuvv = (tf.einsum('lmJK,kmKI->lkIJ', t_u_ijIJ, t_u_klKL) -
            tf.einsum('lmJK,kmKI->lkIJ', t_v_ijKL, t_v_klIJ))
  t_T = tf.einsum('ijIJ,lkIJ->lkij', t_uv, t_uuvv)
  t_A1 = (-4.0 / 21.0) * tf.trace(tf.einsum('mijn->ijmn', t_T))
  t_A2 = (-4.0 / (3 * 3)) * (
      # Antisymmetrize in last 3 indices, taking into account antisymmetry
      # in last two indices.
      t_T
      + tf.einsum('lijk->ljki', t_T)
      + tf.einsum('lijk->lkij', t_T))
  t_A1_real = tf.real(t_A1)
  t_A1_imag = tf.imag(t_A1)
  t_A2_real = tf.real(t_A2)
  t_A2_imag = tf.imag(t_A2)
  t_A1_potential = (-3.0 / 4) * (
      tf.einsum('ij,ij->', t_A1_real, t_A1_real) +
      tf.einsum('ij,ij->', t_A1_imag, t_A1_imag))
  t_A2_potential = (1.0 / 24) * (
      tf.einsum('ijkl,ijkl->', t_A2_real, t_A2_real) +
      tf.einsum('ijkl,ijkl->', t_A2_imag, t_A2_imag))
  t_potential = t_A1_potential + t_A2_potential
  #
  return dict(v70=t_v70,
              vielbein=t_complex_vielbein,
              tee_tensor=t_T,
              a1=t_A1,
              a2=t_A2,
              potential=t_potential)


def call_with_critical_point_scanner(f, *args):
  """Calls f(scanner, *args) in TensorFlow session-context.

  Here, `scanner` will be a function with signature
  scanner(seed:int, scale:float) -> (potential, stationarity, pos_vector).

  The function `scanner` can only perform a scan when called from within
  the TF session-context that is set up by this function.
  """
  graph = tf.Graph()
  with graph.as_default():
    t_input = tf.placeholder(tf.float64, shape=[70])
    t_v70 = tf.Variable(initial_value=numpy.zeros([70]),
                        trainable=True,
                        dtype=tf.float64)
    op_assign_input = tf.assign(t_v70, t_input)
    d = tf_so8_sugra_potential(t_v70)
    t_potential = d['potential']
    t_stationarity = tf_so8_sugra_stationarity(d['a1'], d['a2'])
    opt = contrib_opt.ScipyOptimizerInterface(
        tf.asinh(t_stationarity), options=dict(maxiter=500))
    with tf.Session() as sess:
      sess.run([tf.global_variables_initializer()])
      def scanner(seed, scale):
        rng = numpy.random.RandomState(seed)
        v70 = rng.normal(scale=scale, size=[70])
        sess.run([op_assign_input], feed_dict={t_input: v70})
        opt.minimize(session=sess)
        n_ret = sess.run([t_potential, t_stationarity, t_v70])
        return n_ret
      return f(scanner, *args)


### Demo. Scans for 20 critical points.


def scan_many(scanner, num_to_produce):
  ret = []
  seed = 0
  while len(ret) < num_to_produce:
    seed += 1
    scanned = scanner(seed, scale=2.0)
    potential, stationarity, v70 = scanned
    if stationarity < 1e-3:
      ret.append(scanned)
      print('%3d / %3d: V=%.6f stationarity=%.3g' % (
          len(ret), num_to_produce, potential, stationarity))
  return ret


scanned = call_with_critical_point_scanner(scan_many, 20)
