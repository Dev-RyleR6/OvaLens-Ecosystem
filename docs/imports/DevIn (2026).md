

**OVALENS: A YOLOV8-BASED DEEP LEARNING SYSTEM FOR**  
**AUTOMATED NEAR-REAL-TIME CANDLING AND SORTING OF**  
**ITIK PINAS DUCK EGGS**

A Capstone Project

Presented to the Faculty of the  
College of Computer Studies  
Foundation University

Dumaguete City, Negros Oriental

In Partial Fulfillment of the Requirements for the Degree of  
Bachelor of Science in Information Technology

**Prepared by:**  
Ryle Anthony Gabotero M.  
Olsen Nathaniel Cafino  
Neil Allen Faburada

**2026**

# **APPROVAL SHEET**

This capstone project entitled "OvaLens: A YOLOv8-Based Deep Learning System for Automated Near-Real-Time Candling and Sorting of Itik Pinas Duck Eggs," prepared and submitted by Ryle Anthony Gabotero M., Olsen Nathaniel Cafino, and Neil Allen Faburada, in partial fulfillment of the requirements for the degree of Bachelor of Science in Information Technology, has been examined and is hereby recommended for acceptance and approval for oral examination.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**Mr. Andrew Mores**  
*Capstone Adviser*

Approved by the Panel of Examiners on the Oral Examination.

Grade: \_\_\_\_\_\_\_\_\_\_\_\_.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
*Panel Chair*

| \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_Panel Member | \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_Panel Member |
| :---: | :---: |

Accepted and approved in partial fulfillment of the requirements for the degree of Bachelor of Science in Information Technology.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**Sheena Mae Sab Sabado**  
*Dean, College of Computer Studies*

# **ACKNOWLEDGMENT**

The researchers wish to extend their deepest gratitude to everyone who has contributed to the development and preparation of this capstone project.  
First and foremost, to Almighty God, for the wisdom, strength, and perseverance granted throughout the duration of this study.  
To Mr. Andrew Mores, the researchers' capstone adviser, for the invaluable guidance, patience, and constructive feedback extended throughout the conceptualization and refinement of OvaLens, including recommendations that helped shape the proposed hardware architecture and research methodology.  
To the panel of examiners, for their insightful critiques and recommendations that helped strengthen the direction and technical soundness of this study.  
To Dean Sheena Mae Sab Sabado and the faculty and staff of the College of Computer Studies, Foundation University, for the knowledge and technical foundation imparted throughout the researchers' academic journey.  
To the management and staff of the partner research hatchery in Negros Oriental, for graciously accommodating the researchers during data-gathering sessions and for sharing their expertise in duck egg candling practices.  
To the researchers' families and friends, for their unwavering support, encouragement, and understanding during the demanding periods of this project.  
And finally, to us, Team DevIn — Ryle, Olsen, and Neil — for the collective dedication, coordination, and shared commitment devoted to developing a locally relevant and technically sound capstone project.

# **EXECUTIVE SUMMARY**

Duck egg candling is a non-destructive inspection process used to assess fertility and embryonic development by directing light through the eggshell. In many Philippine hatchery settings, candling remains manual and depends on worker experience, sustained visual attention, and repeated handling, creating a need for more consistent image-based decision support.  
This capstone project proposes OvaLens, a YOLOv8-based deep learning system for automated near-real-time candling and sorting of Itik Pinas duck eggs at a partner research hatchery in Negros Oriental. The study will use locally collected images from IP-Itim and IP-Khaki, the two Itik Pinas pure lines, and IP-Kayumanggi, their commercial hybrid, across the hatchery's Day 10, Day 18, and Day 25 candling schedule. Each egg will be annotated with a whole-egg bounding box and classified as Fertile, Infertile, or Abnormal. Object detection is used to verify egg presence and position before a sorting decision is accepted.  
The prototype will combine a controlled LED candling chamber, Raspberry Pi-based edge inference, and an indexed pocket-conveyor with stepper-driven transport and servo-actuated sorting. Eggs will be manually loaded into individual cradles, tracked from imaging to sorting, and routed to the appropriate tray. Invalid or low-confidence detections will require manual review. A desktop control application will manage the mechanism and display current results, while a web-based dashboard will provide batch logs and summary statistics.  
The study will target at least 3,000 locally collected annotated images while recording unique eggs, incubation batches, genetic groups, stages, and observed class distributions. Model evaluation will include egg-level classification measures, mAP, and inference latency, while system evaluation will include sorting accuracy, cradle-tracking reliability, successful processing cycles, processing time, throughput, and manual-review frequency. In this study, near-real-time means that a valid prediction becomes available during the indexed candling pause and before the egg reaches the point where its routing decision is required. OvaLens aims to provide a locally grounded reference for deep learning-assisted duck egg candling and automated sorting in a Philippine hatchery context.

