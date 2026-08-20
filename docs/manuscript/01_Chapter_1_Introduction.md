# Chapter 1: Introduction

## 1.1 Project Context & Background
Duck farming (*Anas platyrhynchos domesticus*, specifically the *Itik PINAS / Kayumanggi* and *Itim* breeds) represents a vital agricultural sector in the Philippines, supporting the commercial production of balut, penoy, and table duck meat.

A critical bottleneck in duck hatchery management is **transillumination candling** conducted at **Day 10** of incubation:
1. **Human Eye Fatigue & Subjectivity**: Manual candlers process thousands of eggs in dark rooms, leading to misclassification errors.
2. **Economic Loss**: Infertile eggs (*penoy*) lose food market value if left in the incubator past Day 10.
3. **Contamination Risks**: Dead/abnormal embryos (*bugok*) risk rotting and bursting inside incubators if not culled early.

## 1.2 Statement of the Problem
* How can deep learning computer vision be optimized for real-time edge execution on localized hatchery sorting conveyors ($\le 35\text{ ms}$ SLA)?
* How can duck egg candling classification accurately distinguish between 3 distinct biological states (Active spider embryo vs Clear unfertilized yolk vs Blood ring/dead embryo)?
* How can a distributed hatchery architecture ensure 100% sorting resilience during local network or power interruptions?

## 1.3 Objectives of the Study
### General Objective:
To design, develop, and evaluate **OvaLens**, an automated duck egg candling, embryonic classification, and hatchery analytics ecosystem.

### Specific Objectives:
1. Train and quantize a YOLOv8 computer vision model into ONNX FP16 format for 3-class duck egg classification.
2. Construct a conveyor sorting station with ESP32 UART actuation and hardware optical debouncing.
3. Implement an offline-first Edge application with local SQLite WAL storage and background HTTP synchronization.
4. Develop a centralized FastAPI REST API and PostgreSQL database for multi-batch lifecycle tracking.
5. Create a React + Vite + TypeScript enterprise dashboard for hatchery operators, featuring incubator tray visualization, mortality analytics, and MLOps metrics.

## 1.4 Significance of the Study
* **Hatchery Operators**: Increases throughput, reduces manual labor eye strain, and provides real-time sorting logs.
* **Hatchery Business Owners**: Maximizes Day 10 Penoy salvage revenue (₱14.00/egg) and prevents wasted incubator thermal energy.
* **Academic Institution (Foundation University)**: Demonstrates practical edge AI, IoT hardware, and full-stack software integration.

## 1.5 Scope and Delimitations
* **Biological Scope**: Duck eggs (*Kayumanggi, Itim, Khaki*) candled between Day 10 to Day 25 of incubation.
* **Hardware Scope**: Raspberry Pi 5 edge processor, ESP32 microcontroller, 12.5 cm/s conveyor belt, and high-intensity cold-LED candling strobe.
