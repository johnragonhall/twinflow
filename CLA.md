---
title: Contributor license agreement
description: The rights you grant when you contribute to twinflow, the rights you keep, and how to sign before your first pull request merges.
topic_type: reference
audience: contributors
---

# Contributor license agreement

You keep your copyright. This is a license, not an assignment. Signing moves no
ownership of anything to anyone. You can still use, publish, sell, or relicense
your own contribution anywhere else, on any terms you like, and you need no
permission from this project to do it.

What signing does is let Jack ship your work under both of the licenses this
project offers. [LICENSING.md](LICENSING.md) explains why a dual-licensed
project cannot take a contribution without an agreement like this one.

Sign once, in your first pull request. One signature covers everything you
contribute after it. The mechanism is in [section 7](#7-how-to-sign).

## 1. Definitions

| Term         | Meaning                                                                                                                                         |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| You          | The copyright owner who signs, or the legal entity authorized to sign for that owner.                                                           |
| Maintainer   | John Ragon Hall, the copyright holder named in [NOTICE](NOTICE).                                                                                |
| The project  | twinflow, at `https://github.com/johnragonhall/twinflow`.                                                                                       |
| Contribution | Any original work of authorship you submit to the project, including any change to work already in it.                                          |
| Submit       | Any communication you send to the project or to the maintainer about it, in any form, except material you mark clearly as "Not a Contribution". |

## 2. Copyright license

You grant the maintainer a perpetual, worldwide, non-exclusive, royalty-free,
irrevocable copyright license to do the following with each contribution:

reproduce it, prepare derivative works of it, publicly display it, publicly perform it, sublicense it, and distribute it and the derivative works of it. <!-- docs-lint-ok STE-TERM-WORD verbatim Apache-2.0 section 2 grant wording, not editable prose -->

That license includes the right to license your contribution, and any work
containing it, under terms other than Apache-2.0. This is the clause the
commercial option rests on. Without it the maintainer holds no right to offer
the whole project on anything except Apache-2.0, and the second option in
[LICENSING.md](LICENSING.md) is unenforceable.

The grant is non-exclusive. You keep every one of those same rights over your
own contribution and can exercise them wherever you like.

## 3. Patent license

You grant the maintainer, and every recipient of software the maintainer
distributes, a perpetual, worldwide, non-exclusive, royalty-free, irrevocable
patent license to make, have made, use, offer to sell, sell, import, and
otherwise transfer your contribution.

That patent license covers only the patent claims you own or control that are
necessarily infringed by your contribution alone, or by the combination of your
contribution with the project.

Defensive termination: if any entity files patent litigation against any entity,
including a cross-claim or a counterclaim in a lawsuit, alleging that your
contribution or the project infringes a patent directly or contributorily, then
every patent license granted under this agreement to that entity for that
contribution ends on the date the litigation is filed.

## 4. What you represent

By signing, you state that each of the following is true.

1. Each contribution is your own original creation.
2. You are legally entitled to grant the licenses in sections 2 and 3.
3. Your employer has no rights to this work, or has given you permission to contribute it, waived those rights, or signed this agreement.
4. You know of no third-party license, patent, or agreement that conflicts with what you grant here.

Tell the maintainer in writing if any of those four stops being true.

## 5. Third-party content

If part of a contribution is not your own creation, submit that part separately
from the parts that are. Name its source, its author, its license, and every
restriction the license carries. Mark it in the pull request with a line of this
shape:

```text
Submitted on behalf of a third party: <author>, under <SPDX id>, from <URL>
```

The maintainer needs that line to decide whether the material can enter the
project at all. The dependency license policy in
[CONTRIBUTING.md](CONTRIBUTING.md) decides the answer.

## 6. Support and warranty

You owe the project no support, no bug fixes, and no maintenance for anything
you contribute. Contributing does not make you responsible for it.

Except for the four statements in section 4, you give every contribution "as
is", with no warranty or condition of any kind, express or implied. That
includes any warranty of merchantability, fitness for a particular purpose,
title, and non-infringement.

The maintainer owes you nothing in return except the Apache-2.0 license every
other user gets, and is under no obligation to use, merge, or keep your
contribution.

## 7. How to sign

Two steps, both inside your first pull request.

1. Add one line to [section 8](#8-signatories), at the end of the list.
2. Sign every commit in the pull request with `git commit -s`.

Your signatory line is your GitHub handle, then one space, then the date you
sign, in `YYYY-MM-DD`. It matches this regular expression exactly:

```text
^- @[A-Za-z0-9-]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2}$
```

A worked signatory line:

```text
- @octocat 2026-08-09
```

`git commit -s` writes the `Signed-off-by` trailer from your `user.name` and
`user.email`. A worked commit:

```text
fix(historian): reject a retention window shorter than one shift

BACKEND
- clamp the window at the configured shift length and raise a config error below it
TEST
- add a boundary case at exactly one shift

Signed-off-by: Mona Lisa Octocat <mona@example.com>
```

CI checks three things. A pull request that fails any of them does not merge.

| Check             | What passes                                                                                                    |
| ----------------- | -------------------------------------------------------------------------------------------------------------- |
| Signature present | The pull request author's handle appears in section 8, either already on `main` or added by this pull request. |
| Line shape        | Every signatory line in section 8 matches the regular expression above.                                        |
| Trailer present   | Every commit in the pull request carries a `Signed-off-by` trailer.                                            |

Add your line at the end of the list rather than in the middle, so two open pull
requests do not collide on the same line.

## 8. Signatories

Each line below is one signature. The person named agreed to every section above
on the date shown.

<!-- Add your line at the end of this list. Nothing follows it. -->

## In plain terms

> You keep your copyright. Your work stays yours, and you can reuse it anywhere.
>
> You let Jack ship your contribution under Apache-2.0 and under a commercial
> license, which is what keeps the dual license in LICENSING.md working.
>
> You confirm the work is yours to give, and that no employer or third party has
> an undeclared claim on it.
>
> There is no warranty in either direction. You give the code as is, and you get
> the same Apache-2.0 license every other user gets.

## What this is not

This is not legal advice, and the author is not a lawyer. If your organization
needs a signed paper agreement, or wants its own counsel to read this first, say
so in a [discussion](https://github.com/johnragonhall/twinflow/discussions)
before you open a pull request.
