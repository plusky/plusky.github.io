---
title: "Is the failure class right?"
summary: "Three weeks of tuning a small local model that comments on failed openQA jobs, and what the labels let me say about it."
date: 2026-11-14
draft: false
toc: true
build:
  publishResources: false
---

On openqa.opensuse.org a small language model writes a comment on failed test jobs. The comment ends with a
class: product bug, test issue or infrastructure problem. For three weeks in October and November 2026 I
tried to make that class right more often.

I started mostly out of curiosity, to see how much I could improve with constrained resources. The
constraint was the small model. I had no particular goal beyond exploration and perhaps some improvement. It
was a learning experience.

Most of what I tried did nothing I could measure. One change looked like a clear win. A rule built on a
second model had the class right on 93 of 128 jobs, where the comments posted in production had 66. But a
frontier model had labelled all 128, most of them with hindsight, knowing what later runs of the same test
did. On the 35 jobs a person had labelled, the rule got 20 right, and production's model and prompt, run
again on the same input, got 19. So the rule agreed better with a model that had hindsight, and no better
with people.

The labels people had set came down to 27 tickets, because one bug fails many jobs. With 27 tickets, a
comparison of two models can reliably show only a difference of about 30 percentage points.

Two things looked useful. One was fixing the prompt and the script around the model. The other was a plain rerun. Of 299
commented jobs, 111 were run again in the same build after a first failure, and 67 of those passed. The
model had answered `Restart: YES`, a line in its comment, on 28 of the 67, and no code acted on that line.

## openQA and the comment

openQA tests an operating system the way a person would: it boots a machine, types, clicks, and compares the
screen with reference screenshots, called needles, and the serial console with expected text. A scenario is
one test on one kind of machine, and a job is one run of a scenario on one build of the system. The openSUSE
instance, openqa.opensuse.org or o3 for short, is public.

When a job fails, somebody has to decide what kind of failure it is: a bug in the product, a test that is
wrong or out of date, or infrastructure, meaning a worker (the machine that runs the job), the network or some outside server
let the job down. Reviewers record the decision as a bug reference in a comment on the job.

o3 also asks a language model. When a job fails and no known-issue pattern matches it, a hook runs
`openqa-llm-investigate`. The script collects what a reviewer would look at and sends it in three questions
to Gemma 4 E4B, quantised to IQ2_M, under llama.cpp on three of the worker hosts, without a GPU. The reply
becomes a comment on the job.

{{< comment-example >}}

The three lines before the footer are the part meant for machines: the class, whether to bisect, and whether
to restart. Only one of them starts anything. On `BISECT: YES` the hook schedules investigation jobs that
retry the test and bisect between the last good and the first bad state.

{{< fig id="pipeline" size="wide" caption="Three answers per job. Only `BISECT` starts anything." >}}

In 42 days the model commented on 6459 jobs in four job groups, about 154 a day. A person later reviewed
about 140 of them, 2.2%. Half of the commented jobs, 3290 or 51%, were in the Development group, where a
person reviewed 4. The script now skips that group.

## The easy part

The first fixes needed no statistics.

I audited 17 failed jobs by hand and ran the model on them. It called 15 of the 17 an infrastructure
problem, because the prompt carried a hint about outages that fired on nearly every build. After the prompt
required evidence for that verdict, 3 of 17 were called infrastructure, and the class matched my audit on 12
of 17 jobs, up from 4.

The script can cut a long prompt to fit a context limit, if one is set; as far as I can see, o3 sets none.
It cuts by characters and assumed 2.5 characters per token. I measured 520 real prompts, 122 of them from an
internal instance. The median is 2.28 characters per token, and 83% of the prompts are below 2.5. With a context
of 16,384 tokens, 11 of the 520 prompts cut by that estimate would still be too long, and one more is too
long whatever the constant. On my test server llama.cpp
answered such a prompt with HTTP 400, and the job got no comment. I proposed 1.9.

{{< fig id="chars-per-token" size="wide" caption="Most real prompts have fewer characters per token than the script assumed." >}}

Gemma thinks before it answers, and about nine tenths of what it generates is never shown. In a later run on
a test VM, one sample each, turning thinking off cut the time for the 17 audited jobs by 37% and dropped
the right class from 13 of 17 to 9, so it stayed on.

