---
name: git-workflow
description: Enforces professional Git workflows including feature branching, Conventional Commits, code reviews, and pull requests for the OvaLens monorepo.
---

# Git Workflow & Collaboration Standard

This skill defines the Git branching, commit messaging, and Pull Request (PR) protocol for the **OvaLens** monorepo.

---

## 🌿 1. Branch Naming Conventions

Always create a dedicated feature or bugfix branch before implementing changes:

| Branch Type | Prefix | Example | Description |
| :--- | :--- | :--- | :--- |
| **New Feature** | `feat/` | `feat/dashboard-analytics-view` | Adding a new page, endpoint, or CV module |
| **Bug Fix** | `fix/` | `fix/opencv-buffer-lag` | Resolving an error or unexpected behavior |
| **Refactoring** | `refactor/` | `refactor/modularize-edge-cv` | Code restructuring without feature changes |
| **Performance** | `perf/` | `perf/onnx-fp16-warmup` | Latency, memory, or FPS improvements |
| **Documentation** | `docs/` | `docs/update-esp32-pinout` | Updating README, guides, or docstrings |
| **Testing** | `test/` | `test/add-batch-lifecycle-tests` | Adding pytest or Jest test cases |
| **Chore** | `chore/` | `chore/update-docker-compose` | Dependency updates or build tooling |

### Creating and Switching to a Feature Branch:
```bash
git checkout -b feat/your-feature-name
```

---

## 📝 2. Conventional Commits Standard

Every commit message must follow this exact format:
```
<type>(<scope>): <short description in imperative mood>

[optional body explaining motivation and technical approach]
```

### Commit Scopes:
* `backend`: FastAPI API, services, models, schemas, or database migrations
* `edge`: OpenCV grabber, ONNX model inference, CustomTkinter UI, or SQLite WAL
* `dashboard`: React components, Zustand store, TanStack Query, or Tailwind styles
* `firmware`: ESP32 Arduino C++, servo timer, or optical debounce
* `agents`: AI assistant instructions, skills, or rulebooks
* `docker`: Dockerfile or docker-compose configurations

### Example Commits:
```bash
git commit -m "feat(dashboard): add Penoy economic salvage calculator card"
git commit -m "fix(edge): resolve DirectShow camera frame buffer starvation"
git commit -m "perf(backend): add index on egg_scans(batch_id, scanned_at)"
```

---

## 🔍 3. Pre-Commit Quality Checklist

Before staging and committing changes, always execute the relevant verification commands:

```bash
# 1. Backend Verification
cd backend
python -m pytest tests/test_api.py -v

# 2. Edge CV Verification
cd edge
python -m pytest tests/test_edge_pipeline.py -v

# 3. Code Style & Hygiene
git status
```

---

## 🚀 4. Pull Request (PR) Workflow

1. **Push Branch to Remote**:
   ```bash
   git push -u origin feat/your-feature-name
   ```

2. **Pull Request Template**:
   ```markdown
   ## 📌 Summary of Changes
   - Clear bullet points summarizing what was built or fixed.

   ## 🧪 Testing & Verification
   - [x] Backend pytest suite passed (6/6 tests)
   - [x] Edge CV pytest suite passed (5/5 tests)
   - [x] No breaking database schema migrations

   ## 📸 Screenshots / Demos (If Applicable)
   - Attach UI screenshots or CLI output logs.
   ```

3. **Merging Strategy**:
   - Always prefer **Squash and Merge** or **Rebase and Merge** to keep the `main` branch commit history clean and linear.
