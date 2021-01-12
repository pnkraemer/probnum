"""General Gaussian filters based on approximating intractable quantities with numerical
quadrature.

Examples include the unscented Kalman filter / RTS smoother which is
based on a third degree fully symmetric rule.
"""

import numpy as np

from probnum.filtsmooth import statespace
from probnum.filtsmooth.gaussfiltsmooth import unscentedtransform as ut
from probnum.random_variables import Normal


class ContinuousUKFComponent(statespace.SDE):
    """Continuous unscented Kalman filter transition."""

    def __init__(
        self, non_linear_sde, dimension, spread=1e-4, priorpar=2.0, special_scale=0.0
    ):
        if not isinstance(non_linear_sde, statespace.SDE):
            raise TypeError("cont_model must be an SDE.")
        self.non_linear_sde = non_linear_sde
        self.ut = ut.UnscentedTransform(dimension, spread, priorpar, special_scale)

        # Discrete UKF is a subclass of DiscreteGaussian, so this choice of inheritance is for consistency
        super().__init__(
            driftfun=self.non_linear_sde.driftfun,
            dispmatfun=self.non_linear_sde.dispmatfun,
            jacobfun=self.non_linear_sde.jacobfun,
        )

        raise NotImplementedError("Implementation incomplete.")

    def transition_realization(self, real, start, stop, linearise_at=None, **kwargs):
        raise NotImplementedError("TODO")  # Issue  #234

    def transition_rv(self, rv, start, stop, linearise_at=None, **kwargs):
        raise NotImplementedError("TODO")  # Issue  #234

    @property
    def dimension(self):
        raise NotImplementedError


class DiscreteUKFComponent(statespace.DiscreteGaussian):
    """Discrete extended Kalman filter transition."""

    def __init__(
        self, disc_model, dimension, spread=1.0, priorpar=2.0, special_scale=0.0
    ):
        self.disc_model = disc_model
        self.ut = ut.UnscentedTransform(dimension, spread, priorpar, special_scale)

        # This inheritance enables things like "diffmatfun_cholesky"
        super().__init__(
            dynamicsfun=self.disc_model.dynamicsfun,
            diffmatfun=self.disc_model.dynamicsfun,
            jacobfun=self.disc_model.jacobfun,
        )

    def transition_realization(self, real, start, **kwargs):
        return self.disc_model.transition_realization(real, start, **kwargs)

    def transition_rv(self, rv, start, linearise_at=None, **kwargs):
        compute_sigmapts_at = linearise_at if linearise_at is not None else rv
        sigmapts = self.ut.sigma_points(
            compute_sigmapts_at.mean, compute_sigmapts_at.cov
        )
        proppts = self.ut.propagate(start, sigmapts, self.disc_model.dynamicsfun)
        meascov = self.disc_model.diffmatfun(start)
        mean, cov, crosscov = self.ut.estimate_statistics(
            proppts, sigmapts, meascov, rv.mean
        )
        return Normal(mean, cov), {"crosscov": crosscov}

    @property
    def dimension(self):
        return self.ut.dimension

    @classmethod
    def from_ode(cls, ode, prior, evlvar):

        spatialdim = prior.spatialdim
        h0 = prior.proj2coord(coord=0)
        h1 = prior.proj2coord(coord=1)

        def dyna(t, x):
            return h1 @ x - ode.rhs(t, h0 @ x)

        def diff(t):
            return evlvar * np.eye(spatialdim)

        disc_model = statespace.DiscreteGaussian(dyna, diff)
        return cls(disc_model, dimension=prior.dimension)