# **TABLE OF CONTENTS**

**APPROVAL SHEET	i**  
**ACKNOWLEDGMENT	ii**  
**EXECUTIVE SUMMARY	iii**  
**CHAPTER 1  INTRODUCTION	1**  
1.1 Rationale of the Study	1  
1.2 Statement of the Problem	3  
1.3 Objectives of the Study	4  
1.3.1 General Objective	4  
1.3.2 Specific Objectives	4  
1.4 Significance of the Study	5  
1.5 Scope and Limitations	7  
**CHAPTER 2  REVIEW OF RELATED LITERATURE	10**  
2.1 Review of Related Literature	10  
2.2 Review of Related Studies	13  
2.3 Synthesis	17  
**REFERENCES	19**

# **CHAPTER 1**

**INTRODUCTION**

## **1.1 Rationale of the Study**

Duck farming remains an important agricultural activity in the Philippines and supports products such as balut and penoy. During incubation, hatchery operators must determine not only whether an egg was initially fertilized but also whether embryonic development remains viable. Candling is therefore a critical non-destructive inspection process in which transmitted light reveals internal conditions associated with fertility and embryo development. Recent Philippine and international studies continue to characterize manual candling as labor-intensive and dependent on human judgment, supporting the development of repeatable image-based assessment methods (Maglasang et al., 2025; Cai et al., 2025; Mulyani et al., 2026). In many hatchery settings, candling is still performed manually under dim conditions and depends heavily on worker experience. Repetitive inspection can contribute to fatigue and inconsistent judgment, creating the possibility that viable eggs are rejected or non-viable eggs remain in the incubation workflow. Recent deep learning research on duck eggs similarly identifies the limitations of manual inspection as a motivation for automated image-based assessment (Cai et al., 2025; Mulyani et al., 2026).  
Recent duck-specific studies demonstrate that automated candling can combine controlled image acquisition with lightweight computer-vision models. Liu et al. (2023) reported 97.55% mAP and 178 ms image latency for AFF-YOLOX on duck-egg hatching trays, while Li et al. (2023) reported 98.10% detection accuracy and 97.79% mAP50 for MobileOne-YOLO on Day 10 duck eggs. Deng et al. (2024) further evaluated a lightweight YOLO-based method for Day 25 duck eggs. These studies demonstrate the technical feasibility of automated duck-egg assessment, but they do not represent the partner hatchery's combined Day 10, Day 18, and Day 25 workflow, the three OvaLens operational classes, or the represented Itik Pinas genetic groups. Deep learning provides a basis for extending this approach. Maglasang et al. (2025) reported 97.40% testing accuracy for a VGG16 transfer-learning model on Filipino candled duck eggs, while Cai et al. (2025) reported 96.03% overall accuracy for an improved ResNet34 model classifying meat duck eggs as unfertilized, live embryonated, or abnormal.  
Zhou et al. (2023) demonstrated lightweight YOLO-family detection on duck egg incubation trays, and Flores (2026) showed the feasibility of YOLO-based fertility detection using locally collected Philippine poultry imagery. More recent work on Cihateup duck eggs also showed that performance varies with incubation stage and image preparation, reinforcing the need to evaluate models within the conditions for which they are intended (Mulyani et al., 2026). OvaLens uses YOLOv8 object detection rather than an image-classification-only model. Although the controlled imaging chamber is designed for one egg per capture, detection provides an explicit check that an egg is present and located within the expected region before a class and confidence score are accepted. The resulting bounding box represents the entire egg, not a specific embryo, blood ring, or defect. This design supports invalid-capture handling and allows the accepted detection to be associated with the physical cradle tracked by the sorting controller.  
The local research context is also important. The partner hatchery maintains IP-Itim and IP-Khaki, the two Itik Pinas pure lines, and IP-Kayumanggi, their commercial hybrid. Santiago et al. (2022) describe IP-Kayumanggi as the progeny of male IP-Khaki and female IP-Itim, while DOST-PCAARRD (2022) identifies these genetic groups within its continuing Itik Pinas development program. Their related origin supports development of one pooled model for the target hatchery, while subgroup reporting can determine whether performance remains consistent across the three represented genetic groups. The hatchery also conducts candling on Day 10, Day 18, and Day 25, allowing the study to assess changing fertility and developmental-viability appearances across its actual operational workflow rather than only during early incubation. OvaLens therefore proposes an integrated deep learning, electromechanical, and information system for automated near-real-time candling and sorting. It combines a locally generated multi-stage Itik Pinas dataset, whole-egg YOLOv8 detection, indexed cradle transport, cradle-level result tracking, class-specific sorting, a Raspberry Pi desktop control application, and a web-based administrative dashboard. The study will evaluate both the vision model and the complete sorting workflow so that system success is not inferred from model accuracy alone.

