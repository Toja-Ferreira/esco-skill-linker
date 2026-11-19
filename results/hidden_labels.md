# Hidden labels in the skill documents

A is `labels_desc` as deployed, B adds each skill's hidden labels to BM25 only, C adds them to BM25 and EmbeddingGemma. Hybrid is weighted score fusion at the deployed BM25 weights (0.4 English, 0.3 Portuguese). Test queries, scored once. Intervals are 95% percentile bootstrap over queries, paired. The decision rule is in `experiments/17_hidden_labels.py`.

## Sizes

| language | hidden labels | skills with hidden | documents changed | skills adding new tokens | all | affected | triggered-gold-new | triggered-nongold-new |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| en | 1,095 | 153 | 153 | 127 | 608 | 148 | 12 | 550 |
| pt | 569 | 30 | 30 | 26 | 608 | 44 | 2 | 132 |

## Test results

### en

| system | variant | slice | queries | nDCG@10 | P@10 | R@10 | MRR |
|---|---|---|---:|---:|---:|---:|---:|
| hybrid | A | all | 608 | 0.3794 | 0.2916 | 0.1554 | 0.6998 |
| hybrid | A | affected | 148 | 0.3923 | 0.3054 | 0.1348 | 0.7091 |
| hybrid | A | triggered-gold-new | 12 | 0.3725 | 0.2833 | 0.0986 | 0.7071 |
| hybrid | A | triggered-nongold-new | 550 | 0.3751 | 0.2884 | 0.1539 | 0.6911 |
| hybrid | B | all | 608 | 0.3794 | 0.2916 | 0.1554 | 0.6998 |
| hybrid | B | affected | 148 | 0.3922 | 0.3054 | 0.1348 | 0.7090 |
| hybrid | B | triggered-gold-new | 12 | 0.3725 | 0.2833 | 0.0986 | 0.7071 |
| hybrid | B | triggered-nongold-new | 550 | 0.3751 | 0.2884 | 0.1539 | 0.6911 |
| hybrid | C | all | 608 | 0.3793 | 0.2916 | 0.1554 | 0.6990 |
| hybrid | C | affected | 148 | 0.3917 | 0.3054 | 0.1348 | 0.7058 |
| hybrid | C | triggered-gold-new | 12 | 0.3725 | 0.2833 | 0.0986 | 0.7071 |
| hybrid | C | triggered-nongold-new | 550 | 0.3749 | 0.2884 | 0.1539 | 0.6901 |
| bm25 | A | all | 608 | 0.3252 | 0.2498 | 0.1339 | 0.6107 |
| bm25 | A | affected | 148 | 0.3276 | 0.2541 | 0.1100 | 0.6068 |
| bm25 | A | triggered-gold-new | 12 | 0.3625 | 0.2750 | 0.0897 | 0.6719 |
| bm25 | A | triggered-nongold-new | 550 | 0.3205 | 0.2464 | 0.1318 | 0.6021 |
| bm25 | B | all | 608 | 0.3251 | 0.2498 | 0.1339 | 0.6110 |
| bm25 | B | affected | 148 | 0.3272 | 0.2541 | 0.1100 | 0.6067 |
| bm25 | B | triggered-gold-new | 12 | 0.3607 | 0.2750 | 0.0897 | 0.6715 |
| bm25 | B | triggered-nongold-new | 550 | 0.3205 | 0.2464 | 0.1318 | 0.6024 |

### pt

