# Step 2 Comparative Analysis

## Paper-ready summary

In the Step 2 comparative scenario study, the controlled Defects4J-derived datasets and the larger repository-backed datasets were evaluated with the same retrieval pipeline but with a lightweight 0–2 rubric rather than a strict ground-truth protocol. Across the selected scenarios, the small datasets averaged 1.67 for retrieval concentration, 1.83 for cross-artifact coverage, 2 for explanation usefulness, and 2 for plausibility; the large datasets averaged 1.5, 0.667, 2, and 1.83 on the same dimensions. The small datasets generally yielded more compact and easier-to-interpret rankings, reflecting their narrower vocabulary and controlled artifact sets. The larger repositories produced useful but broader outputs: recommendations often spanned more implementation files and the explanation fields required more manual interpretation. These observations support using Step 1 for strict benchmarking and Step 2 as a complementary behavioral comparison across dataset scale and provenance.

## Compact table format suggestion

Use one compact table with rows grouped by dataset family and trigger type. Suggested columns: Family, Trigger, N, Retrieval concentration (mean), Cross-artifact coverage (mean), Explanation usefulness (mean), Plausibility (mean), Typical artifact types, Representative note.