## **1.2 Statement of the Problem**

Manual duck egg candling at the partner hatchery depends on visual inspection and repeated handling, while available automated studies do not fully represent the hatchery's combination of Itik Pinas genetic groups, Day 10, Day 18, and Day 25 candling stages, three operational egg classes, and integrated tracking-and-sorting workflow.  
The study therefore seeks to determine whether a locally trained YOLOv8-based system can provide reliable automated near-real-time candling and sorting under these conditions. Specifically, the study will answer the following questions:  
1\. How accurately can the YOLOv8 model detect and classify candled Itik Pinas duck eggs as Fertile, Infertile, or Abnormal?  
2\. How does model performance vary across IP-Itim, IP-Khaki, and IP-Kayumanggi and across the Day 10, Day 18, and Day 25 candling stages represented in the dataset?  
3\. How reliably can the integrated prototype maintain egg-to-cradle association and route classified eggs to the correct collection tray?  
4\. What end-to-end processing time, throughput, successful-cycle rate, and manual-review frequency can the proposed system achieve under controlled hatchery trials?

## **1.3 Objectives of the Study**

### **1.3.1 General Objective**

To develop and evaluate OvaLens, a YOLOv8-based deep learning system for fertility and developmental viability assessment through automated near-real-time candling and sorting of Itik Pinas duck eggs under the conditions of a partner research hatchery in Negros Oriental.

### **1.3.2 Specific Objectives**

*  To design and implement a Raspberry Pi-controlled candling and handling prototype using controlled illumination, fixed camera geometry, an indexed pocket-conveyor, positional reference sensing, and servo-actuated sorting mechanisms. 

*  To generate a locally collected candling image dataset representing IP-Itim, IP-Khaki, and IP-Kayumanggi across the partner hatchery's Day 10, Day 18, and Day 25 candling sessions, with records of unique eggs, incubation batches, stages, and observed class distributions. 

*  To develop a YOLOv8 object detection model that detects the whole egg and assigns the Fertile, Infertile, or Abnormal operational class with an associated confidence score. 

* To develop a Raspberry Pi desktop control application for mechanism control, cradle tracking, classification display, and manual-review alerts, together with a web-based administrative dashboard for batch monitoring and reporting. 

* To evaluate model performance using egg-level classification measures, object-detection metrics, inference latency, and subgroup results by Itik Pinas genetic group and candling stage. 

*  To evaluate end-to-end prototype performance using sorting accuracy, cradle-tracking accuracy, successful-cycle rate, manual-review frequency, processing time, and throughput.

## **1.4 Significance of the Study**

The findings and outputs of this study may benefit the following stakeholders:

### **Duck Farm Owners and Hatchery Operators**

OvaLens will provide evidence on whether a compact edge-computing prototype can automate important portions of candling and sorting under a localized hatchery workflow. If the prototype meets its model and system performance targets, it may serve as a basis for reducing repetitive manual inspection and for future cost and deployment studies in small- to medium-scale hatchery environments.

### **Candling Workers**

After eggs are manually loaded into individual cradles, the prototype will automate indexed positioning, image capture, classification display, cradle tracking, and downstream sorting. This may reduce repetitive handling and provide workers with immediate decision support while preserving a manual-review path for uncertain cases.

### **Duck Farmers and Production Managers**

Batch-level classification records and session summaries may provide additional information for incubation-space management, flock planning, and review of egg-status trends. These benefits will depend on the accuracy and reliability demonstrated during prototype evaluation.

### **Consumers**

Consumers may benefit indirectly if more consistent hatchery inspection contributes to better process control. The study will not directly measure consumer outcomes or product-quality effects.

### **Philippine Duck Farming Industry**

OvaLens may provide a localized technical reference for integrating deep learning, edge computing, and electromechanical automation in duck hatchery operations. The study is intended as a prototype-level contribution rather than evidence of industry-wide readiness or commercial cost superiority.

