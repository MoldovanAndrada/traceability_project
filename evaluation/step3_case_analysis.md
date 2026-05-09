# Step 3 Qualitative Case Analysis

Step 3 complements the quantitative benchmark and comparative analysis with a qualitative case analysis of a small set of representative scenarios. Rather than computing another family-level score, it inspects individual requirement- and code-driven changes end to end: the trigger text, returned artifact types, explanation signals, and whether the resulting trace is plausible and interpretable.

## Selected cases

### C1. traceability_lang — REQ-1

**Selection reason.** Controlled requirement-change case with explicit normalization/capitalization vocabulary; selected as a clean success-oriented example.

#### 1. Trigger

- **Trigger type:** requirement_change (requirement-side)
- **What changed:** US-01 (Normalize+Capitalize): V1: Capitalize only. → V2: Normalize whitespace + remove accents + capitalize via facade.

#### 2. Returned artifacts

- **Returned artifact types:** story, test_case, code, fault
- **Top results overall:**
- R1: `US-01` (story; score=0.7361; confidence=medium/0.6549; terms: 01, capitalize, normalize, us, via; support: lexical, graph, semantic)
- R2: `TC-001` (test_case; score=0.5316; confidence=medium/0.5407; terms: 01, accents, capitalize, normalize, us; support: graph, lexical)
- R3: `TC-003` (test_case; score=0.5289; confidence=medium/0.5368; terms: 01, capitalize, normalize, us, whitespace; support: graph, lexical)
- R4: `TC-004` (test_case; score=0.4991; confidence=medium/0.5082; terms: 01, capitalize, normalize, us; support: graph, lexical)
- R5: `TC-002` (test_case; score=0.4986; confidence=medium/0.5074; terms: 01, capitalize, normalize, us; support: graph, lexical)

- **Top results by type:**
  - story: US-01 (R1); US-13 (R10); US-03 (R17)
  - test_case: TC-001 (R2); TC-003 (R3); TC-004 (R4)
  - code: traceability_lang/code/TextAnalytics.java (R7); traceability_lang/code/TextWrapper.java (R12); traceability_lang/code/StringUtils.java (R18)
  - fault: Bug-04 (R8); Bug-19 (R9); Bug-05 (R13)

#### 3. Explanation signals

- **Top confidence labels:** medium, medium, medium, medium, medium
- **Matched terms:** R1 US-01: 01, capitalize, normalize, us, via; R2 TC-001: 01, accents, capitalize, normalize, us; R3 TC-003: 01, capitalize, normalize, us, whitespace; R4 TC-004: 01, capitalize, normalize, us
- **Support sources:** R1 US-01: lexical, graph, semantic; R2 TC-001: graph, lexical; R3 TC-003: graph, lexical; R4 TC-004: graph, lexical
- **Graph/structural support:** R1 score=1.0 neighbors=0 path=None; R2 score=1.0 neighbors=0 path=None; R3 score=1.0 neighbors=0 path=None; R4 score=1.0 neighbors=0 path=None

#### 4. Interpretation

The ranking is focused: the first results stay in the selected dataset and expose story, test_case, code, fault. The top identifiers (US-01; TC-001; TC-003) and lexical cues (capitalize, normalize, via, accents, whitespace) are semantically aligned with the trigger, so the result is plausible and easy to interpret.

#### 5. Takeaway

This case illustrates a clean scenario-level trace where lexical, semantic, and confidence signals point to the same concern.

### C2. traceability_time_poc_complex — REQ-2

**Selection reason.** Controlled requirement-change case about overflow and 24h wrap; selected because it tends to mix relevant time artifacts with broader temporal utilities.

#### 1. Trigger

- **Trigger type:** requirement_change (requirement-side)
- **What changed:** US-02 (Time Addition): V1: Simple addition. → V2: Proper overflow handling (sec→min→hour, 24h wrap).

#### 2. Returned artifacts

