# rampr - regionalize workflow

This package takes national input-output data and employment data and produces regionalized IO matrices for any US county. It does this in four steps: KJC output estimation, missing employment imputation, location quotient computation, and regionalization.

---

## 1. KJC — Kendrick-Jaycox Regional Output (`kjc.py`)

The Kendrick-Jaycox method estimates how much of a national industry's output belongs to a given region, using employment as the allocation key.

**What it does:** Given national output $X_i^n$ for industry $i$ and employment data, it estimates regional output $X_i^r$ for a county.

$$s_i^r = \frac{E_i^r}{E_i^n} \quad \text{(regional employment share of industry } i \text{)}$$

$$X_i^r = s_i^r \times X_i^n \quad \text{(regional output)}$$

**Assumptions:**
- Regional output is proportional to regional employment share
- Employment is a reasonable proxy for output when direct output data is unavailable
- Shares are bounded: $0 \leq s_i^r \leq 1$ and $\sum_r s_i^r \leq 1$

---

## 2. KJC Imputation — Filling Missing Regional Output (`kjc_imputation`)

Some counties have missing regional output for certain sectors. This function fills those gaps using a scaling approach.

**Step 1** — Compute area-level scale from observed sectors only:

$$s_r = \frac{\sum_{i \notin \text{miss}} X_r^i}{\sum_{i \notin \text{miss}} X_n^i}$$

**Step 2** — Impute missing regional output using the area scale:

$$\hat{X}_r^i = X_n^i \times s_r \quad \forall i \in \text{miss}$$

where $X_n^i$ is always observed — only $X_r^i$ can be missing.

**Step 3** — Global fallback for counties with all sectors missing:

$$s_{global} = \frac{\sum_{r,i \notin \text{miss}} X_r^i}{\sum_{r,i \notin \text{miss}} X_n^i}$$

$$\hat{X}_r^i = X_n^i \times s_{global} \quad \text{if still missing}$$

**Assumptions:**
- National output $X_n^i$ is always observed — only regional output can be missing
- A county's output structure mirrors its observed sectors scaled by a single ratio
- If a county has no observed sectors at all, the national average ratio is used as a fallback

---

## 3. MSI — Missing Sector Employment Imputation (`msi.py`)

Five BEA sectors have no employment data for any county. This function estimates their employment using a regional employment-to-output ratio.

**Step 1** — Identify sectors missing for ALL counties:

$$\mathcal{M} = \{i : E_r^i = \text{NaN} \quad \forall r\}$$

**Step 2** — Compute employment-output ratio per county from known sectors:

$$\theta_r = \frac{\sum_{i \notin \mathcal{M}} E_r^i}{\sum_{i \notin \mathcal{M}} X_r^i} \quad \text{(employees per dollar of output)}$$

**Step 3** — Impute missing employment:

$$\hat{E}_r^i = \theta_r \times X_r^i \quad \forall i \in \mathcal{M}$$

$$\hat{E}_r^i = \max(\hat{E}_r^i, \ 0) \quad \text{(employment cannot be negative)}$$

**Step 4** — Fill back into employment table:

$$E_r^i = \begin{cases} E_r^i & \text{if observed} \\ \hat{E}_r^i & \text{if } i \in \mathcal{M} \end{cases}$$

**Assumptions:**
- The employment-output ratio $\theta_r$ is stable across sectors within a county
- Missing sectors follow the same productivity pattern as observed sectors in that county
- Employment is non-negative

---

## 4. LQ — Simple Location Quotient (`lq.py`)

The location quotient measures how specialized a county is in a given industry relative to the national average.

$$LQ_r^j = \frac{E_r^j / E_r}{E_n^j / E_n}$$

Where:
- $E_r^j$ = employment in county $r$, industry $j$
- $E_r$ = total employment in county $r$
- $E_n^j$ = national employment in industry $j$
- $E_n$ = total national employment

**Interpretation:**
- $LQ = 1$ — county matches the national average
- $LQ > 1$ — county is specialized in that industry
- $LQ < 1$ — county is underspecialized
- $LQ = 0$ — no employment in that sector

**Assumptions:**
- Employment is a reasonable proxy for specialization
- The national economy is the reference benchmark

---

## 5. Regionalization — SQRT-SLQ Method (`regionalize.py`)

The final step scales the national IO transactions matrix $Z^n$ down to a regional matrix $Z^r$ using a phi factor derived from location quotients.

**Step 1** — Compute the regionalization factor:

$$\phi_{ij}^r = \min\left(\text{cap},\ \sqrt{LQ_i^r \times LQ_j^r}\right)$$

**Step 2** — Apply to national IO matrix:

$$Z_{ij}^r = \phi_{ij}^r \times Z_{ij}^n$$

**Why the geometric mean of two LQs?** Following Flegg & Webber (1997) and Round (1983), using both the supplying industry $i$ and purchasing industry $j$ avoids the upward bias of naive single-LQ methods. The square root damps extreme values while symmetrically accounting for both supply and demand specialization (Miller & Blair, 2009).

**Why cap at 1.0?** A county cannot import more than it consumes — capping $\phi \leq 1$ ensures the regional matrix never exceeds the national one.

**Assumptions:**
- Regional trade follows national technical coefficients scaled by local specialization
- Supply and demand specialization are symmetric and equally weighted
- $\phi_{ij} \leq 1$ — regions cannot be more interconnected than the national economy

---

## References

- Flegg, A.T. & Webber, C.D. (1997). On the appropriate use of location quotients in generating regional input-output tables.
- Miller, R.E. & Blair, P.D. (2009). *Input-Output Analysis: Foundations and Extensions*. Cambridge University Press.
- Round, J.I. (1983). Nonsurvey techniques: A critical review of the theory and the evidence.