### **Researchers and Students**

The study may serve as a reference for future work on localized agricultural computer vision, edge-deployed deep learning, egg-handling automation, and longitudinal candling datasets in Philippine conditions.

## **1.5 Scope and Limitations**

### **Scope**

This study will develop and evaluate OvaLens as a prototype for automated near-real-time candling and sorting of Itik Pinas duck eggs. The system will use a controlled LED candling chamber, fixed camera geometry, Raspberry Pi-based edge processing, and a lightweight YOLOv8 object-detection model. Each valid image will contain an egg-level bounding box assigned to one of three operational classes: Fertile, Infertile, or Abnormal. The bounding box will identify the whole egg and will not be interpreted as localization of a specific internal diagnostic structure. The primary dataset will be collected at one academic-institution-owned research hatchery in Negros Oriental and will represent IP-Itim, IP-Khaki, and IP-Kayumanggi. Data collection will follow the hatchery's Day 10, Day 18, and Day 25 candling schedule. Class frequencies will be recorded as they occur in the actual workflow; the study will not force equal representation of all classes at every stage. Earlier rejected eggs may therefore be absent from later candling sessions. The study will target at least 3,000 locally collected annotated images and will record the number of unique physical eggs, incubation batches, genetic groups, candling stages, and operational class labels represented. Detailed dataset partitioning, annotation agreement procedures, and model-training parameters will be specified in Chapter 3\.  
The operational classes are defined from candling appearance. Fertile refers to an egg showing features consistent with continuing viable embryonic development at the observed stage. Infertile refers to an egg remaining clear or uniformly translucent without visible evidence of embryonic development. Abnormal refers to an egg showing features consistent with non-viable or disrupted development, such as a blood ring, atypical clouding, or another stage-inappropriate internal appearance. These labels are candling-based operational assessments rather than complete embryological diagnoses.  
The physical prototype will use manual egg loading followed by automated indexed transport, imaging, result tracking, and sorting. A primary stepper motor will drive the pocket-conveyor, while auxiliary servos will actuate the class-specific sorting mechanisms.  
The controller will associate each accepted classification with the corresponding cradle as it moves downstream. Invalid or low-confidence detections and synchronization faults will be directed to a manual-review state. The software scope will include a Raspberry Pi desktop application for equipment control and worker feedback and a web-based dashboard for batch logs, class statistics, and session reports. Model evaluation will include egg-level classification performance, standard object-detection metrics, subgroup analysis by genetic group and candling stage, and inference latency.  
The target model inference latency is no more than 200 milliseconds per image on the selected Raspberry Pi deployment, while complete mechanical processing time will be measured separately. Prototype evaluation will include correct sorting, cradle tracking, successful processing cycles, manual-review frequency, processing time, and throughput. In this study, near-real-time means that a valid prediction becomes available during the indexed candling pause and before the egg reaches the point at which its routing decision is required; it does not imply deterministic hard real-time operation.

### **Limitations**

* The dataset will be collected from one research hatchery in Negros Oriental. Findings will therefore be specific to the represented Itik Pinas population, imaging environment, and operational workflow unless independently validated elsewhere.  
* IP-Itim, IP-Khaki, and IP-Kayumanggi may not occur in equal proportions within each incubation batch. Subgroup performance will be reported, but pooled performance will not be interpreted as demonstrated generalization to unrelated duck breeds.  
* The partner hatchery's routine records do not independently distinguish every Infertile case from every Abnormal case. The study will therefore use a written labeling guide, multiple reviewers, hatchery consultation, and later observations or hatch outcomes where feasible. Some ambiguous internal conditions may remain unverifiable without destructive biological examination.  
* The study will evaluate only the Day 10, Day 18, and Day 25 checkpoints used by the partner hatchery. These stages are local operational checkpoints and are not proposed as a universal candling schedule.  
* Reliable image acquisition will depend on controlled illumination and camera geometry. Material changes in lighting, shell appearance, camera placement, or hatchery conditions may require recalibration, validation, or retraining.  
* The prototype will not evaluate external shell defects, compare alternative deep learning architectures, compare alternative conveyor designs, or test whether indexed handling itself improves hatchability.

# **CHAPTER 2**

**REVIEW OF RELATED LITERATURE**

## **2.1 Review of Related Literature**

### **Manual Candling and Non-Destructive Egg Assessment**