| system | variant | slice | queries | nDCG@10 | P@10 | R@10 | MRR |
|---|---|---|---:|---:|---:|---:|---:|
| hybrid | A | all | 608 | 0.3439 | 0.2620 | 0.1379 | 0.6539 |
| hybrid | A | affected | 44 | 0.4063 | 0.3159 | 0.1525 | 0.7503 |
| hybrid | A | triggered-gold-new | 2 | 0.2419 | 0.2500 | 0.1190 | 0.2679 |
| hybrid | A | triggered-nongold-new | 132 | 0.3409 | 0.2477 | 0.1369 | 0.6587 |
| hybrid | B | all | 608 | 0.3438 | 0.2622 | 0.1380 | 0.6528 |
| hybrid | B | affected | 44 | 0.4067 | 0.3182 | 0.1535 | 0.7473 |
| hybrid | B | triggered-gold-new | 2 | 0.2419 | 0.2500 | 0.1190 | 0.2679 |
| hybrid | B | triggered-nongold-new | 132 | 0.3404 | 0.2485 | 0.1372 | 0.6539 |
| hybrid | C | all | 608 | 0.3438 | 0.2622 | 0.1380 | 0.6528 |
| hybrid | C | affected | 44 | 0.4067 | 0.3182 | 0.1535 | 0.7473 |
| hybrid | C | triggered-gold-new | 2 | 0.2419 | 0.2500 | 0.1190 | 0.2679 |
| hybrid | C | triggered-nongold-new | 132 | 0.3404 | 0.2485 | 0.1372 | 0.6539 |
| bm25 | A | all | 608 | 0.2659 | 0.2030 | 0.1072 | 0.5237 |
| bm25 | A | affected | 44 | 0.3143 | 0.2500 | 0.1170 | 0.6087 |
| bm25 | A | triggered-gold-new | 2 | 0.2685 | 0.2000 | 0.0964 | 0.6250 |
| bm25 | A | triggered-nongold-new | 132 | 0.2759 | 0.2015 | 0.1138 | 0.5641 |
| bm25 | B | all | 608 | 0.2659 | 0.2030 | 0.1071 | 0.5236 |
| bm25 | B | affected | 44 | 0.3122 | 0.2477 | 0.1157 | 0.6087 |
| bm25 | B | triggered-gold-new | 2 | 0.2689 | 0.2000 | 0.0964 | 0.6250 |
| bm25 | B | triggered-nongold-new | 132 | 0.2758 | 0.2015 | 0.1136 | 0.5641 |

## Paired differences

Mean per-query difference with its interval; won and lost are the shares of queries where the first variant scored higher and lower.

### en

