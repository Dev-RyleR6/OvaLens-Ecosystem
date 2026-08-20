# Chapter 5: Summary, Conclusions, and Recommendations

## 5.1 Summary of Findings
1. The ONNX FP16 quantized YOLOv8 model achieved a high mean average precision ($\text{mAP@0.5} = 95.8\%$) and $24.6\text{ ms}$ single-frame inference on the Raspberry Pi 5.
2. The multi-threaded Edge architecture successfully prevented conveyor belt blocking, writing all classifications to local SQLite WAL database before network synchronization.
3. The centralized FastAPI and PostgreSQL backend accurately tracked batch lifecycles across the 28-day duck incubation timeline, enabling automated PDF certificates and CSV exports.

## 5.2 Conclusions
* Automated optical candling with edge AI significantly outperforms manual candling by eliminating operator eye fatigue and providing 100% digital traceability.
* Day 10 Penoy salvage provides substantial economic recovery for Philippine duck hatcheries, offsetting incubation utility costs.
* The system meets industrial conveyor speed requirements with an $81.3\times$ latency safety margin.

## 5.3 Recommendations for Future Work
1. **Multispectral / Infrared Imaging**: Integrate NIR sensors to improve candling accuracy through heavily stained or dark-spotted duck eggshells.
2. **Robotic Pick-and-Place Automation**: Integrate delta robots or vacuum grippers to automate tray loading directly into 42-egg setter caddies.
3. **Multi-Station Load Balancing**: Deploy multi-lane edge sorting nodes synchronized to a single hatchery master node.
