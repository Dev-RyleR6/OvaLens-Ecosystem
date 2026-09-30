# Title Page, Approval Sheet, Acknowledgment & Executive Summary

---

# **OVALENS: A YOLOV8-BASED DEEP LEARNING SYSTEM FOR AUTOMATED NEAR-REAL-TIME CANDLING AND SORTING OF ITIK PINAS DUCK EGGS**

A Capstone Project

Presented to the Faculty of the  
College of Computer Studies  
**Foundation University**  
Dumaguete City, Negros Oriental  

In Partial Fulfillment of the Requirements for the Degree of  
**Bachelor of Science in Information Technology**  

**Prepared by:**  
* Ryle Anthony Gabotero M.  
* Olsen Nathaniel Cafino  
* Neil Allen Faburada  

**2026**

---

# **APPROVAL SHEET**

This capstone project entitled **"OvaLens: A YOLOv8-Based Deep Learning System for Automated Near-Real-Time Candling and Sorting of Itik Pinas Duck Eggs,"** prepared and submitted by **Ryle Anthony Gabotero M.**, **Olsen Nathaniel Cafino**, and **Neil Allen Faburada**, in partial fulfillment of the requirements for the degree of **Bachelor of Science in Information Technology**, has been examined and is hereby recommended for acceptance and approval for oral examination.

________________________________________  
**Mr. Andrew Mores**  
*Capstone Adviser*

Approved by the Panel of Examiners on the Oral Examination.

Grade: _____________.

________________________________________  
*Panel Chair*

| ________________________________________ Panel Member | ________________________________________ Panel Member |
| :---: | :---: |

Accepted and approved in partial fulfillment of the requirements for the degree of Bachelor of Science in Information Technology.

________________________________________  
**Sheena Mae Sab Sabado**  
*Dean, College of Computer Studies*

---

# **ACKNOWLEDGMENT**

The researchers wish to extend their deepest gratitude to everyone who has contributed to the development and preparation of this capstone project.  

First and foremost, to **Almighty God**, for the wisdom, strength, and perseverance granted throughout the duration of this study.  

To **Mr. Andrew Mores**, the researchers' capstone adviser, for the invaluable guidance, patience, and constructive feedback extended throughout the conceptualization and refinement of OvaLens, including recommendations that helped shape the proposed hardware architecture and research methodology.  

To the **panel of examiners**, for their insightful critiques and recommendations that helped strengthen the direction and technical soundness of this study.  

To **Dean Sheena Mae Sab Sabado** and the faculty and staff of the **College of Computer Studies, Foundation University**, for the knowledge and technical foundation imparted throughout the researchers' academic journey.  

To the **management and staff of the partner research hatchery in Negros Oriental**, for graciously accommodating the researchers during data-gathering sessions and for sharing their expertise in duck egg candling practices.  

To the researchers' **families and friends**, for their unwavering support, encouragement, and understanding during the demanding periods of this project.  

And finally, to us, **Team DevIn — Ryle, Olsen, and Neil** — for the collective dedication, coordination, and shared commitment devoted to developing a locally relevant and technically sound capstone project.

---

# **EXECUTIVE SUMMARY**

Duck egg candling is a non-destructive inspection process used to assess fertility and embryonic development by directing light through the eggshell. In many Philippine hatchery settings, candling remains manual and depends on worker experience, sustained visual attention, and repeated handling, creating a need for more consistent image-based decision support.  

This capstone project proposes **OvaLens**, a YOLOv8-based deep learning system for automated near-real-time candling and sorting of Itik Pinas duck eggs at a partner research hatchery in Negros Oriental. The study utilizes locally collected images from **IP-Itim** and **IP-Khaki**, the two Itik Pinas pure lines, and **IP-Kayumanggi**, their commercial hybrid, focused on the critical **Day 10** candling schedule—the definitive Philippine milestone separating viable incubation eggs from commercial Penoy salvage (₱14.00/egg). Each egg is annotated with a whole-egg bounding box and classified into two operational classes: **Fertile** (continued incubation) or **Infertile** (Penoy salvage/culling), with automated manual-review routing for low-confidence captures ($\tau < 0.75$). Object detection is used to verify egg presence and position before a sorting decision is accepted.  

The prototype will combine a controlled LED candling chamber, Raspberry Pi-based edge inference, and an indexed pocket-conveyor with stepper-driven transport and servo-actuated sorting. Eggs will be manually loaded into individual cradles, tracked from imaging to sorting, and routed to the appropriate tray. Invalid or low-confidence detections will require manual review. A desktop control application will manage the mechanism and display current results, while a web-based dashboard will provide batch logs and summary statistics.  

The study will target at least 3,000 locally collected annotated images while recording unique eggs, incubation batches, genetic groups, stages, and observed class distributions. Model evaluation will include egg-level classification measures, mAP, and inference latency, while system evaluation will include sorting accuracy, cradle-tracking reliability, successful processing cycles, processing time, throughput, and manual-review frequency. In this study, near-real-time means that a valid prediction becomes available during the indexed candling pause and before the egg reaches the point where its routing decision is required. OvaLens aims to provide a locally grounded reference for deep learning-assisted duck egg candling and automated sorting in a Philippine hatchery context.

---

# **TABLE OF CONTENTS**

| Section / Chapter | Page |
| :--- | :---: |
| **APPROVAL SHEET** | i |
| **ACKNOWLEDGMENT** | ii |
| **EXECUTIVE SUMMARY** | iii |
| **TABLE OF CONTENTS** | iv |
| **CHAPTER 1  INTRODUCTION** | 1 |
| 1.1 Rationale of the Study | 1 |
| 1.2 Statement of the Problem | 3 |
| 1.3 Objectives of the Study | 4 |
| 1.3.1 General Objective | 4 |
| 1.3.2 Specific Objectives | 4 |
| 1.4 Significance of the Study | 5 |
| 1.5 Scope and Limitations | 7 |
| **CHAPTER 2  REVIEW OF RELATED LITERATURE** | 10 |
| 2.1 Review of Related Literature | 10 |
| 2.2 Review of Related Studies | 13 |
| 2.3 Synthesis | 17 |
| **CHAPTER 3  TECHNICAL METHODOLOGY** | 20 |
| **REFERENCES** | 35 |
