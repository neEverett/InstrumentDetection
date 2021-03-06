# -*- coding: utf-8 -*-
###############################################################
# Code of this file partly originates from: scikit.talkbox
# Author of scikit.talkbox: cournape
# Github: https://github.com/cournape/talkbox
#
# The original code is edited to suit this program
# And a new function to compute △MFCC and △△MFCC is added
###############################################################

import numpy as np

from scipy.fftpack import fft
from scipy.fftpack.realtransforms import dct

def trfbank(fs, nfft, lowfreq, linsc, logsc, nlinfilt, nlogfilt):
    """Compute triangular filterbank for MFCC computation."""
    # Total number of filters
    nfilt = nlinfilt + nlogfilt

    # Compute the filter bank
    # Compute start/middle/end points of the triangular filters in spectral domain
    freqs = np.zeros(nfilt+2)
    freqs[:nlinfilt] = lowfreq + np.arange(nlinfilt) * linsc
    freqs[nlinfilt:] = freqs[nlinfilt-1] * logsc ** np.arange(1, nlogfilt + 3)
    heights = 2./(freqs[2:] - freqs[0:-2])

    # Compute filterbank coeff (in fft domain, in bins)
    fbank = np.zeros((nfilt, nfft))
    # FFT bins (in Hz)
    nfreqs = np.arange(nfft) / (1. * nfft) * fs
    for i in range(nfilt):
        low = freqs[i]
        cen = freqs[i+1]
        hi = freqs[i+2]

        lid = np.arange(np.floor(low * nfft / fs) + 1,
                        np.floor(cen * nfft / fs) + 1, dtype=np.int)
        lslope = heights[i] / (cen - low)
        rid = np.arange(np.floor(cen * nfft / fs) + 1,
                        np.floor(hi * nfft / fs) + 1, dtype=np.int)
        rslope = heights[i] / (hi - cen)
        fbank[i][lid] = lslope * (nfreqs[lid] - low)
        fbank[i][rid] = rslope * (hi - nfreqs[rid])
    return fbank

def delta(ceps):
    """计算差分"""
    #时间差取2 差分参数来自当前帧的前两帧和后两帧的线性组合
    delta = np.zeros(ceps.shape)
    for k in range(ceps.shape[1]):
        c = ceps[:,k]
        tmpdelta = np.zeros(c.shape)
        for i in range(len(c)):
            if (i < 2):
                tmpdelta[i] = c[i+1] - c[i]
            elif (i > len(c)-3):
                tmpdelta[i] = c[i] - c[i-1]
            else:
                tmpdelta[i] = ((c[i+1]-c[i-1])+2*(c[i+2]-c[i-2]))/(10**0.5)
                #Reference:http://www.docin.com/p-893673729.html
        delta[:,k] = tmpdelta

    return delta


def mfcc(f, fs, frameLength, nceps=13):
    nfft = frameLength * 2
    lowfreq = 133.33
    #highfreq = 6855.4976
    linsc = 200/3.
    logsc = 1.0711703
    #三角滤波器组的几个参数

    nlinfil = 13
    nlogfil = 27
    #滤波器的个数

    fbank = trfbank(fs, nfft, lowfreq, linsc, logsc, nlinfil, nlogfil)
    data = np.array([frame.data for frame in f]) #所有帧的内容
    # Compute the spectrum magnitude
    spec = np.abs(fft(data, nfft, axis=-1))
    # Filter the spectrum through the triangle filterbank
    mspec = np.log10(np.dot(spec, fbank.T))
    #由于通过短时能量筛选去除了静音帧，理论上此处不会出现系数为0的情况
    #如果删除了排除静音帧的步骤，有可能会存在0系数导致无法计算，此时可用下方代码替代
    #epsilon = 1e-6
    #mspec = np.log10(np.dot(np.maximum(spec, epsilon), fbank.T))
    # Use the DCT to 'compress' the coefficients (spectrum -> cepstrum domain)
    ceps = dct(mspec, type=2, norm='ortho', axis=-1)[:, 1:nceps]
    # 一般取DCT后的第2个到第13个系数作为MFCC系数

    #计算一阶△MFCC，以反映音频的动态特征
    deltamfcc = delta(ceps)
    ceps = np.concatenate((ceps, deltamfcc), axis=1) #将差分mfcc参数扩展到原ceps后

    #继续计算二阶差分△△MFCC
    deltadeltamfcc = delta(deltamfcc)
    ceps = np.concatenate((ceps, deltadeltamfcc), axis=1)
    return ceps

