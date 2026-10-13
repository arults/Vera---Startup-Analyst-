# Method reference and verification limit

The official R survival package documentation describes the Aalen–Johansen product of an initial state distribution and transition matrices, explicit initial states, and company/subject grouping through summed influence contributions for robust infinitesimal-jackknife variance:

https://search.r-project.org/CRAN/refmans/survival/html/survfit.formula.html

Read on 11 October 2026. This is a method reference, not an executed cross-library validation. R was not installed in the local executor. The candidate's checks are separately implemented exact-arithmetic, finite-difference and synthetic-path comparisons. They do not establish finite-sample confidence coverage, source qualification, population completeness or real-world predictive accuracy. The primary uncertainty obligation remains company-clustered bootstrap; the IJ calculation is explicitly a diagnostic.
