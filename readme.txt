Regression testing change impact analysis: a proof of concept using a LIGHTWEIGHT multi-agent systema rchitecture
traceability driven regression selection. more like a Semantic Change Impact Analysis Framework / EVENT-DRIVEN 

cum rulezi?: intai rulezy jupyter pt a calcula similaritatile, apoi main.py pt a porni watcherul 
PT FIX erori de path main-ul trebuie rulat asa: python -m src.main

Troubleshooting TensorFlow/Keras startup errors
-----------------------------------------------
The embedding model is provided by Sentence Transformers and uses its PyTorch
backend. Transformers may also discover an unrelated TensorFlow installation and
try to initialize it, producing oneDNN messages, deprecated tf.losses warnings,
or a TensorFlow/Keras compatibility traceback before this application starts.
The application now sets USE_TF=0 before importing Sentence Transformers, which
prevents that unused optional backend from loading. TensorFlow is not required by
this project; the messages do not indicate a failure in the embedding model.



goal: A Multi-Agent AI Architecture for Automated Regression Testing and Fault Localization - este O LUCRARE CARE ARE ACEST NUME - graph-based program dependency analysis, test prioritization agent  -> https://www.researchgate.net/profile/Micheal-James/publication/394464415_A_Multi-Agent_AI_Architecture_for_Automated_Regression_Testing_and_Fault_Localization/links/689c71e4a645d8252ba43a0f/A-Multi-Agent-AI-Architecture-for-Automated-Regression-Testing-and-Fault-Localization.pdf 

synthetic dataset by design - because real datasets do not model requirements or functional tests.
This system isolates the traceability problem.
Java application: because like python, the fact that it is close to English make it easier for the LLM to associate stories to the code
future work: explore more programming language, understand which ones are best fits, larger systems, real-project implementation

- future work: the ideal setting has nodes as platforms such as testrail/jira for user stories and test cases, retrieving them via api keys 
-COD: defects4j common lang - due to simplicity
pentru modificare in user stories cu cautare in code... The AI will output:
-pt watcher am folosit un simplu process ce ruleaza in main.py (?), dar se poate face cu webhooks??

am ajuns la concluzia ca pt credibilitate si practice approapiation voi folosi defects4j: cel mai simplu si bine documentat proiect pt care se pot genera automat tcs si rescrie documentatia bazat pe Javadoc -> commons-lang 
-> se va folosi o singura clasa de cod (referentiat, pt ca intreaga clasa e prea mult) - StringUtils

documentatia privine din documentatia oficiala: https://commons.apache.org/proper/commons-lang/apidocs/org/apache/commons/lang3/StringUtils.html

TODO next: 1.toggle from tests/from stories
2. sa extindem la ~5 proiecte asemanatoare (pt ENASE 3 - inca 2 defects 4j)
3. tool (de exemplu plugin)