Candling uses transmitted light to reveal internal egg conditions associated with fertility and embryonic development without breaking the shell. Recent duck-egg research continues to identify manual candling as labor-intensive, time-consuming, and dependent on operator judgment. Liu et al. (2023) and Li et al. (2023) framed automated hatching-information detection as a response to these limitations, while Philippine work by Maglasang et al. (2025) likewise noted that manual inspection in small- to medium-scale farms can be laborious and prone to error. Cai et al. (2025) and Mulyani et al. (2026) further showed that machine-vision assessment can support repeatable evaluation when images are collected under defined incubation and imaging conditions. These findings support OvaLens's use of controlled candling illumination, fixed camera geometry, explicit operational labels, and a manual-review path for uncertain detections.

### **Itik Pinas Genetic Groups Relevant to the Study**

The three duck groups represented in OvaLens are related Itik Pinas genetic groups rather than unrelated breeds. Santiago et al. (2022) describe IP-Kayumanggi as a commercial hybrid produced from male IP-Khaki and female IP-Itim. DOST-PCAARRD (2022) similarly identifies IP-Itim and IP-Khaki as the Itik Pinas pure lines and IP-Kayumanggi as the commercial line promoted through the national duck research and development program. This relationship supports training one pooled model for the partner hatchery while still reporting subgroup performance to determine whether prediction quality differs among IP-Itim, IP-Khaki, and IP-Kayumanggi.

### **Deep Learning and Computer Vision in Duck-Egg Assessment**

Recent studies demonstrate that convolutional and detection-based models can classify candled duck eggs into operationally meaningful categories. Maglasang et al. (2025) evaluated five transfer-learning CNN backbones on 9,600 candled duck-egg images and reported 97.40% testing accuracy for VGG16 in a fertilized, unfertilized, and rotten classification task. Cai et al. (2025) reported 96.03% overall accuracy for an improved ResNet34 model that classified meat duck eggs as unfertilized, live embryonated, or abnormal. Mulyani et al. (2026) showed that EfficientNet-B3 performance on Cihateup duck eggs changed across incubation ranges and improved materially after image enhancement. Together, these findings support the use of deep learning while reinforcing that performance must be validated on the exact population, stages, imaging setup, and class definitions used by OvaLens.

### **YOLO Architectures for Efficient Object Detection**

YOLO-family detectors combine localization and class prediction in a single inference pipeline, making them relevant to systems that must make decisions while objects are moving through a mechanical workflow. Duck-specific studies have already demonstrated lightweight YOLO variants for hatching assessment. Zhou et al. (2023) used a lightweight YOLOX-Tiny-based detector on duck-egg incubation trays; Liu et al. (2023) developed AFF-YOLOX for early hatching information; Li et al. (2023) developed MobileOne-YOLO from YOLOv7; and Deng et al. (2024) proposed YOLO-Lite for Day 25 dead-embryo detection. OvaLens uses the Ultralytics YOLOv8 software framework (Jocher et al., 2023), but its bounding box represents the entire egg rather than an internal embryo or defect. Detection is retained to verify that an egg is present and positioned within the expected image region before a class and confidence score are accepted.

### **Edge Deployment for Agricultural Vision Systems**

Edge deployment places image processing near the acquisition hardware and can reduce dependence on continuous network connectivity. Chamara et al. (2023) demonstrated an agricultural edge-imaging platform that integrated Raspberry Pi hardware with classification, segmentation, detection, and counting tasks and explicitly measured processing speed and power consumption. Although crop monitoring differs from duck-egg candling, the study supports the feasibility of compact edge hardware for agricultural computer vision. For OvaLens, model suitability will therefore be established through measured inference latency on the selected Raspberry Pi configuration rather than through desktop or GPU results alone.

### **Mechanical Handling, Transport, and Egg Safety**

Automated inspection also requires attention to physical handling. Torma and Gaal (2024) reported hatchability differences associated with vibration and packaging during hatching-egg transport. Their work concerns transported chicken hatching eggs and does not directly prove that any specific duck-egg conveyor will improve or reduce hatchability. It nevertheless supports treating vibration and abrupt movement as engineering risks. OvaLens therefore uses indexed cradle movement, controlled stopping at the candling station, positional synchronization, and a gentler release path for eggs classified as Fertile as precautionary design measures.

## **2.2 Review of Related Studies**

***Liu et al. (2023) \- AFF-YOLOX: An Improved Lightweight YOLOX Network to Detect Early Hatching Information of Duck Eggs***

