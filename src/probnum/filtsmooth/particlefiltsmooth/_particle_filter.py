"""Particle filters."""

import abc
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from probnum import random_variables, statespace
from probnum.filtsmooth.bayesfiltsmooth import BayesFiltSmooth
from probnum.filtsmooth.filtsmoothposterior import FiltSmoothPosterior
from probnum.type import FloatArgType, IntArgType

from ..gaussfiltsmooth import (
    DiscreteEKFComponent,
    DiscreteUKFComponent,
    IteratedDiscreteComponent,
)
from ._particle_filter_posterior import ParticleFilterPosterior


def effective_number_of_events(categ_rv: random_variables.Categorical) -> float:
    """Effective number of events in the support of a categorical random variable.

    In a particle filter, this is used as the effective number of
    particles.
    """
    return 1.0 / np.sum(categ_rv.event_probabilities ** 2)


def resample_categorical(
    categ_rv: random_variables.Categorical,
) -> random_variables.Categorical:
    """Resample a categorical random variable."""
    num_particles = len(categ_rv.support)
    new_support = categ_rv.sample(size=num_particles)
    new_event_probs = np.ones(categ_rv.event_probabilities.shape) / len(
        categ_rv.event_probabilities
    )
    return random_variables.Categorical(
        support=new_support,
        event_probabilities=new_event_probs,
        random_state=categ_rv.random_state,
    )


class ParticleFilter(BayesFiltSmooth):
    r"""Particle filter (PF). Also known as sequential Monte Carlo method.

    A PF estimates the posterior distribution of a Markov process given noisy, non-linear observations,
    with a set of particles.

    Parameters
    ----------
    dynamics_model :
        Prior dynamics. Since the PF is essentially a discrete-time algorithm,
        the prior must be a discrete model (or at least one with an equivalent discretisation).
        This transition must support `forward_realization`.
    measurement_model :
        Measurement model. Must be a discrete model that supports `forward_realization`.
    initrv :
        Initial random variable. Can be any `RandomVariable` object that implements `sample()`.
    num_particles :
        Number of particles to use.
    linearized_measurement_model :
        Linearized measurement model that is used as an importance density. In principle,
        any discrete-time model that supports `backward_realization` is applicable.
        In practice, it will almost always be one out of `DiscreteEKFComponent`, `DiscreteUKFComponent`,
        or `IteratedDiscreteComponent`. Linear components are also possible, but would most often imply
        that a particle filter is not required, because the filtering problem can be used much faster
        with a Kalman filter. The exception to this rule is if the initial random variable is not Gaussian.
        Optional. Default is None, which implies the bootstrap PF.
    with_resampling :
        Whether after each step the effective number of particles shall be checked, and, if too low,
        the state should be resampled. Optional. Default is `True`.
    resampling_percentage_threshold :
        Percentage threshold for resampling. That is, it is the value :math:`p` such that
        resampling is performed if :math:`N_{\text{eff}} < p \, N_\text{particles}` holds.
    """

    def __init__(
        self,
        dynamics_model: Union[statespace.LTISDE, statespace.DiscreteGaussian],
        measurement_model: statespace.DiscreteGaussian,
        initrv: random_variables.RandomVariable,
        num_particles: IntArgType,
        linearized_measurement_model: Optional[statespace.DiscreteGaussian] = None,
        with_resampling: bool = True,
        resampling_percentage_threshold: FloatArgType = 0.1,
    ) -> None:
        self.dynamics_model = dynamics_model
        self.measurement_model = measurement_model
        self.initrv = initrv
        self.num_particles = num_particles

        self.with_resampling = with_resampling
        self.resampling_percentage_threshold = resampling_percentage_threshold
        self.min_effictive_num_of_particles = (
            resampling_percentage_threshold * num_particles
        )

        # If None, the dynamics model is used as a fallback option
        # which results in the bootstrap PF.
        # Any linearised measurement model that could be used in a
        # Gaussian filter can be used here and will likely be a better choice.
        self.linearized_measurement_model = linearized_measurement_model

    def filter(self, dataset, times, _previous_posterior=None):

        # Initialize:
        particles = []
        weights = []
        for idx in range(self.num_particles):

            dynamics_rv = self.initrv
            proposal_state, proposal_weight = self.compute_new_particle(
                dataset[0], times[0], dynamics_rv
            )
            particles.append(proposal_state)
            weights.append(proposal_weight)

        weights = weights / np.sum(weights)
        curr_rv = random_variables.Categorical(
            support=np.array(particles), event_probabilities=weights
        )
        rvs = [curr_rv]

        for idx in range(1, len(times)):
            curr_rv, _ = self.filter_step(
                start=times[idx - 1],
                stop=times[idx],
                randvar=curr_rv,
                data=dataset[idx],
            )
            rvs.append(curr_rv)
        return ParticleFilterPosterior(rvs, times)

    def filter_step(self, start, stop, randvar, data):
        """Perform a particle filter step.

        It consists of the following steps:
        1. Propagating the "past" particles through the dynamics model.
        2. Computing a "proposal" random variable.
        This is either the prior dynamics model or the output of a filter step
        of an (approximate) Gaussian filter.
        3. Sample from the proposal random variable. This is the "new" particle.
        4. Propagate the particle through the measurement model.
        This is required in order to require the PDF of the resulting RV at
        the data. If this is small, the weight of the particle will be small.
        5. Compute weights ("event probabilities") of the new particle.
        This requires evaluating the PDFs of all three RVs (dynamics, proposal, measurement).

        After this is done for all particles, the weights are normalized in order to sum to 1.
        """
        new_weights = randvar.event_probabilities.copy()
        new_support = randvar.support.copy()

        for idx, (particle, weight) in enumerate(zip(new_support, new_weights)):

            dynamics_rv, _ = self.dynamics_model.forward_realization(
                particle, t=start, dt=(stop - start)
            )

            proposal_state, proposal_weight = self.compute_new_particle(
                data, stop, dynamics_rv
            )

            new_support[idx] = proposal_state
            new_weights[idx] = proposal_weight

        new_weights = new_weights / np.sum(new_weights)
        new_rv = random_variables.Categorical(
            support=new_support, event_probabilities=new_weights
        )

        if self.with_resampling:
            if effective_number_of_events(new_rv) < self.min_effictive_num_of_particles:
                new_rv = resample_categorical(new_rv)

        return new_rv, {}

    def compute_new_particle(self, data, stop, dynamics_rv):
        """Compute a new particle."""
        proposal_rv = self.dynamics_to_proposal_rv(dynamics_rv, data=data, t=stop)
        proposal_state = proposal_rv.sample()
        meas_rv, _ = self.measurement_model.forward_realization(proposal_state, t=stop)
        proposal_weight = (
            meas_rv.pdf(data)
            * dynamics_rv.pdf(proposal_state)
            / proposal_rv.pdf(proposal_state)
        )
        return proposal_state, proposal_weight

    def dynamics_to_proposal_rv(self, dynamics_rv, data, t):
        """Turn a dynamics RV into a proposal RV.

        The output of this function depends on the choice of PF. For the
        bootstrap PF, nothing happens. For other PFs, the importance
        density is used to improve the proposal. Currently, only
        approximate Gaussian importance densities are provided.
        """
        proposal_rv = dynamics_rv
        if self.linearized_measurement_model is not None:
            proposal_rv, _ = self.linearized_measurement_model.backward_realization(
                data, proposal_rv, t=t
            )
        return proposal_rv