| system | comparison | slice | n | nDCG@10 | P@10 | R@10 | MRR | won / lost (nDCG@10) |
|---|---|---|---:|---|---|---|---|---:|
| hybrid | B−A | all | 608 | -0.0000 [-0.0001, +0.0001] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [-0.0000, +0.0001] | 0% / 1% |
| hybrid | B−A | affected | 148 | -0.0000 [-0.0005, +0.0004] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0000 [-0.0001, +0.0000] | 1% / 1% |
| hybrid | B−A | triggered-gold-new | 12 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | B−A | triggered-nongold-new | 550 | -0.0000 [-0.0001, +0.0001] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [-0.0000, +0.0001] | 0% / 1% |
| hybrid | C−A | all | 608 | -0.0001 [-0.0004, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0008 [-0.0025, +0.0000] | 0% / 1% |
| hybrid | C−A | affected | 148 | -0.0005 [-0.0017, +0.0001] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0033 [-0.0101, +0.0002] | 1% / 3% |
| hybrid | C−A | triggered-gold-new | 12 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | C−A | triggered-nongold-new | 550 | -0.0002 [-0.0004, -0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0009 [-0.0027, +0.0000] | 0% / 1% |
| hybrid | C−B | all | 608 | -0.0001 [-0.0004, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0008 [-0.0025, +0.0000] | 0% / 0% |
| hybrid | C−B | affected | 148 | -0.0005 [-0.0017, +0.0002] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0033 [-0.0101, +0.0003] | 1% / 1% |
| hybrid | C−B | triggered-gold-new | 12 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | C−B | triggered-nongold-new | 550 | -0.0002 [-0.0005, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0009 [-0.0028, +0.0001] | 0% / 1% |
| bm25 | B−A | all | 608 | -0.0000 [-0.0002, +0.0001] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0003 [-0.0000, +0.0008] | 1% / 1% |
| bm25 | B−A | affected | 148 | -0.0004 [-0.0009, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0000 [-0.0001, +0.0000] | 1% / 3% |
| bm25 | B−A | triggered-gold-new | 12 | -0.0018 [-0.0053, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0005 [-0.0014, +0.0000] | 0% / 8% |
| bm25 | B−A | triggered-nongold-new | 550 | -0.0000 [-0.0002, +0.0002] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0003 [-0.0000, +0.0009] | 1% / 1% |

### pt

| system | comparison | slice | n | nDCG@10 | P@10 | R@10 | MRR | won / lost (nDCG@10) |
|---|---|---|---:|---|---|---|---|---:|
| hybrid | B−A | all | 608 | -0.0001 [-0.0004, +0.0002] | +0.0002 [+0.0000, +0.0005] | +0.0001 [+0.0000, +0.0002] | -0.0010 [-0.0029, +0.0000] | 0% / 0% |
| hybrid | B−A | affected | 44 | +0.0003 [-0.0019, +0.0029] | +0.0023 [+0.0000, +0.0068] | +0.0009 [+0.0000, +0.0028] | -0.0030 [-0.0091, +0.0000] | 2% / 2% |
| hybrid | B−A | triggered-gold-new | 2 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | B−A | triggered-nongold-new | 132 | -0.0005 [-0.0021, +0.0006] | +0.0008 [+0.0000, +0.0023] | +0.0003 [+0.0000, +0.0009] | -0.0048 [-0.0134, +0.0000] | 1% / 2% |
| hybrid | C−A | all | 608 | -0.0001 [-0.0004, +0.0002] | +0.0002 [+0.0000, +0.0005] | +0.0001 [+0.0000, +0.0002] | -0.0010 [-0.0029, -0.0000] | 0% / 0% |
| hybrid | C−A | affected | 44 | +0.0003 [-0.0019, +0.0029] | +0.0023 [+0.0000, +0.0068] | +0.0009 [+0.0000, +0.0028] | -0.0030 [-0.0091, +0.0000] | 2% / 2% |
| hybrid | C−A | triggered-gold-new | 2 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | C−A | triggered-nongold-new | 132 | -0.0005 [-0.0021, +0.0006] | +0.0008 [+0.0000, +0.0023] | +0.0003 [+0.0000, +0.0009] | -0.0048 [-0.0134, +0.0000] | 1% / 2% |
| hybrid | C−B | all | 608 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | -0.0000 [-0.0000, +0.0000] | 0% / 0% |
| hybrid | C−B | affected | 44 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | C−B | triggered-gold-new | 2 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| hybrid | C−B | triggered-nongold-new | 132 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0% / 0% |
| bm25 | B−A | all | 608 | -0.0000 [-0.0003, +0.0003] | -0.0000 [-0.0005, +0.0005] | -0.0000 [-0.0003, +0.0002] | -0.0001 [-0.0002, +0.0000] | 1% / 1% |
| bm25 | B−A | affected | 44 | -0.0021 [-0.0061, +0.0008] | -0.0023 [-0.0068, +0.0000] | -0.0013 [-0.0040, +0.0000] | +0.0000 [+0.0000, +0.0000] | 5% / 7% |
| bm25 | B−A | triggered-gold-new | 2 | +0.0004 [+0.0000, +0.0009] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 50% / 0% |
| bm25 | B−A | triggered-nongold-new | 132 | -0.0001 [-0.0016, +0.0015] | -0.0000 [-0.0023, +0.0023] | -0.0002 [-0.0013, +0.0008] | +0.0000 [+0.0000, +0.0000] | 5% / 2% |

## Weight dev would select

BM25's weight in the hybrid, swept on dev by nDCG@10. Reported, not adopted.

| language | variant | dev-selected weight | dev nDCG@10 | deployed weight | dev nDCG@10 at deployed |
|---|---|---:|---:|---:|---:|
| en | A | 0.4 | 0.3797 | 0.4 | 0.3797 |
| en | B | 0.4 | 0.3796 | 0.4 | 0.3796 |
| en | C | 0.4 | 0.3796 | 0.4 | 0.3796 |
| pt | A | 0.3 | 0.3381 | 0.3 | 0.3381 |
| pt | B | 0.3 | 0.3380 | 0.3 | 0.3380 |
| pt | C | 0.3 | 0.3380 | 0.3 | 0.3380 |

## Course-text probe

Rank of each expected skill in the fused top 50; blank is not in the top 50.

| language | sentence | course | expected skill | A | B | C |
|---|---|---|---|---:|---:|---:|
| en | The course aims to develop students' ability to understand, design and implement programmes in C language, applying structured programming principles. | Programming | computer programming | 9 | 11 | 17 |
| en | The aim is for students to become autonomous in the use of Unix/Linux environments, master the process of compilation and execution via command line, and understand the complete software development cycle. | Programming | operating systems |  |  |  |
| en | The aim is for students to become autonomous in the use of Unix/Linux environments, master the process of compilation and execution via command line, and understand the complete software development cycle. | Programming | systems development life-cycle |  |  |  |
| en | By the end of the course, students should be able to analyse problems, break down solutions into functions and modules, use control structures, arrays, pointers, strings and data structures appropriately, and manipulate files and dynamic memory. | Programming | computer programming | 22 | 22 | 34 |
| en | By the end of the course, students should be able to analyse problems, break down solutions into functions and modules, use control structures, arrays, pointers, strings and data structures appropriately, and manipulate files and dynamic memory. | Programming | task algorithmisation |  |  |  |
| en | The course also aims to foster good practices in organisation, documentation and code testing, promoting the rigour and clarity essential to engineering programming. | Programming | implement ICT coding conventions | 1 | 1 | 1 |
| en | The course also aims to foster good practices in organisation, documentation and code testing, promoting the rigour and clarity essential to engineering programming. | Programming | execute software tests |  |  |  |
| en | The C Programming course introduces the fundamentals of structured programming, integrating the use of Unix/Linux systems and command line compilation. | Programming | computer programming | 4 | 6 | 6 |
| en | The C Programming course introduces the fundamentals of structured programming, integrating the use of Unix/Linux systems and command line compilation. | Programming | operating systems |  | 45 |  |
| en | The essential concepts of the C language are covered: programme structure, data types, operators and flow control. | Programming | computer programming | 7 | 7 | 8 |
| en | Skills are developed in modularisation with functions, use of arrays, pointers, strings and structures (struct). | Programming | computer programming | 16 | 16 | 19 |
| en | It also includes working with text and binary files, command line arguments and dynamic memory, culminating in the organisation of programmes in multiple files using make. | Programming | computer programming | 6 | 6 | 10 |
| en | The course aims to provide students with a solid foundation for understanding, developing and testing small and medium complexity programmes in C, applying good practices of readability and efficiency. | Programming | computer programming | 9 | 9 | 9 |
| en | The course aims to provide students with a solid foundation for understanding, developing and testing small and medium complexity programmes in C, applying good practices of readability and efficiency. | Programming | execute software tests |  |  |  |
| en | The course aims to provide students with a solid foundation for understanding, developing and testing small and medium complexity programmes in C, applying good practices of readability and efficiency. | Programming | implement ICT coding conventions | 7 | 7 | 7 |
| en | Develop algorithms for the solution of specific problems | Introduction to Programming | algorithms | 5 | 5 | 5 |
| en | Develop algorithms for the solution of specific problems | Introduction to Programming | task algorithmisation | 18 | 18 | 18 |
| en | Implement programs and scripts using a programming language | Introduction to Programming | computer programming | 7 | 9 | 10 |
| en | Implement programs and scripts using a programming language | Introduction to Programming | use scripting programming | 1 | 1 | 1 |
| en | Do debugging of computer programs | Introduction to Programming | debug software | 2 | 2 | 2 |
| en | In the end, students should have skills in the domain of web technologies, allowing them to understand, intervene and collaborate in the web development process, so that it can be adapted for digital marketing, when used this means of communication. | Web Programming | web programming | 31 | 32 | 32 |
| en | Web design main elements, using HTML | Introduction to Web | use markup languages | 1 | 1 | 1 |
| en | Web design main elements, using HTML | Introduction to Web | implement front-end website design | 10 | 10 | 10 |
| en | Web design customization, using CSS and Twitter Bootstrap | Introduction to Web | CSS | 1 | 1 | 1 |
| en | Web design customization, using CSS and Twitter Bootstrap | Introduction to Web | implement front-end website design | 3 | 3 | 3 |
| en | JavaScript programming language | Introduction to Web | JavaScript | 1 | 1 | 1 |
| en | Programming DOM elements | Introduction to Web | JavaScript | 22 | 27 | 42 |
| en | Programming DOM elements | Introduction to Web | web programming | 2 | 2 | 2 |
| en | Information representation obtained in JSON. | Introduction to Web | information structure | 6 | 6 | 11 |
| en | C++ is one of the most popular programming language in the world, due to the advantages it offers, such as high performance, object orientation, a high degree of flexibility, a wide variety of data structures and ready-to-use algorithms, among others. | Microcredencial in Object-Oriented Programming (OOP) in C++ | C++ | 2 | 2 | 2 |
| en | C++ is one of the most popular programming language in the world, due to the advantages it offers, such as high performance, object orientation, a high degree of flexibility, a wide variety of data structures and ready-to-use algorithms, among others. | Microcredencial in Object-Oriented Programming (OOP) in C++ | use object-oriented programming | 1 | 1 | 1 |

No-fit sentences, labelled with no expected skill. Not ranked, and not counted in rule 2:

| sentence | course |
|---|---|
| The teaching methodology associated with the curricular unit will be based on a problem-based learning approach, with theoretical-practical classes involving the exposure of different programmatic concepts, and the autonomous resolution of practical problems for consolidation of knowledge. | Introduction to Programming |
| This micro-credential aims to equip students with a set of skills that are not only relevant but also indispensable in today's technology-driven scenario. | Microcredencial in Object-Oriented Programming (OOP) in C++ |

## Decision

- rule 1: B−A ndcg@10 all: lower bound -0.0001 > -0.005
- rule 1: B−A precision@10 all: lower bound +0.0000 > -0.005
- rule 1: B−A ndcg@10 triggered-nongold-new: lower bound -0.0001 > -0.005
- rule 1: B−A precision@10 triggered-nongold-new: lower bound +0.0000 > -0.005
- rule 2: probe sentences better 0, worse 4, expected skills leaving the top 10 1: does not hold
- rule 1 holds; rule 2 does not hold; C beats B on both: no
- rule 3: no switch, keep A

The deployed configuration is unchanged by this experiment.

## Timing

| step | seconds |
|---|---:|
| load data | 0.2 |
| en: documents and slices | 7.1 |
| en: BM25 index, B | 6.2 |
| en: re-embed 153 changed documents, C | 0.0 |
| en: dev weight sweep | 10.6 |
| en: test scoring | 0.3 |
| en: paired bootstrap | 0.1 |
| en: probe | 20.1 |
| pt: documents and slices | 3.9 |
| pt: BM25 index, B | 3.6 |
| pt: re-embed 30 changed documents, C | 0.0 |
| pt: dev weight sweep | 10.7 |
| pt: test scoring | 0.3 |
| pt: paired bootstrap | 0.1 |
| pt: probe | 0.0 |
