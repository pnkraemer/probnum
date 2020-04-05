"""
Kalman filtering for continuous-discrete and discrete-discrete state
space models.

Potential refactoring
---------------------
Replicate factory pattern of Normal()
to create consistency in the codebase.
"""
import numpy as np

from probnum.filtsmooth.gaussfiltsmooth import gaussianfilter
from probnum.prob import RandomVariable
from probnum.prob.distributions import Normal
from probnum.filtsmooth.statespace.continuous.linearsdemodel import *
from probnum.filtsmooth.statespace.discrete.discretegaussianmodel import *


__all__ = ["KalmanFilter"]

class KalmanFilter(gaussianfilter.GaussianFilter):
    """
    """

    def __init__(self, dynamod, measmod, initrv, _nsteps=5):
        """
        """
        if _is_not_linear(dynamod):
            raise TypeError("Kalman filter doesn't support dynamic model")
        if not issubclass(type(measmod), DiscreteGaussianModel):
            raise TypeError("Kalman filter doesn't support measurement model")
        if not issubclass(type(initrv.distribution), Normal):
            raise TypeError("Kalman filter doesn't support"
                            "initial distribution")
        self.dynamod = dynamod
        self.measmod = measmod
        self.initdist = initrv
        self._nsteps = _nsteps

    @property
    def dynamicmodel(self):
        """ """
        return self.dynamod

    @property
    def measurementmodel(self):
        """ """
        return self.measmod

    @property
    def initialdistribution(self):
        """ """
        return self.initdist

    def predict(self, start, stop, randvar, *args, **kwargs):
        """
        """
        if _is_discrete(self.dynamod):
            return self._predict_discrete(start, randvar, *args, **kwargs)
        else:
            return self._predict_continuous(start, stop, randvar, *args,
                                            **kwargs)

    def _predict_discrete(self, start, randvar, *args, **kwargs):
        """
        "Stop" is ignored in the discrete case.
        """
        mean, covar = randvar.mean(), randvar.cov()
        if np.isscalar(mean) and np.isscalar(covar):
            mean, covar = mean * np.ones(1), covar * np.eye(1)
        dynamat = self.dynamod.dynamicsmatrix(start, *args, **kwargs)
        forcevec = self.dynamod.force(start, *args, **kwargs)
        diffmat = self.dynamod.diffusionmatrix(start, *args, **kwargs)
        mpred = dynamat @ mean + forcevec
        cpred = dynamat @ covar @ dynamat.T + diffmat
        return RandomVariable(distribution=Normal(mpred, cpred))

    def _predict_continuous(self, start, stop, randvar, *args, **kwargs):
        """
        The cont. models that are allowed here all have an
        implementation of chapman-kolmogorov.
        """
        step = ((stop - start) / self._nsteps)
        return self.dynamicmodel.chapmankolmogorov(start, stop, step, randvar,
                                                   *args, **kwargs)

    def update(self, time, randvar, data, *args, **kwargs):
        """
        Only discrete measurement models reach this point.

        Hence, the update is straightforward.
        """
        return self._update_discrete(time, randvar, data, *args, **kwargs)

    def _update_discrete(self, time, randvar, data, *args, **kwargs):
        """
        Kalman gain: ccest @ inv(covest)

        Returns 12a - 12c in Tronarp et al. in that order!
        """
        mpred, cpred = randvar.mean(), randvar.cov()
        if np.isscalar(mpred) and np.isscalar(cpred):
            mpred, cpred = mpred * np.ones(1), cpred * np.eye(1)
        measmat = self.measurementmodel.dynamicsmatrix(time, *args, **kwargs)
        meascov = self.measurementmodel.diffusionmatrix(time, *args, **kwargs)
        meanest = measmat @ mpred
        covest = measmat @ cpred @ measmat.T + meascov
        ccest = cpred @ measmat.T
        mean = mpred + ccest @ np.linalg.solve(covest, data - meanest)
        cov = cpred - ccest @ np.linalg.solve(covest.T, ccest.T)
        return RandomVariable(distribution=Normal(mean, cov)), covest, ccest, meanest


def _is_discrete(model):
    """
    Checks whether the underlying model is discrete.
    Used in determining whether to use discrete or
    continuous KF update.
    """
    return issubclass(type(model), DiscreteGaussianModel)


def _is_not_linear(model):
    """
    If model is neither discrete Gaussian or continuous linear,
    it returns false.
    """
    if issubclass(type(model), LinearSDEModel):
        return False
    elif issubclass(type(model), DiscreteGaussianLinearModel):
        return False
    return True