# SB26 OpenReview submission fields

Form: https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/SB26_Challenge (the Submission invitation stays open until 2027-01-15 03:00 UTC). Round one closes Nov 13 AoE = 2026-11-14 11:59 UTC (organizer, Kaggle topic 757845); round-one main text 4-8 pages excluding references and appendix (organizer, topic 757604).

**PDF:** `submission/SB26_paper_polished.pdf` (identical to `paper/main.pdf`)

**Title:** Schedule-Aware Demand-Based Reset: A Structured Rule-Based Controller for Cross-Building HVAC Transfer

**Authors:** Neel Sirivara (University of Washington)

**Keywords:** HVAC control, building energy, rule-based control, transfer to unseen buildings, reward misspecification, CMA-ES

**TL;DR (≤250 chars):** A rule-based HVAC controller built from plant topology and physics transfers to unseen buildings, beats the strongest baseline 7.5x, and shows that black-box tuning exploits a reward with no frost cost.

**Abstract:**

HVAC controllers rarely move between buildings without being re-identified or re-tuned for each site. We study a setting in which transfer is the whole problem: a single policy runs procedurally generated office buildings it has never seen, under weather it has not seen, and is scored on occupant comfort, energy cost and carbon. We propose SADR (Schedule-Aware Demand-Based Reset), a deterministic rule-based controller that reads the plant topology from the building metadata and otherwise encodes only physics that every generated building shares. Three properties of the plant and reward shape most of its design: comfort is charged only while occupants are present, supply air can only be cooled, so all heat enters through reheat coils at a gas price with a closed form, and fan power grows with the 3/2 power of static pressure. On the 30 public scenarios the final controller scores 0.00730 (lower is better), about 7.5 times below the strongest organizer baseline, and in a leave-one-out ablation supplying the coldest air at the lowest flow is the largest single contributor. From the third development round on, a change was accepted only under a rule fixed before its confirmation runs, on buildings or weather not used to choose it. Tuning the constants with CMA-ES suggests a lesson that reaches beyond this benchmark: a reward that charges nothing for an empty building far below freezing is exploited through whichever constants remain free, so a physical constraint missing from the reward has to enter the selection rule. The remaining loss is mostly gas spent in deep cold.

**Consents:** tick both (author emails shared with PCs; release on acceptance).
