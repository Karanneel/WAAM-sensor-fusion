# Decisions

## 2026-10-17: Start with WAAM

Use wire mass conservation for bead area and a lumped thermal model. Compare
height, temperature and standoff estimates while keeping a shared controller.
Detailed early planning is preserved in the archived source snapshot.

## 2026-10-26: Original predictions recorded

The original plan states a freeze date of October 26. It first entered local
Git history on October 31, alongside the implementation. Its wording and the
subsequent verdicts are retained in [the historical record](../history/registered-plan-2026-10-26.md).

## 2026-11-01: Correct the experiment and simplify the documentation

Use travel speed for height control. Align layer-end measurement timing and
separate training/test builds. Keep learned and EKF sensor-subset results
separate and include a learned model without sensors. Report the previously
inspected variant as sensitivity analysis. See [the revision record](revision-2026-11-01.md)
and [current protocol](../experiment-protocol.md).
