---
name: git-workflow
description: Enforces professional Git workflows including feature branching, Conventional Commits, GitHub CLI (gh) PR automation, and CI/CD verification.
---

# Git Workflow & GitHub CLI (`gh`) Automation Standard

This skill provides step-by-step instructions for AI agents and engineers on branch creation, Conventional Commits, GitHub CLI PR automation, and CI/CD quality gates for the **OvaLens** monorepo.

---

## 🌿 1. Branch Naming Protocol

Before implementing any feature, bug fix, or refactor, always branch from `main`:

| Type | Branch Pattern | Example |
| :--- | :--- | :--- |
| **Feature** | `feat/<scope>-<description>` | `feat/dashboard-penoy-calc` |
| **Bug Fix** | `fix/<scope>-<description>` | `fix/edge-opencv-lag` |
| **Refactor** | `refactor/<scope>-<description>` | `refactor/backend-auth-routes` |
| **Performance** | `perf/<scope>-<description>` | `perf/edge-onnx-fp16-export` |
| **Documentation** | `docs/<description>` | `docs/update-operations-guide` |
| **Testing** | `test/<scope>-<description>` | `test/add-batch-api-tests` |
| **Chore** | `chore/<description>` | `chore/update-github-ci` |

### Step 1: Create & Switch to Branch:
```bash
git checkout -b feat/your-feature-name
```

---

## 📝 2. Conventional Commits Standard

All commit messages MUST follow the Conventional Commits specification:

```
<type>(<scope>): <short imperative subject>

[optional body explaining technical motivation and changes]
```

### Valid Scopes:
* `backend` | `edge` | `dashboard` | `firmware` | `agents` | `docker` | `ci`

### Commit Execution:
```bash
git add .
git commit -m "feat(dashboard): add interactive Penoy yield salvage estimator"
```

---

## 🚀 3. Automated GitHub CLI (`gh`) Pull Request Workflow

When the feature is complete and local test suites pass, use the **GitHub CLI (`gh`)** to automate the PR lifecycle:

### Step 1: Push Branch to GitHub
```bash
git push -u origin feat/your-feature-name
```

### Step 2: Open Pull Request via GitHub CLI
```bash
gh pr create \
  --title "feat(dashboard): add interactive Penoy yield salvage estimator" \
  --body "## 📌 Summary
- Added dynamic Penoy economic salvage simulator to AnalyticsPage.tsx.
- Integrated energy savings calculation (18 days incubation power cost avoided).

## 🧪 Testing Verification
- [x] Backend tests passed (6/6)
- [x] Edge tests passed (5/5)
- [x] React production build verified (\`npm run build\`)"
```

### Step 3: Check Automated CI Build Status
```bash
# View active CI test workflows triggered by GitHub Actions
gh pr checks
```

### Step 4: View PR Diff in Terminal
```bash
gh pr diff
```

### Step 5: Merge Pull Request via CLI
```bash
# Squash and merge once CI checks pass
gh pr merge --squash --delete-branch
```

### Step 6: Sync Local `main`
```bash
git checkout main
git pull origin main
```

---

## 🧪 4. Mandatory Pre-PR Test Checklist

Always execute these local verification commands before opening a PR:

1. **Backend Tests**: `cd backend && python -m pytest tests/test_api.py -v`
2. **Edge CV Tests**: `cd edge && python -m pytest tests/test_edge_pipeline.py -v`
3. **Dashboard Build**: `cd dashboard && npm run build`