- **Returned artifact types:** test_case, fault
- **Top results overall:**
- R1: `TC-003` (test_case; score=0.6584; confidence=medium/0.6085; terms: 02, overflow, time, us; support: graph, semantic)
- R2: `TC-018` (test_case; score=0.5383; confidence=medium/0.5445; terms: time, us; support: graph, semantic)
- R3: `Bug-03` (fault; score=0.5171; confidence=medium/0.5344; terms: 02, addition, hour, us, wrap; support: lexical, graph, historical_fault_co_location)
- R4: `Bug-04` (fault; score=0.4523; confidence=low/0.4988; terms: 02, hour, overflow, us; support: graph, historical_fault_co_location)
- R5: `TC-022` (test_case; score=0.446; confidence=low/0.4422; terms: 02, hour, time, us; support: graph)

- **Top results by type:**
  - test_case: TC-003 (R1); TC-018 (R2); TC-022 (R5)
  - fault: Bug-03 (R3); Bug-04 (R4); Bug-09	TimeFormatter.java	US-04	Single digit hour not zero padded	String.format("%02d", hour) (R9)
  - story: US-03 (R11)

#### 3. Explanation signals

- **Top confidence labels:** medium, medium, medium, low, low
- **Matched terms:** R1 TC-003: 02, overflow, time, us; R2 TC-018: time, us; R3 Bug-03: 02, addition, hour, us, wrap; R4 Bug-04: 02, hour, overflow, us
- **Support sources:** R1 TC-003: graph, semantic; R2 TC-018: graph, semantic; R3 Bug-03: lexical, graph, historical_fault_co_location; R4 Bug-04: graph, historical_fault_co_location
- **Graph/structural support:** R1 score=1.0 neighbors=0 path=None; R2 score=1.0 neighbors=0 path=None; R3 score=1.0 neighbors=0 path=None; R4 score=1.0 neighbors=0 path=None

#### 4. Interpretation

The output is plausible but broader: the top ranks include test_case, fault, and the leading artifacts (TC-003; TC-018; Bug-03) share useful terms such as overflow, time, addition, hour, wrap. Some lower-ranked results widen to neighboring concepts, making the case partially successful rather than perfectly focused.

#### 5. Takeaway

This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment.

### C3. traceability_math_large - corect final — CODE-Bug-05

**Selection reason.** Code/fault-triggered division-by-zero case; selected to inspect whether code-side evidence leads back to code, tests, and related faults.

#### 1. Trigger

- **Trigger type:** code_change (code-side)
- **What changed:** Bug-05 PrimeChecker.java 1 treated as prime n==1 true n<=1 false

#### 2. Returned artifacts

- **Returned artifact types:** fault, code, test_case, story
- **Top results overall:**
- R1: `Bug-05` (fault; score=0.8557; confidence=high/0.9206; terms: 05, 1, as, bug, false, java; support: semantic, lexical, graph)
- R2: `traceability_math_large - corect final/src/org/apache/commons/math4/PrimeChecker.java` (code; score=0.4702; confidence=low/0.4494; terms: 1, false, java, n, primechecker, true; support: graph)
- R3: `traceability_math_large - corect final/src/org/apache/commons/math4/Fibonacci.java` (code; score=0.3809; confidence=low/0.3682; terms: 1, java, n; support: graph)
- R4: `traceability_math_large - corect final/src/org/apache/commons/math4/Factorial.java` (code; score=0.3792; confidence=low/0.3657; terms: 1, java, n; support: graph)
- R5: `Bug-07` (fault; score=0.3712; confidence=low/0.4041; terms: 1, bug, java, n; support: graph)

- **Top results by type:**
  - fault: Bug-05 (R1); Bug-07 (R5); Bug-06 (R11)
  - code: traceability_math_large - corect final/src/org/apache/commons/math4/PrimeChecker.java (R2); traceability_math_large - corect final/src/org/apache/commons/math4/Fibonacci.java (R3); traceability_math_large - corect final/src/org/apache/commons/math4/Factorial.java (R4)
  - test_case: TC-031 (R6); TC-052 (R15); TC-030 (R16)
  - story: US-02 (R7); US-08 (R14)

#### 3. Explanation signals

