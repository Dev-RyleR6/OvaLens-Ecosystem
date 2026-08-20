# Chapter 2: Review of Related Literature and Studies

## 2.1 Duck Incubation & Embryonic Development
* Duck egg incubation period: 28 days.
* Milestones:
  - **Day 0**: Setting in setter cabinet.
  - **Day 10 (1st Candling)**: Distinguishing fertile spider blood vascular networks from clear infertile penoy eggs.
  - **Day 18 (2nd Candling & Transfer)**: Transfer from setter trays to hatcher baskets.
  - **Day 25 (Pipping)**: Internal and external shell pipping.
  - **Day 28 (Hatch)**: Duckling emergence.

## 2.2 Computer Vision in Agricultural Egg Sorting
* Evolution from traditional image processing (Sobel filters, thresholding) to Deep Convolutional Neural Networks (CNNs) and YOLO architectures.
* Challenges with duck eggs vs chicken eggs: Duck eggshells have thicker, greasier cuticles and higher opacity, requiring high-intensity 10W–20W LED transillumination.

## 2.3 Edge AI & Quantization Techniques (FP32 vs FP16 ONNX)
* Comparison between heavy PyTorch runtimes and lightweight ONNX Runtime with hardware acceleration (ARM NEON / TensorRT).

## 2.4 Distributed Offline-First Architectures
* SQLite Write-Ahead Logging (WAL) for local high-throughput transactional integrity during network disconnections.

## 2.5 Conceptual Framework (IPO Model)
* **Input**: Duck egg transillumination frames, conveyor optical sensor triggers, operator batch configurations.
* **Process**: ONNX FP16 inference, geometric heuristics, ESP32 kinematic actuation ($\Delta t = D/v$), SQLite WAL logging, REST sync.
* **Output**: Pneumatic physical sorting (Accept/Reject), digital batch reports, incubator tray matrix, economic salvage analytics.