A finer quantisation of the same model, Q8, changed the class on 24 of 95 jobs whose class a person had
set, mostly towards product bug. That matters below, because most of my experiments ran on Q8.

## What "right" means

To say that a change makes the class right more often I need failures whose class is known. On o3 that
means failures a person has reviewed.

In 42 days, 1316 failed jobs carried a bug reference. 1226 of them got it from a bot or by carry-over from
an earlier job of the same scenario. 90 were set by a person. Of the 83 whose ticket is public, not one is
an infrastructure problem. A network hiccup usually gets a restart, not a ticket.

Going back further gave me 98 jobs with a reference set by a person, 50 product bugs and 48 test issues. I
call this set gold. Its weakness is that jobs come in clusters: one bug fails the same test for a week and
every one of those jobs carries the same ticket. The 98 jobs come from 27 tickets, the largest with 18 jobs. 8 of
the 27 do not map cleanly onto the three classes, and they hold 40 of the 98 jobs.

For infrastructure there was no human label at all, so I made a second set, silver: 299 failed o3 jobs,
each labelled by a frontier model, with a second pass where the first was unsure. No person checked these
labels. Unlike the commenting model, the labeller had hindsight: it could see whether the same scenario
passed an hour later and which ticket a reviewer attached the next day. It came out at 87 product, 87 test,
111 infrastructure and 14 unclear. The labeller worked from written class definitions. About half of its
infrastructure labels, 56 of 111, had a rerun in the same build that passed.

{{< fig id="labels" size="wide" caption="Few labels come from people. They cluster by ticket, and none is labelled infrastructure." >}}

With 27 tickets, a paired comparison of two models at the usual 5% level and 80% power can show a difference
of about 30 points, if about a third of the tickets change between the two. Fifteen points would need 105
tickets, and ten points 235.

{{< fig id="detectable" caption="With 27 tickets only a gap of about 30 points shows; 10 points need 235." >}}

Nothing I tried was going to be 30 points better.

## The noise floor

I compared one prompt with itself late. I would now do it before comparing two prompts.

The same prompt on Gemma at Q8, with the same settings, run a second time a day later, kept its class on 29
of 35 gold jobs. Among the 16 test issues in that set, 11 kept their class. Four days after the first run I
ran the same prompt again on another 16 gold jobs, half of them from the 35, and 7 kept their class. Easy jobs are steady: of 34 product bugs from an internal instance, 33 got the same class twice.

{{< fig id="repeat" caption="The same prompt run twice does not always give the same class." >}}

The script asks its first two questions at temperature 0.3 and the verdict at 0. Asking a verdict again
at temperature 0, on the same stored answers to the first two, still changed 3 of 36 classes.

So if a new prompt gets three more jobs right than the old one, one run each, it has shown nothing.

## What the model gets wrong

On the gold jobs the errors are not spread evenly. Gemma at Q8 answered 95 of the 98; three prompts did not
fit its context. Of 49 product-bug jobs it called 44 product. Of 46 test-issue jobs it called 39 product and
6 test. The IQ2_M quantisation that runs in production called 15 of the 46 test, but called only 35 of
the 49 product bugs a product bug. Both got 50 of 95 right.

{{< fig id="confusion" size="wide" caption="Gemma calls most test issues product bugs, at Q8 and as production runs it (IQ2_M). Below: what production posted on the 111 jobs the frontier labeller called infrastructure." toggles="all:All jobs,script:Script failures,needle:Needle failures,serial:Serial console" >}}

The figure splits failures by how they show up: a screen that does not match its needle, a script that exits
with an error, or unexpected output on the serial console. The class follows that more than the cause. A
failing script reads as "the product is broken": of 13 test issues that showed up as a failing script, Gemma
at Q8 called none a test issue. Of 7 on the serial console, it called none a test issue either.

Agreement between runs does not rescue this. Where two runs agreed, the class was right on 18 of 18 product
jobs and on 1 of 11 test-issue jobs, so voting would only make the model more consistently wrong about test
issues.

To see how much of this is the small model, I gave a frontier model exactly the input Gemma gets, with the
written class definitions. On 26 gold
tickets, averaged per ticket, it was right on 65% against 60% for Gemma as production runs it. A much stronger model did no better that I could see, so most of the limit seems to be in what the prompt
contains and in the labels I compare with.

