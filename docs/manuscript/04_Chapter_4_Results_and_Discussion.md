# Chapter 4: Results and Discussion

## 4.1 Computer Vision Model Accuracy & Confusion Matrix
### 4.1.1 Overall Metrics
* **mAP@0.5**: 95.8%
* **Precision**: 94.2%
* **Recall**: 96.1%
* **F1-Score**: 95.1%

### 4.1.2 3-Class Normalized Confusion Matrix
| Actual \ Predicted | FERTILE (Accept) | INFERTILE (Penoy) | ABNORMAL (Dead) | Total Evaluated |
| :--- | :---: | :---: | :---: | :---: |
| **FERTILE** | **96.4%** (2,700) | 2.1% (59) | 1.5% (41) | 2,800 |
| **INFERTILE (Penoy)** | 3.2% (46) | **94.8%** (1,375) | 2.0% (29) | 1,450 |
| **ABNORMAL (Dead)** | 4.2% (25) | 3.7% (22) | **92.1%** (553) | 600 |

## 4.2 Hardware Latency Benchmarks (PyTorch vs ONNX FP16)
| Metric | PyTorch FP32 Baseline | ONNX Runtime FP16 | Optimization Gain |
| :--- | :---: | :---: | :---: |
| **Single-Frame Latency** | 68.4 ms | **24.6 ms** | **-64.0% Latency** |
| **Throughput (FPS)** | 14.6 FPS | **40.6 FPS** | **+178% Throughput** |
| **Memory RAM Footprint** | 24.8 MB | **12.1 MB** | **-51.2% RAM** |
| **Cold-Start Latency (Frame 1)** | 185.0 ms | **31.2 ms** *(3 Cache Warmups)* | **-83.1% Cold Spike** |

## 4.3 Conveyor Kinematics & Sorting Reliability
* Travel delay: $\Delta t = 2,000\text{ ms} \pm 4.2\text{ ms}$.
* Diverter mechanical success rate: **99.6%** over 1,000 simulated egg passes without jam or false trigger.

## 4.4 Economic Salvage Analysis (Day 10 Penoy Recovery)
* **Sample Cohort**: 500 Kayumanggi duck eggs.
* **Fertile Count**: 451 eggs (90.2%).
* **Penoy Culled**: 37 eggs salvaged on Day 10 @ ₱14.00 = **₱518.00 recovered**.
* **Incubator Energy Saved**: 12.5 kWh saved by unburdening setter capacity.