- **Top confidence labels:** high, low, low, low, low
- **Matched terms:** R1 Bug-05: 05, 1, as, bug, false, java, n, prime; R2 traceability_math_large - corect final/src/org/apache/commons/math4/PrimeChecker.java: 1, false, java, n, primechecker, true; R3 traceability_math_large - corect final/src/org/apache/commons/math4/Fibonacci.java: 1, java, n; R4 traceability_math_large - corect final/src/org/apache/commons/math4/Factorial.java: 1, java, n
- **Support sources:** R1 Bug-05: semantic, lexical, graph; R2 traceability_math_large - corect final/src/org/apache/commons/math4/PrimeChecker.java: graph; R3 traceability_math_large - corect final/src/org/apache/commons/math4/Fibonacci.java: graph; R4 traceability_math_large - corect final/src/org/apache/commons/math4/Factorial.java: graph
- **Graph/structural support:** R1 score=1.0 neighbors=0 path=None; R2 score=1.0 neighbors=0 path=None; R3 score=1.0 neighbors=0 path=None; R4 score=1.0 neighbors=0 path=None

#### 4. Interpretation

The ranking is focused: the first results stay in the selected dataset and expose fault, code, test_case, story. The top identifiers (Bug-05; traceability_math_large - corect final/src/org/apache/commons/math4/PrimeChecker.java; traceability_math_large - corect final/src/org/apache/commons/math4/Fibonacci.java) and lexical cues (false, prime, primechecker, treated, true) are semantically aligned with the trigger, so the result is plausible and easy to interpret.

#### 5. Takeaway

This case illustrates a clean scenario-level trace where lexical, semantic, and confidence signals point to the same concern.

### C4. traceability_lang — CODE-Bug-20

**Selection reason.** Code/fault-triggered language-normalization case; selected as a partially successful case where related string artifacts can broaden the ranking.

#### 1. Trigger

- **Trigger type:** code_change (code-side)
- **What changed:** Bug-20 StringUtils.java normalizeAndCapitalize bypasses LangFacade and misses accent removal return StringFormatter.toFirstUpper(s); return LangFacade.normalizeAndCapitalize(s);

#### 2. Returned artifacts

- **Returned artifact types:** fault, code, test_case
- **Top results overall:**
- R1: `Bug-20` (fault; score=0.8581; confidence=high/0.922; terms: 20, accent, and, bug, bypasses, java; support: semantic, lexical, graph)
- R2: `traceability_lang/code/StringUtils.java` (code; score=0.6517; confidence=medium/0.5888; terms: java, langfacade, normalizeandcapitalize, return, s, stringformatter; support: graph)
- R3: `traceability_lang/code/LangFacade.java` (code; score=0.6499; confidence=medium/0.5904; terms: and, java, langfacade, normalizeandcapitalize, return, s; support: graph, semantic)
- R4: `traceability_lang/code/StringValidator.java` (code; score=0.5788; confidence=medium/0.5507; terms: java, return, s, stringformatter, stringutils; support: graph, semantic)
- R5: `traceability_lang/code/StringFormatter.java` (code; score=0.5778; confidence=medium/0.5483; terms: java, return, s, stringformatter, tofirstupper; support: graph)

- **Top results by type:**
  - fault: Bug-20 (R1); Bug-13 (R6); Bug-03 (R16)
  - code: traceability_lang/code/StringUtils.java (R2); traceability_lang/code/LangFacade.java (R3); traceability_lang/code/StringValidator.java (R4)
  - test_case: TC-003 (R8); TC-001 (R9); TC-004 (R11)
  - story: US-01 (R15); US-12 (R17)

#### 3. Explanation signals

- **Top confidence labels:** high, medium, medium, medium, medium
- **Matched terms:** R1 Bug-20: 20, accent, and, bug, bypasses, java, langfacade, misses; R2 traceability_lang/code/StringUtils.java: java, langfacade, normalizeandcapitalize, return, s, stringformatter, stringutils, tofirstupper; R3 traceability_lang/code/LangFacade.java: and, java, langfacade, normalizeandcapitalize, return, s, stringformatter, tofirstupper; R4 traceability_lang/code/StringValidator.java: java, return, s, stringformatter, stringutils
- **Support sources:** R1 Bug-20: semantic, lexical, graph; R2 traceability_lang/code/StringUtils.java: graph; R3 traceability_lang/code/LangFacade.java: graph, semantic; R4 traceability_lang/code/StringValidator.java: graph, semantic
- **Graph/structural support:** R1 score=1.0 neighbors=0 path=None; R2 score=1.0 neighbors=0 path=None; R3 score=1.0 neighbors=0 path=None; R4 score=1.0 neighbors=0 path=None

