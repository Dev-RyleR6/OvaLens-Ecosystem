# Chapter 1: Introduction

## 1.1 Rationale of the Study

Duck farming remains an important agricultural activity in the Philippines and supports products such as balut and penoy. During incubation, hatchery operators must determine not only whether an egg was initially fertilized but also whether embryonic development remains viable. Candling is therefore a critical non-destructive inspection process in which transmitted light reveals internal conditions associated with fertility and embryo development. Recent Philippine and international studies continue to characterize manual candling as labor-intensive and dependent on human judgment, supporting the development of repeatable image-based assessment methods (Maglasang et al., 2025; Cai et al., 2025; Mulyani et al., 2026). In many hatchery settings, candling is still performed manually under dim conditions and depends heavily on worker experience. Repetitive inspection can contribute to fatigue and inconsistent judgment, creating the possibility that viable eggs are rejected or non-viable eggs remain in the incubation workflow. Recent deep learning research on duck eggs similarly identifies the limitations of manual inspection as a motivation for automated image-based assessment (Cai et al., 2025; Mulyani et al., 2026).  

Recent duck-specific studies demonstrate that automated candling can combine controlled image acquisition with lightweight computer-vision models. Liu et al. (2023) reported 97.55% mAP and 178 ms image latency for AFF-YOLOX on duck-egg hatching trays, while Li et al. (2023) reported 98.10% detection accuracy and 97.79% mAP50 for MobileOne-YOLO on Day 10 duck eggs. Deng et al. (2024) further evaluated a lightweight YOLO-based method for late-stage duck eggs. These studies demonstrate the technical feasibility of automated duck-egg assessment, but they do not represent OvaLens's Day 10 binary classification workflow or the represented Itik Pinas genetic groups. Deep learning provides a basis for extending this approach. Maglasang et al. (2025) reported 97.40% testing accuracy for a VGG16 transfer-learning model on Filipino candled duck eggs, while Cai et al. (2025) reported 96.03% overall accuracy for a multi-state classification model.

Zhou et al. (2023) demonstrated lightweight YOLO-family detection on duck egg incubation trays, and Flores (2026) showed the feasibility of YOLO-based fertility detection using locally collected Philippine poultry imagery. More recent work on Cihateup duck eggs also showed that performance varies with incubation stage and image preparation, reinforcing the need to evaluate models within the conditions for which they are intended (Mulyani et al., 2026). OvaLens uses YOLOv8 object detection rather than an image-classification-only model. Although the controlled imaging chamber is designed for one egg per capture, detection provides an explicit check that an egg is present and located within the expected region before a class and confidence score are accepted. The resulting bounding box represents the entire egg, not a specific embryo, blood ring, or defect. This design supports invalid-capture handling and allows the accepted detection to be associated with the physical cradle tracked by the sorting controller.

The local research context is also important. The partner hatchery maintains IP-Itim and IP-Khaki, the two Itik Pinas pure lines, and IP-Kayumanggi, their commercial hybrid. Santiago et al. (2022) describe IP-Kayumanggi as the progeny of male IP-Khaki and female IP-Itim, while DOST-PCAARRD (2022) identifies these genetic groups within its continuing Itik Pinas development program. Their related origin supports development of one pooled model for the target hatchery, while subgroup reporting can determine whether performance remains consistent across the three represented genetic groups. OvaLens focuses on the Day 10 candling checkpoint and proposes an integrated deep learning, electromechanical, and information system for automated near-real-time binary fertility classification and sorting. It combines a locally generated Day 10 Itik Pinas dataset, whole-egg YOLOv8 detection, indexed cradle transport, cradle-level result tracking, a Raspberry Pi desktop control application, and a web-based administrative dashboard. The study will evaluate both the vision model and the complete sorting workflow so that system success is not inferred from model accuracy alone.

---

## 1.2 Statement of the Problem

Manual duck egg candling at the partner hatchery depends on visual inspection and repeated handling, while available automated studies do not fully represent its Itik Pinas genetic groups, Day 10 binary fertility classes, and integrated tracking-and-sorting workflow.

The study therefore seeks to determine whether a locally trained YOLOv8-based system can provide reliable automated near-real-time candling and sorting under these conditions. Specifically, the study will answer the following questions:  

1. How accurately can the YOLOv8 model detect and classify Day 10 Itik Pinas duck eggs as **Fertile** or **Infertile**?
2. How does Day 10 model performance vary across **IP-Itim**, **IP-Khaki**, and **IP-Kayumanggi**?
3. How reliably can the integrated prototype maintain egg-to-cradle association and route classified eggs to the correct collection tray?  
4. What end-to-end processing time, throughput, successful-cycle rate, and manual-review frequency can the proposed system achieve under controlled hatchery trials?

---

## 1.3 Objectives of the Study

### 1.3.1 General Objective
To develop and evaluate OvaLens, a YOLOv8-based deep learning system for fertility and developmental viability assessment through automated near-real-time candling and sorting of Itik Pinas duck eggs under the conditions of a partner research hatchery in Negros Oriental.

