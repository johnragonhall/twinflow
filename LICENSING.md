---
title: Licensing
description: How twinflow is licensed, what the Apache-2.0 terms ask of you, and when you would want a commercial license instead.
topic_type: reference
audience: users
---

# Licensing

twinflow is dual licensed. Almost everyone uses the first option and owes nothing.

## Option 1: Apache License 2.0 <!-- docs-lint-ok HEAD-01 Apache License 2.0 is the license's published name -->

The default. Free for any purpose, including commercial use, with no fee and no
permission needed. The full text is in [LICENSE](LICENSE), and every section number
below is a section of that file.

Three redistribution conditions come with it, and they are the reason this project uses
Apache-2.0 rather than MIT:

| Section | What it asks of a redistributor                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4(a)    | Give any other recipient of the work, or of a derivative work, a copy of the license.                                                                         |
| 4(b)    | Make any modified file carry a prominent notice stating that you changed it.                                                                                  |
| 4(c)    | Retain, in the source form of any derivative work you distribute, the copyright, patent, trademark, and attribution notices from the source form of the work. |
| 4(d)    | Include a readable copy of the attribution notices held in [NOTICE](NOTICE), in the derivative work you distribute.                                           |

Section 4(b) is the one people miss. Renaming the project and removing the author does
not satisfy it. If you fork twinflow and ship your own version, the modified files say
so, and the NOTICE content travels with it.

Apache-2.0 also grants an explicit patent license under section 3, which MIT does not.
That protects you as much as it protects the author.

## Option 2: A commercial license

You want this only if Apache-2.0's obligations do not fit your situation. Common
reasons:

- You want to redistribute twinflow inside a closed product without carrying the
  attribution notices.
- Your legal department requires a negotiated agreement with a named counterparty
  rather than a public license.
- You want a warranty, an indemnity, or a support commitment. Apache-2.0 disclaims
  warranties in section 7 and limits liability in section 8. Section 9 lets a
  redistributor offer such terms on their own behalf, which is what option 2 does.
- You want to relicense derivative work under terms Apache-2.0 does not permit.

Commercial terms are negotiated per engagement. Open a
[GitHub discussion](https://github.com/johnragonhall/twinflow/discussions)
asking for commercial terms, and the maintainer replies with a private route.
Do not put anything confidential in the discussion itself.

Nothing about the commercial option restricts the Apache-2.0 option. It is an addition,
not a limitation. If Apache-2.0 works for you, use it and ignore this section.

## Contributing, and why there is a contributor agreement

A dual license only works if one party holds the rights to relicense the whole work. An
outside contribution that arrives under Apache-2.0 alone cannot go into a commercially
licensed copy. The dual license then breaks the first time someone contributes.

Contributors sign the agreement in [CLA.md](CLA.md) for that reason. It grants the maintainer a
license broad enough to relicense, and it leaves the contributor holding their own
copyright. You keep your work, you can use it anywhere else, and you are not assigning
ownership.

The Qt Project takes the same shape of agreement, and publishes the same limit on it:

> the contributor retains ownership of the contribution as the Qt Project does not
> require copyright assignment for contributions made to the Qt Project <!-- docs-lint-ok STE-TERM-WORD verbatim quotation from qt.io, not editable prose -->

Source: <https://www.qt.io/contributionagreement>, retrieved 2026-08-09. A contributor
agreement is a license grant. It is not a claim on your code.

## Third-party dependencies

Dependencies must carry a license compatible with Apache-2.0 redistribution. The
dependency policy and the allowlist live in [CONTRIBUTING.md](CONTRIBUTING.md), which
also states how the allowlist is checked today and which milestone automates it.

Apache-2.0 is compatible with MIT, BSD, and ISC dependencies. It is not compatible with
GPLv2. GPLv3 and AGPL-3.0 dependencies are refused, because they would force the whole
work under terms that break both licensing options above. MPL-2.0 is accepted for a
development dependency and refused for one shipped at run time, and CONTRIBUTING.md
gives the reasoning for that split.

## What this is not

This page describes how the project is licensed. It is not legal advice, and the author
is not a lawyer. If the distinction matters to your organization, have your own counsel
read [LICENSE](LICENSE).