#### 4. Interpretation

The output is plausible but broader: the top ranks include fault, code, test_case, and the leading artifacts (Bug-20; traceability_lang/code/StringUtils.java; traceability_lang/code/LangFacade.java) share useful terms such as accent, bypasses, langfacade, misses, normalizeandcapitalize, removal, return, stringformatter. Some lower-ranked results widen to neighboring concepts, making the case partially successful rather than perfectly focused.

#### 5. Takeaway

This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment.

### C5. dataset-api — REQ-1

**Selection reason.** Repository-backed requirement-change case with broad command-schema validation scope; selected to illustrate scale-driven ambiguity and noisy but interpretable links.

#### 1. Trigger

- **Trigger type:** requirement_change (requirement-side)
- **What changed:** US-177 (Command schema validation): V1 baseline behavior. → V2 refined behavior (stricter validation + clearer errors + edge-case handling).

#### 2. Returned artifacts

- **Returned artifact types:** fault, test_case
- **Top results overall:**
- R1: `Bug-045` (fault; score=0.5768; confidence=medium/0.5661; terms: behavior, v1, v2; support: graph, semantic)
- R2: `Bug-021` (fault; score=0.5134; confidence=medium/0.5318; terms: behavior; support: graph, semantic)
- R3: `TC-183` (test_case; score=0.4625; confidence=medium/0.5044; terms: behavior, command, handling, schema, validation; support: lexical, graph)
- R4: `TC-184` (test_case; score=0.4625; confidence=medium/0.5044; terms: behavior, command, handling, schema, validation; support: lexical, graph)
- R5: `TC-185` (test_case; score=0.4625; confidence=medium/0.5044; terms: behavior, command, handling, schema, validation; support: lexical, graph)

- **Top results by type:**
  - fault: Bug-045 (R1); Bug-021 (R2); Bug-254 (R7)
  - test_case: TC-183 (R3); TC-184 (R4); TC-185 (R5)

#### 3. Explanation signals

- **Top confidence labels:** medium, medium, medium, medium, medium
- **Matched terms:** R1 Bug-045: behavior, v1, v2; R2 Bug-021: behavior; R3 TC-183: behavior, command, handling, schema, validation; R4 TC-184: behavior, command, handling, schema, validation
- **Support sources:** R1 Bug-045: graph, semantic; R2 Bug-021: graph, semantic; R3 TC-183: lexical, graph; R4 TC-184: lexical, graph
- **Graph/structural support:** R1 score=1.0 neighbors=0 path=None; R2 score=1.0 neighbors=0 path=None; R3 score=1.0 neighbors=0 path=None; R4 score=1.0 neighbors=0 path=None

#### 4. Interpretation

The retrieval is interpretable but noisy: the top ranks include fault, test_case, yet broad repository vocabulary and generic validation terms spread attention across artifacts such as Bug-045; Bug-021; TC-183; TC-184. The explanation fields help identify why these artifacts surfaced, but the ranking is less decisive.

#### 5. Takeaway

This case illustrates the ambiguity that appears when a broad repository-backed trigger maps to many plausible artifacts.

### C6. dataset-app-frontend — CODE-Bug-015

**Selection reason.** Repository-backed code/fault trigger about option-fetch failures blocking PDF generation; selected to show mixed fault/story retrieval on a realistic UI workflow.

#### 1. Trigger