## Screens with a pass rule written first

In the third week I had more ideas than time to run them. One run of ten prompt variants over the 116
labelled jobs I tuned prompts on, gold and silver jobs, some of them from the internal instance, took seven
and a half hours. So I screened: a small fixed sample, and a pass rule written down before the run.

The sample was 71 jobs with the three classes in equal parts, split into halves A and B. 29 of the 71 came
from the internal instance, so for this set I give counts only. An idea runs on A first. It passes if it
gets at least three more jobs right than the run it is compared with, its control, and no class loses two.
Only then does it run on B, where it has to gain at least three again, with no class losing two. Answering "product" every time scores 24 of 71. The
production prompt scores 28 with Gemma at Q8.

In two days I logged 179 comparisons: prompt wordings, other ways of asking, added facts, sampling with a
vote, other models. 31 passed and 148 did not.

{{< fig id="screens" size="wide" caption="Each comparison against its pass line: the 164 of the 179 that have a net count. A line joins a pass on half A to the later run of the same idea on half B." >}}

Of the 19 comparisons that passed on A and were then run on B, 18 failed there. That is what you see when
the pass rule sits inside the run-to-run noise.

Bigger models did better than Gemma, but no better than the two-question rule in the next section. Kev-27B,
a 27B model of the decision kind described there, scored 47 of 71, as many as that rule. Gemma's own 26B sibling needed a
median of 978 seconds per job with eight jobs in parallel.

On the evening of 11 November I stopped the slow models. I felt we were not investing our time most
efficiently.

## A decision model and one good question

A chat model writes text and I parse a class out of it. A decision model skips the text. It reads the same
material, takes a question and a list of allowed answers, and returns a probability for each answer.

{{< fig id="decision" size="wide" caption="A chat model writes an answer; a decision model weighs the answers it is given." >}}

I used elephant-1, a 9B decision model that runs on the same llama.cpp. On its own it was no better than
Gemma: on the gold jobs it was right on 42 of 95 against Gemma's 50, and it called 26 jobs infrastructure,
none of which was.

One question picked out infrastructure. On the 116 jobs I tuned on, I asked "did the test environment
fail?". The model gave "yes" a probability of 0.3 or more on 19 of the 30 infrastructure jobs and on 5 of
the 86 others. I read that threshold off the data after seeing it, which is the thing the screens were meant
to prevent.

{{< fig id="env" caption="The same question on the 128 jobs of the frozen run (next section): 22 of 42 infrastructure jobs reached 0.3, against 5 of the 86 others." >}}

I also handed elephant-1's answer to Gemma as a hint. That passed its screen. Then I compared the answers:
steered Gemma repeated elephant-1's label on 59 of 71 jobs, so the gain was elephant-1's. What surprised me
most was how one can steer an LLM to an incorrect conclusion.

That left a rule with two questions and no Gemma in it. If the environment answer is 0.3 or more, the class
is infrastructure. Otherwise it is whichever of product and test elephant-1 rates higher. Counted afterwards
from stored answers, on jobs its threshold came from, it scored 47 of 71. On my test server it needs
about 8.5 GiB of memory for a second model server and, from a fit on ten requests, an estimated median of 55
seconds per job.

## The frozen run and the audit

Everything above was tuned on jobs I had looked at. Before asking anyone to review a change I wanted one run
with nothing left to adjust. I wrote the rule, the threshold and the scoring into a file, recorded the hash
of the job list, and ran it on 128 o3 jobs of the silver set. None of them was among the jobs the threshold
had been read from. They were not entirely new, though. I had partly worded the question on the same pool,
and 12 share a test and a build with jobs I tuned on.

The comments that production had posted on those jobs had the class right on 66. The rule had it right on
93. The file named two versions: as the main rule, one that asks the product-or-test question with the
options in three orders, and this two-question rule as the cheaper fallback. Both met the bar written in the
file, with 95 and 93, and I report the cheaper one.

