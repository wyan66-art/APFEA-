"""APFEA prototype v0.1 - AI-assisted Phenomenological Foundry Engineering Approach.

Implements the computational core of APFEA v3 Part One:
  * VT-shift estimation (design against VTs, not the PDK's VT0)
  * Corner-lot DOE planning aligned to real silicon corner splits (VTs +/- 3 sigma)
  * Pre-tape-out margin report with a VTs1 recommendation for silicon corner lots

This is a PLANNER / bookkeeper, not a circuit simulator. No SPICE is run;
block pass/fail comes from each block's declared VT window vs. the corner
spread - the same comparison APFEA v3 prescribes before tape-out.
"""
__version__ = "0.1.0"
