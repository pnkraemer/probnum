# Style Guide for Code Contributions

This style guide summarizes code conventions used in `probnum`. This is intended as a reference for developers. The primary standard that should be applied is [PEP 8](https://www.python.org/dev/peps/pep-0008/).

## Code

### Imports

- `import x` for importing packages and modules.
- `from x import y` where `x` is the package prefix and `y` is the module name with no prefix.
- `from x import y as z` if two modules named `y` are to be imported or if `y` is an inconveniently long name.
- `import y as z` only when `z` is a standard abbreviation (e.g., `np` for `numpy`).

### Naming

- `joined_lower` for functions, methods, attributes, variables
- `joined_lower` or `ALL_CAPS` for constants
- `StudlyCaps` for classes
- `camelCase` only to conform to pre-existing conventions, e.g. in `unittest`

### Other Notational Conventions
- mat vs mtrx


## Documentation

### Docstrings

This package uses the [`numpy` docstring format](https://numpydoc.readthedocs.io/en/latest/format.html#numpydoc-docstring-guide). For probabilistic numerical methods make sure to include the appropriate citations and include examples which can be used as tests via `doctest`. Here is a detailed example of a docstring for a PN method.

```python
def problinsolve(A, b, A0=None, Ainv0=None, x0=None, assume_A="sympos", maxiter=None, atol=10 ** -6, rtol=10 ** -6,
                 callback=None, **kwargs):
    """
    Infer a solution to the linear system :math:`A x = b` in a Bayesian framework.

    Probabilistic linear solvers infer solutions to problems of the form

    ...

    Parameters
    ----------
    A : array-like or LinearOperator, shape=(n,n)
        A square matrix or linear operator.

    ...

    Returns
    -------
    x : RandomVariable, shape=(n,) or (n, nrhs)
        Approximate solution :math:`x` to the linear system. Shape of the return matches the shape of ``b``.

		...

    Raises
    ------
    ValueError
        If size mismatches detected or input matrices are not square.

    Notes
    -----
    For a specific class of priors the probabilistic linear solver recovers the iterates of the conjugate gradient

    ...

    References
    ----------
    .. [1] Wenger, J. and Hennig, P., Probabilistic Linear Solvers for Machine Learning, 2020

    ...

    See Also
    --------
    bayescg : Solve linear systems with prior information on the solution.

    Examples
    --------
    >>> import numpy as np
    >>> np.random.seed(1)
    >>> n = 20
    >>> A = np.random.rand(n, n)
    >>> A = 0.5 * (A + A.T) + 5 * np.eye(n)
    >>> b = np.random.rand(n)
    >>> x, A, Ainv, info = problinsolve(A=A, b=b)
    >>> print(info["iter"])
    10
    """

```

### Example Notebooks

Functionality of `probnum` is explained in detail in the form of `jupyter` notebooks under `/docs/source/notebooks`. These can be added to the documentation by editing `/docs/source/notebooks/examples`.