- **Trigger type:** code_change (code-side)
- **What changed:** Bug-015 com/Altinn/app-frontend-react/pull/3840 Source: https://github.com/Altinn/app-frontend-react/issues/3842 State: OPEN Labels: kind/bug, status/triage Title: Options failing to fetch should block PDF generation Description: ### Description of the bug If an option query fails, the PDF will just show the option value. Instead it should fail and let the user retry. Options are usually simple json files that rarely fail to fetch, however, apps can also implement option lists through code with any kind of external dependency which may fail for unkown reasons. In the browser normally this is not a huge issue, the layout will look a bit weird but the user can always refresh the page. But a PDF generated successfully is permanent, so we should not accept potentially saving incorrect data there. https://github.com/Altinn/app-frontend-react/pull/3840#issuecomment-3502246948 ### Steps To Reproduce 1. Instantiate an app with options and fill it out 2. Go to `?pdf=1` 3. Block the options request in browser dev tools 4. Summary should show the option value (not label) and readyForPrint is present ### Additional Information _No response_

#### 2. Returned artifacts

- **Returned artifact types:** fault, story
- **Top results overall:**
- R1: `Bug-015` (fault; score=0.8674; confidence=medium/0.7271; terms: 015, 1, 2, 3, 3502246948, 3840; support: semantic, lexical, graph)
- R2: `Bug-342` (fault; score=0.6248; confidence=medium/0.5555; terms: 1, 2, 3, 4, _no, a; support: graph)
- R3: `Bug-520` (fault; score=0.6185; confidence=medium/0.553; terms: 1, 2, 3, 4, a, additional; support: graph)
- R4: `Bug-323` (fault; score=0.6151; confidence=medium/0.5495; terms: 1, 2, 3, 4, _no, a; support: graph)
- R5: `Bug-376` (fault; score=0.6126; confidence=medium/0.5512; terms: 1, 2, 3, 4, _no, a; support: graph)

- **Top results by type:**
  - fault: Bug-015 (R1); Bug-342 (R2); Bug-520 (R3)
  - story: US-077 (R9); US-129 (R10); US-032 (R11)

#### 3. Explanation signals

- **Top confidence labels:** medium, medium, medium, medium, medium
- **Matched terms:** R1 Bug-015: 015, 1, 2, 3, 3502246948, 3840, 3842, 4; R2 Bug-342: 1, 2, 3, 4, _no, a, additional, altinn; R3 Bug-520: 1, 2, 3, 4, a, additional, altinn, an; R4 Bug-323: 1, 2, 3, 4, _no, a, additional, altinn
- **Support sources:** R1 Bug-015: semantic, lexical, graph; R2 Bug-342: graph; R3 Bug-520: graph; R4 Bug-323: graph
- **Graph/structural support:** R1 score=1.0 neighbors=0 path=None; R2 score=1.0 neighbors=0 path=None; R3 score=1.0 neighbors=0 path=None; R4 score=1.0 neighbors=0 path=None

#### 4. Interpretation

The output is plausible but broader: the top ranks include fault, story, and the leading artifacts (Bug-015; Bug-342; Bug-520) share useful terms such as app. Some lower-ranked results widen to neighboring concepts, making the case partially successful rather than perfectly focused.

#### 5. Takeaway

This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment.

## Synthesis

Across the cases, the retrieval framework is most convincing when the trigger contains specific domain terms or identifiers that align with code, tests, and faults. The same explanation fields remain useful on noisier repository-backed inputs, but rankings become broader and require more analyst interpretation because many artifacts share generic validation, UI, or schema vocabulary.

## Compact table suggestion

| Case | Trigger type | Dataset | Returned types | Main observation |
|---|---|---|---|---|
| C1 | requirement_change | traceability_lang | story, test_case, code, fault | This case illustrates a clean scenario-level trace where lexical, semantic, and confidence signals point to the same concern. |
| C2 | requirement_change | traceability_time_poc_complex | test_case, fault | This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment. |
| C3 | code_change | traceability_math_large - corect final | fault, code, test_case, story | This case illustrates a clean scenario-level trace where lexical, semantic, and confidence signals point to the same concern. |
| C4 | code_change | traceability_lang | fault, code, test_case | This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment. |
| C5 | requirement_change | dataset-api | fault, test_case | This case illustrates the ambiguity that appears when a broad repository-backed trigger maps to many plausible artifacts. |
| C6 | code_change | dataset-app-frontend | fault, story | This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment. |