Liu et al. (2023) proposed AFF-YOLOX for detecting early hatching information from multiple duck eggs on standard incubation trays. The model incorporated attention-based feature fusion and network simplification to improve speed while maintaining detection quality. It achieved 97.55% mAP, reduced the model to approximately 0.49 million parameters, and reported 178 ms latency per image. The study is directly relevant to OvaLens because it demonstrates that lightweight YOLO-family detection can support time-sensitive duck-egg hatching assessment. OvaLens differs by using one controlled candling image per cradle, three operational classes, later hatchery checkpoints, and Raspberry Pi-based deployment with downstream physical sorting.

***Li et al. (2023) \- MobileOne-YOLO: Improving the YOLOv7 Network for the Detection of Unfertilized Duck Eggs and Early Duck Embryo Development***

Li et al. (2023) developed MobileOne-YOLO to identify unfertilized eggs, dead embryos, and healthy embryos from duck eggs inspected on Day 10\. The model achieved 98.10% detection accuracy, 98.55% precision and recall, 97.79% mAP50, and 142.8 FPS on the reported test configuration. The study is particularly relevant because its three biological states closely resemble OvaLens's Fertile, Infertile, and Abnormal operational categories. However, OvaLens will evaluate a locally collected Itik Pinas dataset across Day 10, Day 18, and Day 25 and will explicitly associate each accepted prediction with a physical conveyor cradle for sorting.

***Zhou et al. (2023) \- Evaluation of Duck Egg Hatching Characteristics with a Lightweight Multi-Target Detection Method***

Zhou et al. (2023) proposed a lightweight multi-target detector based on YOLOX-Tiny for identifying hatching characteristics of duck eggs on incubation trays. The reported model achieved 99.74% mAP, operated at 57 FPS, and reduced the parameter count to approximately 1.93 million. The study provides a strong precedent for lightweight duck-egg object detection where multiple eggs must be located and assessed efficiently. OvaLens differs because it uses a single-egg controlled chamber, whole-egg detection as an image-validity check, and cradle-level result tracking through an indexed sorting mechanism.

***Galos and Saminiano (2024) \- Real-Time “Balut” Smart Incubator Egg Assessment Using Convolutional Neural Network***

Galos and Saminiano (2024) developed a Philippine smart-incubator system that used a camera and CNN to distinguish Balut and Penoy eggs. Their evaluation reported 99.5% precision, 99.9% recall, a 99.7% F1 score, and a 98.89% device-functionality rate during an 18-day incubation assessment. This study is important to OvaLens because it is a recent Philippine duck-egg automation project that connects computer vision with incubation hardware. OvaLens extends the problem from a two-status incubator assessment to three operational classes, three hatchery candling checkpoints, explicit object detection, conveyor tracking, and automated routing to separate collection trays.

***Deng et al. (2024) \- Nondestructive Testing of Duck Eggs During Incubation Using YOLO-Lite***

Deng et al. (2024) designed an image-acquisition setup for duck eggs removed from incubation trays on Day 25 and proposed a simplified YOLOv4-based detector called YOLO-Lite for identifying dead embryos. The model reported 98.33% average recognition accuracy, 94.12% recall, and approximately 15 ms single-frame recognition time. This study is highly relevant to OvaLens because Day 25 is one of the partner hatchery's actual candling checkpoints and because the work demonstrates lightweight late-stage duck-egg detection. OvaLens differs by evaluating three classes across multiple stages and integrating prediction acceptance with cradle synchronization and sorting decisions.

***Maglasang et al. (2025) \- Duck Egg Embryonic Development Classification Using Transfer Learning and CNN***

Maglasang et al. (2025) classified Philippine candled duck eggs as fertilized, unfertilized, or rotten using five transfer-learning CNN backbones. Their dataset contained 9,600 images, and VGG16 achieved 97.40% testing accuracy after the authors applied image preprocessing and augmentation. The work is a strong local benchmark because it uses Philippine duck-egg imagery and a three-category formulation that is operationally close to OvaLens. OvaLens differs by using object detection instead of image classification alone, evaluating the specific Itik Pinas genetic groups maintained by the partner hatchery, and measuring the performance of the complete tracking-and-sorting workflow.

***Cai et al. (2025) \- Detection of Hatching Information of Meat Duck Eggs Based on Deep Learning***

