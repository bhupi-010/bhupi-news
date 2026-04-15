---
title: "Show HN: Visualizing OpenClaw runs to debug flaws and token spikes"
date: "2026-04-14T19:02:45Z"
description: "Built a trace view to see OpenClaw LLM / tool / subagent calls and debug it.\n\nComments URL: https://news.ycombinator.com/item?id=47769889\nPoints: 1\n# Comments: 0"
category: "Dev News"
source: "https://github.com/epsilla-cloud/clawtrace"
tags: ["github.com", "dev-news"]
---

![Featured Image](https://opengraph.githubassets.com/353e7596727d56bc4b0db3f61002740c85f30bcc2c820ae84d82861f14d5906e/epsilla-cloud/clawtrace)

clawtrace.ai  · 
 Docs  · 
 Ask Tracy
My OpenClaw agent burned ~40× its normal token budget in under an hour.
Root cause: it was appending ~1,500 messages of history to every LLM call. By the tim… [+7203 chars]

[Read original article](https://github.com/epsilla-cloud/clawtrace)
