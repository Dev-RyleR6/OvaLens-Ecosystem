---
name: code-reviewer
description: Performs thorough security, architectural, and quality audits on OvaLens pull requests and code modifications.
---

# OvaLens Code Reviewer & Security Auditor

This skill provides an automated code review protocol to ensure high security, architectural adherence to `AGENTS.md`, and optimal edge/backend resilience across the OvaLens monorepo.

---

## 🛡️ 1. Security & Compliance Checklist

* [ ] **Zero Hardcoded Secrets**: Ensure no API keys, JWT secrets, database passwords, or IP addresses are hardcoded in `.py`, `.ts`, or `.ino` files. All secrets must read from environment variables via Pydantic `Settings`.
* [ ] **SQL Injection Defense**: Verify all database queries use SQLAlchemy 2.0 ORM or parameterized `text("... WHERE id = :id")` bindings. Never use Python f-strings or string concatenation in SQL.
* [ ] **RBAC & Endpoint Protection**: Verify sensitive endpoints (`/api/v1/batches`, `/api/v1/devices`) are guarded by `Depends(get_current_active_user)` or `Depends(get_api_key)`.
* [ ] **Input Sanitization**: Ensure Pydantic v2 models validate data ranges (e.g. `confidence: float = Field(..., ge=0.0, le=1.0)`).

---

## ⚡ 2. Edge CV & IoT Resiliency Audit

* [ ] **Non-Blocking GUI**: Ensure camera frame acquisition, ONNX inference, serial writing, and HTTP sync run in dedicated background threads and never block the main CustomTkinter UI loop.
* [ ] **SQLite WAL Verification**: Confirm SQLite connections execute `PRAGMA journal_mode = WAL;` and `PRAGMA synchronous = NORMAL;` on connection initialization.
* [ ] **Hardware Disconnection Fallbacks**: Confirm the edge application gracefully enters Mock / Simulation mode if the USB camera or ESP32 serial port is unplugged, without raising uncaught exceptions.
* [ ] **Idempotent Ingestion**: Verify scan synchronization uses PostgreSQL `ON CONFLICT (scan_id) DO NOTHING` to safely absorb duplicate packets.

---

## 🎨 3. Design System & Brand Compliance

* [ ] **Foundation University Theme**:
  * Primary Maroon: `#800000` | Dark Maroon: `#5C0000`
  * Agri-Green (Fertile): `#357a38` | Reject Red: `#DC2626`
  * Dark Slate Surface: `#0F172A` | Card: `#1E293B`
* [ ] **Typography**: Segoe UI / Inter / Outfit modern fonts with clear hierarchy.

---

## 📋 4. Review Report Template

When conducting a code review, structure your feedback using this format:

```markdown
### 🔍 Code Review Summary

- **Security & Secrets**: [PASS / CONCERN]
- **Architectural Tenets**: [PASS / CONCERN]
- **Edge Resiliency**: [PASS / CONCERN]
- **Test Coverage**: [PASS / CONCERN]

#### 💡 Critical Feedback & Suggested Refactors:
1. **[File/Line]**: Issue description and suggested drop-in replacement.
```