Cai et al. (2025) used an improved ResNet34 architecture with attention mechanisms to classify meat duck eggs as unfertilized, live embryonated, or abnormal. The optimized network achieved 96.03% overall classification accuracy and was designed for early-to-middle incubation assessment. Its three-status formulation is closely aligned with OvaLens's operational classes and supports treating abnormal development separately from simple infertility. OvaLens differs by using a YOLOv8 detector, evaluating the partner hatchery's Day 10, Day 18, and Day 25 sessions, and incorporating a manual-review state when confidence or cradle synchronization is insufficient.

***Alpeisov et al. (2025) \- Using an Optoelectronic Method for the Non-Destructive Sorting of Hatching Duck Eggs***

Alpeisov et al. (2025) developed a stationary optoelectronic system specifically adapted to Adigel duck eggs. The setup combined image processing with weight and distance sensing to classify eggs for incubation suitability. Automatic and manual measurements showed correlations above 0.95 with mean relative error below 2%, and the reported overall classification accuracy was 97.7%. Although the study evaluates pre-incubation morphometric suitability rather than candled fertility, it is relevant because it demonstrates recent duck-specific non-destructive sorting and emphasizes that duck morphology and reflectivity require dedicated calibration. OvaLens instead focuses on internal candling appearance during incubation and routes eggs according to Fertile, Infertile, or Abnormal status.

***Mulyani et al. (2026) \- Classification of Cihateup Duck Egg Fertility Using Convolutional Neural Network EfficientNet-B3***

Mulyani et al. (2026) evaluated EfficientNet-B3 on Cihateup duck-egg candling images collected during the first 24 hours and Days 8-15. With image enhancement, the model achieved 77% and 80% accuracy for the two incubation ranges, respectively, while performance without enhancement was substantially lower. The study is relevant because it demonstrates that incubation stage and image preparation can materially affect fertility-classification performance. OvaLens therefore treats stage as an explicit dataset attribute and will report performance separately for Day 10, Day 18, and Day 25 rather than relying only on one pooled accuracy value.

***Flores (2026) \- Lightweight Vision Models for Egg Fertility Detection***

Flores (2026) optimized a YOLOv11 model for fertility detection using locally collected images of native Philippine chicken eggs and reported improvements in mAP50-95, precision, recall, and inference speed after hyperparameter tuning. Although the species differs from OvaLens, the study is relevant as a recent Philippine example of lightweight YOLO-based fertility detection using locally generated poultry imagery. OvaLens extends this local computer-vision direction to Itik Pinas duck eggs and combines the detector with candling hardware, cradle tracking, manual-review handling, and automated sorting.

## **2.3 Synthesis**

The recent studies reviewed from 2023 to 2026 show a clear movement from manual duck-egg candling toward controlled imaging, CNN-based classification, lightweight YOLO-family detection, and automated or optoelectronic sorting. Liu et al. (2023), Li et al. (2023), Zhou et al. (2023), and Deng et al. (2024) demonstrate that lightweight object detection can identify duck-egg hatching conditions with high reported accuracy and practical inference speed. Philippine studies by Galos and Saminiano (2024) and Maglasang et al. (2025) provide locally relevant evidence that computer vision can support Balut/Penoy or embryonic-development assessment, while Flores (2026) demonstrates the continuing use of YOLO-based fertility detection on locally collected Philippine poultry imagery.  
The literature also indicates that strong model metrics do not automatically establish performance under a different hatchery workflow. Cai et al. (2025) use a three-status formulation similar to OvaLens, Mulyani et al. (2026) shows that stage and image preparation affect results, and Alpeisov et al. (2025) emphasizes the need for duck-specific calibration in non-destructive sorting. The studies differ in duck population, incubation day, image-acquisition geometry, class definitions, model architecture, hardware, and system objective. Their metrics therefore provide technical benchmarks rather than directly transferable performance expectations.  
OvaLens addresses a specific combination of gaps: a locally collected Itik Pinas dataset representing IP-Itim, IP-Khaki, and IP-Kayumanggi; evaluation across the partner hatchery's Day 10, Day 18, and Day 25 workflow; three operational classes of Fertile, Infertile, and Abnormal; whole-egg YOLOv8 detection; Raspberry Pi edge inference; cradle-level result tracking; manual-review handling; and automatic downstream sorting. The study will evaluate both model performance and the integrated electromechanical workflow so that system success is based not only on prediction accuracy but also on whether the prototype preserves egg-to-result association, routes eggs correctly, and operates with measurable processing time and throughput under controlled hatchery trials.

# **REFERENCES**