Then I audited the labels, because a gain of 27 jobs was more than anything had moved before. All 128 were
silver labels, made by the frontier labeller. 108 of them had been made with hindsight, 36 of the 42
infrastructure labels among them. A rerun that passed is a fair sign of an infrastructure problem. It is not
something a model can see in the log of the failed job. And the labeller had worked from the same written
class definitions that I later gave to elephant-1.

Three checks do not depend on those labels.

- People's labels. The largest set with a person's label and both answers, the rule's and a replay of
  production's, was 35 gold jobs.
  They were not among the 128, and they were among the jobs I had chosen the threshold on, which should have
  favoured the rule. The rule got 20 right, a replay of production 19.
- Reruns. Of the silver jobs I had run elephant-1 on, 50 passed when rerun in the same build. The posted
  comment had said infrastructure on 20 of them, the rule on 16.
- Reviewers. 14 of the 128 carried a bug reference from a reviewer, two bugs, both in the product. The
  posted comment had 9 right, the rule 10.

{{< fig id="confirm" size="wide" caption="The rule beats the posted comments on the model-made labels, 93 to 66, but is only one job ahead on people's labels and behind on reruns." toggles="all:All 128 labels,source:By source of the label" >}}

So the rule agrees much better than production with a hindsight labeller that shares its vocabulary, and no
better with people. The [pull request](https://github.com/os-autoinst/os-autoinst-scripts/pull/814) is still
open. I have left it as groundwork: the second server and its wiring both work, and with a better label set the
experiment is one setting away.

## The rerun

If an infrastructure label often means that a later run passed, then the best infrastructure detector on
offer is the rerun.

I went back to the 299 silver jobs and looked at what happened to each after it failed. 188 were first
failures: the previous run of the same scenario had not failed. Of those, 67 passed when they were run again
in the same build,[^68] 44 were rerun and failed again, and 77 were never rerun. Of the 67, 56 were labelled
infrastructure and 11 test issue. None was a product bug, partly because the labeller saw the passing rerun.

{{< fig id="reruns" size="wide" caption="67 first failures passed on a rerun. `Restart: YES` would have retried 28 of them, the hook's rule 8." >}}

The hook starts investigation jobs only on `BISECT: YES`. The model said YES on 17 of the 67, and the hook
retried 8 of them. For 25 the model said no, and for another 25 the script set it to NO, whatever the model had
said, because another job of the build failed in the same module. The same comment also said whether to restart the job: `Restart:
YES` on 62 of the 299 jobs, and on 28 of the 67 that then passed. No code acted on that line.

I opened a [pull request](https://github.com/os-autoinst/os-autoinst-scripts/pull/821) that starts one retry
job when the comment says `Restart: YES`. A retry that passes marks the failure as likely sporadic, which is
what the class line was worst at.

## What went upstream

I opened 28 pull requests against os-autoinst-scripts and openQA between 25 October and 14 November. 22 are
merged. Open are the decision model in the script, the characters-per-token constant, the retry on `Restart:
YES` and three small changes. The work is tracked in a
[public ticket](https://progress.opensuse.org/issues/210255).

## What I would do differently

I would count the labels before the first experiment, per class and per ticket. On day one that would have
shown the 30-point limit. I would measure the noise floor next
and size every pass rule from it. I would ask of every label where it comes from. And I would read every
field the system already produces before building anything to replace it.

## How this was done

I wrote the scripts and ran the experiments with an AI coding assistant. From the screens on, each run had a
pass rule written to a file before it started. A frontier model made the silver labels, checked the gold tickets that did not map
cleanly, and was the larger model in the comparison on Gemma's input.

The data comes from o3, which is public, but job pages there expire, so I link none. Parts
of several sets came from an internal instance and appear as counts only. The timings come from an aarch64
test VM and from my test server, with two EPYC 9354 CPUs, not from o3. The numbers behind every figure are in the
repository of this site.

The limits, in one place. Human labels cover 27 tickets. Infrastructure labels come only from the frontier model, most of them made with hindsight. The
comments run on one instance, and all local models ran on CPUs. The rule has run on only 14 human-labelled
jobs it had not seen, from two bugs, both in the product.

As for the comments themselves, they seem useful. I hope the open pull requests get merged.

[^68]: The comments on the pull requests say 68. One of those reruns had failed and was set to passed by a
    `force_result` label after a retry of it passed.
