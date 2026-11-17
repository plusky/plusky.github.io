---
title: "Is the failure class right? The measurements"
summary: "The tables and figures that did not fit into the article: server tuning, the models I compared, the ideas that did not hold, and where the data is."
date: 2026-11-17
draft: false
toc: true
build:
  publishResources: false
---

This page belongs to [Is the failure class right?](/posts/failure-class/). The article shows the measurements
its argument needs. The rest is here so that it is not lost: what I measured, on which jobs, and what came
out. Most tables end with what I did with the result.

How to read the tables:

- Every table names its sample. "Public" jobs are those of openqa.opensuse.org, which anyone can read. Sets
  that also hold jobs of an internal instance appear as counts only.
- A cell written as *a of b* is a count out of a total, most often jobs right of jobs asked.
- Unless a table says otherwise, a number is one run. The article explains why a difference of a few jobs
  between two runs means little.

Terms the tables use:

- *Gold* jobs have a bug or ticket reference that a person set. *Silver* labels come from a frontier model.
  Most of them were made with *hindsight*: the labeller could see what happened to the job afterwards.
- IQ2_M, Q4_0, Q4_K_M and Q8_0 are *quantisations* of Gemma: the same model stored with fewer or more bits
  per weight. Production runs IQ2_M.
- Besides the class, a comment ends with a `BISECT` line and a `Restart` line. The hook starts investigation
  jobs on `BISECT: YES`.
- The *screens* are the two halves, A and B, of one set of labelled jobs on which I tried ideas. The *frozen
  run* is the one test whose rules were written down beforehand.
- elephant-1 is a *decision model*: it returns a probability for each allowed answer. Its *label question*
  asks whether the failure is a product bug or a test issue, its *environment question* whether the test
  environment failed.

## Server tuning

A job asks the model three questions in one chat. I replayed a fixed set of jobs, whose answers I had checked
by hand, against servers with different settings.

{{< result id="tuning-replay" >}}

Most of what Gemma generates is thinking that the comment never shows. Turning it off saves time, and it cost
right answers, so it stayed on.

{{< fig id="thinking" caption="Thinking on against thinking off, on the same replayed jobs: how much the model generated, how long a job took and how many jobs got the right class." >}}

Each question repeats the conversation so far. A server that has just answered the first question can take
almost all of the next prompt from its cache, but only if the next question reaches the same server.

{{< fig id="routing" caption="The three questions of one job, before and after the load balancer was told to keep a job on one server. The share taken from the cache was measured in the replay below, where one server answered every question." >}}

{{< result id="tuning-prompt-cache" >}}

I also changed single server settings, one at a time.

{{< result id="tuning-micro" >}}

A less compressed model file reads prompts faster. On the jobs where the two files gave different classes,
running each again showed no difference between them.

{{< result id="tuning-flips" >}}

The server also loaded the file that lets Gemma read images, although the script sends only text.

{{< result id="tuning-mmproj" >}}

## Prompt size

llama-server can divide its context among the requests it serves at once. The benchmark server did, so one
request got an eighth of the configured size. The script cuts a prompt that is too long, and it measures the
prompt in characters, not in tokens.

{{< fig id="slots" caption="How the benchmark server divided its context into slots, with two real prompts against one slot." >}}

{{< result id="prompt-size-context" >}}

## Labels and readers

To tune a model you need failures whose cause somebody recorded. These tables count how many there are, and
how many of the model's comments a person looks at.

{{< fig id="readers" caption="Jobs that got a comment from the model, by job group, and the share of them a person later reviewed." >}}

{{< result id="labels-supply" >}}

{{< result id="labels-linked" >}}

{{< result id="labels-internal" >}}

## Models compared

I compared the models first on the labelled sets I had, and then on the screens.

{{< result id="models-gold" >}}

{{< result id="models-decision-silver" >}}

{{< result id="models-quantisation" >}}

Then I kept Gemma's analysis fixed and changed only the wording of the last question.

{{< result id="models-variants" >}}

These are the approaches that were run on both halves of the screen set.

{{< fig id="models" caption="Jobs right on the screen set per approach, with the right answers per class beside each bar. The mark on every bar is what always answering product gets. The highlighted row is the rule with two questions that the article proposes." >}}

{{< result id="models-speed" >}}

## Every screening try

All 179 comparisons of the two screens are listed in the article, in the data table under
[its figure of the screens](/posts/failure-class/#fig-screens). One more idea from the screens was to flag the jobs on which
two models disagree.

{{< result id="screens-flags" >}}

## Confirmation details

The article gives the result of the frozen run. Here are its counts per class, the disagreement idea on the
same jobs, and what one decision request costs.

{{< result id="confirmation-run" >}}

{{< result id="confirmation-disagreement" >}}

{{< fig id="latency" caption="Seconds of one decision request against the size of its prompt, for each setting of threads and questions, and requests sent together against the same request alone." >}}

{{< result id="confirmation-latency" >}}

Jobs do not arrive one by one, which matters for a step that takes about a minute.

{{< result id="confirmation-arrivals" >}}

## Follow-up ideas

After the frozen run I tried a few more ideas.

{{< result id="ideas-screenshot" >}}

{{< result id="ideas-no-last-good" >}}

{{< result id="ideas-last-good-line" >}}

{{< result id="ideas-neighbours" >}}

The rerun is the idea that held. The article shows it; this table has what its figure leaves out.

{{< result id="ideas-rerun-details" >}}

## Early replays

The first change to the prompt was measured on the jobs I had checked by hand, before I had any labelled set.

{{< result id="early-prompt-fix" >}}

## Pull requests

{{< fig id="prs" caption="The pull requests of the work by topic, each from the day it was opened to the day it was merged, as read on 2026-11-14." >}}

## The data

The numbers on this page and in the article are files in the
[repository of this site](https://github.com/plusky/plusky.github.io):

- [`data/results`](https://github.com/plusky/plusky.github.io/tree/main/data/results) has one file per table
  on this page, and the one the figure of all approaches is drawn from.
- [`data/fig`](https://github.com/plusky/plusky.github.io/tree/main/data/fig) has the numbers behind every
  other figure, and a file that explains the fields.
- [`data/jobs`](https://github.com/plusky/plusky.github.io/tree/main/data/jobs) has one row per job for three
  sets of public jobs: the public jobs of the frozen run, the gold jobs and the jobs of the rerun analysis. A
  row has the job number, the label and what each model or rule answered, as fixed codes.

Not there: logs, prompts, the model's answers, and any row of a job from the internal instance. Job pages on
openqa.opensuse.org expire, so the job numbers will stop resolving over time.
