from __future__ import annotations
import numpy as np


def disaggregate_sector(A, j, alpha, zeta, copy=True):
    """
    Disaggregate sector j in an input-output coefficient matrix A into
    two subsectors:
        j1 = annual grain
        j2 = perennial grain

    Parameters
    ----------
    A : array_like, shape (n, n)
        Technical coefficients matrix.
    j : int
        Index of the sector/column to split.
    alpha : float
        Share of the original sector allocated to the second subsector
        (e.g. perennial grain). Must satisfy 0 <= alpha <= 1.
    zeta : array_like, shape (n,)
        Row-specific relative intensity coefficients, where
            zeta[i] = a[i, j, 2] / a[i, j, 1]
    copy : bool, default True
        If True, work on a copy of A.

    Returns
    -------
    A_new : ndarray, shape (n + 1, n + 1)
        Expanded coefficient matrix with sector j replaced by two sectors.
        The ordering is:
            [0, ..., j-1, j1, j2, j+1, ..., n-1]
    info : dict
        Dictionary containing useful intermediate results:
            - 'a1': first split column
            - 'a2': second split column
            - 'original_column': original A[:, j]
            - 'alpha': alpha
            - 'zeta': zeta

    Notes
    -----
    This function only splits the *column* j, i.e. the input structure
    of the sector. If you also want to split the *row* j (sales/output
    distribution), that requires an additional assumption/system.

    The original row/column j is replaced by two sectors, but the row
    split here is done by simple duplication with proportional allocation:
        row_j1 = (1 - alpha) * row_j
        row_j2 = alpha * row_j
    except for the intersection block, which is filled consistently from
    the split columns.

    In many applications, you may want a more defensible row-splitting rule.
    """
    A = np.array(A, dtype=float, copy=copy)
    n, m = A.shape
    if n != m:
        raise ValueError("A must be a square matrix.")

    if not (0 <= j < n):
        raise IndexError("j is out of bounds.")

    if not (0 <= alpha <= 1):
        raise ValueError("alpha must be between 0 and 1.")

    zeta = np.asarray(zeta, dtype=float)
    if zeta.shape != (n,):
        raise ValueError(f"zeta must have shape ({n},), got {zeta.shape}.")

    if np.any(zeta < 0):
        raise ValueError("All zeta values must be nonnegative.")

    # Original column to split
    a = A[:, j]

    # Denominator for exact identity preservation
    denom = (1 - alpha) + alpha * zeta
    if np.any(denom == 0):
        raise ValueError("Encountered zero denominator in split formula.")

    # Split columns
    a1 = a / denom
    a2 = zeta * a1

    # Build expanded matrix
    A_new = np.zeros((n + 1, n + 1), dtype=float)

    # Indices in new matrix
    # old indices < j stay the same
    # old index j becomes j and j+1
    # old indices > j shift by +1
    def new_index(old_idx):
        if old_idx < j:
            return old_idx
        elif old_idx > j:
            return old_idx + 1
        else:
            raise ValueError("Original split index maps to two positions.")

    # Copy all unaffected cells
    for r in range(n):
        for c in range(n):
            if r == j or c == j:
                continue
            rr = new_index(r)
            cc = new_index(c)
            A_new[rr, cc] = A[r, c]

    # Split the target column j into j and j+1
    for r in range(n):
        rr = r if r < j else r + 1
        if r == j:
            # handled below in 2x2 block
            continue
        A_new[rr, j] = a1[r]
        A_new[rr, j + 1] = a2[r]

    # Split the target row j proportionally
    row = A[j, :]
    for c in range(n):
        if c == j:
            continue
        cc = c if c < j else c + 1
        A_new[j, cc] = (1 - alpha) * row[c]
        A_new[j + 1, cc] = alpha * row[c]

    # Fill the 2x2 intersection block consistently
    # Original self-coefficient A[j, j] is split using same rule
    a_jj = A[j, j]
    denom_j = (1 - alpha) + alpha * zeta[j]
    a1_j = a_jj / denom_j
    a2_j = zeta[j] * a1_j

    # Allocate self/input relations proportionally by output shares
    A_new[j, j] = (1 - alpha) * a1_j
    A_new[j + 1, j] = alpha * a1_j
    A_new[j, j + 1] = (1 - alpha) * a2_j
    A_new[j + 1, j + 1] = alpha * a2_j

    info = {
        "a1": a1,
        "a2": a2,
        "original_column": a,
        "alpha": alpha,
        "zeta": zeta,
    }

    return A_new, info