### 1.3.2 Specific Objectives
1. **Electromechanical Prototype**: To design and implement a Raspberry Pi-controlled candling and handling prototype using controlled illumination, fixed camera geometry, an indexed pocket-conveyor, positional reference sensing, and servo-actuated sorting mechanisms.  
2. **Local Day 10 Dataset**: To generate a locally collected Day 10 candling image dataset representing IP-Itim, IP-Khaki, and IP-Kayumanggi, with records of unique eggs, incubation batches, and observed binary class distributions.
3. **YOLOv8 Detection Model**: To develop a YOLOv8 object detection model that detects the whole egg and assigns the Fertile or Infertile operational class with an associated confidence score.  
4. **Desktop & Web Software**: To develop a Raspberry Pi desktop control application for mechanism control, cradle tracking, classification display, and manual-review alerts, together with a web-based administrative dashboard for batch monitoring and reporting.  
5. **Model Evaluation**: To evaluate model performance using egg-level classification measures, object-detection metrics, inference latency, and subgroup results by Itik Pinas genetic group and Day 10 batch.
6. **Prototype & Workflow Evaluation**: To evaluate end-to-end prototype performance using sorting accuracy, cradle-tracking accuracy, successful-cycle rate, manual-review frequency, processing time, and throughput.

---

## 1.4 Significance of the Study

The findings and outputs of this study may benefit the following stakeholders:

### Duck Farm Owners and Hatchery Operators
OvaLens will provide evidence on whether a compact edge-computing prototype can automate important portions of candling and sorting under a localized hatchery workflow. If the prototype meets its model and system performance targets, it may serve as a basis for reducing repetitive manual inspection and for future cost and deployment studies in small- to medium-scale hatchery environments.

### Candling Workers
After eggs are manually loaded into individual cradles, the prototype will automate indexed positioning, image capture, classification display, cradle tracking, and downstream sorting. This may reduce repetitive handling and provide workers with immediate decision support while preserving a manual-review path for uncertain cases.

### Duck Farmers and Production Managers
Batch-level classification records and session summaries may provide additional information for incubation-space management, flock planning, and review of egg-status trends. These benefits will depend on the accuracy and reliability demonstrated during prototype evaluation.

### Consumers
Consumers may benefit indirectly if more consistent hatchery inspection contributes to better process control. The study will not directly measure consumer outcomes or product-quality effects.

### Philippine Duck Farming Industry
OvaLens may provide a localized technical reference for integrating deep learning, edge computing, and electromechanical automation in duck hatchery operations. The study is intended as a prototype-level contribution rather than evidence of industry-wide readiness or commercial cost superiority.

### Researchers and Students
The study may serve as a reference for future work on localized agricultural computer vision, edge-deployed deep learning, egg-handling automation, and longitudinal candling datasets in Philippine conditions.

---

## 1.5 Scope and Limitations

### Scope
This study will develop and evaluate OvaLens as a prototype for automated near-real-time Day 10 candling and sorting of Itik Pinas duck eggs. The system will use a controlled LED candling chamber, fixed camera geometry, Raspberry Pi-based edge processing, and a lightweight YOLOv8 object-detection model. Each valid image will contain an egg-level bounding box assigned to one of two operational classes: **Fertile** or **Infertile**. The bounding box will identify the whole egg and will not be interpreted as localization of a specific internal diagnostic structure.

The primary dataset will be collected at one academic-institution-owned research hatchery in Negros Oriental and will represent **IP-Itim**, **IP-Khaki**, and **IP-Kayumanggi** at the **Day 10** candling checkpoint. Class frequencies will be recorded as they occur in the actual workflow; the study will not force equal class representation. The study will target at least 3,000 locally collected annotated images and will record the number of unique physical eggs, incubation batches, genetic groups, and binary operational labels represented. Detailed dataset partitioning, annotation agreement procedures, and model-training parameters will be specified in Chapter 3.

The operational classes are defined from candling appearance:
* **Fertile**: refers to an egg showing features consistent with continuing viable embryonic development at the observed stage.
* **Infertile**: refers to any Day 10 egg not accepted as Fertile and routed to the Penoy salvage stream.

These labels are candling-based operational assessments rather than complete embryological diagnoses.

The physical prototype will use manual egg loading followed by automated indexed transport, imaging, result tracking, and sorting. A primary stepper motor will drive the pocket-conveyor, while auxiliary servos will actuate the class-specific sorting mechanisms. The controller will associate each accepted classification with the corresponding cradle as it moves downstream. Invalid or low-confidence detections and synchronization faults will be directed to a manual-review state.

The software scope will include a Raspberry Pi desktop application for equipment control and worker feedback and a web-based dashboard for batch logs, class statistics, and session reports. Model evaluation will include egg-level classification performance, standard object-detection metrics, subgroup analysis by genetic group and Day 10 batch, and inference latency.

The target model inference latency is **no more than 200 milliseconds** per image on the selected Raspberry Pi deployment, while complete mechanical processing time will be measured separately. Prototype evaluation will include correct sorting, cradle tracking, successful processing cycles, manual-review frequency, processing time, and throughput. In this study, **near-real-time** means that a valid prediction becomes available during the indexed candling pause and before the egg reaches the point at which its routing decision is required; it does not imply deterministic hard real-time operation.

### Limitations
* The dataset will be collected from one research hatchery in Negros Oriental. Findings will therefore be specific to the represented Itik Pinas population, imaging environment, and operational workflow unless independently validated elsewhere.  
* IP-Itim, IP-Khaki, and IP-Kayumanggi may not occur in equal proportions within each incubation batch. Subgroup performance will be reported, but pooled performance will not be interpreted as demonstrated generalization to unrelated duck breeds.  
* The binary Day 10 label does not provide a complete embryological diagnosis. Ambiguous images will require manual review under a written labeling guide.
* The study will evaluate only the Day 10 checkpoint used by OvaLens; it is not proposed as a universal candling schedule.
* Reliable image acquisition will depend on controlled illumination and camera geometry. Material changes in lighting, shell appearance, camera placement, or hatchery conditions may require recalibration, validation, or retraining.  
* The prototype will not evaluate external shell defects, compare alternative deep learning architectures, compare alternative conveyor designs, or test whether indexed handling itself improves hatchability.
