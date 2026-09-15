# Capstone Documentation & Diagram Import Staging

Drop your raw Google Docs exports, manuscript drafts, and Google Drive diagrams into this folder or directly into their respective folders.

---

## 📥 Supported File Formats & Destinations

### 1. Manuscript & Text Documents (Google Docs)
* **Accepted Formats**: `.docx`, `.txt`, `.html`, `.md`, or `.pdf`
* **Target Destination**: [`docs/manuscript/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/manuscript/)
* **What happens**: We will convert and split your text into clean, formal Markdown files across Chapters 1 to 5, References, and Appendices following the Foundation University thesis template.

### 2. Diagrams & Schematics (Google Drive / Draw.io)
* **Accepted Formats**: `.io`, `.drawio`, `.drawio.svg`, `.png`, `.svg`, `.pdf`
* **Target Destinations**:
  * System Architecture $\to$ [`docs/diagrams/architecture/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/)
  * Operational Flowcharts $\to$ [`docs/diagrams/flowcharts/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts/)
  * Wiring & Schematics $\to$ [`docs/diagrams/hardware_schematics/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/hardware_schematics/)
  * Relational Database ERD $\to$ [`docs/diagrams/database_erds/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/database_erds/)
  * UML Use Cases $\to$ [`docs/diagrams/use_cases/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/use_cases/)

> [!TIP]
> **Can AI read `.io` / `.drawio` files?**  
> **Yes!** Draw.io (`.io` / `.drawio`) files are structured XML diagrams. The AI can read, parse, and analyze every node, label, connector, flowchart decision, and UML actor directly, whether uncompressed or compressed.