Alpeisov, S., Moldazhanov, A., Kulmakhambetova, A., Azizov, A., Otebayev, Z., & Zinchenko, D. (2025). Using an optoelectronic method for the non-destructive sorting of hatching duck eggs. AgriEngineering, 7(12), 411\. https://doi.org/10.3390/agriengineering7120411  
Cai, J., Li, Y., Ji, Y., Xu, M., Liu, Z., Wang, Y., Wang, H., Duan, E., Huo, L., Liu, Y., Zhang, Y., Huan, H., Han, G., & Bai, Z. (2025). Detection of hatching information of meat duck eggs based on deep learning. Animals, 15(23), 3400\. https://doi.org/10.3390/ani15233400  
Chamara, N., Bai, G., & Ge, Y. (2023). AICropCAM: Deploying classification, segmentation, detection, and counting deep-learning models for crop monitoring on the edge. Computers and Electronics in Agriculture, 215, 108420\. https://doi.org/10.1016/j.compag.2023.108420  
Deng, G., Guo, J., & Li, Q. (2024). Nondestructive testing of duck eggs during incubation using YOLO-Lite. Ukrainian Journal of Physical Optics, 25(2), 02021-02035. https://doi.org/10.3116/16091833/Ukr.J.Phys.Opt.2024.02021  
Department of Science and Technology-Philippine Council for Agriculture, Aquatic and Natural Resources Research and Development. (2022, April 27). Itik for life program for sustainability of Philippine duck industry. https://ispweb.pcaarrd.dost.gov.ph/itik-for-life-program-for-sustainability-of-philippine-duck-industry/  
Flores, E. J. (2026). Lightweight vision models for egg fertility detection. Engineering, Technology & Applied Science Research, 16(1), 31618-31623. https://doi.org/10.48084/etasr.15693  
Galos, J., & Saminiano, B. L. (2024). Real-time “Balut” smart incubator egg assessment using convolutional neural network. In 2024 5th International Conference on Industrial Engineering and Artificial Intelligence (IEAI) (pp. 53-60). IEEE. https://doi.org/10.1109/IEAI62569.2024.00018  
Jocher, G., Chaurasia, A., & Qiu, J. (2023). Ultralytics YOLOv8 (Version 8.0.0) \[Computer software\]. https://github.com/ultralytics/ultralytics  
Li, Q., Shao, Z., Zhou, W., Su, Q., & Wang, Q. (2023). MobileOne-YOLO: Improving the YOLOv7 network for the detection of unfertilized duck eggs and early duck embryo development \- A novel approach. Computers and Electronics in Agriculture, 214, 108316\. https://doi.org/10.1016/j.compag.2023.108316  
Liu, Y., Xiao, D., Zhou, J., & Zhao, S. (2023). AFF-YOLOX: An improved lightweight YOLOX network to detect early hatching information of duck eggs. Computers and Electronics in Agriculture, 210, 107893\. https://doi.org/10.1016/j.compag.2023.107893  
Maglasang, J. J., Merced, A. C., Penales, L. B., Montemayor, J. J. M., Crisostomo, R. V., Macalisang, H. A. R. C. P., & Maulana, M. M. (2025). Duck egg embryonic development classification using transfer learning and CNN. Smart Agricultural Technology, 11, 100932\. https://doi.org/10.1016/j.atech.2025.100932  
Mulyani, E. D. S., Mufizar, T., Rohpandi, D., Djuliani, A., Rahmatulloh, E., & Rahmat, R. S. A. (2026). Classification of Cihateup duck egg fertility using convolutional neural network EfficientNet-B3. IAES International Journal of Artificial Intelligence, 15(1), 798-809. https://doi.org/10.11591/ijai.v15.i1.pp798-809  
Santiago, R. C., Villareal, K. D., San Agustin, M. M., Balotro, R. B., Rey, C. R., Esguerra, J. P. M., Lambio, A. L., & Magpantay, V. A. (2022). Growth, egg production, and phenotypic characteristics of the commercial hybrid egg-type Philippine Mallard duck (IP Kayumanggi) under intensive management system. Philippine Journal of Science, 151(3), 1287-1296. https://doi.org/10.56899/151.03.40  
Torma, T. A., & Gaal, K. K. (2024). Measuring the mechanical effects of egg transport in field and modelled conditions. Chemical Engineering Transactions, 114, 979-984. https://doi.org/10.3303/CET24114164  
Zhou, J., Liu, Y., Zhou, S., Chen, M., & Xiao, D. (2023). Evaluation of duck egg hatching characteristics with a lightweight multi-target detection method. Animals, 13(7), 1204\. https://doi.org/10.3390/ani13071204  
