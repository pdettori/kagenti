---
name: test
description: Test writing, reviewing, and running for Kagenti - smart router for test workflows
---

> 📊 **[View workflow diagram](README.md#test-workflow)**

# Test Skills

Test management for Kagenti: write, review, and run tests.

## Auto-Select Sub-Skill

```
What do you need?
    │
    ├─ Write new tests
    │   → test:write
    │
    ├─ Review existing tests for quality
    │   → test:review
    │
    ├─ Run tests on Kind cluster
    │   → test:run-kind
    │
    ├─ Run tests on HyperShift cluster
    │   → test:run-hypershift
    │
    └─ Full TDD loop (write + run + iterate)
        → tdd (which links back here for test quality)
```

## Available Skills

| Skill | Purpose | Auto-approve |
|-------|---------|--------------|
| `test:write` | Write new E2E/unit tests | N/A (code editing) |
| `test:review` | Review test quality, catch bad patterns | N/A (analysis) |
| `test:run-kind` | Run tests on Kind cluster | All auto-approved |
| `test:run-hypershift` | Run tests on HyperShift cluster | All auto-approved |

## Test Workflow in TDD

```
tdd:* → Write/fix code → test:write (if new tests needed)
                        → test:review (verify test quality)
                        → test:run-kind or test:run-hypershift
                        → Pass? → git:commit → git:rebase → Push
```

## Related Skills

- `tdd:ci` - CI-driven TDD loop
- `tdd:kind` - TDD on Kind
- `tdd:hypershift` - TDD on HyperShift
- `git:commit` - Commit after tests pass
