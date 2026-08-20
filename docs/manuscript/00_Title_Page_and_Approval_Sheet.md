# Title Page, Approval Sheet & Abstract

**OVALENS: AN AUTOMATED DUCK EGG CANDLING, EMBRYONIC FERTILITY CLASSIFICATION, AND ECONOMIC HATCHERY ANALYTICS ECOSYSTEM**

A Capstone Project Presented to the Faculty of  
**Foundation University**  
Dumaguete City, Negros Oriental, Philippines  

---

### In Partial Fulfillment of the Requirements for the Degree of
**Bachelor of Science in Information Technology / Computer Engineering / Computer Science**

**By:**  
**Ryle Gabotero (Project Lead & Developer)**  

**Date:** March 2026  

---

## 📜 Abstract

Duck egg candling is a labor-intensive, human-dependent process in Philippine duck hatcheries ("balut" and "penoy" industries). Traditional candling suffers from operator eye fatigue, inconsistent classification accuracy, and absence of digital yield tracking. 

**OvaLens** is an automated, industrial-grade duck egg candling and fertility classification ecosystem. Powered by an ONNX FP16-quantized YOLOv8 computer vision model deployed on a Raspberry Pi 5 edge controller, OvaLens achieves real-time inference (24.6 ms/frame) synchronized with an ESP32 pneumatic conveyor diverter. The system classifies duck eggs into three biological categories: **Fertile** (incubate to Day 28), **Infertile/Penoy** (salvaged on Day 10 for commercial food sale @ ₱14.00), and **Abnormal/Dead** (discarded early). A centralized FastAPI backend and PostgreSQL database provide real-time batch lifecycle management, economic salvage calculations, SQLite WAL offline edge synchronization, and an enterprise administrative dashboard.
