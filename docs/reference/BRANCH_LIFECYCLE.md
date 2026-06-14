# Branch Lifecycle

This repository preserves benchmark phases by branch.

## Branch roles

- `main`: frozen Phase 1 baseline in substance.
- `cc-agent-model-branch`: frozen Phase 2 baseline in substance.
- `phase3`: active Phase 3 router/dashboard/runner/provider work.

All Phase 3 implementation, benchmark configs, scripts, docs, dashboard code, and results should be developed on `phase3`.

## Default-branch dispatch wrapper

GitHub manual workflow dispatch expects a dispatchable workflow on the default branch. For that reason only, `main` contains a narrow Phase 3 arm-dispatch wrapper.

The wrapper must check out `phase3` before doing real work:

```yaml
- uses: actions/checkout@v4
  with:
    ref: phase3
```

Changes to `main` before Phase 3 promotion should be limited to this wrapper unless explicitly approved.

## Phase 3 promotion

When Phase 3 is complete, the expected transition is:

1. Confirm Phase 1 and Phase 2 artifacts remain preserved.
2. Confirm Phase 3 reports/results are final enough to become the primary branch.
3. Promote or merge `phase3` into `main`.
4. Remove the special default-branch wrapper behavior because the real Phase 3 workflow will then be native to `main`.
5. Decide whether to retain, archive, or remove `cc-agent-model-branch`.

Do not delete historical branches until their artifacts and reports have been verified.
