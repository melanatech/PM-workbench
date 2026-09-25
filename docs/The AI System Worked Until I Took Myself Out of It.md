# The AI System Worked Until I Took Myself Out of It

I spent part of maternity leave building a system to make my PM job less manually exhausting. Not the obvious AI stuff like writing a PRD or summarizing a meeting; those were already getting easier. I was trying to deal with the work between the work: a decision changes in a meeting, Jira still reflects the old version, the roadmap says something slightly different, a metric lives somewhere else, and by Friday somebody has to reconstruct what is actually true. None of that is particularly glamorous, but before I went on leave, I was surprised by how much of my week disappeared into it.

I built workflows to carry more of that work, and for a while they seemed to work well enough that I started thinking about how somebody else could use them. So I made a training course with a fake company, fake Jira data, fake customer evidence, and real outputs. The point was to let another PM learn the system by running it rather than sitting through an explanation of what each workflow was supposed to do.

That is when the system started looking much worse.

A discovery workflow said it was reading Slack and Jira even though it had no direct access to either. A prototype workflow announced that it had built something without giving the learner anything to open. Other commands ended with some version of “saved” or “prepared,” which had seemed perfectly acceptable when I was using them myself. As soon as I imagined another person sitting there, though, those phrases became obviously inadequate. Where did you save it? What exactly did you check? How did you get that information? What am I supposed to do with the result?

At first I treated these as problems with the course. Eventually I realized the course was doing its job perfectly: it was showing me the system without the benefit of me.

That distinction ended up mattering more than any individual workflow I built. When I used the system myself, I was filling in an enormous amount without noticing. If something said it had saved an output, I knew roughly where to look. If two artifacts disagreed, I usually knew which one had changed more recently. If a workflow made a slightly wrong assumption about how something at my company worked, I corrected for it almost automatically because I already understood the environment.

I thought I had built a system that knew more of those things than it actually did. What I had really built was a system with a fairly experienced human standing next to it, constantly supplying missing context.

I suspect this is one of the easiest ways to overestimate AI capability in knowledge work. The person using the tool contributes memory, judgment, organizational context and a sense for when something feels wrong, but because the final output appears in the AI window, some of the combined capability gets attributed back to the AI. You don't really see how much the human is contributing until you remove them.

That is why teaching the system turned out to be a better test than using it. A new person doesn't have your mental patch file. They don't know that “the dashboard” means one particular dashboard, that Tuesday's decision supersedes what is still sitting in Jira, or that “saved” means there should now be a file in a folder you happen to know exists. They force implicit knowledge into the open, and some of what looks like a documentation problem turns out to be a product problem: the system only appeared complete because its original user knew how to compensate for it.

Once I saw that, another part of the project made more sense too. I had gone into this assuming the big productivity gain would come from making things faster to produce. That part was real. What I underestimated was how much useful friction had been bundled into the old, slower way of working.

When a PRD takes an afternoon, there is a natural limit to how many versions of it you create. When you personally spend an hour updating a roadmap and another hour writing the leadership update, you carry a lot of the relationship between those artifacts in your head. You remember the decision that changed, you notice that the wording no longer lines up, and you are less likely to create five competing versions simply because making the sixth is annoying.

That process is inefficient, but some accidental quality control comes with the inefficiency.

AI changes the economics of production much faster than it changes the economics of coordination. It can generate the research plan, rewrite the roadmap narrative, update a spec, create a prototype and draft the leadership summary without getting tired of any of them. Now you have six artifacts instead of three, and the cost of producing each one has fallen dramatically. The cost of making sure all six still agree with one another — and with reality — has not fallen at the same rate.

That was one of the more useful things this project taught me. AI makes production abundant. It does not automatically make coherence abundant.

A surprising amount of PM work sits in that gap. It's deciding that a metric should be retrieved from the dashboard that owns it rather than independently recomputed because the model is capable of doing the math. It's noticing that something framed as an experiment is really a usability question and does not need a five-person adversarial review. It's deciding that an automatic retry should stop after one attempt because another blind retry is just spending more money before anybody has looked at why the first one failed.

Those were all real corrections I made while building the system, and what struck me was how often the better answer involved doing less. The models were usually trying to help, but they consistently reached toward the more complete, sophisticated or defensible version of the task: more analysis, more reviewers, more automation, more process. My contribution was often narrowing the problem back down to what was actually necessary.

That feels much closer to product management than “getting good at prompting.”

The more time I spent on the project, the less convinced I became that AI fluency is primarily about knowing how to coax better outputs from a model. I think a larger part of it is knowing where the model's work should stop. What source is allowed to settle this question? What information is actually missing? Does this problem deserve another layer of analysis, or are we adding rigor cosmetically? Should the system make this decision, or should it make the relevant information easier for a person to judge?

Those are not new questions. Product people ask versions of them constantly. What changes with AI is how easy it becomes to postpone answering them, because the tool can keep generating plausible work in the meantime.

That is also why I am skeptical of some of the ways companies are measuring AI productivity. Usage, documents generated, workflows automated and estimated hours saved all tell you something about the cost of production. They tell you much less about what happened after production got cheap.

I would want to know how much time teams spend reviewing AI-assisted work, how often they have to reconcile outputs that should agree, and how much rework appears later because something plausible traveled farther through the organization than it should have. If output rises sharply while review and reconciliation stay flat or decline, that is meaningful leverage. If output rises and people simply spend the saved time checking, correcting and stitching everything back together, then some of the work has moved rather than disappeared.

This is why I keep coming back to the training course, although I don't think the takeaway is that everyone should go build one. The useful part was removing the expert user from the loop. Give the workflow to someone who doesn't already know what you meant. Give them realistic inputs and make the system produce something they can actually inspect. Then watch where they need context that exists nowhere except in your head.

Some of those places will be documentation gaps. Some will expose missing product decisions. And some will reveal that what looked like intelligence in the system was actually judgment being supplied invisibly by the person using it.

I started this project trying to automate the repetitive parts of product management, and I still think that's worthwhile. What changed is my view of what becomes scarce when you succeed. It isn't usually the document anymore. It is knowing which document should exist, what it is allowed to claim, which source gets to win when things disagree, and when the impressive version of an answer is worse than the smaller one.

The system didn't suddenly get worse when I tried to teach it to somebody else. It just stopped getting so much free labor from me.