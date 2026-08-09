---
title: Licensing
description: How twinflow is licensed, what the Apache-2.0 terms ask of you, and when you would want a commercial license instead.
topic_type: reference
audience: users
---

# Licensing

twinflow is dual licensed. Almost everyone uses the first option and owes nothing.

## Option 1: Apache License 2.0

The default. Free for any purpose, including commercial use, with no fee and no
permission needed. The full text is in [LICENSE](LICENSE).

Three obligations come with it, and they are the reason this project uses Apache-2.0
rather than MIT:

| Section    | What it requires                                                                                                                |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 4(a)       | Give recipients a copy of the license.                                                                                          |
| 4(b)       | If you change a file, that file must carry a prominent notice saying you changed it.                                            |
| 4(c), 4(d) | Keep the existing copyright and attribution notices, and carry the contents of [NOTICE](NOTICE) into anything you redistribute. |

Section 4(b) is the one people miss. Renaming the project and removing the author does
not satisfy it. If you fork twinflow and ship your own version, the modified files say
so, and the NOTICE content travels with it.

Apache-2.0 also grants you an explicit patent license under section 3, which MIT does
not. That protects you as much as it protects the author.

## Option 2: A commercial license

You want this only if Apache-2.0's obligations do not fit your situation. Common
reasons:

- You want to redistribute twinflow inside a closed product without carrying the
  attribution notices.
- Your legal department requires a negotiated agreement with a named counterparty
  rather than a public license.
- You want a warranty, an indemnity, or a support commitment. Apache-2.0 explicitly
  provides none of those, and it says so in sections 7 and 8.
- You want to relicense derivative work under terms Apache-2.0 does not permit.

Commercial terms are negotiated per engagement. Contact the maintainer through the
address in [CITATION.cff](CITATION.cff) or by opening a
[GitHub discussion](https://github.com/johnragonhall/twinflow/discussions).

Nothing about the commercial option restricts the Apache-2.0 option. It is an addition,
not a limitation. If Apache-2.0 works for you, use it and ignore this section.

## Contributing, and why there is a contributor agreement

A dual license only works if one party holds the rights to relicense the whole work. If
an outside contribution arrives under Apache-2.0 alone, the maintainer cannot include it
in a commercially licensed copy, and the dual license breaks the first time someone
contributes.

Contributors sign the agreement in [CLA.md](CLA.md) for that reason. It grants the maintainer a
license broad enough to relicense, and it leaves the contributor holding their own
copyright. You keep your work, you can use it anywhere else, and you are not assigning
ownership.

This is the same reason projects like Qt, MongoDB, and Elastic use contributor
agreements. It is not a claim on your code.

## Third-party dependencies

Dependencies must carry a license compatible with Apache-2.0 redistribution. The
dependency policy and the allowlist live in [CONTRIBUTING.md](CONTRIBUTING.md), and CI
checks it on every change.

Apache-2.0 is compatible with MIT, BSD, and ISC dependencies. It is not compatible with
GPLv2. GPLv3 and AGPL dependencies are refused, because they would force the whole work
under terms that break both licensing options above.

## What this is not

This page describes how the project is licensed. It is not legal advice, and the author
is not a lawyer. If the distinction matters to your organization, have your own counsel
read [LICENSE](LICENSE).
