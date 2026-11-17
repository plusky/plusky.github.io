---
title: "Is the failure class right?"
summary: "A small language model comments on failed test jobs of openSUSE. I tried to make its verdicts better. The hard part was telling whether they got better."
date: 2026-11-14
draft: false
toc: true
build:
  publishResources: false
---

On openqa.opensuse.org, a small language model comments on failed test jobs. It gets what a human reviewer
would look at and says what kind of failure it sees. In the autumn of 2026 I tuned it. The first pull
requests are from 25 October, and most of the work was done in the week of 7 to 14 November.

I started mostly out of curiosity, to see how much I could improve with constrained resources. The
constraint was the small model. I had no particular goal beyond exploration and perhaps some improvement.

The short version:

- Small fixes to the prompt and the script made visible differences.
- Whether the model's verdict is right could hardly be measured, because too few failures had a cause
  recorded by a person.
- One change looked like a clear win until I checked where the right answers it was scored against came
  from.
- What looked most useful was a plain rerun. The comment already said whether to restart a job, and no code
  acted on that line.

## What openQA does and what the model adds

[openQA](https://open.qa) tests an operating system the way a person would. It boots a machine, types,
clicks, and compares the screen with reference screenshots, called needles, and the serial console with
expected text. One run of one test scenario on one build of the system is a job. openqa.opensuse.org, o3 for
short, is the public instance that tests openSUSE.

When a job fails, somebody has to decide what kind of failure it is. There are three kinds:

- a **product bug**: the software under test is wrong;
- a **test issue**: the test is wrong or out of date;
- **infrastructure**: a worker (the machine that runs the job), the network or some outside server let the
  job down.

A reviewer records the decision by linking a bug or a ticket on the job. That link is called a bug
reference.

o3 also asks a language model. When a job fails and no known issue matches it, a hook on o3 runs a script
called `openqa-llm-investigate`. The script sends what a reviewer would look at to Gemma 4 E4B. The model
runs under llama.cpp on three of the worker hosts, without a graphics card, in a heavily compressed form
(quantised to a level called IQ2_M). Its reply becomes a comment on the job:

{{< comment-example >}}

The three lines before the footer are meant for programs: the class, whether to bisect, and whether to
restart the job. Only `BISECT: YES` starts anything: the hook then schedules investigation jobs that retry
the test and search for the change that broke it.

{{< fig id="pipeline" caption="How a failed job gets its comment. Of the three closing lines, people read the class, the hook acts on `BISECT: YES`, and nothing is connected to `Restart`." >}}

In 42 days the model commented on 6459 jobs in four job groups. A person later reviewed about 140 of them,
2.2%.

## The easy fixes

The first fixes needed no statistics.

The prompt, the text that tells the model what to do, carried a hint about outages that fired on nearly
every build. On 17 jobs I audited by hand, the model called 15 an infrastructure problem. After the prompt
required evidence for that verdict, 3 of 17 were called infrastructure, and the class matched my audit on 12
of 17 jobs, up from 4 ([#802][s802]).

Half of the commented jobs, 3290 or 51%, were in the Development group, where a person reviewed 4. The
script now skips that group ([#810][s810]).

The third fix is about length. A model reads text as tokens, which are pieces of words, and can take in only
so many. The script can cut a long prompt to fit such a limit, if one is set; as far as I can see, o3 sets
none. It cuts by characters and assumed 2.5 characters per token ([#799][s799]). Most real prompts have fewer,
so a cut prompt can still be too long. I proposed 1.9 ([#815][s815]).

{{< fig id="chars-per-token" caption="Each bar counts how many of 520 real prompts, 122 of them from an internal instance, have that many characters per token. The median is 2.28 and 83% of the prompts are below the assumed 2.5, so they hold more tokens than the script expects." >}}

## Too few labels

To say that a change makes the class right more often, I need failures whose class is known. Such a known
class is a label.

Reviewers are the natural source. In 42 days, 1316 failed jobs carried a bug reference, but 1226 of them got
it from a bot or by carry-over from an earlier job of the same scenario. 90 were set by a person, and of the
83 whose ticket is public, not one is an infrastructure problem. A network hiccup usually gets a restart,
not a ticket.

Going back further gave 98 jobs with a reference set by a person, 50 product bugs and 48 test issues. This
is the gold set. It comes from 27 tickets, since one bug can fail many jobs.

For infrastructure I had a frontier model, one of the most capable models available, label 299 failed o3
jobs. This is the silver set. No person checked these labels, and the labeller had hindsight, which the
commenting model lacks: it could see whether the same scenario passed an hour later.

{{< fig id="labels" caption="Where the labels come from. Top: of 1316 failed jobs with a bug reference, a person set the 90 at the right end, enlarged below. Middle: the 98 gold jobs, one square per job and one group per ticket; hollow squares are jobs on tickets that do not map cleanly onto a class. Bottom: the 299 jobs a model labelled. Green, infrastructure, appears only there." >}}

Jobs that share a ticket are not independent, so what counts is the number of tickets. With 27, a comparison
of two models can reliably show only a difference of about 30 percentage points. Fifteen points would need 105 tickets,
and ten points 235.

{{< fig id="detectable" caption="The smallest difference between two models that a labelled set of a given size can show, for a paired comparison at the usual 5% level and 80% power, if about a third of the tickets change between the two. Anything in the grey area is too small to show reliably." >}}

## A noisy model

Asked the same thing twice, the model does not always give the same class. For most experiments I used Q8,
a less compressed version of the same Gemma. A second run a day later, with the same prompt and the same
settings, kept the class on 29 of 35 gold jobs.

So if a new prompt gets three more jobs right than the old one, one run each, it has shown nothing.

{{< fig id="repeat" caption="Each bar is a set of jobs run twice with the same prompt and the same settings. Grey: the class stayed the same. Purple: it changed. In one set of 16 jobs, run again after four days, more than half changed." >}}

## What the model gets wrong

Gemma leans towards product bug. Of the 46 test-issue jobs in the gold set that it answered, Gemma at Q8
called 39 a product bug and 6 a test issue. The IQ2_M version that runs in production called 15 of the 46 a
test issue, but called only 35 of the 49 product bugs a product bug. Both got 50 of 95 jobs right.

{{< fig id="confusion" caption="Each row is a group of jobs whose class has a label; the colours show what the model answered. A model that was always right would make the product-bug rows all blue and the test-issue rows all orange. The last row is what production posted on the 111 jobs the frontier labeller called infrastructure. The buttons filter by how the failure showed up: of 13 test issues that showed up as a failing script, Gemma at Q8 called none a test issue." toggles="all:All jobs,script:Script failures,needle:Needle failures,serial:Serial console" >}}

A much larger model did no better that I could see. A frontier model given exactly Gemma's input, with the
written class definitions, was right on 65% of 26 gold tickets, averaged per ticket, against 60% for Gemma
as production runs it.

## What I tried

One run of ten prompt variants over the 116 labelled jobs I tuned prompts on took seven and a half hours, so
I screened ideas on a small sample instead: 71 jobs with the three classes in equal parts, split into halves
A and B. 29 of the 71 came from an internal instance, so for this set I give counts only.

The pass rule was written down before each run: at least three more jobs right than the comparison run, and
no class losing two. An idea ran on A first, and on B only if it passed.

In two days I logged 179 comparisons: prompt wordings, added facts, sampling with a vote, other models. 31
passed and 148 did not. Of the 19 that passed on A and were then run on B, 18 failed there. That is what you
see when the pass rule sits inside the run-to-run noise.

{{< fig id="screens" caption="Each dot is one comparison of an idea with the run it was measured against, placed by how many more jobs the idea got right (right of 0) or fewer (left of 0). Only dots on or beyond a vertical line passed: +3 on one half, +5 on both together. A line joins a pass on half A to the later run of the same idea on half B. Drawn are the 164 of the 179 comparisons that have such a count." >}}

Bigger models did better than Gemma, but no better than the rule in the next section. On the evening of 11
November I stopped the slow models. I felt we were not investing our time most efficiently.

## A second model

Gemma is a chat model: it writes text, and the script parses a class out of it. A decision model takes a
question and a list of allowed answers, and returns a probability for each answer. I used elephant-1, a 9B
decision model that runs on the same llama.cpp.

{{< fig id="decision" caption="Left: a chat model writes text, and the class is read from its last lines. Right: a decision model is given the possible answers and returns a probability for each." >}}

On its own it was no better than Gemma: on the gold jobs it was right on 42 of 95 against Gemma's 50. But
one question picked out infrastructure. Asked "did the test environment fail?" on the 116 jobs I tuned on,
it gave "yes" a probability of 0.3 or more on 19 of the 30 infrastructure jobs and on 5 of the 86 others. I
read that threshold off the data after seeing it.

{{< fig id="env" caption="Each dot is one of the 128 jobs of the test in the next section, placed by the probability elephant-1 gave to a failed test environment. Dots in the grey area, at 0.3 or more, are called infrastructure: 22 of the 42 infrastructure jobs, and 5 of the 86 others." >}}

That left a rule with two questions and no Gemma in it. If the environment answer is 0.3 or more, the class
is infrastructure. Otherwise it is whichever of product and test elephant-1 rates higher. The package for
its server is merged ([openQA #8102][o8102]); the change to the script is open ([#814][s814]).

I also handed elephant-1's answer to Gemma as a hint. That passed its screen on the small sample, but the
steered Gemma repeated elephant-1's label on 59 of 71 jobs, so the gain was elephant-1's. What surprised me most was how one can
steer an LLM to an incorrect conclusion.

## The test and the audit

To test the rule I froze it first. I wrote the rule, the threshold and the scoring into a file, and then ran
it on 128 o3 jobs of the silver set[^frozen]. The comments posted in production had the class right on 66 of
the 128. The rule had it right on 93.

Then I audited the labels. All 128 were silver labels. 108 of them had been made with hindsight, 36 of the
42 infrastructure labels among them. A rerun that passed is a fair sign of an infrastructure problem. It is
not something a model can see in the log of the failed job. And the labeller had worked from the same
written class definitions that I later gave to elephant-1.

Three checks do not depend on those labels. The plainest uses 35 gold jobs, labelled by people. The rule got
20 right. Production's model and prompt, run again on the same input, got 19. These jobs were among the ones
I had chosen the threshold on, which should have favoured the rule. The other two checks are in the lower
half of the figure.

{{< fig id="confirm" caption="Grey: the posted comments (for the 35 gold jobs, production's model and prompt run again). Purple: the rule. Top: how many jobs each had right against the labels a model made; the rule is far ahead, 93 to 66. Bottom: the three checks that do not use those labels. For the 50 jobs that passed when rerun, the bars count how often each said infrastructure. In these three checks the rule is one job ahead twice and four jobs behind once." toggles="all:All 128 labels,source:By source of the label" >}}

So the rule agrees much better than production with a hindsight labeller that shares its vocabulary, and no
better with people.

## The rerun

If an infrastructure label often means that a later run passed, then the best infrastructure detector on
offer is the rerun. Of the 299 silver jobs, 188 were first failures: the previous run of the same scenario
had not failed. 67 of those passed when they were run again in the same build[^68].

The hook starts investigation jobs only on `BISECT: YES`, and it retried 8 of the 67. The same comment also
said whether to restart the job: `Restart: YES` on 28 of the 67. No code acted on that line.
[#821][s821] starts one retry job when the comment says `Restart: YES`.

{{< fig id="reruns" caption="Top: what became of the 299 jobs. 188 were first failures, and 67 of those passed when run again. Bottom: four possible retry rules. Grey is how many jobs a rule retries, purple how many of the 67 it covers." >}}

## Pull requests

I opened 28 pull requests against [os-autoinst-scripts](https://github.com/os-autoinst/os-autoinst-scripts)
and [openQA](https://github.com/os-autoinst/openQA) between 25 October and 13 November. 22 are merged. The
work is tracked in a [public ticket](https://progress.opensuse.org/issues/210255).

| topic | merged | open |
|---|---|---|
| Prompt and verdict rules | [#789][s789] [#790][s790] [#791][s791] [#795][s795] [#798][s798] [#801][s801] [#802][s802] | |
| Comments and the hook | [#788][s788] [#796][s796] [#797][s797] [openQA #8023][o8023] | [#817][s817] [#819][s819] [openQA #8113][o8113] |
| Prompt length | [#799][s799] [#800][s800] | [#815][s815] |
| Routing and the model server | [#808][s808] [openQA #8069][o8069] [openQA #8070][o8070] [openQA #8071][o8071] | |
| Groups nobody reviews | [#810][s810] | |
| Decision model | [openQA #8102][o8102] | [#814][s814] |
| Retry on `Restart: YES` | | [#821][s821] |
| CI | [#792][s792] [#809][s809] [#816][s816] | |

## What I would do differently

- Count the labels before the first experiment, per class and per ticket. On day one that would have shown
  the 30-point limit.
- Measure the noise floor next and size every pass rule from it.
- Ask of every label where it comes from.
- Read every field the system already produces before building anything to replace it.

## How this was done

I wrote the scripts and ran the experiments with an AI coding assistant. A frontier model made the silver
labels, checked the gold tickets that did not map cleanly, and was the larger model in the comparison on
Gemma's input.

The data comes from o3, which is public, but job pages there expire, so I link none. Parts of several sets
came from an internal instance and appear as counts only. The numbers behind every figure are in the
[repository of this site](https://github.com/plusky/plusky.github.io). The measurements that did not fit here
are on a [separate page](/posts/failure-class-data/).

As for the comments themselves, they seem useful. I hope the open pull requests get merged.

[^frozen]: None of the 128 was among the jobs the threshold had been read from, though I had partly worded
    the question on the same pool, and 12 share a test and a build with jobs I tuned on. The file named two
    versions: as the main rule, one that asks the product-or-test question with the options in three orders,
    and this two-question rule as the cheaper fallback. Both met the bar written in the file, with 95 and
    93, and I report the cheaper one.

[^68]: The comments on the pull requests say 68. One of those reruns had failed and was set to passed by a
    `force_result` label after a retry of it passed.

[s788]: https://github.com/os-autoinst/os-autoinst-scripts/pull/788
[s789]: https://github.com/os-autoinst/os-autoinst-scripts/pull/789
[s790]: https://github.com/os-autoinst/os-autoinst-scripts/pull/790
[s791]: https://github.com/os-autoinst/os-autoinst-scripts/pull/791
[s792]: https://github.com/os-autoinst/os-autoinst-scripts/pull/792
[s795]: https://github.com/os-autoinst/os-autoinst-scripts/pull/795
[s796]: https://github.com/os-autoinst/os-autoinst-scripts/pull/796
[s797]: https://github.com/os-autoinst/os-autoinst-scripts/pull/797
[s798]: https://github.com/os-autoinst/os-autoinst-scripts/pull/798
[s799]: https://github.com/os-autoinst/os-autoinst-scripts/pull/799
[s800]: https://github.com/os-autoinst/os-autoinst-scripts/pull/800
[s801]: https://github.com/os-autoinst/os-autoinst-scripts/pull/801
[s802]: https://github.com/os-autoinst/os-autoinst-scripts/pull/802
[s808]: https://github.com/os-autoinst/os-autoinst-scripts/pull/808
[s809]: https://github.com/os-autoinst/os-autoinst-scripts/pull/809
[s810]: https://github.com/os-autoinst/os-autoinst-scripts/pull/810
[s814]: https://github.com/os-autoinst/os-autoinst-scripts/pull/814
[s815]: https://github.com/os-autoinst/os-autoinst-scripts/pull/815
[s816]: https://github.com/os-autoinst/os-autoinst-scripts/pull/816
[s817]: https://github.com/os-autoinst/os-autoinst-scripts/pull/817
[s819]: https://github.com/os-autoinst/os-autoinst-scripts/pull/819
[s821]: https://github.com/os-autoinst/os-autoinst-scripts/pull/821
[o8023]: https://github.com/os-autoinst/openQA/pull/8023
[o8069]: https://github.com/os-autoinst/openQA/pull/8069
[o8070]: https://github.com/os-autoinst/openQA/pull/8070
[o8071]: https://github.com/os-autoinst/openQA/pull/8071
[o8102]: https://github.com/os-autoinst/openQA/pull/8102
[o8113]: https://github.com/os-autoinst/openQA/pull/8113
